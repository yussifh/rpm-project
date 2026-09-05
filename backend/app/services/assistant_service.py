"""
AssistantService — the AI Health Assistant described in the system spec:
"ML = Prediction Engine, AI Assistant = Explanation + Health Guidance".

This service is deliberately NOT where risk is calculated — it never
calls a model to classify/predict anything. Its only two jobs are:
  1. Gather the patient's OWN stored data (profile, vitals, ML
     predictions + reasons, trend classifications, active alerts) into a
     bounded context.
  2. Either short-circuit with a deterministic emergency message (see
     _check_emergency_override), or hand that exact context to an LLM
     with a system prompt that hard-constrains it to explain what's
     already there — never diagnose, never prescribe, never invent data
     that isn't in the context it was given.

Why an emergency override BYPASSES the LLM rather than just instructing
it to sound urgent: an LLM call can fail, be slow, or (rarely) not follow
its system prompt exactly. For a genuinely critical alert, the system
should not depend on a network call succeeding and behaving correctly to
tell the patient something is seriously wrong — that message is generated
locally, deterministically, before any LLM is involved. This mirrors the
project's own rule from the spec: "For potential emergencies, the system
should provide an urgent warning rather than relying on normal health
advice" — "relying on" is read here as including relying on the AI
Assistant's own normal-conversation path.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AssistantUnavailableError, NotFoundError
from app.models.assistant_message import AssistantMessage
from app.models.enums import AlertStatus, RiskLevel
from app.repositories.alert_repository import AlertRepository
from app.repositories.assistant_repository import AssistantMessageRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.vitals_repository import VitalsRepository
from app.services.trend_analysis import FIELD_CONFIG, DataPoint, ForecastPosition, classify_trend, forecast_trend

CONVERSATION_HISTORY_TURNS = 10  # messages, not full pairs

EMERGENCY_OVERRIDE_MESSAGE = (
    "⚠️ Your recent readings include a critical alert that hasn't been resolved yet. "
    "This may need urgent attention. Please contact a healthcare professional or emergency "
    "services now rather than waiting on this chat — I'm not able to assess whether this is "
    "an emergency, and a delay could matter. If you believe this is a medical emergency, "
    "please seek immediate care."
)

SYSTEM_PROMPT_TEMPLATE = """You are the AI Health Assistant inside a remote patient monitoring \
system for diabetes, hypertension, and stroke. You are talking directly to the patient.

Your role is strictly to EXPLAIN data that has already been calculated by the system's \
trained machine learning models and rule-based trend analysis — you do not calculate risk \
yourself, and you must never contradict, second-guess, or restate a different number than \
what is given to you below.

HARD RULES — follow all of them on every reply:
1. Use ONLY the patient data given to you in the CONTEXT section below. Never invent, \
guess, or assume a vital sign, prediction, diagnosis, or history detail that is not present \
in the context. If the patient asks about something not in the context, say plainly that you \
don't have that information rather than guessing.
2. Never state or imply a medical diagnosis. You may explain what a risk score or trend means \
in plain language, but phrase it as risk/pattern information, not as "you have X condition".
3. Never prescribe medication, recommend a medication dosage or change, or tell the patient to \
start, stop, or adjust any medication.
4. Never claim certainty the underlying data doesn't support. If a risk level is "moderate", \
do not describe it as "high" or "nothing to worry about" — reflect it accurately.
5. For any risk level of "high" or "critical", or any consistently-abnormal trend, include a \
recommendation to seek evaluation from a qualified healthcare professional.
6. If the context includes a "forecast" line for a measurement, present it explicitly as a \
projection ("may reach X in about Y days if this trend continues"), never as a scheduled or \
certain future event, and never with more precision than the projection itself states. If no \
forecast line is given for a measurement, do not invent one or estimate your own — only relay \
forecasts that are already present in the context.
7. Keep answers concise, warm, and in plain language — the patient is not a clinician.
8. You are not a substitute for professional medical care, and you should say so if the \
patient seems to be relying on you instead of seeking care for a concerning pattern.

