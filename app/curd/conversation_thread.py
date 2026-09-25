import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation_thread import ConversationThread


async def get_thread(db: AsyncSession, thread_id: str) -> ConversationThread | None:
    return await db.get(ConversationThread, thread_id)


async def upsert_thread(
    db: AsyncSession, *, thread_id: str, owner_id: uuid.UUID, title: str | None = None
) -> ConversationThread:
    """存在则刷新活跃时间，不存在则创建（title 只首次写入）"""
    thread = await db.get(ConversationThread, thread_id)
    if thread:
        thread.last_active_at = datetime.now(timezone.utc)
        if title and not thread.title:
            thread.title = title
        await db.commit()
        await db.refresh(thread)
        return thread
    thread = ConversationThread(thread_id=thread_id, owner_id=owner_id, title=title)
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


async def bump_turn(
    db: AsyncSession, thread: ConversationThread, *, new_summary: str | None = None
) -> ConversationThread:
    thread.turn_count = (thread.turn_count or 0) + 1
    thread.last_active_at = datetime.now(timezone.utc)
    if new_summary is not None:
        thread.rolling_summary = new_summary
    await db.commit()
    await db.refresh(thread)
    return thread


async def list_threads(
    db: AsyncSession, owner_id: uuid.UUID, *, limit: int = 50
) -> list[ConversationThread]:
    stmt = (
        select(ConversationThread)
        .where(ConversationThread.owner_id == owner_id)
        .order_by(ConversationThread.last_active_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())