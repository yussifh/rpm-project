"""
Prediction routes — nested under /patients/{patient_id}/predictions.

There is no doctor role in this system: the ML model is the prediction
engine, and the patient is the one who consumes it. Both triggering a NEW
prediction (POST) and reading prediction HISTORY (GET) follow the standard
patient-access rule (self, or admin) — a patient runs their own risk
assessment (e.g. after logging new vitals), while admin retains access for
support/data-correction purposes.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.authorization import ensure_patient_access
from app.core.exceptions import InsufficientDataError, NotFoundError
from app.models.enums import DiseaseType, UserRole
from app.models.user import User
from app.schemas.prediction import ModelInfoOut, RiskPredictionOut
from app.services.patient_service import PatientService
from app.services.prediction_service import PredictionService

router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.PATIENT))])


def get_prediction_service(db: Session = Depends(get_db)) -> PredictionService:
    return PredictionService(db)


def get_patient_service(db: Session = Depends(get_db)) -> PatientService:
    return PatientService(db)


@router.post(
    "/{patient_id}/predictions/{disease_type}",
    response_model=RiskPredictionOut,
    status_code=status.HTTP_201_CREATED,
)
def generate_prediction(
    patient_id: uuid.UUID,
    disease_type: DiseaseType,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    prediction_service: PredictionService = Depends(get_prediction_service),
):
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)

    try:
        return prediction_service.predict(patient_id, disease_type)
    except InsufficientDataError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{patient_id}/predictions", response_model=list[RiskPredictionOut])
def list_predictions(
    patient_id: uuid.UUID,
    disease_type: DiseaseType | None = None,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    prediction_service: PredictionService = Depends(get_prediction_service),
):
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)
    return prediction_service.list_for_patient(patient_id, disease=disease_type)
