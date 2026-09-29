import logging
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.curd import memory as memory_crud
from app.curd.audit_log import record_event
from app.models.audit_log import AuditAction
from app.models.meeting import Meeting
from app.models.memory import MemoryKind
from app.services.llm_service import LlmService

logger = logging.getLogger(__name__)
settings = get_settings()

_VALID_KINDS = {k.value for k in MemoryKind}
_MAX_CANDIDATES = 20      # 单次抽取上限，防 LLM 爆量
_MAX_INPUT_CHARS = 8000   # 喂给抽取器的文本上限


def _clamp_importance(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, f))


def _rrf(rank_lists: list[list[dict]], k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion：融合多路排名，score = Σ 1/(k + rank)"""
    scores: dict = {}
    meta: dict = {}
    for rl in rank_lists:
        for rank, hit in enumerate(rl):
            hid = hit["id"]
            scores[hid] = scores.get(hid, 0.0) + 1.0 / (k + rank + 1)
            meta.setdefault(hid, hit)
    fused = []
    for hid, sc in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        row = dict(meta[hid])
        row["score"] = round(sc, 6)
        fused.append(row)
    return fused


class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LlmService(db)

    async def ingest_from_meeting(
        self, meeting_id: uuid.UUID, *, source: str = "auto_extract"
    ) -> dict:
        """从会议纪要/转录抽取长期记忆：逐条 embedding → 去重/演进 → 落库 → 审计"""
        db = self.db
        if not settings.MEMORY_ENABLED:
            return {"ok": True, "skipped": "disabled", "created": 0, "superseded": 0}

        m = await db.get(Meeting, meeting_id)
        if not m or not m.owner_id:
            return {"ok": False, "error": "meeting not found or unowned", "created": 0, "superseded": 0}

        text = "\n\n".join(x for x in [m.summary, m.transcript] if x).strip()
        if not text:
            return {"ok": True, "skipped": "no content", "created": 0, "superseded": 0}

        candidates = await self.llm.extract_memories(text[:_MAX_INPUT_CHARS])
        created = superseded = 0

        for c in candidates[:_MAX_CANDIDATES]:
            content = (c.get("content") or "").strip()
            if not content:
                continue
            kind = c.get("kind") if c.get("kind") in _VALID_KINDS else MemoryKind.FACT.value
            subject = (c.get("subject") or None)
            importance = _clamp_importance(c.get("importance"))

            emb = await self.llm._get_embedding(content)

            # 去重/演进：同 owner（可选同 subject）高相似 → 视为同一事实的新版本
            similar = []
            if emb:
                similar = await memory_crud.find_similar(
                    db, owner_id=m.owner_id, embedding=emb, limit=1,
                    min_similarity=settings.MEMORY_SIM_THRESHOLD,
                )

            new = await memory_crud.create_memory(
                db, owner_id=m.owner_id, content=content, kind=kind, subject=subject,
                meeting_id=m.id, embedding=emb, importance=importance,
            )
            created += 1

            if similar:
                old = await memory_crud.get_memory(db, similar[0]["id"], m.owner_id)
                if old:
                    await memory_crud.supersede_memory(db, old, new.id)
                    superseded += 1
                    await record_event(
                        db, action=AuditAction.MEMORY_SUPERSEDE.value,
                        user_id=m.owner_id, meeting_id=m.id, resource="memory",
                        detail={"old": str(old.id), "new": str(new.id), "subject": subject},
                    )

            await record_event(
                db, action=AuditAction.MEMORY_WRITE.value,
                user_id=m.owner_id, meeting_id=m.id, resource="memory",
                detail={"memory_id": str(new.id), "kind": kind, "subject": subject, "source": source},
            )

        logger.info("memory ingest meeting=%s created=%d superseded=%d", meeting_id, created, superseded)
        return {"ok": True, "created": created, "superseded": superseded}

    async def recall(
            self,
            query: str,
            owner_id: uuid.UUID,
            *,
            kind: str | None = None,
            subject: str | None = None,
            since: datetime | None = None,
            limit: int | None = None,
    ) -> list[dict]:
        """统一召回：向量(bge-m3) + 关键词(pg_trgm) 双路 → RRF 融合，全程 owner 隔离"""
        db = self.db
        limit = limit or settings.MEMORY_TOP_K
        q = (query or "").strip()
        if not q:
            return []

        qvec = await self.llm._get_embedding(q)
        vec_hits = []
        if qvec:
            vec_hits = await memory_crud.find_similar(
                db, owner_id=owner_id, embedding=qvec, limit=limit * 2,
                min_similarity=settings.MEMORY_RECALL_MIN_SIM,
                kind=kind, subject=subject, since=since,
            )
        kw_hits = []
        if settings.MEMORY_HYBRID:
            kw_hits = await memory_crud.search_by_keyword(
                db, owner_id=owner_id, query=q, limit=limit * 2,
                kind=kind, subject=subject, since=since,
            )
        return _rrf([vec_hits, kw_hits])[:limit]