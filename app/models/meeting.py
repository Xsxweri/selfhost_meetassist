import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List
from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
if TYPE_CHECKING:
    from app.models.transcript import Transcript
    from app.models.user import User

class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # bge-m3 输出 1024 维向量
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    transcript_segments: Mapped[List["Transcript"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    owner: Mapped["User | None"] = relationship(lazy="joined")

    def __repr__(self) -> str:
        return f"<Meeting(id={self.id}, title={self.title!r})>"