import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.action_item import ActionItemResponse


class ShareLinkCreate(BaseModel):
    allow_download: bool = True
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class ShareLinkResponse(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    token: str
    path: str
    allow_download: bool
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SharedMeetingResponse(BaseModel):
    title: str
    summary: Optional[str] = None
    created_at: datetime
    allow_download: bool
    action_items: List[ActionItemResponse] = []
    transcripts: List[str] = []