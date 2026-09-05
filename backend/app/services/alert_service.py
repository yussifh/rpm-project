"""
AlertService — creation and lifecycle management (new -> acknowledged ->
resolved) of AI/threshold-generated alerts, plus role-scoped listing.

Alert CREATION is triggered internally by VitalsService (threshold rules
and/or AI-prediction risk crossing a threshold) — there is no public
"create an alert" endpoint, since alerts should only ever originate from
the system's own monitoring logic, not be freely authored by a user.

There is no doctor role in this system: a patient can VIEW their own
alerts (visibility is the point of an early-warning system), but
acknowledging/resolving an alert is an admin action — treated as a
data-quality/triage action on the system's output, not a clinical one.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import InsufficientPermissionsError, NotFoundError
from app.models.alert import Alert
from app.models.enums import AlertSeverity, AlertStatus, UserRole
from app.models.user import User
from app.repositories.alert_repository import AlertRepository
from app.services.audit_service import AuditService


class AlertService:
    def __init__(self, db: Session):
        self.db = db
        self.alerts = AlertRepository(db)
        self.audit = AuditService(db)

    def create_alert(
        self,
        patient_id: uuid.UUID,
        severity: AlertSeverity,
        title: str,
        message: str,
        related_vital_id: uuid.UUID | None = None,
        related_prediction_id: uuid.UUID | None = None,
    ) -> Alert:
        alert = Alert(
            patient_id=patient_id,
            severity=severity,
            title=title,
            message=message,
            related_vital_id=related_vital_id,
            related_prediction_id=related_prediction_id,
        )
        return self.alerts.create(alert)

    def list_for_current_user(self, current_user: User, status: AlertStatus | None = None) -> list[Alert]:
        if current_user.role == UserRole.ADMIN:
            return self.alerts.list_all(status=status)
        if current_user.role == UserRole.PATIENT and current_user.patient_profile:
            return self.alerts.list_for_patient(current_user.patient_profile.id, status=status)
        return []

    def acknowledge(self, alert_id: uuid.UUID, current_user: User) -> Alert:
        alert = self._get_and_authorize(alert_id, current_user)
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        updated = self.alerts.save(alert)
        self.audit.log(
            action="ACKNOWLEDGE_ALERT",
            entity_type="Alert",
            entity_id=alert_id,
            user_id=current_user.id,
        )
        return updated

    def resolve(self, alert_id: uuid.UUID, current_user: User) -> Alert:
        alert = self._get_and_authorize(alert_id, current_user)
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        updated = self.alerts.save(alert)
        self.audit.log(
            action="RESOLVE_ALERT",
            entity_type="Alert",
            entity_id=alert_id,
            user_id=current_user.id,
        )
        return updated

    def _get_and_authorize(self, alert_id: uuid.UUID, current_user: User) -> Alert:
        """Admin-only: closing out an alert is a triage action on the
        system's own output, not something a patient self-service or a
        doctor performs (no doctor role exists)."""
        alert = self.alerts.get_by_id(alert_id)
        if not alert:
            raise NotFoundError("Alert", str(alert_id))

        if current_user.role == UserRole.ADMIN:
            return alert
        raise InsufficientPermissionsError()
