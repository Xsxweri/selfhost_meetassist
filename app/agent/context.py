from dataclasses import dataclass
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

@dataclass
class AgentContext:
    """Agent 工具执行上下文：每次工具调用时短生命周期创建，避免跨 interrupt 持有 DB 会话"""
    db: AsyncSession
    owner_id: uuid.UUID
    user_id: uuid.UUID
    ip: str | None = None
    user_agent: str | None = None
