"""
MedicalHistoryEntry — discrete, dated clinical history items (past
diagnoses, surgeries, family history), distinct from the free-text summary
on PatientProfile. Modeled as its own table (not a JSON blob) so entries
can be queried, filtered, and displayed as a structured timeline in the UI.
"""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin
from app.models.types import PortableUUID


class MedicalHistoryEntry(Base, TimestampMixin):
    __tablename__ = "medical_history_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False
    )

    condition_name: Mapped[str] = mapped_column(String(200), nullable=False)
    diagnosed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[str | None] = mapped_column(String(150), nullable=True)  # admin name/id snapshot

    # --- Relationships ---
    patient: Mapped["PatientProfile"] = relationship(back_populates="medical_history")

    def __repr__(self) -> str:
        return f"<MedicalHistoryEntry {self.condition_name}>"
