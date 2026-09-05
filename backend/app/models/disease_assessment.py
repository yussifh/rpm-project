"""
DiseaseAssessment — a patient's disease-specific symptom checklist
submission (e.g. the stroke FAST assessment, diabetes symptom check,
hypertension symptom check described in the RPM workflow spec).

Design decision: `symptoms` is stored as flexible JSON (a dict of
symptom-key -> value, e.g. {"face_drooping": true, "arm_weakness": "left"})
rather than one column per possible symptom across three diseases. This
matches the "flexible design" the workflow spec itself recommends: the
set of relevant symptoms differs per disease, and the frontend is the
source of truth for which checklist to render for a given disease_type —
the backend just stores whatever structured answers it's given.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import DiseaseType
from app.models.types import PortableJSON, PortableUUID, str_enum_column


class DiseaseAssessment(Base):
    __tablename__ = "disease_assessments"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Reuses the same Postgres enum type as risk_predictions.disease_type
    # (created in the 0001 migration) rather than minting a duplicate type.
    disease_type: Mapped[DiseaseType] = mapped_column(str_enum_column(DiseaseType, "disease_type"), nullable=False)
    symptoms: Mapped[dict] = mapped_column(PortableJSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    patient: Mapped["PatientProfile"] = relationship()

    def __repr__(self) -> str:
        return f"<DiseaseAssessment patient={self.patient_id} disease={self.disease_type}>"
