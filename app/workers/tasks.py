import asyncio
import uuid

from sqlalchemy import select

from app.workers.celery_app import celery
from app.db.session import AsyncSessionLocal
from app.curd import memory as memory_crud
from app.curd.action_item import replace_action_items
from app.models.meeting import Meeting
from app.services.llm_service import LlmService
from app.services.memory_service import MemoryService


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


@celery.task(name="generate_summary", bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=600, retry_jitter=True, max_retries=3)
def generate_summary_task(self, meeting_id: str):
    """异步生成会议纪要（Celery 任务，Windows 需 --pool=solo）"""
    result = asyncio.run(_run_generate_summary(meeting_id))

    if isinstance(result, dict) and result.get("status") == "ok":
        try:
            extract_memories_task.delay(meeting_id)
        except Exception:
            pass
    return result


async def _run_extract_memories(meeting_id: str) -> dict:
    """在独立事件循环 + 独立会话中抽取长期记忆"""
    async with AsyncSessionLocal() as db:
        return await MemoryService(db).ingest_from_meeting(uuid.UUID(meeting_id))


@celery.task(
    name="extract_memories",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3
)
def extract_memories_task(meeting_id: str):
    """异步抽取长期记忆（Celery 任务，Windows 需 --pool=solo）"""
    return asyncio.run(_run_extract_memories(meeting_id))


async def _run_archive_superseded(before_days: int) -> dict:
    """在独立事件循环 + 独立会话中归档过时的记忆"""
    async with AsyncSessionLocal() as db:
        n = await memory_crud.archive_superseded(db, before_days=before_days)
        return {"archived_count": n}


@celery.task(name="archive_superseded_memories")
def archive_superseded_task(before_days: int = 90):
    """周期归档超期演进链记忆，防表膨胀（Celery beat 触发，Windows 需 --pool=solo）"""
    return asyncio.run(_run_archive_superseded(before_days))