CONTEXT (the patient's own data — this is everything you know about them):
{context}
"""


@dataclass
class AssistantReply:
    message: AssistantMessage
    is_emergency_override: bool


class AssistantService:
    def __init__(self, db: Session):
        self.db = db
        self.patients = PatientRepository(db)
        self.vitals = VitalsRepository(db)
        self.predictions = PredictionRepository(db)
        self.alerts = AlertRepository(db)
        self.messages = AssistantMessageRepository(db)

    # --- Public API ---

    def list_history(self, patient_id: uuid.UUID) -> list[AssistantMessage]:
        return self.messages.list_for_patient(patient_id)

    def send_message(self, patient_id: uuid.UUID, content: str) -> AssistantReply:
        patient = self.patients.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("PatientProfile", str(patient_id))

        user_message = self.messages.create(
            AssistantMessage(patient_id=patient_id, role="user", content=content)
        )

        if self._has_active_emergency(patient_id):
            reply = self.messages.create(
                AssistantMessage(
                    patient_id=patient_id,
                    role="assistant",
                    content=EMERGENCY_OVERRIDE_MESSAGE,
                    is_emergency_override=True,
                )
            )
            return AssistantReply(message=reply, is_emergency_override=True)

        context = self._build_context(patient_id)
        history = self.messages.list_recent_for_patient(patient_id, limit=CONVERSATION_HISTORY_TURNS)
        reply_text = self._call_llm(context, history)

        reply = self.messages.create(
            AssistantMessage(patient_id=patient_id, role="assistant", content=reply_text)
        )
        return AssistantReply(message=reply, is_emergency_override=False)

    # --- Emergency override ---

    def _has_active_emergency(self, patient_id: uuid.UUID) -> bool:
        """Deterministic, rule-based check — see module docstring for why
        this bypasses the LLM entirely rather than asking it to be
        careful. Triggers on either an unresolved critical alert (any
        age — it stays "active" until acknowledged/resolved, which is
        what the alert lifecycle is for), or the single most recent
        prediction per disease being at CRITICAL risk.

        Deliberately does NOT time-window this by comparing
        `created_at`/`predicted_at` against a cutoff: those columns come
        back from the database without reliable timezone information
        depending on the backend, and status-based filtering (unresolved,
        most-recent) is both simpler and more correct here — an
        unresolved critical alert from yesterday is still unresolved.
        """
        recent_alerts = self.alerts.list_for_patient(patient_id)
        has_critical_alert = any(
            a.severity.value == "critical" and a.status != AlertStatus.RESOLVED for a in recent_alerts
        )
        if has_critical_alert:
            return True

        latest_predictions = self.predictions.list_for_patient(patient_id)
        # list_for_patient returns newest-first across all disease types;
        # take the single most recent per disease.
        seen_diseases = set()
        for prediction in latest_predictions:
            if prediction.disease_type in seen_diseases:
                continue
            seen_diseases.add(prediction.disease_type)
            if prediction.risk_level == RiskLevel.CRITICAL:
                return True
        return False

    # --- Context building ---

    def _build_context(self, patient_id: uuid.UUID) -> str:
        patient = self.patients.get_by_id(patient_id)
        lines: list[str] = []

        age = self._age_from_dob(patient.date_of_birth)
        lines.append(f"Patient: age {age}, gender {patient.gender.value}")
        if patient.primary_condition:
            lines.append(f"Primary monitored condition: {patient.primary_condition.value}")
        if patient.height_cm and patient.weight_kg:
            bmi = patient.weight_kg / ((patient.height_cm / 100) ** 2)
            lines.append(f"Height: {patient.height_cm} cm, Weight: {patient.weight_kg} kg, BMI: {bmi:.1f}")

        latest_vital = self.vitals.get_latest_for_patient(patient_id)
        if latest_vital:
            lines.append(f"\nMost recent vitals reading ({latest_vital.recorded_at.date().isoformat()}):")
            for field_name in FIELD_CONFIG:
                value = getattr(latest_vital, field_name, None)
                if value is not None:
                    lines.append(f"  - {FIELD_CONFIG[field_name].label}: {value} {FIELD_CONFIG[field_name].unit}")
        else:
            lines.append("\nNo vitals readings have been logged yet.")

        lines.append("\nRecent trend analysis (last 90 days):")
        window_start = datetime.now(timezone.utc) - timedelta(days=90)
        readings = self.vitals.list_for_patient(patient_id, start=window_start, limit=1000)
        any_trend = False
        for field_name in FIELD_CONFIG:
            points = [
                DataPoint(recorded_at=r.recorded_at, value=getattr(r, field_name))
                for r in readings
                if getattr(r, field_name) is not None
            ]
            if not points:
                continue
            trend = classify_trend(field_name, points)
            if trend.direction.value == "insufficient_data":
                continue
            any_trend = True
            abnormal_note = " (persistently abnormal)" if trend.is_consistently_abnormal else ""
            lines.append(f"  - {trend.label}: {trend.direction.value}{abnormal_note} — {trend.summary}")

            forecast = forecast_trend(field_name, points)
            if forecast.position in (
                ForecastPosition.APPROACHING_THRESHOLD,
                ForecastPosition.RETURNING_TO_RANGE,
                ForecastPosition.DRIFTING_FURTHER,
            ):
                lines.append(f"      forecast: {forecast.summary}")
        if not any_trend:
            lines.append("  - Not enough history yet for a trend on any measurement.")

        lines.append("\nLatest AI risk predictions:")
        latest_predictions = self.predictions.list_for_patient(patient_id)
        seen_diseases = set()
        any_prediction = False
        for prediction in latest_predictions:
            if prediction.disease_type in seen_diseases:
                continue
            seen_diseases.add(prediction.disease_type)
            any_prediction = True
            lines.append(
                f"  - {prediction.disease_type.value}: risk level {prediction.risk_level.value} "
                f"(score {prediction.risk_score:.2f}), model version {prediction.model_version}, "
                f"data source: {prediction.data_source}"
            )
            for reason in prediction.reasons:
                lines.append(f"      reason: {reason}")
        if not any_prediction:
            lines.append("  - No risk predictions have been generated yet.")

        active_alerts = [a for a in self.alerts.list_for_patient(patient_id) if a.status != AlertStatus.RESOLVED]
        if active_alerts:
            lines.append("\nActive (unresolved) alerts:")
            for alert in active_alerts[:5]:
                lines.append(f"  - [{alert.severity.value}] {alert.title}: {alert.message}")

        return "\n".join(lines)

    @staticmethod
    def _age_from_dob(dob) -> int:
        today = datetime.now(timezone.utc).date()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    # --- LLM call ---

    def _call_llm(self, context: str, history: list[AssistantMessage]) -> str:
        if not settings.ANTHROPIC_API_KEY:
            raise AssistantUnavailableError(
                "The AI Health Assistant is not configured on this server (no API key set)."
            )

        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - dependency is in requirements.txt
            raise AssistantUnavailableError("The AI Health Assistant's dependencies are not installed.") from exc

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)
        messages = [{"role": m.role, "content": m.content} for m in history]

        try:
            response = client.messages.create(
                model=settings.ASSISTANT_MODEL,
                max_tokens=settings.ASSISTANT_MAX_TOKENS,
                system=system_prompt,
                messages=messages,
            )
        except Exception as exc:  # anthropic raises its own exception hierarchy; keep this broad
            raise AssistantUnavailableError("The AI Health Assistant couldn't be reached. Please try again.") from exc

        text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        return "".join(text_blocks).strip() or (
            "I wasn't able to generate a response to that — could you try rephrasing your question?"
        )
