"""
Admin routes — all endpoints here require the ADMIN role, enforced via
`require_roles(UserRole.ADMIN)` at the router level (applied once to the
whole router via `dependencies=`, rather than repeated on every route).

There is no doctor role in this system. Admin manages the technical side:
patient accounts, other admins, and (see api/v1/ml_admin.py) datasets/model
training/model versions — never clinical consultation.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.exceptions import DuplicateEmailError, NotFoundError
from app.models.enums import UserRole
from app.schemas.admin import AdminCreateRequest, PatientCreateRequest
from app.schemas.audit_log import AuditLogOut
from app.schemas.patient import PatientProfileOut, PatientProfileUpdate, PatientWithUserOut
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate
from app.services.audit_service import AuditService
from app.services.user_management_service import UserManagementService

router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN))])


def get_user_management_service(db: Session = Depends(get_db)) -> UserManagementService:
    return UserManagementService(db)


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    return AuditService(db)


def _patient_with_user(patient) -> PatientWithUserOut:
    return PatientWithUserOut(
        **PatientProfileOut.model_validate(patient).model_dump(),
        full_name=patient.user.full_name,
        email=patient.user.email,
        phone_number=patient.user.phone_number,
    )


@router.post("/users/patient", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreateRequest,
    current_user: User = Depends(get_current_user),
    service: UserManagementService = Depends(get_user_management_service),
):
    try:
        return service.create_patient(payload, actor_user_id=current_user.id)
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/users/admin", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_admin(
    payload: AdminCreateRequest,
    current_user: User = Depends(get_current_user),
    service: UserManagementService = Depends(get_user_management_service),
):
    try:
        return service.create_admin(payload, actor_user_id=current_user.id)
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/users", response_model=list[UserOut])
def list_users(
    role: UserRole | None = Query(default=None),
    service: UserManagementService = Depends(get_user_management_service),
):
    return service.list_users(role=role)


@router.patch("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: UserManagementService = Depends(get_user_management_service),
):
    try:
        return service.set_active_status(user_id, is_active=False, actor_user_id=current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/users/{user_id}/activate", response_model=UserOut)
def activate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: UserManagementService = Depends(get_user_management_service),
):
    try:
        return service.set_active_status(user_id, is_active=True, actor_user_id=current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: AuditService = Depends(get_audit_service),
):
    """Read-only, admin-only view of the audit trail. There is no
    update/delete here — audit logs are immutable by design."""
    return service.logs.list_all(action=action, entity_type=entity_type, skip=skip, limit=limit)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    service: UserManagementService = Depends(get_user_management_service),
):
    """Edit a user's core identity fields (name, email, phone) — any role."""
    try:
        return service.update_user_details(user_id, payload, actor_user_id=current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.patch("/patients/{patient_id}", response_model=PatientWithUserOut)
def update_patient(
    patient_id: uuid.UUID,
    payload: PatientProfileUpdate,
    current_user: User = Depends(get_current_user),
    service: UserManagementService = Depends(get_user_management_service),
):
    """Edit a patient's medical profile fields (DOB, gender, blood group, etc.)."""
    try:
        updated = service.update_patient_profile(patient_id, payload, actor_user_id=current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return _patient_with_user(updated)
