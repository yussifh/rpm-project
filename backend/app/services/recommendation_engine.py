"""
Recommendation engine — turns a completed risk prediction (score, reasons,
risk level) and the patient's own vitals pattern into a short, prioritized
list of clinically-grounded recommendations.

Design decisions:

- DETERMINISTIC, NOT AN LLM CALL. Consistent with how this system already
  handles anything the patient sees synchronously after "Confirm and
  Analyze" (see trend_analysis.py, alert_rules.py): the LLM is reserved
  for the standalone AI Assistant chat, not the core analysis pipeline.
  This keeps vitals submission fast and reproducible, and keeps it
  working even when no LLM API key is configured.

- "DYNAMIC" MEANS DATA-DRIVEN, NOT RANDOMIZED. The same patient data
  always produces the same recommendations (reproducible, testable,
  explainable — every recommendation traces back to a specific rule and
  a specific input value), but different data produces meaningfully
  different output. A patient with high glucose gets glucose-specific
  guidance; a patient with elevated BP gets BP-specific guidance; a
  patient with neither gets general maintenance guidance. This is NOT a
  fixed block of text shown regardless of what's actually in front of it.

- CAPPED AND PRIORITIZED, NOT EXHAUSTIVE. Every rule that could plausibly
  fire is scored by clinical priority; only the top MAX_RECOMMENDATIONS
  survive. A wall of generic advice dilutes the recommendations that
  actually matter for this patient's specific result.

- HARD SAFETY RULE: this module NEVER recommends starting, stopping, or
  adjusting a medication or its dosage. Every candidate below is
  lifestyle, self-monitoring, or professional-referral guidance —
  consistent with the project's standing rule (also enforced in the AI
  Assistant's system prompt) that only a qualified professional adjusts
  treatment. Adherence reminders ("you've missed doses") are fine — a
  recommendation to change WHAT is taken or HOW MUCH is not, and no rule
  in this file should ever produce one.
"""

from dataclasses import dataclass

from app.models.enums import DiseaseType, RiskLevel

MAX_RECOMMENDATIONS = 4

# Recommendations at/above this risk level always include a
# professional-evaluation referral, regardless of which other rules fire —
# mirrors the same threshold used for AI-triggered alerts elsewhere in the
# system (VitalsService.AI_ALERT_RISK_LEVELS).
REFERRAL_RISK_LEVELS = {RiskLevel.HIGH, RiskLevel.CRITICAL}


@dataclass
class _Candidate:
    text: str
    priority: int  # higher fires first when the list is capped


def generate_recommendations(
    disease: DiseaseType,
    risk_level: RiskLevel,
    features: dict,
    recent_glucose: list[float],
    recent_bp: list[tuple[int, int]],
    missed_medication_count: int,
) -> list[str]:
    """Returns at most MAX_RECOMMENDATIONS strings, ordered by priority.

    `features` is the exact feature dict PredictionService fed to the
    model for this prediction (same snapshot the stored `reasons` were
    built from) — using it here rather than re-querying vitals keeps the
    recommendations consistent with what the score itself was based on.
    `recent_glucose`/`recent_bp` are the last few raw readings (most
    recent first), used only to detect short streaks (e.g. "3 readings in
    a row elevated") the same way _build_reasons already does.
    """
    candidates: list[_Candidate] = []

    if disease == DiseaseType.DIABETES:
        candidates += _diabetes_candidates(features, recent_glucose)
    elif disease == DiseaseType.HYPERTENSION:
        candidates += _hypertension_candidates(features, recent_bp)
    elif disease == DiseaseType.STROKE:
        candidates += _stroke_candidates(features, recent_bp, recent_glucose)

    if missed_medication_count >= 2:
        candidates.append(
            _Candidate(
                f"You've missed {missed_medication_count} scheduled dose(s) in the last week — consistent "
                f"adherence to your existing treatment plan matters for keeping this risk score accurate. "
                f"If a dose is hard to fit into your routine, that's worth raising with your prescriber.",
                priority=7,
            )
        )

    if risk_level in REFERRAL_RISK_LEVELS:
        candidates.append(
            _Candidate(
                f"This result is {risk_level.value} risk — please arrange an evaluation with a qualified "
                f"healthcare professional rather than managing this from monitoring alone.",
                priority=10,
            )
        )
    elif not candidates:
        # Low/moderate risk and nothing else fired — give the patient
        # something concrete rather than an empty list.
        candidates.append(
            _Candidate(
                "Your current readings don't show a specific concern — keep logging vitals on a "
                "regular schedule so any change gets caught early.",
                priority=1,
            )
        )

    candidates.sort(key=lambda c: -c.priority)

    seen: set[str] = set()
    result: list[str] = []
    for c in candidates:
        if c.text in seen:
            continue
        seen.add(c.text)
        result.append(c.text)
        if len(result) >= MAX_RECOMMENDATIONS:
            break
    return result


