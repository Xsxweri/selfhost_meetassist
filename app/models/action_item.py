import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

class ActionItemPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ActionItemStatus(str, enum.Enum):
    PENDING = "pending"        # LLM 生成，待用户确认
    CONFIRMED = "confirmed"    # 已确认
    DONE = "done"              # 已完成
    DISMISSED = "dismissed"    # 已忽略/无效

class ActionItem(Base):
    """会议待办事项（LLM 生成，可被用户编辑/确认）"""
    __tablename__ = "action_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    assignee: Mapped[str | None] = mapped_column(String(200), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ActionItemPriority.MEDIUM.value
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ActionItemStatus.PENDING.value
    )
    source_start: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<ActionItem(meeting_id={self.meeting_id}, status={self.status})>"