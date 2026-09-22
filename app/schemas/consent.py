import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.consent import ConsentType, ConsentAction


class ConsentCreate(BaseModel):
    consent_type: ConsentType
    action: ConsentAction
    note: Optional[str] = None

class ConsentResponse(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    user_id: uuid.UUID
    consent_type: str
    action: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }

class ConsentStatus(BaseModel):
    consent_type: str
    granted: bool
    updated_at: Optional[datetime] = None