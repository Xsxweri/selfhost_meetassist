import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ActionItemBase(BaseModel):
    content: str = Field(..., min_length=1)
    assignee: Optional[str] = Field(None, max_length=200)
    due_date: Optional[datetime] = None
    priority: str = Field("medium", pattern="^(low|medium|high)$")
    source_start: Optional[float] = None
    source_end: Optional[float] = None


class ActionItemCreate(ActionItemBase):
    pass


class ActionItemUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    assignee: Optional[str] = Field(None, max_length=200)
    due_date: Optional[datetime] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    status: Optional[str] = Field(None, pattern="^(pending|confirmed|done|dismissed)$")
    source_start: Optional[float] = None
    source_end: Optional[float] = None


class ActionItemResponse(ActionItemBase):
    id: uuid.UUID
    meeting_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SummaryResponse(BaseModel):
    meeting_id: uuid.UUID
    summary: Optional[str] = None
    action_items: List[ActionItemResponse] = []