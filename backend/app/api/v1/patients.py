"""
Patient routes.

Access pattern:
  - /me endpoints: PATIENT role only, always operates on the caller's own profile
  - /{patient_id} and list endpoints: ADMIN (all patients) and PATIENT (self only)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.authorization import ensure_patient_access
from app.core.exceptions import NotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.patient import AssignConditionRequest, PatientProfileOut, PatientProfileUpdate, PatientWithUserOut
from app.services.patient_service import PatientService

router = APIRouter()


def get_patient_service(db: Session = Depends(get_db)) -> PatientService:
    return PatientService(db)


def _with_user(patient) -> PatientWithUserOut:
    return PatientWithUserOut(
        **PatientProfileOut.model_validate(patient).model_dump(),
        full_name=patient.user.full_name,
        email=patient.user.email,
        phone_number=patient.user.phone_number,
    )


@router.get("/me", response_model=PatientProfileOut, dependencies=[Depends(require_roles(UserRole.PATIENT))])
def get_my_profile(current_user: User = Depends(get_current_user)):
    if not current_user.patient_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    return current_user.patient_profile


@router.patch("/me", response_model=PatientProfileOut, dependencies=[Depends(require_roles(UserRole.PATIENT))])
def update_my_profile(
    payload: PatientProfileUpdate,
    current_user: User = Depends(get_current_user),
    service: PatientService = Depends(get_patient_service),
):
    if not current_user.patient_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    return service.update_profile(current_user.patient_profile, payload)


@router.get(
    "",
    response_model=list[PatientWithUserOut],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def list_patients(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    service: PatientService = Depends(get_patient_service),
):
    """Admin-only: manages the patient roster (technical/admin side of the system)."""
    patients = service.list_for_admin(skip=skip, limit=limit)
    return [_with_user(p) for p in patients]


@router.get(
    "/{patient_id}",
    response_model=PatientWithUserOut,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.PATIENT))],
)
def get_patient(
    patient_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PatientService = Depends(get_patient_service),
):
    try:
        patient = service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)
    return _with_user(patient)


@router.patch(
    "/{patient_id}/condition",
    response_model=PatientWithUserOut,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def assign_condition(
    patient_id: uuid.UUID,
    payload: AssignConditionRequest,
    current_user: User = Depends(get_current_user),
    service: PatientService = Depends(get_patient_service),
):
    """Assigns the patient's primary condition — drives which vitals
    fields and symptom checklist the patient sees. Admin-only: there is no
    doctor role in this system to diagnose/assign it."""
    try:
        patient = service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)
    updated = service.update_profile(patient, PatientProfileUpdate(primary_condition=payload.primary_condition))
    return _with_user(updated)
