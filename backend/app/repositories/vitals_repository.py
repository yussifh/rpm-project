"""
VitalsRepository — data access for `vital_readings`. Originally created in
Module 5 as a minimal read-only helper for the prediction service; now
extended with the full create/list operations needed for the vitals
ingestion API (Module 6).
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.vitals import VitalReading


class VitalsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, vital_id: uuid.UUID) -> VitalReading | None:
        return self.db.get(VitalReading, vital_id)

    def get_latest_for_patient(self, patient_id: uuid.UUID) -> VitalReading | None:
        stmt = (
            select(VitalReading)
            .where(VitalReading.patient_id == patient_id)
            .order_by(VitalReading.recorded_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_patient(
        self,
        patient_id: uuid.UUID,
        start: datetime | None = None,
        end: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[VitalReading]:
        stmt = select(VitalReading).where(VitalReading.patient_id == patient_id)
        if start is not None:
            stmt = stmt.where(VitalReading.recorded_at >= start)
        if end is not None:
            stmt = stmt.where(VitalReading.recorded_at <= end)
        stmt = stmt.order_by(VitalReading.recorded_at.desc()).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, vital: VitalReading) -> VitalReading:
        self.db.add(vital)
        self.db.commit()
        self.db.refresh(vital)
        return vital
