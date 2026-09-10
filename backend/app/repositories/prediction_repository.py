"""
PredictionRepository — raw queries against `risk_predictions`.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prediction import RiskPrediction


class PredictionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_patient(self, patient_id: uuid.UUID, disease_type=None) -> list[RiskPrediction]:
        stmt = select(RiskPrediction).where(RiskPrediction.patient_id == patient_id)
        if disease_type is not None:
            stmt = stmt.where(RiskPrediction.disease_type == disease_type)
        stmt = stmt.order_by(RiskPrediction.predicted_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def find_by_patient_disease_vital(
        self, patient_id: uuid.UUID, disease_type, source_vital_id: uuid.UUID
    ) -> RiskPrediction | None:
        stmt = (
            select(RiskPrediction)
            .where(
                RiskPrediction.patient_id == patient_id,
                RiskPrediction.disease_type == disease_type,
                RiskPrediction.source_vital_id == source_vital_id,
            )
            .order_by(RiskPrediction.predicted_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def create(self, prediction: RiskPrediction) -> RiskPrediction:
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction
