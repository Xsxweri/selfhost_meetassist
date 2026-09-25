import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


# 审计动作
class AuditAction(str, enum.Enum):
    USER_LOGIN = "user.login"
    MEETING_CREATE = "meeting.create"
    MEETING_DELETE = "meeting.delete"
    MEETING_RESTORE = "meeting.restore"
    CONSENT_GRANT = "consent.grant"
    CONSENT_REVOKE = "consent.revoke"
    SUMMARY_GENERATE = "summary.generate"
    SHARE_CREATE = "share.create"
    SHARE_REVOKE = "share.revoke"
    SHARE_ACCESS = "share.access"
    EXPORT = "export"

    # ===== Agent 审计 =====
    AGENT_RUN = "agent.run"  # 一次完整 Agent 目标执行
    AGENT_ACTION = "agent.action"    # 单个敏感工具执行留痕

    # ===== 记忆层 审计 =====
    MEMORY_WRITE = "memory.write"  # 写入长期记忆
    MEMORY_SUPERSEDE = "memory.supersede"  # 记忆被新事实取代


class AuditLog(Base):
    """审计日志（追加式，不可修改，用于合规留痕）"""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<AuditLog(action={self.action}, user_id={self.user_id})>"