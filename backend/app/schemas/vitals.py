"""
Vital reading schemas.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import DiseaseType, VitalSource
from app.schemas.prediction import RiskPredictionOut


class VitalReadingCreate(BaseModel):
    recorded_at: datetime | None = None  # defaults to "now" if omitted
    source: VitalSource = VitalSource.MANUAL

    # Which condition(s) this submission should be assessed for — see
    # app/services/vitals_service.py and app/ai_engine/feature_schema.py
    # (CONDITION_VITAL_FIELDS). Optional/empty for backward compatibility
    # (e.g. an admin logging a reading with no AI assessment attached) —
    # when empty, no risk prediction is generated for this submission,
    # only the deterministic threshold-based alert check runs.
    conditions: list[DiseaseType] = Field(default_factory=list)

    blood_pressure_systolic: int | None = Field(default=None, ge=50, le=300)
    blood_pressure_diastolic: int | None = Field(default=None, ge=30, le=200)
    heart_rate_bpm: int | None = Field(default=None, ge=20, le=250)
    blood_glucose_mg_dl: float | None = Field(default=None, ge=20, le=800)
    skin_thickness_mm: float | None = Field(default=None, ge=1, le=100)
    serum_insulin_mu_u_ml: float | None = Field(default=None, ge=1, le=900)
    diabetes_pedigree_function: float | None = Field(default=None, ge=0.02, le=2.5)
    height_cm: float | None = Field(default=None, ge=50, le=250)
    bmi: float | None = Field(default=None, ge=10, le=70)
    age_years: int | None = Field(default=None, ge=1, le=120)
    spo2_percent: float | None = Field(default=None, ge=50, le=100)
    temperature_celsius: float | None = Field(default=None, ge=25, le=45)
    respiratory_rate: int | None = Field(default=None, ge=5, le=60)
    weight_kg: float | None = Field(default=None, ge=2, le=400)
    notes: str | None = None

    @model_validator(mode="after")
    def at_least_one_reading(self):
        vital_fields = [
            self.blood_pressure_systolic,
            self.blood_pressure_diastolic,
            self.heart_rate_bpm,
            self.blood_glucose_mg_dl,
            self.skin_thickness_mm,
            self.serum_insulin_mu_u_ml,
            self.diabetes_pedigree_function,
            self.height_cm,
            self.bmi,
            self.age_years,
            self.spo2_percent,
            self.temperature_celsius,
            self.respiratory_rate,
            self.weight_kg,
        ]
        if all(v is None for v in vital_fields):
            raise ValueError("At least one vital measurement must be provided")
        return self


class VitalReadingOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    recorded_at: datetime
    source: VitalSource
    blood_pressure_systolic: int | None
    blood_pressure_diastolic: int | None
    heart_rate_bpm: int | None
    blood_glucose_mg_dl: float | None
    skin_thickness_mm: float | None
    serum_insulin_mu_u_ml: float | None
    diabetes_pedigree_function: float | None
    height_cm: float | None
    bmi: float | None
    age_years: int | None
    spo2_percent: float | None
    temperature_celsius: float | None
    respiratory_rate: int | None
    weight_kg: float | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrendDataPointOut(BaseModel):
    recorded_at: datetime
    value: float


class ForecastOut(BaseModel):
    """Predictive trend forecast — see app.services.trend_analysis.
    forecast_trend(). Distinct from the trend classification above: this
    is a claim about the future (when a value may cross a threshold if
    its current trajectory continues), so it carries its own confidence
    score and fails safe (position="low_confidence", no day count) rather
    than ever guessing when the underlying data doesn't support it."""

    position: str
    days_projected: float | None
    target_value: float | None
    r_squared: float | None
    summary: str


class VitalTrendOut(BaseModel):
    """One field's trend classification — see app.services.trend_analysis
    for how `direction`/`summary` are derived (rule-based, not ML)."""

    field: str
    label: str
    unit: str
    direction: str
    is_consistently_abnormal: bool
    sample_size: int
    earliest_average: float | None
    recent_average: float | None
    summary: str
    data_points: list[TrendDataPointOut]
    forecast: ForecastOut | None = None


class VitalTrendsOut(BaseModel):
    period_days: int
    trends: list[VitalTrendOut]


class SkippedPredictionOut(BaseModel):
    """Why a selected condition didn't get a prediction this submission —
    e.g. missing height/weight for BMI. Surfaced to the patient rather
    than silently dropped, so "Confirm and Analyze" never quietly loses
    a condition the patient explicitly selected (spec: validate the
    selected condition(s))."""

    disease_type: DiseaseType
    reason: str


class VitalSubmissionResult(BaseModel):
    """Response for POST /patients/{id}/vitals — bundles the saved
    reading with the condition-specific results generated from it in the
    same request, so the frontend can render the Results Page (spec
    section 9) immediately after "Confirm" without a second round trip."""

    vital: VitalReadingOut
    predictions: list[RiskPredictionOut]
    skipped: list[SkippedPredictionOut]
