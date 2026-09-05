"""
MedicalHistoryService — business logic for structured medical history
entries. Write access is restricted to admin at the router layer via
ensure_can_write_clinical_entry; this service assumes that check already
passed.
"""

import uuid

from sqlalchemy.orm import Session

from app.models.medical_history import MedicalHistoryEntry
from app.repositories.medical_history_repository import MedicalHistoryRepository
from app.schemas.medical_history import MedicalHistoryCreate


class MedicalHistoryService:
    def __init__(self, db: Session):
        self.db = db
        self.history = MedicalHistoryRepository(db)

    def list_for_patient(self, patient_id: uuid.UUID) -> list[MedicalHistoryEntry]:
        return self.history.list_by_patient(patient_id)

    def add_entry(
        self, patient_id: uuid.UUID, data: MedicalHistoryCreate, recorded_by: str | None
    ) -> MedicalHistoryEntry:
        entry = MedicalHistoryEntry(
            patient_id=patient_id,
            condition_name=data.condition_name,
            diagnosed_date=data.diagnosed_date,
            notes=data.notes,
            recorded_by=recorded_by,
        )
        return self.history.create(entry)
