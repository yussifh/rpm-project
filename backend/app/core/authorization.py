"""
Authorization helpers for patient-scoped clinical data.

Design decision: access to a given patient's records follows ONE rule,
reused everywhere (medical history, medications, vitals, predictions,
etc.) rather than re-implemented per-router:

    - ADMIN can access any patient's records
    - PATIENT can access only their own records

Centralizing this avoids the classic bug pattern where one endpoint
enforces the rule but a sibling endpoint forgets to.
"""

from fastapi import HTTPException, status

from app.models.enums import UserRole
from app.models.patient import PatientProfile
from app.models.user import User


def ensure_patient_access(current_user: User, patient: PatientProfile) -> None:
    if current_user.role == UserRole.ADMIN:
        return

    if current_user.role == UserRole.PATIENT:
        if current_user.patient_profile and patient.id == current_user.patient_profile.id:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only access your own records",
        )

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def ensure_can_write_clinical_entry(current_user: User, patient: PatientProfile) -> None:
    """Stricter check for WRITE actions on clinical entries (e.g. medical
    history). Only admin (data correction/entry) may write these — patients
    read their own records but don't author clinical history entries
    themselves; there is no doctor role to author them either."""
    if current_user.role == UserRole.ADMIN:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only an admin may perform this action",
    )
