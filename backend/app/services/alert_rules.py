"""
Threshold-based alert rules for vitals — the FAST, deterministic half of
the early-warning system (the AI-prediction-based half lives in
alert_service.py's integration with PredictionService).

Design decision: pure functions operating on plain values, no ORM/DB
dependency — mirrors the same reasoning as app.ai_engine (testable in
isolation, reusable outside the API if needed). Thresholds here are
simplified, commonly-cited clinical reference points for a demo/FYP
system — NOT a substitute for clinician-defined, patient-specific
thresholds in a real deployment (e.g. a patient with chronic hypotension
may have a different "normal" baseline).
"""

from typing import TypedDict


class ThresholdAlert(TypedDict):
    severity: str  # "warning" | "critical"
    title: str
    message: str


def evaluate_vital_thresholds(
    systolic_bp: int | None = None,
    diastolic_bp: int | None = None,
    heart_rate: int | None = None,
    glucose: float | None = None,
    spo2: float | None = None,
) -> list[ThresholdAlert]:
    alerts: list[ThresholdAlert] = []

    # --- Blood pressure (hypertension) ---
    if systolic_bp is not None and diastolic_bp is not None:
        if systolic_bp >= 180 or diastolic_bp >= 120:
            alerts.append(
                {
                    "severity": "critical",
                    "title": "Hypertensive Crisis",
                    "message": f"Blood pressure {systolic_bp}/{diastolic_bp} mmHg requires immediate attention.",
                }
            )
        elif systolic_bp >= 140 or diastolic_bp >= 90:
            alerts.append(
                {
                    "severity": "warning",
                    "title": "Elevated Blood Pressure",
                    "message": f"Blood pressure {systolic_bp}/{diastolic_bp} mmHg is above the normal range.",
                }
            )

    # --- Blood glucose (diabetes) ---
    if glucose is not None:
        if glucose < 54:
            alerts.append(
                {
                    "severity": "critical",
                    "title": "Severe Hypoglycemia",
                    "message": f"Blood glucose {glucose} mg/dL is dangerously low.",
                }
            )
        elif glucose < 70:
            alerts.append(
                {
                    "severity": "warning",
                    "title": "Low Blood Glucose",
                    "message": f"Blood glucose {glucose} mg/dL is below the normal range.",
                }
            )
        elif glucose >= 300:
            alerts.append(
                {
                    "severity": "critical",
                    "title": "Severe Hyperglycemia",
                    "message": f"Blood glucose {glucose} mg/dL is dangerously high.",
                }
            )
        elif glucose >= 200:
            alerts.append(
                {
                    "severity": "warning",
                    "title": "High Blood Glucose",
                    "message": f"Blood glucose {glucose} mg/dL is above the normal range.",
                }
            )

    # --- SpO2 (general / stroke-relevant) ---
    if spo2 is not None:
        if spo2 < 90:
            alerts.append(
                {
                    "severity": "critical",
                    "title": "Severe Hypoxemia",
                    "message": f"Oxygen saturation {spo2}% is critically low.",
                }
            )
        elif spo2 < 95:
            alerts.append(
                {
                    "severity": "warning",
                    "title": "Low Oxygen Saturation",
                    "message": f"Oxygen saturation {spo2}% is below the normal range.",
                }
            )

    # --- Heart rate ---
    if heart_rate is not None:
        if heart_rate >= 180 or heart_rate <= 40:
            alerts.append(
                {
                    "severity": "critical",
                    "title": "Critical Heart Rate",
                    "message": f"Heart rate {heart_rate} bpm is at a critical level.",
                }
            )
        elif heart_rate >= 120 or heart_rate <= 50:
            alerts.append(
                {
                    "severity": "warning",
                    "title": "Abnormal Heart Rate",
                    "message": f"Heart rate {heart_rate} bpm is outside the normal range.",
                }
            )

    return alerts
