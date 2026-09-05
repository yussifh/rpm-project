"""
Disease assessment routes — nested under /patients/{patient_id}/assessments.

Unlike medical history (diagnosis records, admin-authored only), a disease
assessment is the patient's own self-reported symptom checklist as part
of daily monitoring — so the patient can write their own, in addition to
an admin recording one on their behalf (e.g. data correction).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.authorization import ensure_patient_access
from app.core.exceptions import NotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.disease_assessment import DiseaseAssessmentCreate, DiseaseAssessmentOut
from app.services.disease_assessment_service import DiseaseAssessmentService
from app.services.patient_service import PatientService

router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.PATIENT))])


def get_assessment_service(db: Session = Depends(get_db)) -> DiseaseAssessmentService:
    return DiseaseAssessmentService(db)


def get_patient_service(db: Session = Depends(get_db)) -> PatientService:
    return PatientService(db)


@router.get("/{patient_id}/assessments", response_model=list[DiseaseAssessmentOut])
def list_assessments(
    patient_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    assessment_service: DiseaseAssessmentService = Depends(get_assessment_service),
):
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)
    return assessment_service.list_for_patient(patient_id)


@router.post("/{patient_id}/assessments", response_model=DiseaseAssessmentOut, status_code=status.HTTP_201_CREATED)
def submit_assessment(
    patient_id: uuid.UUID,
    payload: DiseaseAssessmentCreate,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    assessment_service: DiseaseAssessmentService = Depends(get_assessment_service),
):
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)
    return assessment_service.submit(patient_id, payload.disease_type, payload.symptoms)
