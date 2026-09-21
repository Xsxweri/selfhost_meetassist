import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class MeetingBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)

class MeetingCreate(MeetingBase):
    """创建会议时前端传入的数据"""
    transcript: Optional[str] = None
    summary: Optional[str] = None

class MeetingUpdate(BaseModel):
    """更新会议时前端传入的数据（所有字段可选）"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    transcript: Optional[str] = None
    summary: Optional[str] = None

class MeetingResponse(MeetingBase):
    """返回给前端的会议数据"""
    id: uuid.UUID
    owner_id: Optional[uuid.UUID] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}