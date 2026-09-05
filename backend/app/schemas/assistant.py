"""
AI Health Assistant chat schemas.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AssistantMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class AssistantMessageOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    role: str
    content: str
    is_emergency_override: bool
    created_at: datetime

    model_config = {"from_attributes": True}
