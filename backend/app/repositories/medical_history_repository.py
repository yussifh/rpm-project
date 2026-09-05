"""
MedicalHistoryRepository — raw queries against `medical_history_entries`.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.medical_history import MedicalHistoryEntry


class MedicalHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_patient(self, patient_id: uuid.UUID) -> list[MedicalHistoryEntry]:
        stmt = (
            select(MedicalHistoryEntry)
            .where(MedicalHistoryEntry.patient_id == patient_id)
            .order_by(MedicalHistoryEntry.diagnosed_date.desc().nulls_last())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, entry: MedicalHistoryEntry) -> MedicalHistoryEntry:
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry
