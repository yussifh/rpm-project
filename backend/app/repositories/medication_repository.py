"""
MedicationRepository — raw queries against `medications` and
`medication_logs`.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.medication import Medication, MedicationLog


class MedicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, medication_id: uuid.UUID) -> Medication | None:
        return self.db.get(Medication, medication_id)

    def list_by_patient(self, patient_id: uuid.UUID, active_only: bool = False) -> list[Medication]:
        stmt = select(Medication).where(Medication.patient_id == patient_id)
        if active_only:
            stmt = stmt.where(Medication.is_active.is_(True))
        stmt = stmt.order_by(Medication.start_date.desc())
        return list(self.db.execute(stmt).scalars().all())

    def create(self, medication: Medication) -> Medication:
        self.db.add(medication)
        self.db.commit()
        self.db.refresh(medication)
        return medication

    def save(self, medication: Medication) -> Medication:
        self.db.add(medication)
        self.db.commit()
        self.db.refresh(medication)
        return medication

    def create_log(self, log: MedicationLog) -> MedicationLog:
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_logs(self, medication_id: uuid.UUID) -> list[MedicationLog]:
        stmt = (
            select(MedicationLog)
            .where(MedicationLog.medication_id == medication_id)
            .order_by(MedicationLog.scheduled_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())
