import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


# 搜索结果
class SearchHit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meeting_id: uuid.UUID
    text: str | None = None
    speaker: str | None = None
    created_at: datetime
    similarity: float


# 搜索响应
class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[SearchHit]