import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.curd.audit_log import record_event
from app.curd.memory import (
    get_memory,
    get_memory_chain,
    list_memories,
    soft_delete_memory,
    update_memory,
)
from app.models.audit_log import AuditAction
from app.models.user import User
from app.schemas.memory import MemoryResponse, MemoryUpdate

router = APIRouter(prefix="/memories", tags=["Memories"])

_KIND_PATTERN = "^(decision|action|preference|fact|entity)$"


@router.get("", response_model=list[MemoryResponse])
async def api_list_memories(
    kind: str | None = Query(None, pattern=_KIND_PATTERN),
    subject: str | None = None,
    include_superseded: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出当前用户的记忆"""
    return await list_memories(
        db, current_user.id, kind=kind, subject=subject,
        include_superseded=include_superseded, skip=skip, limit=limit,
    )


@router.get("/{memory_id}", response_model=MemoryResponse)
async def api_get_memory(
    memory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单条记忆详情"""
    mem = await get_memory(db, memory_id, current_user.id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    return mem


@router.patch("/{memory_id}", response_model=MemoryResponse)
async def api_update_memory(
    memory_id: uuid.UUID,
    payload: MemoryUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑记忆可变字段（kind/subject/content/importance）"""
    mem = await get_memory(db, memory_id, current_user.id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    updated = await update_memory(db, mem, **fields)
    await record_event(
        db,
        action=AuditAction.MEMORY_WRITE.value,
        user_id=current_user.id,
        meeting_id=mem.meeting_id,
        resource="memory",
        detail={"memory_id": str(memory_id), "op": "update", "fields": list(fields.keys())},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return updated


@router.delete("/{memory_id}", status_code=204)
async def api_delete_memory(
    memory_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """软删除记忆"""
    mem = await get_memory(db, memory_id, current_user.id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    await soft_delete_memory(db, mem)
    await record_event(
        db,
        action=AuditAction.MEMORY_WRITE.value,
        user_id=current_user.id,
        meeting_id=mem.meeting_id,
        resource="memory",
        detail={"memory_id": str(memory_id), "op": "soft_delete"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return None


@router.get("/{memory_id}/chain", response_model=list[MemoryResponse])
async def api_memory_chain(
    memory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查看记忆完整演进链（最旧→最新，含被取代的历史版本）"""
    chain = await get_memory_chain(db, memory_id, current_user.id)
    if not chain:
        raise HTTPException(status_code=404, detail="Memory not found")
    return chain
