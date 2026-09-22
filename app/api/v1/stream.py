import asyncio
import json
import uuid

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.curd.consent import get_consent_status
from app.curd.meeting import get_meeting
from app.curd.user import get_user_by_id
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.asr import get_asr
from app.services.asr_service import AsrService

router = APIRouter(tags=["Stream"])
settings = get_settings()

# 16-bit 单声道：每秒字节数
BYTES_PER_SECOND = settings.ASR_SAMPLE_RATE * 2


async def _authenticate(ws: WebSocket) -> User | None:
    token = ws.query_params.get("token")
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        return None
    async with AsyncSessionLocal() as db:
        return await get_user_by_id(db, user_id)


async def _check_recording_consent(db: AsyncSession, meeting_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    status_list = await get_consent_status(db, meeting_id, user_id)
    return next((s["granted"] for s in status_list if s["consent_type"] == "recording"), False)


async def _flush(ws: WebSocket, asr, buffer: bytearray, offset: float, meeting_id: uuid.UUID) -> float:
    """转写当前缓冲：回推字幕 + 落库，返回新的时间偏移"""
    if not buffer:
        return offset
    audio = np.frombuffer(bytes(buffer), dtype=np.int16).astype(np.float32) / 32768.0
    duration = len(audio) / settings.ASR_SAMPLE_RATE
    segments = await asyncio.to_thread(asr.transcribe, audio, settings.ASR_SAMPLE_RATE)

    for seg in segments:
        seg["start"] = round(seg["start"] + offset, 3)
        seg["end"] = round(seg["end"] + offset, 3)
        seg.setdefault("speaker", "SPEAKER_00")

    if segments:
        await ws.send_json({"type": "subtitle", "segments": segments})
        try:
            async with AsyncSessionLocal() as db:
                await AsrService(db).process_asr_result(meeting_id, segments)
        except Exception as exc:  # 落库/向量失败不阻断实时字幕
            await ws.send_json({"type": "warning", "detail": f"persist failed: {exc}"})

    buffer.clear()
    return offset + duration


@router.websocket("/meetings/{meeting_id}/stream")
async def meeting_stream(websocket: WebSocket, meeting_id: uuid.UUID):
    user = await _authenticate(websocket)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    # 归属 + 录音授权校验
    async with AsyncSessionLocal() as db:
        meeting = await get_meeting(db, meeting_id, user.id)
        if not meeting:
            await websocket.send_json({"type": "error", "detail": "Meeting not found"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        if not await _check_recording_consent(db, meeting_id, user.id):
            await websocket.send_json({"type": "error", "detail": "Recording consent required"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    asr = get_asr()
    buffer = bytearray()
    offset = 0.0
    await websocket.send_json({"type": "ready", "sample_rate": settings.ASR_SAMPLE_RATE})

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            if (data := message.get("bytes")) is not None:
                buffer.extend(data)
                if len(buffer) >= BYTES_PER_SECOND * settings.ASR_FLUSH_SECONDS:
                    offset = await _flush(websocket, asr, buffer, offset, meeting_id)

            elif (text := message.get("text")) is not None:
                try:
                    ctrl = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if ctrl.get("type") == "flush":
                    offset = await _flush(websocket, asr, buffer, offset, meeting_id)
                elif ctrl.get("type") == "end":
                    offset = await _flush(websocket, asr, buffer, offset, meeting_id)
                    await websocket.send_json({"type": "end", "duration": round(offset, 3)})
                    break
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "detail": f"{type(exc).__name__}: {exc}"})
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass