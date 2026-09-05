"""
EmergencyContactService — notifies a patient's emergency contact when a
CRITICAL alert fires.

Design decision (simulated, not a real SMS/email send): this system has
no configured SMS/email gateway (no Twilio/SES credentials, no such
setting exists in app.core.config), and wiring one up is an
infrastructure decision for a real deployment, not a demo project. Rather
than silently doing nothing, or pretending to send something with no
record of it, this logs the notification explicitly (server log + audit
trail) and marks the alert as notified — so the FEATURE (deciding who
should be notified, when, and recording that decision) is real and
testable, while the actual delivery mechanism is an intentionally-marked
integration point. Swapping in a real provider later means implementing
`_deliver()` — the decision logic above it doesn't change.

Design decision (CRITICAL only, not WARNING): this mirrors real systems
(e.g. Tellihealth notifies family specifically for severe events like a
dangerous drop in blood sugar) — a caregiver alerted on every WARNING-level
reading would quickly start ignoring the channel entirely, defeating the
point of having it for the events that actually matter.
"""

import logging

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.enums import AlertSeverity
from app.models.patient import PatientProfile
from app.repositories.alert_repository import AlertRepository
from app.services.audit_service import AuditService

logger = logging.getLogger("app.emergency_contact")


class EmergencyContactService:
    def __init__(self, db: Session):
        self.db = db
        self.alerts = AlertRepository(db)
        self.audit = AuditService(db)

    def notify_if_applicable(self, patient: PatientProfile, alert: Alert) -> bool:
        """Returns True if a notification was recorded, False otherwise
        (not critical, or no emergency contact on file — both are normal,
        expected outcomes, not errors)."""
        if alert.severity != AlertSeverity.CRITICAL:
            return False

        if not patient.emergency_contact_name or not patient.emergency_contact_phone:
            return False

        self._deliver(patient, alert)

        alert.emergency_contact_notified = True
        self.alerts.save(alert)

        self.audit.log(
            action="EMERGENCY_CONTACT_NOTIFIED",
            entity_type="Alert",
            entity_id=alert.id,
            user_id=None,  # system-triggered, not a specific user's action
            metadata={
                "patient_id": str(patient.id),
                "contact_name": patient.emergency_contact_name,
                "alert_title": alert.title,
            },
        )
        return True

    def _deliver(self, patient: PatientProfile, alert: Alert) -> None:
        """The actual send. See module docstring — this is the
        intentional integration point for a real SMS/email provider.
        For now, delivery is simulated via a structured log line."""
        logger.warning(
            "[SIMULATED EMERGENCY CONTACT NOTIFICATION] Would notify %s at %s: "
            "'%s' — %s (patient_id=%s, alert_id=%s)",
            patient.emergency_contact_name,
            patient.emergency_contact_phone,
            alert.title,
            alert.message,
            patient.id,
            alert.id,
        )
