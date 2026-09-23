import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem, ActionItemPriority, ActionItemStatus


async def replace_action_items(
    db: AsyncSession, meeting_id: uuid.UUID, items: list[dict]
) -> list[ActionItem]:
    """幂等重写某会议待办：先删旧的全部，再插入新生成的"""
    await db.execute(delete(ActionItem).where(ActionItem.meeting_id == meeting_id))
    objs = []
    for it in items:
        obj = ActionItem(
            meeting_id=meeting_id,
            content=it["content"],
            assignee=it.get("assignee"),
            due_date=it.get("due_date"),
            priority=it.get("priority") or ActionItemPriority.MEDIUM.value,
            status=ActionItemStatus.PENDING.value,
            source_start=it.get("source_start"),
            source_end=it.get("source_end"),
        )
        db.add(obj)
        objs.append(obj)
    await db.commit()
    for obj in objs:
        await db.refresh(obj)
    return objs


async def list_action_items(db: AsyncSession, meeting_id: uuid.UUID) -> list[ActionItem]:
    result = await db.execute(
        select(ActionItem)
        .where(ActionItem.meeting_id == meeting_id)
        .order_by(ActionItem.created_at)
    )
    return list(result.scalars().all())


async def get_action_item(
    db: AsyncSession, meeting_id: uuid.UUID, item_id: uuid.UUID
) -> ActionItem | None:
    result = await db.execute(
        select(ActionItem).where(
            ActionItem.id == item_id, ActionItem.meeting_id == meeting_id
        )
    )
    return result.scalar_one_or_none()


async def update_action_item(db: AsyncSession, item: ActionItem, data: dict) -> ActionItem:
    for field, value in data.items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


async def delete_action_item(db: AsyncSession, item: ActionItem) -> None:
    await db.delete(item)
    await db.commit()