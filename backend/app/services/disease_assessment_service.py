import uuid

from sqlalchemy.orm import Session

from app.models.disease_assessment import DiseaseAssessment
from app.models.enums import DiseaseType
from app.repositories.disease_assessment_repository import DiseaseAssessmentRepository


class DiseaseAssessmentService:
    def __init__(self, db: Session):
        self.db = db
        self.assessments = DiseaseAssessmentRepository(db)

    def submit(self, patient_id: uuid.UUID, disease_type: DiseaseType, symptoms: dict) -> DiseaseAssessment:
        assessment = DiseaseAssessment(patient_id=patient_id, disease_type=disease_type, symptoms=symptoms)
        return self.assessments.create(assessment)

    def list_for_patient(self, patient_id: uuid.UUID) -> list[DiseaseAssessment]:
        return self.assessments.list_for_patient(patient_id)
