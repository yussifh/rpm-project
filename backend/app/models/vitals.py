"""
VitalReading — the core time-series table this entire system is built on.

Design decision: all vital types (BP, glucose, heart rate, SpO2, temp) live
in ONE wide table rather than one table per vital type. Rationale:
  1. Readings are typically captured together in a single check-in event
     (a patient logs BP + heart rate + glucose at once).
  2. The AI prediction service needs a combined feature row per timestamp
     anyway — a wide table avoids expensive joins/pivots at inference time.
  3. Nullable columns are acceptable here since not every reading includes
     every vital (e.g. a glucose-only entry for a diabetic patient).

Indexed on (patient_id, recorded_at) since the dominant query pattern is
"latest N readings for patient X" and "readings for patient X in date range".
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import VitalSource
from app.models.mixins import TimestampMixin
from app.models.types import PortableUUID, str_enum_column


class VitalReading(Base, TimestampMixin):
    __tablename__ = "vital_readings"
    __table_args__ = (
        Index("ix_vitals_patient_recorded", "patient_id", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False
    )

    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[VitalSource] = mapped_column(
        str_enum_column(VitalSource, "vital_source"), default=VitalSource.MANUAL, nullable=False
    )

    # --- Cardiovascular / Hypertension ---
    blood_pressure_systolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blood_pressure_diastolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heart_rate_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Diabetes ---
    blood_glucose_mg_dl: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Extra Pima-dataset measurements the diabetes model now uses — see
    # app/ai_engine/feature_schema.py (DIABETES_FEATURES). Kept nullable
    # since not every reading includes every measurement.
    skin_thickness_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    serum_insulin_mu_u_ml: Mapped[float | None] = mapped_column(Float, nullable=True)
    diabetes_pedigree_function: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Optional manual substitution inputs: let a patient enter the missing
    # body-metric/Age features directly instead of deriving them from the
    # profile (height/weight/DOB). When present these take priority; when
    # blank the profile-derived values are used (see prediction_service).
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    bmi: Mapped[float | None] = mapped_column(Float, nullable=True)
    age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- General / Stroke risk signals ---
    spo2_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    respiratory_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Shared across stroke / diabetes / hypertension care plans ---
    # Weight trend is a meaningful signal for all three tracked conditions
    # (fluid retention in hypertension/stroke risk, unexplained loss/gain
    # in diabetes management), so it lives here alongside the other
    # general vitals rather than being disease-specific.
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    notes: Mapped[str | None] = mapped_column(nullable=True)

    # --- Relationships ---
    patient: Mapped["PatientProfile"] = relationship(back_populates="vitals")
    triggered_alerts: Mapped[list["Alert"]] = relationship(back_populates="related_vital")

    def __repr__(self) -> str:
        return f"<VitalReading patient={self.patient_id} at={self.recorded_at}>"
