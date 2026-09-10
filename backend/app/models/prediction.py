"""
RiskPrediction — stores the output of the AI risk models (stroke, diabetes,
hypertension) for full traceability and historical trend charting.

Design decision: `input_features` (JSONB) stores a snapshot of exactly what
was fed into the model at inference time. This is critical for a healthcare
AI system — if a patient or admin questions why a prediction was made, or
the model is retrained later, you can always reconstruct what the model saw,
independent of whatever the VitalReading table looks like today. This is
an auditability/explainability requirement, not just nice-to-have.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import DiseaseType, RiskLevel
from app.models.mixins import TimestampMixin
from app.models.types import PortableJSON, PortableUUID, str_enum_column


class RiskPrediction(Base, TimestampMixin):
    __tablename__ = "risk_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False
    )
    source_vital_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("vital_readings.id", ondelete="SET NULL"), nullable=True
    )

    disease_type: Mapped[DiseaseType] = mapped_column(
        str_enum_column(DiseaseType, "disease_type"), nullable=False, index=True
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 - 1.0 probability
    risk_level: Mapped[RiskLevel] = mapped_column(str_enum_column(RiskLevel, "risk_level"), nullable=False)

    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "real-framingham-heart-study-n4240-clean~3800" or
    # "real-pima-n724+bootstrap-augmented-n2172" — surfaced in the UI so a
    # clinician looking at a score knows how much weight it can bear.
    # Not just an internal note: this is what stands between "AI decision
    # support" and an unlabeled black-box number.
    data_source: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown")
    input_features: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    # Human-readable explanation of the score — e.g. "Blood pressure has
    # remained above 170/110 mmHg for 3 consecutive readings", "Medication
    # missed twice this week". Generated alongside the score at predict
    # time (see PredictionService._build_reasons), stored as a plain list
    # of strings so the UI can render it directly without re-deriving it.
    reasons: Mapped[list] = mapped_column(PortableJSON, nullable=False, default=list)
    # Patient-facing clinical recommendations — lifestyle/monitoring/
    # professional-referral guidance derived from THIS prediction's own
    # reasons, risk level, and vitals pattern (see PredictionService.
    # _build_recommendations). Stored alongside reasons, at the same
    # prediction-time snapshot, for the same auditability reason: what
    # guidance was actually given for this specific reading, not a
    # live-recalculated suggestion that could silently change later.
    # NEVER contains medication start/stop/dosage guidance — see that
    # method's docstring for the hard rule behind this.
    recommendations: Mapped[list] = mapped_column(PortableJSON, nullable=False, default=list)

    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # --- Relationships ---
    patient: Mapped["PatientProfile"] = relationship(back_populates="risk_predictions")
    triggered_alerts: Mapped[list["Alert"]] = relationship(back_populates="related_prediction")

    def __repr__(self) -> str:
        return f"<RiskPrediction {self.disease_type} score={self.risk_score}>"
