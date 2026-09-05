"""
MedicationService — business logic for prescriptions (Medication) and
adherence tracking (MedicationLog).
"""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.medication import Medication, MedicationLog
from app.repositories.medication_repository import MedicationRepository
from app.schemas.medication import MedicationCreate, MedicationLogCreate, MedicationUpdate
from app.services.audit_service import AuditService


class MedicationService:
    def __init__(self, db: Session):
        self.db = db
        self.medications = MedicationRepository(db)
        self.audit = AuditService(db)

    def list_for_patient(self, patient_id: uuid.UUID, active_only: bool = False) -> list[Medication]:
        return self.medications.list_by_patient(patient_id, active_only=active_only)

    def get_by_id(self, medication_id: uuid.UUID) -> Medication:
        medication = self.medications.get_by_id(medication_id)
        if not medication:
            raise NotFoundError("Medication", str(medication_id))
        return medication

    def add(
        self,
        patient_id: uuid.UUID,
        data: MedicationCreate,
        actor_user_id: uuid.UUID | None = None,
    ) -> Medication:
        medication = Medication(
            patient_id=patient_id,
            name=data.name,
            dosage=data.dosage,
            frequency=data.frequency,
            instructions=data.instructions,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        created = self.medications.create(medication)
        self.audit.log(
            action="ADD_MEDICATION",
            entity_type="Medication",
            entity_id=created.id,
            user_id=actor_user_id,
            metadata={"patient_id": str(patient_id), "name": data.name, "dosage": data.dosage},
        )
        return created

    def update(self, medication: Medication, data: MedicationUpdate) -> Medication:
        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(medication, field, value)
        return self.medications.save(medication)

    def log_dose(self, medication_id: uuid.UUID, data: MedicationLogCreate) -> MedicationLog:
        log = MedicationLog(
            medication_id=medication_id,
            scheduled_at=data.scheduled_at,
            status=data.status,
            taken_at=data.taken_at,
        )
        return self.medications.create_log(log)

    def list_logs(self, medication_id: uuid.UUID) -> list[MedicationLog]:
        return self.medications.list_logs(medication_id)
