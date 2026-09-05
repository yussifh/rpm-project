"""
PatientService — business logic for patient profile access/updates.
Authorization (who can see/edit which patient) is enforced by the caller
via app.core.authorization, not duplicated here.
"""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.patient import PatientProfile
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientProfileUpdate


class PatientService:
    def __init__(self, db: Session):
        self.db = db
        self.patients = PatientRepository(db)

    def get_by_id(self, patient_id: uuid.UUID) -> PatientProfile:
        patient = self.patients.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("PatientProfile", str(patient_id))
        return patient

    def get_by_user_id(self, user_id: uuid.UUID) -> PatientProfile:
        patient = self.patients.get_by_user_id(user_id)
        if not patient:
            raise NotFoundError("PatientProfile", str(user_id))
        return patient

    def list_for_admin(self, skip: int = 0, limit: int = 50) -> list[PatientProfile]:
        return self.patients.list_all(skip=skip, limit=limit)

    def update_profile(self, patient: PatientProfile, data: PatientProfileUpdate) -> PatientProfile:
        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(patient, field, value)
        return self.patients.save(patient)
