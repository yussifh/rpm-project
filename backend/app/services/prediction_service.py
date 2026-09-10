"""
PredictionService — the bridge between clinical data (PatientProfile,
VitalReading, MedicalHistoryEntry) and the framework-agnostic AI engine
(app.ai_engine.inference.risk_engine).

Design decision: this is the ONLY place that translates between the
ORM/DB world (DiseaseType enum, RiskLevel enum, SQLAlchemy models) and the
AI engine's plain-string/plain-dict world. The AI engine itself never
imports SQLAlchemy; this service is the seam where the two layers meet —
consistent with the Clean Architecture boundary described in the system
architecture diagram (Module 1).
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.ai_engine.feature_schema import DIABETES, HYPERTENSION, STROKE
from app.ai_engine.inference import ModelNotTrainedError, risk_engine
from app.core.exceptions import InsufficientDataError, NotFoundError
from app.models.enums import DiseaseType, Gender, MedicationStatus, RiskLevel
from app.models.patient import PatientProfile
from app.models.prediction import RiskPrediction
from app.repositories.disease_assessment_repository import DiseaseAssessmentRepository
from app.repositories.medical_history_repository import MedicalHistoryRepository
from app.repositories.medication_repository import MedicationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.vitals_repository import VitalsRepository
from app.services.recommendation_engine import generate_recommendations

# Bridges the ORM-facing enum to the AI engine's plain string keys.
DISEASE_TYPE_TO_KEY = {
    DiseaseType.STROKE: STROKE,
    DiseaseType.DIABETES: DIABETES,
    DiseaseType.HYPERTENSION: HYPERTENSION,
}

RISK_LEVEL_FROM_STRING = {
    "low": RiskLevel.LOW,
    "moderate": RiskLevel.MODERATE,
    "high": RiskLevel.HIGH,
    "critical": RiskLevel.CRITICAL,
}

HYPERTENSION_HISTORY_KEYWORDS = ("hypertension", "high blood pressure")
HEART_DISEASE_HISTORY_KEYWORDS = ("heart disease", "cardiac", "coronary", "myocardial")


def _calculate_age(date_of_birth: date) -> int:
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def _calculate_bmi(height_cm: float | None, weight_kg: float | None) -> float | None:
    if not height_cm or not weight_kg:
        return None
    height_m = height_cm / 100
    return round(weight_kg / (height_m**2), 2)


class PredictionService:
    def __init__(self, db: Session):
        self.db = db
        self.patients = PatientRepository(db)
        self.vitals = VitalsRepository(db)
        self.history = MedicalHistoryRepository(db)
        self.predictions = PredictionRepository(db)
        self.medications = MedicationRepository(db)
        self.assessments = DiseaseAssessmentRepository(db)

    def build_features(self, patient: PatientProfile, disease: DiseaseType) -> tuple[dict, uuid.UUID | None]:
        """Returns (feature_dict, source_vital_id). Raises InsufficientDataError
        if required clinical inputs (e.g. no vitals logged yet, missing BMI)
        aren't available for this disease's feature set."""
        latest_vital = self.vitals.get_latest_for_patient(patient.id)
        if latest_vital is None:
            raise InsufficientDataError(
                "This patient has no vitals readings yet. At least one vitals "
                "entry is required before a risk prediction can be generated."
            )

        # BMI/Age come from the patient profile by default, but a reading
        # can supply them manually (manual BMI/Age/height inputs on the
        # vitals form) — manual values take priority. Weight from the
        # reading (if any) takes priority over the profile weight too.
        bmi = latest_vital.bmi or _calculate_bmi(
            latest_vital.height_cm or patient.height_cm,
            latest_vital.weight_kg or patient.weight_kg,
        )
        if bmi is None:
            raise InsufficientDataError(
                "Patient height and weight must both be recorded before a risk "
                "prediction can be generated (required to compute BMI). Alternatively, "
                "a BMI value can be entered directly on the vitals reading."
            )

        age = latest_vital.age_years or _calculate_age(patient.date_of_birth)

        history_entries = self.history.list_by_patient(patient.id)
        condition_names = " ".join(e.condition_name.lower() for e in history_entries)
        hypertension_flag = int(any(kw in condition_names for kw in HYPERTENSION_HISTORY_KEYWORDS))
        heart_disease_flag = int(any(kw in condition_names for kw in HEART_DISEASE_HISTORY_KEYWORDS))

        all_features = {
            "age": age,
            "gender_male": int(patient.gender == Gender.MALE),
            "hypertension_flag": hypertension_flag,
            "heart_disease_flag": heart_disease_flag,
            "avg_glucose_level": latest_vital.blood_glucose_mg_dl,
            "glucose": latest_vital.blood_glucose_mg_dl,
            "bmi": bmi,
            "systolic_bp": latest_vital.blood_pressure_systolic,
            "diastolic_bp": latest_vital.blood_pressure_diastolic,
            "heart_rate": latest_vital.heart_rate_bpm,
            "diabetes_pedigree": latest_vital.diabetes_pedigree_function,
        }

        required = risk_engine.expected_features(DISEASE_TYPE_TO_KEY[disease])
        missing = [f for f in required if all_features.get(f) is None]
        if missing:
            raise InsufficientDataError(
                f"Missing required vitals for a {disease.value} prediction: {missing}. "
                "Please log a vitals reading including these fields first."
            )

        feature_dict = {name: all_features[name] for name in required}
        return feature_dict, latest_vital.id

    def predict(self, patient_id: uuid.UUID, disease: DiseaseType) -> RiskPrediction:
        patient = self.patients.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("PatientProfile", str(patient_id))

        features, source_vital_id = self.build_features(patient, disease)

        # Deduplication: if a prediction for this patient + disease already
        # exists for this exact vital reading, return it instead of creating
        # a duplicate. This prevents multiple identical predictions when
        # record_reading is called repeatedly or the prediction pipeline
        # is triggered more than once per submission.
        existing = self.predictions.find_by_patient_disease_vital(
            patient.id, disease, source_vital_id
        )
        if existing is not None:
            return existing

        try:
            result = risk_engine.predict(DISEASE_TYPE_TO_KEY[disease], features)
        except ModelNotTrainedError as exc:
            raise InsufficientDataError(str(exc))

        # Fetched once, shared by both reasons and recommendations, so
        # both are built from the exact same snapshot of recent readings
        # rather than two separate queries that could (rarely) disagree.
        recent_vitals = self.vitals.list_for_patient(patient.id, limit=5)
        risk_level = RISK_LEVEL_FROM_STRING[result["risk_level"]]
        missed_count = self._count_recent_missed_doses(patient)

        # Clinical adequacy override for diabetes.
        #
        # The diabetes model was trained on the Pima Indians Diabetes dataset,
        # which is overwhelmingly female and has a very high baseline diabetes
        # prevalence. As a result it systematically UNDER-predicts diabetes for
        # male patients (or anyone outside that population) even with clearly
        # elevated glucose. Rather than retrain (out of scope), we apply a
        # conservative, reproduciable clinical override: when a patient shows a
        # SUSTAINED pattern of high glucose (>=2 of the last 3 readings >= 180
        # mg/dL), the model score is corrected upward to reflect that this is
        # not a one-off reading. This mirrors the "confirmation over time"
        # design already used for hypertension/stroke alert escalation.
        corrected_score = result["risk_score"]
        if disease == DiseaseType.DIABETES:
            risk_level, corrected_score = self._apply_diabetes_override(
                risk_level, result["risk_score"], recent_vitals
            )

        reasons = self._build_reasons(patient, disease, features, recent_vitals, missed_count)
        recommendations = generate_recommendations(
            disease=disease,
            risk_level=risk_level,
            features=features,
            recent_glucose=[v.blood_glucose_mg_dl for v in recent_vitals],
            recent_bp=[(v.blood_pressure_systolic, v.blood_pressure_diastolic) for v in recent_vitals],
            missed_medication_count=missed_count,
        )

        prediction = RiskPrediction(
            patient_id=patient.id,
            source_vital_id=source_vital_id,
            disease_type=disease,
            risk_score=corrected_score,
            risk_level=risk_level,
            model_version=result["model_version"],
            data_source=result["data_source"],
            input_features=features,
            reasons=reasons,
            recommendations=recommendations,
            predicted_at=datetime.now(timezone.utc),
        )
        return self.predictions.create(prediction)

    def _apply_diabetes_override(
        self,
        risk_level: RiskLevel,
        model_score: float,
        recent_vitals: list,
    ) -> tuple[RiskLevel, float]:
        """Corrects the diabetes model's systematic under-prediction using
        a sustained high-glucose pattern.

        Pima-derived model tuning heavily discounts elevated glucose for
        non-Pima (especially male) patients, so a single high reading is
        NOT enough to override — we need >=2 of the last 3 readings >= 180
        mg/dL (sustained, not a one-off). Precedence:
          - If already HIGH/CRITICAL: leave the (more conservative) model
            level alone.
          - Sustained high glucose + model says MODERATE or below -> bump
            to HIGH.
        Returns (risk_level, corrected_score)."""
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return risk_level, model_score

        high_glucose = [
            v.blood_glucose_mg_dl for v in recent_vitals if v.blood_glucose_mg_dl
        ][:3]
        if len(high_glucose) >= 2 and sum(1 for g in high_glucose if g >= 180) >= 2:
            return RiskLevel.HIGH, max(model_score, 0.7)
        return risk_level, model_score

    def _count_recent_missed_doses(self, patient: PatientProfile) -> int:
        """Missed medication doses in the last 7 days across this
        patient's active medications — shared by _build_reasons and the
        recommendation engine so both reflect the same count."""
        active_meds = self.medications.list_by_patient(patient.id, active_only=True)
        missed_count = 0
        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        for med in active_meds:
            for log in self.medications.list_logs(med.id):
                log_time = log.scheduled_at
                if log_time.tzinfo is None:
                    log_time = log_time.replace(tzinfo=timezone.utc)
                if log.status == MedicationStatus.MISSED and log_time >= one_week_ago:
                    missed_count += 1
        return missed_count

    def _build_reasons(
        self,
        patient: PatientProfile,
        disease: DiseaseType,
        features: dict,
        recent_vitals: list,
        missed_count: int,
    ) -> list[str]:
        """Builds a plain-English explanation for a risk score, combining:
        recent vitals trends, medication adherence, and self-reported
        assessment symptoms — not just the bare score. This is what makes
        the AI output explainable rather than a black-box number."""
        reasons: list[str] = []

        if disease in (DiseaseType.HYPERTENSION, DiseaseType.STROKE):
            high_bp_streak = 0
            for v in recent_vitals:
                if v.blood_pressure_systolic and v.blood_pressure_diastolic and (
                    v.blood_pressure_systolic >= 140 or v.blood_pressure_diastolic >= 90
                ):
                    high_bp_streak += 1
                else:
                    break
            if high_bp_streak >= 3:
                reasons.append(
                    f"Blood pressure has been elevated (\u2265140/90 mmHg) for the last "
                    f"{high_bp_streak} consecutive readings."
                )
            elif features.get("systolic_bp") and features["systolic_bp"] >= 180:
                reasons.append(f"Latest systolic blood pressure of {features['systolic_bp']} mmHg is critically high.")

        if disease == DiseaseType.DIABETES:
            glucose = features.get("avg_glucose_level") or features.get("glucose")
            if glucose and glucose >= 200:
                reasons.append(f"Latest blood glucose reading of {glucose} mg/dL is above the diabetic threshold.")
            high_glucose_streak = sum(
                1 for v in recent_vitals[:3] if v.blood_glucose_mg_dl and v.blood_glucose_mg_dl >= 180
            )
            if high_glucose_streak >= 2:
                reasons.append(f"Blood glucose has been high (\u2265180 mg/dL) in {high_glucose_streak} of the last 3 readings.")

        if features.get("bmi") and features["bmi"] >= 30:
            reasons.append(f"BMI of {features['bmi']} falls in the obese range, a known risk factor.")

        if features.get("hypertension_flag"):
            reasons.append("Medical history includes a prior hypertension diagnosis.")
        if features.get("heart_disease_flag"):
            reasons.append("Medical history includes a prior heart disease diagnosis.")

        # Medication adherence — missed doses in the last 7 days across
        # this patient's active medications (count computed once in
        # predict() and shared with the recommendation engine).
        if missed_count >= 2:
            reasons.append(f"Medication has been missed {missed_count} time(s) in the last week.")

        # Most recent self-reported symptom assessment for this disease.
        latest_assessment = self.assessments.get_latest_for_patient(patient.id)
        if latest_assessment and latest_assessment.disease_type == disease:
            reported = [k.replace("_", " ") for k, v in latest_assessment.symptoms.items() if v not in (False, None, "", "no")]
            if reported:
                reasons.append(f"Patient recently reported: {', '.join(reported)}.")

        if not reasons:
            reasons.append("No specific risk factors stood out beyond the overall vitals pattern used by the model.")

        return reasons

    def list_for_patient(self, patient_id: uuid.UUID, disease: DiseaseType | None = None) -> list[RiskPrediction]:
        return self.predictions.list_for_patient(patient_id, disease_type=disease)

    def get_model_info(self, disease: DiseaseType) -> dict:
        """Static model-transparency info — not patient-specific. See
        RiskPredictionEngine.model_info for what this returns."""
        key = DISEASE_TYPE_TO_KEY[disease]
        try:
            return risk_engine.model_info(key)
        except ModelNotTrainedError as exc:
            raise InsufficientDataError(str(exc)) from exc
