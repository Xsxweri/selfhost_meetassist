import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.curd.meeting import (
    create_meeting,
    delete_meeting,
    get_meeting,
    list_meetings,
    restore_meeting,
    update_meeting,
)
from app.curd.consent import create_consent
from app.curd.audit_log import record_event
from app.models.consent import ConsentAction, ConsentType
from app.models.audit_log import AuditAction
from app.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingResponse, MeetingUpdate

router = APIRouter(prefix="/meetings", tags=["Meetings"])

# ========= 创建会议 =========
@router.post("", response_model=MeetingResponse, status_code=201)
async def api_create_meeting(
    meeting_in: MeetingCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = await create_meeting(db, meeting_in, owner_id=current_user.id)
    await record_event(
        db,
        action=AuditAction.MEETING_CREATE.value,
        user_id=current_user.id,
        meeting_id=meeting.id,
        resource="meeting",
        detail={"title": meeting.title},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return meeting

# ========= 列出会议 =========
@router.get("", response_model=list[MeetingResponse])
async def api_list_meetings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await list_meetings(db, skip=skip, limit=limit, owner_id=current_user.id)

# ========= 获取会议 =========
@router.get("/{meeting_id}", response_model=MeetingResponse)
async def api_get_meeting(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = await get_meeting(db, meeting_id, owner_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting

# ========= 更新会议 =========
@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def api_update_meeting(
    meeting_id: uuid.UUID,
    meeting_in: MeetingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = await get_meeting(db, meeting_id, owner_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return await update_meeting(db, meeting, meeting_in)

# ========= 删除会议 =========
@router.delete("/{meeting_id}", status_code=204)
async def api_delete_meeting(
    meeting_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = await get_meeting(db, meeting_id, owner_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    # 删除即撤回录音授权（append-only 留痕）
    await create_consent(
        db,
        meeting_id=meeting.id,
        user_id=current_user.id,
        consent_type=ConsentType.RECORDING,
        action=ConsentAction.REVOKE,
        ip_address=ip,
        user_agent=ua,
        note="auto-revoked on meeting deletion",
    )
    await record_event(
        db,
        action=AuditAction.CONSENT_REVOKE.value,
        user_id=current_user.id,
        meeting_id=meeting.id,
        resource="consent",
        detail={"consent_type": ConsentType.RECORDING.value, "auto": True},
        ip_address=ip,
        user_agent=ua,
    )
    # 软删除
    await delete_meeting(db, meeting)
    await record_event(
        db,
        action=AuditAction.MEETING_DELETE.value,
        user_id=current_user.id,
        meeting_id=meeting.id,
        resource="meeting",
        ip_address=ip,
        user_agent=ua,
    )

# ========= 恢复会议 =========
@router.post("/{meeting_id}/restore", response_model=MeetingResponse)
async def api_restore_meeting(
    meeting_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = await get_meeting(db, meeting_id, owner_id=current_user.id, include_deleted=True)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    await restore_meeting(db, meeting)
    await record_event(
        db,
        action=AuditAction.MEETING_RESTORE.value,
        user_id=current_user.id,
        meeting_id=meeting.id,
        resource="meeting",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return meeting