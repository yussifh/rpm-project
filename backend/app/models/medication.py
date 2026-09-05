"""
Medication + MedicationLog — separates the medication RECORD (what/how
much/how often) from ADHERENCE TRACKING (did the patient actually take it).

Design decision: this is a classic one-to-many split. `Medication` is the
record (relatively static, self-reported by the patient — there is no
doctor role in this system to prescribe it). `MedicationLog` is an
append-only adherence trail (one row per dose event), which is what powers
medication-tracking analytics/charts without ever mutating the medication
record itself.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import MedicationStatus
from app.models.mixins import TimestampMixin
from app.models.types import PortableUUID, str_enum_column


class Medication(Base, TimestampMixin):
    __tablename__ = "medications"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "500mg"
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "twice daily"
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --- Relationships ---
    patient: Mapped["PatientProfile"] = relationship(back_populates="medications")
    logs: Mapped[list["MedicationLog"]] = relationship(
        back_populates="medication", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Medication {self.name} ({self.dosage})>"


class MedicationLog(Base, TimestampMixin):
    __tablename__ = "medication_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    medication_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("medications.id", ondelete="CASCADE"), nullable=False
    )

    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[MedicationStatus] = mapped_column(
        str_enum_column(MedicationStatus, "medication_status"), nullable=False
    )
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Relationships ---
    medication: Mapped["Medication"] = relationship(back_populates="logs")

    def __repr__(self) -> str:
        return f"<MedicationLog {self.status} at={self.scheduled_at}>"
