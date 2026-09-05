"""
AI Health Assistant chat routes — nested under /patients/{patient_id}/assistant.

This is what replaced patient<->doctor messaging when the doctor role was
removed (see 0006_remove_doctor_role migration). Follows the standard
patient-access rule: self or admin.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.authorization import ensure_patient_access
from app.core.exceptions import AssistantUnavailableError, NotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.assistant import AssistantMessageCreate, AssistantMessageOut
from app.services.assistant_service import AssistantService
from app.services.patient_service import PatientService

router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.PATIENT))])


def get_assistant_service(db: Session = Depends(get_db)) -> AssistantService:
    return AssistantService(db)


def get_patient_service(db: Session = Depends(get_db)) -> PatientService:
    return PatientService(db)


@router.get("/{patient_id}/assistant/messages", response_model=list[AssistantMessageOut])
def list_assistant_messages(
    patient_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)
    return assistant_service.list_history(patient_id)


@router.post(
    "/{patient_id}/assistant/messages",
    response_model=AssistantMessageOut,
    status_code=status.HTTP_201_CREATED,
)
def send_assistant_message(
    patient_id: uuid.UUID,
    payload: AssistantMessageCreate,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """Sends the patient's message and returns the assistant's reply (the
    reply is the response body — the user's own message was already
    persisted as a side effect and is visible via GET .../messages)."""
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)

    try:
        result = assistant_service.send_message(patient_id, payload.content)
    except AssistantUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return result.message
