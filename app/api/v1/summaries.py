import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.curd.meeting import get_meeting
from app.curd.audit_log import record_event
from app.models.audit_log import AuditAction
from app.curd.action_item import (
    delete_action_item,
    get_action_item,
    list_action_items,
    replace_action_items,
    update_action_item,
)
from app.models.user import User
from app.schemas.action_item import (
    ActionItemResponse,
    ActionItemUpdate,
    SummaryResponse,
)
from app.services.llm_service import LlmService
from app.workers.tasks import generate_summary_task

router = APIRouter(prefix="/meetings", tags=["Summaries"])


async def _ensure_owned_meeting(db: AsyncSession, meeting_id: uuid.UUID, current_user: User):
    meeting = await get_meeting(db, meeting_id, current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.post("/{meeting_id}/summary", response_model=SummaryResponse)
async def api_generate_summary(
    meeting_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成结构化纪要 + 待办，并持久化（幂等重写待办）"""
    meeting = await _ensure_owned_meeting(db, meeting_id, current_user)
    data = await LlmService(db).generate_summary(meeting_id)

    summary_text = (data.get("summary") or "").strip()
    key_points = data.get("key_points") or []
    if key_points:
        summary_text = (
            summary_text + "\n\n要点：\n" + "\n".join(f"- {k}" for k in key_points)
        ).strip()

    meeting.summary = summary_text  # 随下方 commit 一并落库
    items = await replace_action_items(db, meeting_id, data.get("action_items", []))
    await record_event(
        db,
        action=AuditAction.SUMMARY_GENERATE.value,
        user_id=current_user.id,
        meeting_id=meeting_id,
        resource="summary",
        detail={"action_item_count": len(items)},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return SummaryResponse(meeting_id=meeting_id, summary=summary_text, action_items=items)


@router.post("/{meeting_id}/summary/async", status_code=202)
async def api_generate_summary_async(
    meeting_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """把纪要生成丢进 Celery 队列，立即返回 task_id（不阻塞请求）"""
    await _ensure_owned_meeting(db, meeting_id, current_user)
    task = generate_summary_task.delay(str(meeting_id))
    await record_event(
        db,
        action=AuditAction.SUMMARY_GENERATE.value,
        user_id=current_user.id,
        meeting_id=meeting_id,
        resource="summary",
        detail={"async": True, "task_id": task.id},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"task_id": task.id, "status": "PENDING"}


@router.get("/{meeting_id}/summary", response_model=SummaryResponse)
async def api_get_summary(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """读取已保存的纪要与待办"""
    meeting = await _ensure_owned_meeting(db, meeting_id, current_user)
    items = await list_action_items(db, meeting_id)
    return SummaryResponse(meeting_id=meeting_id, summary=meeting.summary, action_items=items)


@router.get("/{meeting_id}/action-items", response_model=list[ActionItemResponse])
async def api_list_action_items(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _ensure_owned_meeting(db, meeting_id, current_user)
    return await list_action_items(db, meeting_id)


@router.patch("/{meeting_id}/action-items/{item_id}", response_model=ActionItemResponse)
async def api_update_action_item(
    meeting_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ActionItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑/确认待办（如改 status=confirmed）"""
    await _ensure_owned_meeting(db, meeting_id, current_user)
    item = await get_action_item(db, meeting_id, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    return await update_action_item(db, item, payload.model_dump(exclude_unset=True))


@router.delete("/{meeting_id}/action-items/{item_id}", status_code=204)
async def api_delete_action_item(
    meeting_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _ensure_owned_meeting(db, meeting_id, current_user)
    item = await get_action_item(db, meeting_id, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    await delete_action_item(db, item)