import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def record_event(
    db: AsyncSession,
    *,
    action: str,
    user_id: uuid.UUID | None = None,
    meeting_id: uuid.UUID | None = None,
    resource: str | None = None,
    detail: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """追加一条审计事件（append-only）"""
    log = AuditLog(
        user_id=user_id,
        meeting_id=meeting_id,
        action=action,
        resource=resource,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def list_audit_logs(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    meeting_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[AuditLog]:
    stmt = select(AuditLog)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if meeting_id is not None:
        stmt = stmt.where(AuditLog.meeting_id == meeting_id)
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())