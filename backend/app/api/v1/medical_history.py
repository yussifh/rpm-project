"""
Medical history routes — nested under /patients/{patient_id}/medical-history.

Read access: admin or the patient themself (ensure_patient_access).
Write access: admin only (ensure_can_write_clinical_entry) — a patient
should not be able to author their own diagnosis history, and there is no
doctor role to author it either.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.authorization import ensure_can_write_clinical_entry, ensure_patient_access
from app.core.exceptions import NotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.medical_history import MedicalHistoryCreate, MedicalHistoryOut
from app.services.medical_history_service import MedicalHistoryService
from app.services.patient_service import PatientService

router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.PATIENT))])


def get_history_service(db: Session = Depends(get_db)) -> MedicalHistoryService:
    return MedicalHistoryService(db)


def get_patient_service(db: Session = Depends(get_db)) -> PatientService:
    return PatientService(db)


@router.get("/{patient_id}/medical-history", response_model=list[MedicalHistoryOut])
def list_medical_history(
    patient_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    history_service: MedicalHistoryService = Depends(get_history_service),
):
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)
    return history_service.list_for_patient(patient_id)


@router.post(
    "/{patient_id}/medical-history",
    response_model=MedicalHistoryOut,
    status_code=status.HTTP_201_CREATED,
)
def add_medical_history_entry(
    patient_id: uuid.UUID,
    payload: MedicalHistoryCreate,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    history_service: MedicalHistoryService = Depends(get_history_service),
):
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_can_write_clinical_entry(current_user, patient)
    return history_service.add_entry(patient_id, payload, recorded_by=current_user.full_name)
