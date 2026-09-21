import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transcript import Transcript
from app.core.config import get_settings

settings = get_settings()

class AsrService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_asr_result(self, meeting_id: str, segments: list[dict]) -> list[Transcript]:
        """按分段保存并逐段生成向量"""
        transcripts = []
        for seg in segments:
            text = seg.get("text", "")
            if not text.strip():
                continue
                
            embedding = await self._get_embedding(text)
            
            transcript = Transcript(
                meeting_id=meeting_id,
                segments=[seg],          # 保留原始分段结构
                text=text,               # 纯文本快照用于检索
                embedding=embedding      # 向量
            )
            self.db.add(transcript)
            transcripts.append(transcript)
        
        await self.db.commit()
        return transcripts

    async def _get_embedding(self, text: str) -> list[float]:
        """调用 Ollama Embedding API (bge-m3)"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                json={"model": settings.EMBEDDING_MODEL, "prompt": text}
            )
            resp.raise_for_status()
            return resp.json()["embedding"]