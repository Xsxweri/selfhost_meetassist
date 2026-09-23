import asyncio
import uuid

from sqlalchemy import select

from app.workers.celery_app import celery
from app.db.session import AsyncSessionLocal
from app.curd.action_item import replace_action_items
from app.models.meeting import Meeting
from app.services.llm_service import LlmService


async def _run_generate_summary(meeting_id: str) -> dict:
    """在独立事件循环 + 独立会话中生成并落库纪要"""
    mid = uuid.UUID(meeting_id)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Meeting).where(Meeting.id == mid, Meeting.deleted_at.is_(None))
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            return {"status": "meeting_not_found"}

        data = await LlmService(db).generate_summary(meeting_id)
        summary_text = (data.get("summary") or "").strip()
        key_points = data.get("key_points") or []
        if key_points:
            summary_text = (
                summary_text + "\n\n要点：\n" + "\n".join(f"- {k}" for k in key_points)
            ).strip()

        meeting.summary = summary_text
        items = await replace_action_items(db, meeting_id, data.get("action_items", []))
        return {
            "status": "ok",
            "summary": summary_text,
            "action_item_count": len(items),
        }


@celery.task(name="generate_summary", bind=True)
def generate_summary_task(self, meeting_id: str):
    """异步生成会议纪要（Celery 任务，Windows 需 --pool=solo）"""
    return asyncio.run(_run_generate_summary(meeting_id))