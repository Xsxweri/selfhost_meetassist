import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.meeting import Meeting


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 结构化分段数据: [{"start": 0.5, "end": 2.1, "speaker": "SPEAKER_00", "text": "..."}]
    segments: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="带时间戳的ASR分段JSON"
    )

    # 该分段的纯文本快照（便于按段检索或增量拼接）
    text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="分段纯文本")

    # bge-m3 生成的向量 (bge-m3 默认输出 1024 维)
    embedding: Mapped[List[float] | None] = mapped_column(
        Vector(1024), nullable=True, comment="文本向量(bge-m3)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ORM 关系
    meeting: Mapped["Meeting"] = relationship(back_populates="transcript_segments")