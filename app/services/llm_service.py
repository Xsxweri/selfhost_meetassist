import json
import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transcript import Transcript
from app.core.config import get_settings

settings = get_settings()
_CODE_FENCE = "`" * 3

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
            return {"summary": "暂无转录内容", "action_items": []}

        prompt = (
            "请根据以下会议转录生成JSON格式的会议纪要，包含 summary(字符串) 和 action_items(字符串列表)：\n\n"
            + "\n".join(contents)
        )
        raw = await self._call_llm(prompt)
        return self._parse_summary(raw)

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
            return {
                "summary": data.get("summary", ""),
                "action_items": data.get("action_items", []),
            }
        except (json.JSONDecodeError, AttributeError):
            # 解析失败时，退化为把原始文本作为 summary
            return {"summary": raw, "action_items": []}

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
                json={"model": settings.EMBEDDING_MODEL, "prompt": text},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]