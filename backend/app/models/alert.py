"""
Alert — the early-warning record generated either by threshold rules
(e.g. BP > 180/120) or by an AI prediction crossing a risk threshold.

Design decision: an Alert can optionally reference the VitalReading and/or
RiskPrediction that triggered it (both nullable FKs), so the origin of
every alert is traceable without forcing every alert to have both. There
is no doctor role in this system — alerts are visible to the patient
themself and to admin, and have a lifecycle (new -> acknowledged ->
resolved) so nothing raised silently disappears without action being
logged.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import AlertSeverity, AlertStatus
from app.models.mixins import TimestampMixin
from app.models.types import PortableUUID, str_enum_column


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False
    )
    related_vital_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("vital_readings.id", ondelete="SET NULL"), nullable=True
    )
    related_prediction_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("risk_predictions.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        str_enum_column(AlertSeverity, "alert_severity"), nullable=False, index=True
    )
    status: Mapped[AlertStatus] = mapped_column(
        str_enum_column(AlertStatus, "alert_status"), default=AlertStatus.NEW, nullable=False, index=True
    )

    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # True when this alert was CRITICAL and the patient had an emergency
    # contact on file at the time it fired — see
    # app/services/emergency_contact_service.py. Kept on the alert itself
    # (not just an audit log entry) so the alert list can show "family
    # notified" directly without a join.
    emergency_contact_notified: Mapped[bool] = mapped_column(default=False, nullable=False)

    # --- Relationships ---
    patient: Mapped["PatientProfile"] = relationship(back_populates="alerts")
    related_vital: Mapped["VitalReading"] = relationship(back_populates="triggered_alerts")
    related_prediction: Mapped["RiskPrediction"] = relationship(back_populates="triggered_alerts")

    def __repr__(self) -> str:
        return f"<Alert {self.severity} - {self.status} - patient={self.patient_id}>"
