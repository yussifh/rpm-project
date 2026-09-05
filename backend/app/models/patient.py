"""
Patient-specific profile data, 1:1 with User where role == PATIENT.

There is no doctor role in this system — `primary_condition` (below) is
assigned by admin, and all clinical/AI features (predictions, trends,
assistant) key off the patient's own data, not a doctor relationship.
"""

import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import DiseaseType, Gender
from app.models.mixins import TimestampMixin
from app.models.types import PortableUUID, str_enum_column


class PatientProfile(Base, TimestampMixin):
    __tablename__ = "patient_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender] = mapped_column(str_enum_column(Gender, "gender"), nullable=False)
    blood_group: Mapped[str | None] = mapped_column(String(5), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Admin-assigned primary condition — drives which vitals fields and
    # symptom-assessment checklist the patient sees (see disease_assessment
    # feature). Nullable: a newly-registered patient has none yet.
    primary_condition: Mapped[DiseaseType | None] = mapped_column(
        str_enum_column(DiseaseType, "patient_primary_condition"), nullable=True
    )

    emergency_contact_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Free-text summary shown on dashboards; detailed entries live in MedicalHistoryEntry
    chronic_conditions_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    user: Mapped["User"] = relationship(back_populates="patient_profile")

    vitals: Mapped[list["VitalReading"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    risk_predictions: Mapped[list["RiskPrediction"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    medications: Mapped[list["Medication"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    medical_history: Mapped[list["MedicalHistoryEntry"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PatientProfile {self.id}>"
