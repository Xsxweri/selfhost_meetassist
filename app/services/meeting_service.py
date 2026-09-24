from sqlalchemy.ext.asyncio import AsyncSession
from app.services.asr_service import AsrService
from app.services.llm_service import LlmService

class MeetingService:
    """会议业务编排层，不直接操作 DB，而是委托给子服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.asr = AsrService(db)
        self.llm = LlmService(db)

    async def add_transcripts(self, meeting_id: str, segments: list[dict]):
        """保存 ASR 分段转录并逐段生成向量（ASR 回调入口）"""
        return await self.asr.process_asr_result(meeting_id, segments)

    async def get_summary(self, meeting_id: str) -> dict:
        """获取会议纪要"""
        return await self.llm.generate_summary(meeting_id)

    async def search(self, query: str, owner_id: str,meeting_id: str = None, limit: int = 5) -> list[dict]:
        """语义搜索会议内容"""
        return await self.llm.semantic_search(query, owner_id=owner_id, meeting_id=meeting_id, limit=limit)