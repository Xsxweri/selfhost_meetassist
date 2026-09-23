import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.curd.meeting import get_meeting, get_active_meeting_by_id
from app.curd.action_item import list_action_items
from app.curd.share_link import (
    create_share_link,
    list_share_links,
    get_share_link_by_token,
    revoke_share_link,
    is_link_active,
)
from app.curd.audit_log import record_event
from app.models.audit_log import AuditAction
from app.models.transcript import Transcript
from app.models.user import User
from app.schemas.share_link import ShareLinkCreate, ShareLinkResponse, SharedMeetingResponse
from app.services import export_service

router = APIRouter(prefix="/meetings/{meeting_id}/shares", tags=["Shares"])
public_router = APIRouter(prefix="/shared", tags=["Shares"])


async def _ensure_owned_meeting(db: AsyncSession, meeting_id: uuid.UUID, current_user: User):
    """确保会议属于当前用户"""
    meeting = await get_meeting(db, meeting_id, current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


async def _load_items_and_texts(db: AsyncSession, meeting_id: uuid.UUID):
    """加载议程项和文字内容"""
    items = await list_action_items(db, meeting_id)
    res = await db.execute(
        select(Transcript).where(Transcript.meeting_id == meeting_id).order_by(Transcript.created_at)
    )
    return items, list(res.scalars().all())


@router.post("", response_model=ShareLinkResponse, status_code=201)
async def api_create_share(
    meeting_id: uuid.UUID,
    payload: ShareLinkCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建分享链接"""
    await _ensure_owned_meeting(db, meeting_id, current_user)
    link = await create_share_link(
        db, meeting_id=meeting_id, created_by=current_user.id,
        allow_download=payload.allow_download, expires_in_days=payload.expires_in_days,
    )
    await record_event(
        db, action=AuditAction.SHARE_CREATE.value, user_id=current_user.id,
        meeting_id=meeting_id, resource="share",
        detail={"allow_download": payload.allow_download, "expires_in_days": payload.expires_in_days},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return link


@router.get("", response_model=list[ShareLinkResponse])
async def api_list_shares(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出分享链接"""
    await _ensure_owned_meeting(db, meeting_id, current_user)
    return await list_share_links(db, meeting_id)


@router.delete("/{token}", response_model=ShareLinkResponse)
async def api_revoke_share(
    meeting_id: uuid.UUID,
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """撤销分享链接"""
    await _ensure_owned_meeting(db, meeting_id, current_user)
    link = await get_share_link_by_token(db, token)
    if not link or link.meeting_id != meeting_id:
        raise HTTPException(status_code=404, detail="Share link not found")
    link = await revoke_share_link(db, link)
    await record_event(
        db, action=AuditAction.SHARE_REVOKE.value, user_id=current_user.id,
        meeting_id=meeting_id, resource="share", detail={"token": token},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return link


@public_router.get("/{token}", response_model=SharedMeetingResponse)
async def api_shared_meeting(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    """公开只读访问，无需鉴权，凭 token"""
    link = await get_share_link_by_token(db, token)
    if not link or not is_link_active(link):
        raise HTTPException(status_code=404, detail="Share link invalid or expired")
    meeting = await get_active_meeting_by_id(db, link.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not available")
    items, transcripts = await _load_items_and_texts(db, meeting.id)
    await record_event(
        db, action=AuditAction.SHARE_ACCESS.value, meeting_id=meeting.id,
        resource="share", detail={"token": token},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return SharedMeetingResponse(
        title=meeting.title, summary=meeting.summary, created_at=meeting.created_at,
        allow_download=link.allow_download, action_items=items,
        transcripts=[t.text for t in transcripts if t.text],
    )


@public_router.get("/{token}/export")
async def api_shared_export(
    token: str,
    request: Request,
    format: str = Query("md", pattern="^(md|json|docx|pdf)$"),
    db: AsyncSession = Depends(get_db),
):
    """分享链接下载（需 allow_download=True）"""
    link = await get_share_link_by_token(db, token)
    if not link or not is_link_active(link):
        raise HTTPException(status_code=404, detail="Share link invalid or expired")
    if not link.allow_download:
        raise HTTPException(status_code=403, detail="Download disabled for this share link")
    meeting = await get_active_meeting_by_id(db, link.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not available")
    items, transcripts = await _load_items_and_texts(db, meeting.id)
    content, media, ext = export_service.build(format, meeting, items, transcripts)
    return Response(
        content=content, media_type=media,
        headers={"Content-Disposition": f'attachment; filename="meeting_{meeting.id}{ext}"'},
    )