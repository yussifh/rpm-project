import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import DiseaseType


class DiseaseAssessmentCreate(BaseModel):
    disease_type: DiseaseType
    symptoms: dict[str, bool | str]


class DiseaseAssessmentOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    disease_type: DiseaseType
    symptoms: dict
    created_at: datetime

    model_config = {"from_attributes": True}
