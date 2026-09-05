"""
PatientRepository — raw queries against `patient_profiles`, isolated from
service-layer business logic.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.patient import PatientProfile


class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, patient_id: uuid.UUID) -> PatientProfile | None:
        stmt = select(PatientProfile).options(joinedload(PatientProfile.user)).where(
            PatientProfile.id == patient_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_user_id(self, user_id: uuid.UUID) -> PatientProfile | None:
        stmt = select(PatientProfile).where(PatientProfile.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self, skip: int = 0, limit: int = 50) -> list[PatientProfile]:
        stmt = select(PatientProfile).options(joinedload(PatientProfile.user)).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def save(self, patient: PatientProfile) -> PatientProfile:
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient
