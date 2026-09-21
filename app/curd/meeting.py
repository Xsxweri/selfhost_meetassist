import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreate, MeetingUpdate

async def create_meeting(db: AsyncSession, meeting_in: MeetingCreate, owner_id: uuid.UUID) -> Meeting:
    meeting = Meeting(**meeting_in.model_dump(), owner_id=owner_id)
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    return meeting

async def get_meeting(db: AsyncSession, meeting_id: uuid.UUID, owner_id: uuid.UUID) -> Meeting | None:
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id, Meeting.owner_id == owner_id))
    return result.scalar_one_or_none()

async def list_meetings(db: AsyncSession, owner_id: uuid.UUID, skip: int = 0, limit: int = 20) -> list[Meeting]:
    result = await db.execute(
        select(Meeting)
        .where(Meeting.owner_id == owner_id)
        .order_by(Meeting.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())

async def update_meeting(db: AsyncSession, meeting: Meeting, meeting_in: MeetingUpdate) -> Meeting:
    update_data = meeting_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(meeting, field, value)
    await db.commit()
    await db.refresh(meeting)
    return meeting

async def delete_meeting(db: AsyncSession, meeting: Meeting) -> None:
    await db.delete(meeting)
    await db.commit()