def _diabetes_candidates(features: dict, recent_glucose: list[float]) -> list[_Candidate]:
    out: list[_Candidate] = []
    glucose = features.get("avg_glucose_level") or features.get("glucose")

    if glucose and glucose >= 200:
        out.append(
            _Candidate(
                f"Your latest glucose reading ({glucose:g} mg/dL) is well above the diabetic threshold — "
                f"reducing simple/refined carbohydrates and sugary drinks at your next few meals, and "
                f"re-checking sooner than your usual interval, is a reasonable near-term step.",
                priority=9,
            )
        )
    elif glucose and glucose >= 140:
        out.append(
            _Candidate(
                f"Your glucose ({glucose:g} mg/dL) is above the normal range — a short post-meal walk "
                f"(even 10-15 minutes) measurably helps glucose clearance and is a low-effort habit to try "
                f"before your next reading.",
                priority=5,
            )
        )

    high_glucose_streak = sum(1 for g in recent_glucose[:3] if g and g >= 180)
    if high_glucose_streak >= 2:
        out.append(
            _Candidate(
                f"Glucose has been elevated in {high_glucose_streak} of your last 3 readings — consider "
                f"checking more frequently for the next few days rather than your normal interval, so a "
                f"persistent pattern doesn't go unnoticed between checks.",
                priority=6,
            )
        )

    bmi = features.get("bmi")
    if bmi and bmi >= 30:
        out.append(
            _Candidate(
                f"BMI of {bmi:g} is in a range that independently raises diabetes risk — the ADA's general "
                f"guidance is ~150 minutes/week of moderate activity (e.g. brisk walking); even modest, "
                f"sustained weight reduction (5-7%) measurably improves glucose control.",
                priority=4,
            )
        )

    return out


def _hypertension_candidates(features: dict, recent_bp: list[tuple[int, int]]) -> list[_Candidate]:
    out: list[_Candidate] = []
    systolic = features.get("systolic_bp")
    diastolic = features.get("diastolic_bp")

    if systolic and systolic >= 180 or (diastolic and diastolic >= 120):
        out.append(
            _Candidate(
                f"Your latest reading ({systolic}/{diastolic} mmHg) is in a range that can require urgent "
                f"attention — if you have symptoms like severe headache, chest pain, or shortness of breath "
                f"alongside this, seek emergency care now rather than waiting on routine follow-up.",
                priority=10,
            )
        )
    elif (systolic and systolic >= 140) or (diastolic and diastolic >= 90):
        out.append(
            _Candidate(
                "Reducing sodium intake (the DASH eating pattern is well-evidenced here — more fruits, "
                "vegetables, and whole grains, less processed/salted food) is one of the most effective "
                "non-medication steps for blood pressure specifically.",
                priority=6,
            )
        )

    elevated_streak = sum(
        1 for s, d in recent_bp[:3] if s and d and (s >= 140 or d >= 90)
    )
    if elevated_streak >= 3:
        out.append(
            _Candidate(
                f"Blood pressure has been elevated for {elevated_streak} consecutive readings — this "
                f"pattern (not just a single high reading) is what's worth flagging to a healthcare "
                f"professional, since a persistent trend carries more weight than one number.",
                priority=8,
            )
        )

    heart_rate = features.get("heart_rate")
    if heart_rate and heart_rate >= 100 and ((systolic and systolic >= 130) or (diastolic and diastolic >= 85)):
        out.append(
            _Candidate(
                "Both blood pressure and heart rate are elevated together — reducing caffeine/stimulant "
                "intake and prioritizing consistent sleep can meaningfully affect both at once.",
                priority=3,
            )
        )

    return out


def _stroke_candidates(
    features: dict, recent_bp: list[tuple[int, int]], recent_glucose: list[float]
) -> list[_Candidate]:
    out: list[_Candidate] = []
    systolic = features.get("systolic_bp")
    glucose = features.get("avg_glucose_level") or features.get("glucose")

    compounding = sum(
        [
            bool(systolic and systolic >= 140),
            bool(glucose and glucose >= 140),
            bool(features.get("hypertension_flag")),
            bool(features.get("heart_disease_flag")),
        ]
    )
    if compounding >= 2:
        out.append(
            _Candidate(
                "More than one stroke risk factor is present at once (elevated blood pressure, elevated "
                "glucose, and/or prior cardiovascular history) — these compound rather than add, which is "
                "why addressing blood pressure AND glucose together matters more here than either alone.",
                priority=8,
            )
        )

    if features.get("hypertension_flag") or features.get("heart_disease_flag"):
        out.append(
            _Candidate(
                "Given your recorded cardiovascular history, staying consistent with your existing "
                "follow-up schedule (not just symptom-driven visits) is specifically protective for "
                "stroke risk.",
                priority=5,
            )
        )

    elevated_streak = sum(1 for s, d in recent_bp[:3] if s and s >= 140)
    if elevated_streak >= 2:
        out.append(
            _Candidate(
                "If you notice sudden face drooping, arm weakness, or slurred speech at any point, treat "
                "it as an emergency (call emergency services immediately) rather than waiting to log it "
                "here — those are the classic stroke warning signs, and timing matters more for stroke "
                "than for the other two conditions this system tracks.",
                priority=7,
            )
        )

    return out
