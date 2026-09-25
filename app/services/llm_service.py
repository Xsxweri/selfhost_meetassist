import json
import httpx
from datetime import datetime
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transcript import Transcript
from app.core.config import get_settings
from app.core.prompts import render_prompt

settings = get_settings()
_CODE_FENCE = "`" * 3
_NULLISH = {"", "null", "none", "无", "n/a"}

class LlmService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== 纪要与待办 ====================
    async def generate_summary(self, meeting_id: str) -> dict:
        """生成结构化纪要 + 待办事项"""
        stmt = select(Transcript.text).where(
            Transcript.meeting_id == meeting_id
        ).order_by(Transcript.created_at)
        result = await self.db.execute(stmt)
        contents = [row[0] for row in result.fetchall() if row[0]]

        if not contents:
            return {"summary": "暂无转录内容", "key_points": [], "action_items": []}

        prompt = render_prompt("meeting_summary",  transcript="\n".join(contents))
        raw = await self._call_llm(prompt)
        return self._parse_summary(raw)

    @staticmethod
    def _parse_due(value) -> datetime | None:
        """解析 due_date"""
        if not isinstance(value, str):
            return None
        v = value.strip()
        if v.lower() in _NULLISH:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(v, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _clean_str(value) -> str | None:
        """清理字符串，如果为空则返回 None"""
        if not isinstance(value, str):
            return None
        v = value.strip()
        return None if v.lower() in _NULLISH else v

    @staticmethod
    def _parse_summary(raw: str) -> dict:
        """解析 LLM 返回的 JSON，带容错"""
        cleaned = raw.strip()
        if cleaned.startswith(_CODE_FENCE):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        try:
            data = json.loads(cleaned)
        except (json.JSONDecodeError, AttributeError):
            # 解析失败时，退化为把原始文本作为 summary
            return {"summary": raw, "key_points": [], "action_items": []}

        items = []
        for it in (data.get("action_items") or []):
            if isinstance(it, str):
                it = {"content": it}
            if not isinstance(it, dict):
                continue
            content = LlmService._clean_str(it.get("content"))
            if not content:
                continue
            priority = str(it.get("priority") or "medium").lower()
            if priority not in {"low", "medium", "high"}:
                priority = "medium"
            items.append({
                "content": content,
                "assignee": LlmService._clean_str(it.get("assignee")),
                "due_date": LlmService._parse_due(it.get("due_date")),
                "priority": priority,
            })

        return {
            "summary": data.get("summary") or "",
            "key_points": data.get("key_points") or [],
            "action_items": items,
    }

    # ==================== 记忆抽取 ====================
    async def extract_memories(self, text: str) -> list[dict]:
        """从会议内容抽取可长期复用的记忆候选；容错解析 JSON"""
        prompt = render_prompt("memory_extract_user", transcript=text)
        raw = await self._call_llm(prompt, json_mode=True)
        return self._parse_memories(raw)

    @staticmethod
    def _parse_memories(raw: str) -> list[dict]:
        cleaned = (raw or "").strip()
        if cleaned.startswith(_CODE_FENCE):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        try:
            data = json.loads(cleaned)
        except (json.JSONDecodeError, AttributeError):
            return []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("memories", [])
        else:
            items = []
        return [i for i in items if isinstance(i, dict)]

    # ==================== 语义搜索 ====================
    async def semantic_search(self, query: str, owner_id: str, meeting_id: str = None, limit: int = 5) -> list[dict]:
        query_embedding = await self._get_embedding(query)
        sql = """
            SELECT t.id, t.text,
                t.segments->0->>'speaker' AS speaker,
                t.meeting_id,
                t.created_at,
                1 - (t.embedding <=> :qvec) AS similarity
            FROM transcripts t
            JOIN meetings m ON m.id = t.meeting_id
            WHERE m.owner_id = :owner
              AND m.deleted_at IS NULL
              AND (:mid IS NULL OR t.meeting_id = :mid)
              AND t.embedding IS NOT NULL
            ORDER BY t.embedding <=> :qvec
            LIMIT :lim
        """
        params = {
            "qvec": str(query_embedding),
            "owner": owner_id,
            "mid": meeting_id,
            "lim": limit,
        }
        result = await self.db.execute(text(sql), params)
        return [dict(row) for row in result.mappings().fetchall()]

    # ==================== 内部工具方法 ====================
    async def _call_llm(self, prompt: str, json_mode: bool = False) -> str:
        payload = {
            "model": settings.LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def _get_embedding(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embed",
                json={"model": settings.EMBEDDING_MODEL, "input": text},
            )
            resp.raise_for_status()
            data = resp.json()

        # /api/embed 返回 {"embeddings": [[...]]}；兼容旧 {"embedding": [...]}
        return data["embeddings"][0] if "embeddings" in data else data["embedding"]