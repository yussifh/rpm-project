"""
Patient profile schemas.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import DiseaseType, Gender


class PatientProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date_of_birth: date
    gender: Gender
    blood_group: str | None
    height_cm: float | None
    weight_kg: float | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    chronic_conditions_summary: str | None
    primary_condition: DiseaseType | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PatientProfileUpdate(BaseModel):
    """
    All fields optional (PATCH semantics) — a patient updating their emergency
    contact shouldn't be forced to resend their entire profile.
    """

    date_of_birth: date | None = None
    gender: Gender | None = None
    blood_group: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    chronic_conditions_summary: str | None = None
    primary_condition: DiseaseType | None = None


class AssignConditionRequest(BaseModel):
    primary_condition: DiseaseType


class PatientWithUserOut(PatientProfileOut):
    """Enriched view for admin listing — includes basic identity fields
    without exposing the full User object (no hashed_password, etc.)."""

    full_name: str
    email: str
    phone_number: str | None
