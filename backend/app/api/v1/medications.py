"""
Medication routes.

- /patients/{patient_id}/medications  -> list (read) / add (write)
- /medications/{medication_id}        -> update medication record (write)
- /medications/{medication_id}/logs   -> adherence log create/list

There is no doctor role in this system, so patients self-report their own
medication list (what they're taking, dosage, frequency) the same way they
self-report vitals — admin retains write access for data correction.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.authorization import ensure_patient_access
from app.core.exceptions import NotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.medication import (
    MedicationCreate,
    MedicationLogCreate,
    MedicationLogOut,
    MedicationOut,
    MedicationUpdate,
)
from app.services.medication_service import MedicationService
from app.services.patient_service import PatientService

router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.PATIENT))])


def get_medication_service(db: Session = Depends(get_db)) -> MedicationService:
    return MedicationService(db)


def get_patient_service(db: Session = Depends(get_db)) -> PatientService:
    return PatientService(db)


@router.get("/patients/{patient_id}/medications", response_model=list[MedicationOut])
def list_medications(
    patient_id: uuid.UUID,
    active_only: bool = False,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    medication_service: MedicationService = Depends(get_medication_service),
):
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)
    return medication_service.list_for_patient(patient_id, active_only=active_only)


@router.post(
    "/patients/{patient_id}/medications",
    response_model=MedicationOut,
    status_code=status.HTTP_201_CREATED,
)
def add_medication(
    patient_id: uuid.UUID,
    payload: MedicationCreate,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    medication_service: MedicationService = Depends(get_medication_service),
):
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)
    return medication_service.add(patient_id, payload, actor_user_id=current_user.id)


@router.patch("/medications/{medication_id}", response_model=MedicationOut)
def update_medication(
    medication_id: uuid.UUID,
    payload: MedicationUpdate,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    medication_service: MedicationService = Depends(get_medication_service),
):
    try:
        medication = medication_service.get_by_id(medication_id)
        patient = patient_service.get_by_id(medication.patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)
    return medication_service.update(medication, payload)


@router.post(
    "/medications/{medication_id}/logs",
    response_model=MedicationLogOut,
    status_code=status.HTTP_201_CREATED,
)
def log_medication_dose(
    medication_id: uuid.UUID,
    payload: MedicationLogCreate,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    medication_service: MedicationService = Depends(get_medication_service),
):
    try:
        medication = medication_service.get_by_id(medication_id)
        patient = patient_service.get_by_id(medication.patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    # Read-level access is enough to log adherence — the patient logs their OWN doses.
    ensure_patient_access(current_user, patient)
    return medication_service.log_dose(medication_id, payload)


@router.get("/medications/{medication_id}/logs", response_model=list[MedicationLogOut])
def get_medication_logs(
    medication_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    medication_service: MedicationService = Depends(get_medication_service),
):
    try:
        medication = medication_service.get_by_id(medication_id)
        patient = patient_service.get_by_id(medication.patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)
    return medication_service.list_logs(medication_id)
