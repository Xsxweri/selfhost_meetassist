import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.curd.meeting import get_meeting
from app.curd.action_item import list_action_items
from app.curd.audit_log import record_event
from app.models.audit_log import AuditAction
from app.models.transcript import Transcript
from app.models.user import User
from app.services import export_service

router = APIRouter(prefix="/meetings/{meeting_id}/export", tags=["Exports"])


# ========= 导出会议内容 ==========
@router.get("")
async def api_export(
    meeting_id: uuid.UUID,
    request: Request,
    format: str = Query("md", pattern="^(md|json|docx|pdf)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = await get_meeting(db, meeting_id, owner_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    items = await list_action_items(db, meeting_id)
    res = await db.execute(
        select(Transcript).where(Transcript.meeting_id == meeting_id).order_by(Transcript.created_at)
    )
    transcripts = list(res.scalars().all())
    content, media, ext = export_service.build(format, meeting, items, transcripts)
    await record_event(
        db, action=AuditAction.EXPORT.value, user_id=current_user.id,
        meeting_id=meeting_id, resource="export", detail={"format": format},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return Response(
        content=content, media_type=media,
        headers={"Content-Disposition": f'attachment; filename="meeting_{meeting_id}{ext}"'},
    )