"""
VitalsService — vitals ingestion PLUS the early-warning pipeline described
in the Module 1 system architecture diagram: every new reading is checked
against fast deterministic thresholds AND, for whichever condition(s) the
patient selected at entry time, fed through that condition's AI risk
model. Anything crossing a threshold becomes an Alert (and a Notification
to the patient themself).

Design decision (condition-based prediction): prediction is NOT run
automatically for all three diseases on every submission. The patient
explicitly selects which condition(s) a given vitals submission is for
(see VitalReadingCreate.conditions), and only those get a RiskPrediction.
This matches the system's own architecture principle — the AI Health
Assistant explains one condition's own data, and predicting a disease the
patient never selected would be exactly the "AI confusing conditions"
behavior the workflow spec explicitly rules out. Threshold-based alerts
are the exception: those run unconditionally regardless of condition
selection, since a dangerous raw vital sign (e.g. BP 195/125) is a safety
concern independent of which ML assessment the patient asked for.

Design decision (sync, not async): both checks run synchronously, inline,
on every vitals submission. For a system of this scale that's simple and
reliable — no message queue/worker infrastructure needed. It DOES mean up
to len(conditions) extra model inferences per vitals submission; if this
were scaling to a large patient population, the AI-prediction half would
move to an async worker queue (e.g. Celery/RQ) so vitals ingestion never
blocks on model inference. That tradeoff is noted here rather than hidden.

Two more things happen when an alert is raised (see _raise_alert):
- Deduplication: if this exact issue is already open and unresolved for
  the patient, no new alert is raised — see AlertRepository.
  find_active_by_title.
- Emergency contact notification: a CRITICAL alert triggers a (simulated)
  notification to the patient's emergency contact, if one is on file —
  see app/services/emergency_contact_service.py.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import InsufficientDataError, NotFoundError
from app.models.enums import AlertSeverity, DiseaseType, RiskLevel
from app.models.patient import PatientProfile
from app.models.prediction import RiskPrediction
from app.models.vitals import VitalReading
from app.repositories.patient_repository import PatientRepository
from app.repositories.vitals_repository import VitalsRepository
from app.schemas.vitals import VitalReadingCreate
from app.services.alert_rules import evaluate_vital_thresholds
from app.services.alert_service import AlertService
from app.services.emergency_contact_service import EmergencyContactService
from app.services.notification_service import NotificationService
from app.services.prediction_service import PredictionService
from app.services.trend_analysis import FIELD_CONFIG, DataPoint, classify_trend, forecast_trend

SEVERITY_MAP = {"warning": AlertSeverity.WARNING, "critical": AlertSeverity.CRITICAL}
AI_ALERT_RISK_LEVELS = {RiskLevel.HIGH, RiskLevel.CRITICAL}

# Clinical thresholds for disease-specific AI alerts that supplement
# the ML model's output. The diabetes model (trained on Pima Indian
# women) under-predicts for male patients with elevated glucose, so a
# hard clinical threshold catches cases the model misses.
DIABETES_GLUCOSE_CRITICAL = 300
DIABETES_GLUCOSE_WARNING = 200


@dataclass
class VitalSubmissionResult:
    vital: VitalReading
    predictions: list[RiskPrediction] = field(default_factory=list)
    # (disease, reason) pairs for selected conditions that couldn't get a
    # prediction this submission (e.g. missing BMI) — surfaced to the
    # patient rather than silently dropped.
    skipped: list[tuple[DiseaseType, str]] = field(default_factory=list)


class VitalsService:
    def __init__(self, db: Session):
        self.db = db
        self.vitals = VitalsRepository(db)
        self.patients = PatientRepository(db)
        self.alert_service = AlertService(db)
        self.notification_service = NotificationService(db)
        self.emergency_contact_service = EmergencyContactService(db)
        self.prediction_service = PredictionService(db)

    def list_for_patient(
        self, patient_id: uuid.UUID, start: datetime | None = None, end: datetime | None = None
    ) -> list[VitalReading]:
        return self.vitals.list_for_patient(patient_id, start=start, end=end)

    def get_trends(self, patient_id: uuid.UUID, days: int = 90):
        """Trend classification AND forward-looking forecast (see
        app.services.trend_analysis) for every vital field the patient has
        at least one reading for, over the requested window. Fields with
        zero readings in the window are omitted entirely rather than
        returned as an empty/insufficient-data placeholder — a chart with
        nothing to plot isn't useful to show.

        Returns a list of (TrendResult, ForecastResult) pairs — kept as
        two separate objects rather than merged, since they answer two
        different questions (what already happened vs. what might happen
        next) with independent confidence gating; see forecast_trend()'s
        docstring for why the forecast is intentionally allowed to fail
        safe on its own, separate from the trend classification.
        """
        start = datetime.now(timezone.utc) - timedelta(days=days)
        # limit=1000 comfortably covers "every reading in a 90-day window"
        # for a self-reported vitals app; list_for_patient's default
        # ordering (most-recent-first) doesn't matter here since
        # classify_trend/forecast_trend sort internally.
        readings = self.vitals.list_for_patient(patient_id, start=start, limit=1000)

        results = []
        for field_name in FIELD_CONFIG:
            points = [
                DataPoint(recorded_at=r.recorded_at, value=getattr(r, field_name))
                for r in readings
                if getattr(r, field_name) is not None
            ]
            if not points:
                continue
            trend = classify_trend(field_name, points)
            forecast = forecast_trend(field_name, points)
            results.append((trend, forecast))
        return results

    def record_reading(self, patient_id: uuid.UUID, data: VitalReadingCreate) -> VitalSubmissionResult:
        patient = self.patients.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("PatientProfile", str(patient_id))

        vital = VitalReading(
            patient_id=patient_id,
            recorded_at=data.recorded_at or datetime.now(timezone.utc),
            source=data.source,
            blood_pressure_systolic=data.blood_pressure_systolic,
            blood_pressure_diastolic=data.blood_pressure_diastolic,
            heart_rate_bpm=data.heart_rate_bpm,
            blood_glucose_mg_dl=data.blood_glucose_mg_dl,
            skin_thickness_mm=data.skin_thickness_mm,
            serum_insulin_mu_u_ml=data.serum_insulin_mu_u_ml,
            diabetes_pedigree_function=data.diabetes_pedigree_function,
            height_cm=data.height_cm,
            bmi=data.bmi,
            age_years=data.age_years,
            spo2_percent=data.spo2_percent,
            temperature_celsius=data.temperature_celsius,
            respiratory_rate=data.respiratory_rate,
            weight_kg=data.weight_kg,
            notes=data.notes,
        )
        vital = self.vitals.create(vital)

        self._run_threshold_checks(patient, vital)
        predictions, skipped = self._run_ai_early_warning(patient, vital, data.conditions)

        return VitalSubmissionResult(vital=vital, predictions=predictions, skipped=skipped)

    # --- Early-warning pipeline ---

    def _run_threshold_checks(self, patient: PatientProfile, vital: VitalReading) -> None:
        triggered = evaluate_vital_thresholds(
            systolic_bp=vital.blood_pressure_systolic,
            diastolic_bp=vital.blood_pressure_diastolic,
            heart_rate=vital.heart_rate_bpm,
            glucose=vital.blood_glucose_mg_dl,
            spo2=vital.spo2_percent,
        )
        for item in triggered:
            self._raise_alert(
                patient=patient,
                severity=SEVERITY_MAP[item["severity"]],
                title=item["title"],
                message=item["message"],
                related_vital_id=vital.id,
            )

    def _run_ai_early_warning(
        self, patient: PatientProfile, vital: VitalReading, conditions: list[DiseaseType]
    ) -> tuple[list[RiskPrediction], list[tuple[DiseaseType, str]]]:
        """Generates a separate prediction for each explicitly-selected
        condition (never all three blind) — see module docstring. Each
        condition is processed independently: one condition failing
        (e.g. missing BMI) doesn't block the others or the vitals save
        itself, it's just reported back as `skipped`."""
        predictions: list[RiskPrediction] = []
        skipped: list[tuple[DiseaseType, str]] = []

        for disease in conditions:
            try:
                prediction = self.prediction_service.predict(patient.id, disease)
            except InsufficientDataError as exc:
                skipped.append((disease, str(exc)))
                continue

            predictions.append(prediction)

            if prediction.risk_level in AI_ALERT_RISK_LEVELS:
                # Confirmation-over-time for AI alerts. The stroke and
                # hypertension models are tuned toward recall (they rarely
                # miss a real problem) at the cost of low precision
                # (~10-13% of high/critical flags are true positives — see
                # training_report.json). Alerting critically — which also
                # notifies the patient's emergency contact — on a SINGLE
                # such prediction would produce frequent false "contact
                # help now" alarms that erode trust and cause real alarm.
                # So a critical alert only escalates (CRITICAL + emergency
                # contact) when the SAME condition was already flagged
                # high/critical on the previous reading — a sustained
                # pattern, not a one-off. A first elevated prediction is
                # still surfaced, but as a WARNING with no emergency
                # contact escalation.
                sustained = self._previous_prediction_was_elevated(
                    patient.id, disease, prediction.id
                )
                if prediction.risk_level == RiskLevel.CRITICAL and sustained:
                    severity = AlertSeverity.CRITICAL
                else:
                    severity = AlertSeverity.WARNING

                self._raise_alert(
                    patient=patient,
                    severity=severity,
                    title=f"Elevated {disease.value.title()} Risk Detected",
                    message=(
                        f"AI model flagged {disease.value} risk as {prediction.risk_level.value} "
                        f"(score {prediction.risk_score:.2f})."
                    ),
                    related_prediction_id=prediction.id,
                )

        # Clinical override: the diabetes ML model (trained on Pima
        # Indian women) under-predicts for male patients with elevated
        # glucose. A hard glucose threshold ensures diabetic-range
        # readings always produce an alert, regardless of the model score.
        glucose = getattr(vital, "blood_glucose_mg_dl", None)
        if glucose is not None:
            title = "Diabetic Range Glucose Detected"
            if glucose >= DIABETES_GLUCOSE_CRITICAL:
                self._raise_alert(
                    patient=patient,
                    severity=AlertSeverity.CRITICAL,
                    title=title,
                    message=(
                        f"Blood glucose {glucose} mg/dL is in the severe hyperglycemic "
                        f"range (>= {DIABETES_GLUCOSE_CRITICAL})."
                    ),
                    related_vital_id=vital.id,
                )
            elif glucose >= DIABETES_GLUCOSE_WARNING:
                self._raise_alert(
                    patient=patient,
                    severity=AlertSeverity.WARNING,
                    title=title,
                    message=(
                        f"Blood glucose {glucose} mg/dL is in the diabetic range "
                        f"(>= {DIABETES_GLUCOSE_WARNING})."
                    ),
                    related_vital_id=vital.id,
                )

        return predictions, skipped

    def _previous_prediction_was_elevated(
        self, patient_id: uuid.UUID, disease: DiseaseType, exclude_id: uuid.UUID
    ) -> bool:
        """True if the most recent prediction for this disease BEFORE the
        current one was also high/critical — i.e. the elevation is a
        sustained pattern across consecutive readings, not a single flag.
        This is the confidence gate that prevents low-precision models
        from firing critical/emergency alerts on a one-off reading."""
        previous = self.prediction_service.list_for_patient(patient_id, disease=disease)
        for pred in previous:
            if pred.id == exclude_id:
                continue
            return pred.risk_level in AI_ALERT_RISK_LEVELS
        return False

    def _raise_alert(
        self,
        patient: PatientProfile,
        severity: AlertSeverity,
        title: str,
        message: str,
        related_vital_id: uuid.UUID | None = None,
        related_prediction_id: uuid.UUID | None = None,
    ) -> None:
        # Deduplication: don't raise a new alert if this exact issue is
        # already open and unresolved for this patient — see
        # AlertRepository.find_active_by_title for why this is keyed on
        # "still unresolved" rather than a time window. Applies to the
        # whole alert (no new row, no new notification, no emergency
        # contact re-trigger) — a still-open issue doesn't need repeating.
        if self.alert_service.alerts.find_active_by_title(patient.id, title) is not None:
            return

        alert = self.alert_service.create_alert(
            patient_id=patient.id,
            severity=severity,
            title=title,
            message=message,
            related_vital_id=related_vital_id,
            related_prediction_id=related_prediction_id,
        )

        self.notification_service.create(
            user_id=patient.user_id,
            title=title,
            message=message,
            notification_type="alert",
        )

        self.emergency_contact_service.notify_if_applicable(patient, alert)
