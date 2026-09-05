import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.disease_assessment import DiseaseAssessment


class DiseaseAssessmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, assessment: DiseaseAssessment) -> DiseaseAssessment:
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        return assessment

    def list_for_patient(self, patient_id: uuid.UUID, limit: int = 50) -> list[DiseaseAssessment]:
        stmt = (
            select(DiseaseAssessment)
            .where(DiseaseAssessment.patient_id == patient_id)
            .order_by(DiseaseAssessment.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_latest_for_patient(self, patient_id: uuid.UUID) -> DiseaseAssessment | None:
        stmt = (
            select(DiseaseAssessment)
            .where(DiseaseAssessment.patient_id == patient_id)
            .order_by(DiseaseAssessment.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()
