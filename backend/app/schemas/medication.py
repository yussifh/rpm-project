"""
Medication and medication adherence log schemas.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import MedicationStatus


class MedicationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    dosage: str = Field(min_length=1, max_length=100)
    frequency: str = Field(min_length=1, max_length=100)
    instructions: str | None = None
    start_date: date
    end_date: date | None = None


class MedicationUpdate(BaseModel):
    dosage: str | None = None
    frequency: str | None = None
    instructions: str | None = None
    end_date: date | None = None
    is_active: bool | None = None


class MedicationOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    name: str
    dosage: str
    frequency: str
    instructions: str | None
    start_date: date
    end_date: date | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MedicationLogCreate(BaseModel):
    scheduled_at: datetime
    status: MedicationStatus
    taken_at: datetime | None = None


class MedicationLogOut(BaseModel):
    id: uuid.UUID
    medication_id: uuid.UUID
    scheduled_at: datetime
    status: MedicationStatus
    taken_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
