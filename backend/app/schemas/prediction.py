"""
Risk prediction schemas.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import DiseaseType, RiskLevel


class RiskPredictionOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    source_vital_id: uuid.UUID | None
    disease_type: DiseaseType
    risk_score: float
    risk_level: RiskLevel
    model_version: str
    data_source: str
    input_features: dict
    reasons: list[str]
    recommendations: list[str]
    predicted_at: datetime

    model_config = {
        "from_attributes": True,
        "protected_namespaces": (),
    }


class ModelInfoOut(BaseModel):
    """
    Static, per-model transparency info — NOT tied to any one patient or
    prediction. Powers the feature-importance chart and model-card content
    in the UI. Read-only reflection of what's baked into the trained
    joblib artifact at `python -m app.ai_engine.train` time.
    """

    disease_type: DiseaseType
    model_version: str
    data_source: str
    feature_names: list[str]
    metrics: dict
    feature_importances: dict[str, float]

    model_config = {"protected_namespaces": ()}
