import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.curd.consent import create_consent, get_consent_status, list_consents
from app.curd.meeting import get_meeting
from app.curd.audit_log import record_event
from app.models.consent import ConsentAction
from app.models.audit_log import AuditAction
from app.models.user import User
from app.schemas.consent import ConsentCreate, ConsentResponse, ConsentStatus

router = APIRouter(prefix="/meetings/{meeting_id}/consents", tags=["Consents"])

async def _ensure_owned_meeting(
    db: AsyncSession, meeting_id: uuid.UUID, current_user: User
):
    """确认会议存在且属于当前用户"""
    meeting = await get_meeting(db, meeting_id, current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.post("", response_model=ConsentResponse, status_code=201)
async def api_grant_or_revoke(
    meeting_id: uuid.UUID,
    payload: ConsentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建授权事件路由"""
    await _ensure_owned_meeting(db, meeting_id, current_user)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    consent = await create_consent(
        db,
        meeting_id=meeting_id,
        user_id=current_user.id,
        consent_type=payload.consent_type,
        action=payload.action,
        ip_address=ip,
        user_agent=ua,
        note=payload.note,
    )
    await record_event(
        db,
        action=(
            AuditAction.CONSENT_REVOKE.value
            if payload.action == ConsentAction.REVOKE
            else AuditAction.CONSENT_GRANT.value
        ),
        user_id=current_user.id,
        meeting_id=meeting_id,
        resource="consent",
        detail={"consent_type": payload.consent_type.value, "note": payload.note},
        ip_address=ip,
        user_agent=ua,
    )
    return consent


@router.get("", response_model=list[ConsentResponse])
async def api_list_consents(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取授权事件列表路由"""
    await _ensure_owned_meeting(db, meeting_id, current_user)
    return await list_consents(db, meeting_id, current_user.id)


@router.get("/status", response_model=list[ConsentStatus])
async def api_consent_status(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前授权状态路由"""
    await _ensure_owned_meeting(db, meeting_id, current_user)
    return await get_consent_status(db, meeting_id, current_user.id)