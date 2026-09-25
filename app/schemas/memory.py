import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

_KIND_PATTERN = "^(decision|action|preference|fact|entity)$"


# 创建记忆
class MemoryCreate(BaseModel):
    kind: str = Field("fact", pattern=_KIND_PATTERN)
    subject: Optional[str] = Field(None, max_length=200)
    content: str = Field(..., min_length=1)
    importance: float = Field(0.5, ge=0.0, le=1.0)
    meeting_id: Optional[uuid.UUID] = None


# 更新记忆
class MemoryUpdate(BaseModel):
    kind: Optional[str] = Field(None, pattern=_KIND_PATTERN)
    subject: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)


# 查询记忆
class MemoryResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    meeting_id: Optional[uuid.UUID] = None
    kind: str
    subject: Optional[str] = None
    content: str
    importance: float
    confidence: float
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    superseded_by: Optional[uuid.UUID] = None
    access_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# 搜索记忆
class MemorySearchHit(BaseModel):
    id: uuid.UUID
    kind: str
    subject: Optional[str] = None
    content: str
    meeting_id: Optional[uuid.UUID] = None
    importance: float
    similarity: float