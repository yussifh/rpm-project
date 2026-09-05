"""
Medical history entry schemas.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class MedicalHistoryCreate(BaseModel):
    condition_name: str = Field(min_length=2, max_length=200)
    diagnosed_date: date | None = None
    notes: str | None = None


class MedicalHistoryOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    condition_name: str
    diagnosed_date: date | None
    notes: str | None
    recorded_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
