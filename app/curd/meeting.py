import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreate, MeetingUpdate


async def create_meeting(db: AsyncSession, meeting_in: MeetingCreate, owner_id: uuid.UUID) -> Meeting:
    """"""
    meeting = Meeting(**meeting_in.model_dump(), owner_id=owner_id)
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    return meeting


async def get_meeting(db: AsyncSession, meeting_id: uuid.UUID, owner_id: uuid.UUID, include_deleted: bool = False
) -> Meeting | None:
    """按 id 取会议"""
    stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.owner_id == owner_id)
    if not include_deleted:
        stmt = stmt.where(Meeting.deleted_at.is_(None))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_meetings(db: AsyncSession, owner_id: uuid.UUID, skip: int = 0, limit: int = 20) -> list[Meeting]:
    """列出会议"""
    result = await db.execute(
        select(Meeting)
        .where(Meeting.owner_id == owner_id, Meeting.deleted_at.is_(None))
        .order_by(Meeting.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_meeting(db: AsyncSession, meeting: Meeting, meeting_in: MeetingUpdate) -> Meeting:
    """更新会议"""
    update_data = meeting_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(meeting, field, value)
    await db.commit()
    await db.refresh(meeting)
    return meeting


async def get_active_meeting_by_id(db: AsyncSession, meeting_id: uuid.UUID) -> Meeting | None:
    """按 id 取未删除会议（供公开分享访问，不校验归属）"""
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def delete_meeting(db: AsyncSession, meeting: Meeting) -> Meeting:
    """软删除：仅打删除时间戳，数据保留以便合规审计与恢复"""
    meeting.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(meeting)
    return meeting


async def restore_meeting(db: AsyncSession, meeting: Meeting) -> Meeting:
    """恢复被软删除的会议"""
    meeting.deleted_at = None
    await db.commit()
    await db.refresh(meeting)
    return meeting