"""
ReportService — the ORM-facing adapter that gathers a patient's profile,
recent vitals, active medications, recent alerts, and latest AI
predictions into the plain dict shape app.reporting.pdf_builder expects,
then calls it to produce PDF bytes.
"""

import csv
import io
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

    CSV_COLUMNS = [
        "Date & Time",
        "Systolic BP (mmHg)",
        "Diastolic BP (mmHg)",
        "Heart Rate (bpm)",
        "Blood Glucose (mg/dL)",
        "Diabetes Pedigree Function",
        "SpO2 (%)",
        "Temperature (°C)",
        "Respiratory Rate (bpm)",
        "Weight (kg)",
        "Height (cm)",
        "BMI",
        "Age (years)",
        "Notes",
        "Diabetes Risk",
        "Hypertension Risk",
        "Stroke Risk",
    ]

    def generate_vitals_history_csv(self, patient_id: uuid.UUID) -> bytes:
        """Exports the patient's ENTIRE vitals history as a spreadsheet
        (.csv) file they can keep and open in Excel/share with a clinician.
        Unlike the PDF summary (which is capped at the 10 latest readings),
        this includes every reading ever logged, in chronological order.
        A UTF-8 BOM is prepended so Excel renders the units column headers
        (e.g. °C) correctly."""
        patient = self.patients.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("PatientProfile", str(patient_id))

        # Page through the whole history — a patient with years of
        # self-reported readings may exceed the repository's page size.
        all_readings: list = []
        offset = 0
        while True:
            page = self.vitals.list_for_patient(patient_id, skip=offset, limit=500)
            if not page:
                break
            all_readings.extend(page)
            offset += len(page)
            if len(page) < 500:
                break

        # Chronological order makes the file read like a proper timeline.
        all_readings.sort(key=lambda v: v.recorded_at)

        # Map each reading to the AI risk predictions generated from it so
        # the exported file mirrors the History table's Risk column (one
        # level per tracked condition). A reading that was never assessed
        # simply gets empty risk cells.
        all_predictions = self.predictions.list_for_patient(patient_id)
        risk_by_vital: dict[uuid.UUID, dict[str, tuple[str, float]]] = {}
        for p in all_predictions:
            if p.source_vital_id is None:
                continue
            risk_by_vital.setdefault(p.source_vital_id, {})[p.disease_type.value] = (
                p.risk_level.value,
                p.risk_score,
            )

        def risk_cell(entry: tuple[str, float] | None) -> str:
            return f"{entry[0]} ({entry[1]:.3f})" if entry else ""

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(self.CSV_COLUMNS)
        for v in all_readings:
            risks = risk_by_vital.get(v.id, {})
            writer.writerow(
                [
                    v.recorded_at.strftime("%Y-%m-%d %H:%M"),
                    v.blood_pressure_systolic if v.blood_pressure_systolic is not None else "",
                    v.blood_pressure_diastolic if v.blood_pressure_diastolic is not None else "",
                    v.heart_rate_bpm if v.heart_rate_bpm is not None else "",
                    v.blood_glucose_mg_dl if v.blood_glucose_mg_dl is not None else "",
                    v.diabetes_pedigree_function if v.diabetes_pedigree_function is not None else "",
                    v.spo2_percent if v.spo2_percent is not None else "",
                    v.temperature_celsius if v.temperature_celsius is not None else "",
                    v.respiratory_rate if v.respiratory_rate is not None else "",
                    v.weight_kg if v.weight_kg is not None else "",
                    v.height_cm if v.height_cm is not None else "",
                    v.bmi if v.bmi is not None else "",
                    v.age_years if v.age_years is not None else "",
                    (v.notes or "").replace("\n", " "),
                    risk_cell(risks.get("diabetes")),
                    risk_cell(risks.get("hypertension")),
                    risk_cell(risks.get("stroke")),
                ]
            )

        # utf-8-sig = UTF-8 with BOM, so Excel detects the encoding.
        return buffer.getvalue().encode("utf-8-sig")

    def _latest_prediction_per_disease(self, patient_id: uuid.UUID):
        all_predictions = self.predictions.list_for_patient(patient_id)  # already newest-first
        seen = set()
        latest = []
        for prediction in all_predictions:
            if prediction.disease_type not in seen:
                seen.add(prediction.disease_type)
                latest.append(prediction)
        return latest
