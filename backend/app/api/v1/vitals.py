"""
Vitals routes — nested under /patients/{patient_id}/vitals.

Admin or the patient themself may SUBMIT a reading (a patient self-logging
their own BP is the core RPM use case; admin may also log it on the
patient's behalf, e.g. data correction). Read access follows the
standard patient-access rule.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.authorization import ensure_patient_access
from app.core.exceptions import NotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.vitals import (
    ForecastOut,
    SkippedPredictionOut,
    VitalReadingCreate,
    VitalReadingOut,
    VitalSubmissionResult,
    VitalTrendOut,
    VitalTrendsOut,
)
from app.services.patient_service import PatientService
from app.services.vitals_service import VitalsService

router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.PATIENT))])


def get_vitals_service(db: Session = Depends(get_db)) -> VitalsService:
    return VitalsService(db)


def get_patient_service(db: Session = Depends(get_db)) -> PatientService:
    return PatientService(db)


@router.post(
    "/{patient_id}/vitals",
    response_model=VitalSubmissionResult,
    status_code=status.HTTP_201_CREATED,
)
def record_vitals(
    patient_id: uuid.UUID,
    payload: VitalReadingCreate,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    vitals_service: VitalsService = Depends(get_vitals_service),
):
    """Saves the reading and, for each condition in `payload.conditions`,
    generates that condition's own risk prediction in the same request —
    this is the "Confirm and Analyze" step of the condition-based vitals
    workflow: the frontend already showed the patient a review popup
    before calling this, so by the time this fires the values are
    final."""
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)

    try:
        result = vitals_service.record_reading(patient_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return VitalSubmissionResult(
        vital=result.vital,
        predictions=result.predictions,
        skipped=[SkippedPredictionOut(disease_type=disease, reason=reason) for disease, reason in result.skipped],
    )


@router.get("/{patient_id}/vitals", response_model=list[VitalReadingOut])
def list_vitals(
    patient_id: uuid.UUID,
    start: datetime | None = None,
    end: datetime | None = None,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    vitals_service: VitalsService = Depends(get_vitals_service),
):
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)
    return vitals_service.list_for_patient(patient_id, start=start, end=end)


@router.get("/{patient_id}/vitals/trends", response_model=VitalTrendsOut)
def get_vitals_trends(
    patient_id: uuid.UUID,
    days: int = 90,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    vitals_service: VitalsService = Depends(get_vitals_service),
):
    """Trend classification AND forward-looking forecast per vital field
    over the given window — see app.services.trend_analysis. This is
    deliberately a separate endpoint from GET /vitals (raw readings): the
    dashboard's Trends section wants the classified summary + forecast +
    narrative text, not just the raw rows it would otherwise have to
    re-derive client-side."""
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)

    if days < 1 or days > 730:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="days must be between 1 and 730")

    trends = vitals_service.get_trends(patient_id, days=days)
    return VitalTrendsOut(
        period_days=days,
        trends=[
            VitalTrendOut(
                field=t.field,
                label=t.label,
                unit=t.unit,
                direction=t.direction.value,
                is_consistently_abnormal=t.is_consistently_abnormal,
                sample_size=t.sample_size,
                earliest_average=t.earliest_average,
                recent_average=t.recent_average,
                summary=t.summary,
                data_points=[{"recorded_at": p.recorded_at, "value": p.value} for p in t.data_points],
                forecast=ForecastOut(
                    position=f.position.value,
                    days_projected=f.days_projected,
                    target_value=f.target_value,
                    r_squared=f.r_squared,
                    summary=f.summary,
                ),
            )
            for t, f in trends
        ],
    )
