"""
ReportService — the ORM-facing adapter that gathers a patient's profile,
recent vitals, active medications, recent alerts, and latest AI
predictions into the plain dict shape app.reporting.pdf_builder expects,
then calls it to produce PDF bytes.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.reporting.pdf_builder import ReportData, build_patient_summary_pdf
from app.repositories.alert_repository import AlertRepository
from app.repositories.medication_repository import MedicationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.vitals_repository import VitalsRepository

VITALS_LIMIT = 10
ALERTS_LIMIT = 10


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.patients = PatientRepository(db)
        self.vitals = VitalsRepository(db)
        self.medications = MedicationRepository(db)
        self.alerts = AlertRepository(db)
        self.predictions = PredictionRepository(db)

    def generate_patient_summary(self, patient_id: uuid.UUID) -> bytes:
        patient = self.patients.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("PatientProfile", str(patient_id))

        recent_vitals = self.vitals.list_for_patient(patient_id, limit=VITALS_LIMIT)
        active_medications = self.medications.list_by_patient(patient_id, active_only=True)
        recent_alerts = self.alerts.list_for_patient(patient_id)[:ALERTS_LIMIT]
        latest_predictions = self._latest_prediction_per_disease(patient_id)

        report_data: ReportData = {
            "patient_name": patient.user.full_name,
            "date_of_birth": patient.date_of_birth.isoformat(),
            "gender": patient.gender.value,
            "blood_group": patient.blood_group or "",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "vitals": [
                {
                    "recorded_at": v.recorded_at.strftime("%Y-%m-%d %H:%M"),
                    "blood_pressure": (
                        f"{v.blood_pressure_systolic}/{v.blood_pressure_diastolic}"
                        if v.blood_pressure_systolic and v.blood_pressure_diastolic
                        else "—"
                    ),
                    "heart_rate": str(v.heart_rate_bpm) if v.heart_rate_bpm else "—",
                    "glucose": str(v.blood_glucose_mg_dl) if v.blood_glucose_mg_dl else "—",
                    "spo2": str(v.spo2_percent) if v.spo2_percent else "—",
                }
                for v in recent_vitals
            ],
            "medications": [
                {
                    "name": m.name,
                    "dosage": m.dosage,
                    "frequency": m.frequency,
                    "status": "Active" if m.is_active else "Inactive",
                }
                for m in active_medications
            ],
            "alerts": [
                {
                    "title": a.title,
                    "severity": a.severity.value,
                    "status": a.status.value,
                    "created_at": a.created_at.strftime("%Y-%m-%d %H:%M"),
                }
                for a in recent_alerts
            ],
            "predictions": [
                {
                    "disease_type": p.disease_type.value,
                    "risk_level": p.risk_level.value,
                    "risk_score": f"{p.risk_score:.2f}",
                    "predicted_at": p.predicted_at.strftime("%Y-%m-%d %H:%M"),
                }
                for p in latest_predictions
            ],
        }

        return build_patient_summary_pdf(report_data)

    def _latest_prediction_per_disease(self, patient_id: uuid.UUID):
        all_predictions = self.predictions.list_for_patient(patient_id)  # already newest-first
        seen = set()
        latest = []
        for prediction in all_predictions:
            if prediction.disease_type not in seen:
                seen.add(prediction.disease_type)
                latest.append(prediction)
        return latest
