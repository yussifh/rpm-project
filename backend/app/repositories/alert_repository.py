"""
AlertRepository — raw queries against `alerts`.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.enums import AlertStatus


class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, alert_id: uuid.UUID) -> Alert | None:
        return self.db.get(Alert, alert_id)

    def list_for_patient(self, patient_id: uuid.UUID, status: AlertStatus | None = None) -> list[Alert]:
        stmt = select(Alert).where(Alert.patient_id == patient_id)
        if status is not None:
            stmt = stmt.where(Alert.status == status)
        stmt = stmt.order_by(Alert.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def list_all(self, status: AlertStatus | None = None, skip: int = 0, limit: int = 100) -> list[Alert]:
        stmt = select(Alert)
        if status is not None:
            stmt = stmt.where(Alert.status == status)
        stmt = stmt.order_by(Alert.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def find_active_by_title(self, patient_id: uuid.UUID, title: str) -> Alert | None:
        """An unresolved alert for this patient with this exact title, if
        one exists — used for alert deduplication (see VitalsService.
        _raise_alert). Deliberately keyed on "still unresolved" rather
        than a time window: once admin resolves the existing alert, a
        fresh threshold/AI crossing correctly raises a new one regardless
        of how much time has passed, and this avoids comparing a
        tz-aware cutoff against created_at, which isn't reliably
        tz-aware coming back from every database backend."""
        stmt = (
            select(Alert)
            .where(Alert.patient_id == patient_id, Alert.title == title, Alert.status != AlertStatus.RESOLVED)
            .order_by(Alert.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def create(self, alert: Alert) -> Alert:
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def save(self, alert: Alert) -> Alert:
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
