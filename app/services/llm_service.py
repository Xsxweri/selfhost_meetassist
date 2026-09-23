import json
import httpx
from datetime import datetime
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transcript import Transcript
from app.core.config import get_settings

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

        prompt = (
            "你是会议纪要助手。请阅读以下会议转录，输出严格 JSON"
            "（不要任何额外文字、不要 markdown 代码块），结构如下：\n"
            "{\n"
            '  "summary": "整体纪要，200字以内",\n'
            '  "key_points": ["要点1", "要点2"],\n'
            '  "action_items": [\n'
            '    {"content": "待办内容", "assignee": "负责人或null", '
            '"due_date": "YYYY-MM-DD或null", "priority": "low|medium|high"}\n'
            "  ]\n"
            "}\n"
            "若没有待办，action_items 为空数组。\n\n"
            "会议转录：\n" + "\n".join(contents)
        )
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

    # ==================== 语义搜索 ====================
    async def semantic_search(self, query: str, meeting_id: str = None, limit: int = 5) -> list[dict]:
        query_embedding = await self._get_embedding(query)
        sql = """
            SELECT id, text, 
                segments->0->>'speaker' AS speaker,
                created_at,
                1 - (embedding <=> :qvec) AS similarity
            FROM transcripts
            WHERE (:mid IS NULL OR meeting_id = :mid)
            AND embedding IS NOT NULL
            ORDER BY embedding <=> :qvec
            LIMIT :lim
        """
        params = {"qvec": str(query_embedding), "mid": meeting_id, "lim": limit}
        result = await self.db.execute(text(sql), params)
        return [dict(row) for row in result.mappings().fetchall()]

    # ==================== 内部工具方法 ====================
    async def _call_llm(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def _get_embedding(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                json={"model": settings.EMBEDDING_MODEL, "input": text},
            )
            resp.raise_for_status()
            return resp.json()["embeddings"][0]