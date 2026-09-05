"""
Trend classification for a patient's vitals history — the rule-based
counterpart to app.ai_engine (which handles point-in-time ML risk
prediction). This module answers a different question: not "how risky is
this patient right now" but "is this specific measurement getting better,
getting worse, holding steady, or bouncing around, over time".

Design decision: this is DELIBERATELY rule-based, not a trained model.
Per the project's own architecture (see AI Health Assistant docs):
  ML model      = prediction / classification / risk estimation
  Trend module  = descriptive statistics over a single measurement series
  AI Assistant  = turns either of the above into patient-friendly language
A trend is a straightforward statistical fact (recent average vs. earlier
average, variance, how often a value has been outside its normal range) —
training a model to answer "is this line going up" would add complexity
without adding accuracy. Keeping it rule-based also means it's fully
explainable: every classification traces back to two numbers you can show
the patient (recent average, earlier average), unlike a learned model's
internals.

Two framings are supported per field:
  - "clinical" fields (BP, glucose, heart rate, SpO2) have a normal range,
    so trend is judged by DISTANCE FROM NORMAL shrinking (improving) or
    growing (worsening) — not just "the number went up", since for e.g.
    blood glucose falling from 250 to 180 is improving even though 180 is
    still above range, and for SpO2 a falling number is the bad direction
    while for blood pressure a falling number is (up to a point) the good
    direction. Distance-from-normal-range unifies this into one rule
    instead of a special case per vital.
  - "neutral" fields (weight) have no inherent good/bad direction, so
    trend is reported as increasing/decreasing/stable/fluctuating without
    an improving/worsening judgment call the system isn't positioned to
    make (weight-loss goals are patient/clinician-specific).
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    WORSENING = "worsening"
    STABLE = "stable"
    FLUCTUATING = "fluctuating"
    INCREASING = "increasing"  # neutral-framing fields only
    DECREASING = "decreasing"  # neutral-framing fields only
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class FieldConfig:
    label: str
    unit: str
    framing: str  # "clinical" | "neutral"
    normal_low: float | None = None
    normal_high: float | None = None
    # Minimum absolute change (in the field's own units) between the
    # earlier-window and recent-window average before we call it a real
    # trend rather than noise — avoids reporting "worsening" over a
    # clinically meaningless 1 mmHg drift.
    noise_floor: float = 0.0


FIELD_CONFIG: dict[str, FieldConfig] = {
    "blood_pressure_systolic": FieldConfig("Systolic blood pressure", "mmHg", "clinical", 90, 120, noise_floor=4),
    "blood_pressure_diastolic": FieldConfig("Diastolic blood pressure", "mmHg", "clinical", 60, 80, noise_floor=3),
    "heart_rate_bpm": FieldConfig("Heart rate", "bpm", "clinical", 60, 100, noise_floor=4),
    "blood_glucose_mg_dl": FieldConfig("Blood glucose", "mg/dL", "clinical", 70, 140, noise_floor=8),
    "spo2_percent": FieldConfig("Oxygen saturation", "%", "clinical", 95, 100, noise_floor=1),
    "weight_kg": FieldConfig("Weight", "kg", "neutral", noise_floor=0.8),
}

MIN_POINTS_FOR_TREND = 3
# A field counts as "consistently abnormal" if at least this fraction of
# the recent readings fall outside its normal range.
CONSISTENTLY_ABNORMAL_THRESHOLD = 0.8

# --- Forecasting (see ForecastResult / forecast_trend below) ---
MIN_POINTS_FOR_FORECAST = 4          # stricter than trend classification — a forecast is a stronger claim
MIN_SPAN_DAYS_FOR_FORECAST = 2.0     # readings all taken within hours of each other can't support a day-scale forecast
MIN_R2_FOR_FORECAST = 0.3            # below this, the linear fit doesn't explain enough variance to trust
FORECAST_HORIZON_DAYS = 90           # beyond this, "some day at this rate" isn't a useful clinical signal


@dataclass
class DataPoint:
    recorded_at: datetime
    value: float


@dataclass
class TrendResult:
    field: str
    label: str
    unit: str
    direction: TrendDirection
    is_consistently_abnormal: bool
    sample_size: int
    earliest_average: float | None
    recent_average: float | None
    summary: str
    data_points: list[DataPoint] = field(default_factory=list)


def _abnormality_distance(value: float, cfg: FieldConfig) -> float:
    """0 if within the normal range, else how far outside it. Used so
    trend direction reflects clinical improvement, not just raw magnitude
    (see module docstring)."""
    if cfg.normal_low is not None and value < cfg.normal_low:
        return cfg.normal_low - value
    if cfg.normal_high is not None and value > cfg.normal_high:
        return value - cfg.normal_high
    return 0.0


def classify_trend(field_name: str, points: list[DataPoint]) -> TrendResult:
    cfg = FIELD_CONFIG.get(field_name)
    if cfg is None:
        raise ValueError(f"No trend configuration for field '{field_name}'")

    ordered = sorted(points, key=lambda p: p.recorded_at)
    values = [p.value for p in ordered]

    if len(ordered) < MIN_POINTS_FOR_TREND:
        return TrendResult(
            field=field_name,
            label=cfg.label,
            unit=cfg.unit,
            direction=TrendDirection.INSUFFICIENT_DATA,
            is_consistently_abnormal=False,
            sample_size=len(ordered),
            earliest_average=None,
            recent_average=None,
            summary=(
                f"Not enough {cfg.label.lower()} readings yet to identify a trend "
                f"— log a few more over time and a trend will appear here."
            ),
            data_points=ordered,
        )

    midpoint = len(ordered) // 2
    earlier_window = ordered[:midpoint] if midpoint > 0 else ordered[:1]
    recent_window = ordered[midpoint:] if midpoint > 0 else ordered[1:]

    earliest_average = statistics.mean(p.value for p in earlier_window)
    recent_average = statistics.mean(p.value for p in recent_window)

    overall_stdev = statistics.pstdev(values) if len(values) > 1 else 0.0

    recent_readings_for_abnormality = ordered[-min(5, len(ordered)):]
    if cfg.framing == "clinical":
        abnormal_count = sum(
            1 for p in recent_readings_for_abnormality if _abnormality_distance(p.value, cfg) > 0
        )
        is_consistently_abnormal = (
            abnormal_count / len(recent_readings_for_abnormality) >= CONSISTENTLY_ABNORMAL_THRESHOLD
        )

        earlier_abnormality = statistics.mean(_abnormality_distance(p.value, cfg) for p in earlier_window)
        recent_abnormality = statistics.mean(_abnormality_distance(p.value, cfg) for p in recent_window)
        delta = recent_abnormality - earlier_abnormality
    else:
        is_consistently_abnormal = False  # no normal range defined for neutral fields
        delta = recent_average - earliest_average

    # "Fluctuating" = swings large relative to the noise floor AND large
    # relative to the net directional move itself — this second check is
    # what catches an alternating high/low/high/low series, where an
    # uneven earlier/recent split can otherwise produce a misleading
    # directional delta purely from where the midpoint happened to fall.
    is_high_variance = overall_stdev >= cfg.noise_floor * 1.5 and overall_stdev > abs(delta) * 1.5

    if cfg.framing == "clinical":
        if is_high_variance:
            direction = TrendDirection.FLUCTUATING
        elif delta <= -cfg.noise_floor:
            direction = TrendDirection.IMPROVING
        elif delta >= cfg.noise_floor:
            direction = TrendDirection.WORSENING
        else:
            direction = TrendDirection.STABLE
    else:
        if is_high_variance:
            direction = TrendDirection.FLUCTUATING
        elif delta <= -cfg.noise_floor:
            direction = TrendDirection.DECREASING
        elif delta >= cfg.noise_floor:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.STABLE

    summary = _build_summary(cfg, direction, is_consistently_abnormal, len(ordered))

    return TrendResult(
        field=field_name,
        label=cfg.label,
        unit=cfg.unit,
        direction=direction,
        is_consistently_abnormal=is_consistently_abnormal,
        sample_size=len(ordered),
        earliest_average=round(earliest_average, 1),
        recent_average=round(recent_average, 1),
        summary=summary,
        data_points=ordered,
    )


def _build_summary(cfg: FieldConfig, direction: TrendDirection, is_consistently_abnormal: bool, n: int) -> str:
    """Plain-language trend narrative — template-generated from the
    classification, not a language model. Deliberately hedged ("your
    recent readings suggest", not "your BP is improving") and never
    phrased as a diagnosis, per the project's safety requirements. A
    professional-evaluation nudge is only appended when there's an actual
    reason for one (worsening trend or a consistently abnormal pattern)."""
    label = cfg.label
    parts: list[str] = []

    if direction == TrendDirection.IMPROVING:
        parts.append(f"{label} has been trending toward the normal range over your last {n} readings.")
    elif direction == TrendDirection.WORSENING:
        parts.append(
            f"{label} has been drifting further from the normal range over your last {n} readings, "
            f"with recent readings higher than earlier ones."
        )
    elif direction == TrendDirection.FLUCTUATING:
        parts.append(f"{label} has been fluctuating across your last {n} readings, without a clear steady direction.")
    elif direction == TrendDirection.STABLE:
        parts.append(f"{label} has stayed relatively stable across your last {n} readings.")
    elif direction == TrendDirection.INCREASING:
        parts.append(f"{label} has been trending upward over your last {n} readings.")
    elif direction == TrendDirection.DECREASING:
        parts.append(f"{label} has been trending downward over your last {n} readings.")

    if is_consistently_abnormal:
        parts.append(
            f"Most of your recent {label.lower()} readings have been outside the normal range. "
            f"Consider discussing this pattern with a qualified healthcare professional."
        )
    elif direction == TrendDirection.WORSENING:
        parts.append("If this continues, consider discussing it with a qualified healthcare professional.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Forecasting — projecting whether/when a vital is likely to cross a
# clinical threshold if its current trajectory continues.
#
# This is deliberately built as a SEPARATE, opt-in step from
# classify_trend() above (not folded into it), because a forecast is a
# stronger, riskier claim than a direction label: "worsening" describes
# what already happened; "may reach 180 mmHg in ~6 days" is a claim about
# the future that a patient could reasonably act on. It therefore needs
# its own, stricter confidence gate (see MIN_* constants above) — and
# critically, when that gate isn't met, forecast_trend() returns WHY
# rather than silently omitting a number or guessing anyway. A forecast
# that quietly fails safe is far better than one that's confidently wrong.
#
# Method: ordinary least-squares linear regression of value against days-
# since-first-reading (closed-form, stdlib-only — no numpy/sklearn needed
# for this; consistent with the rest of this module being deliberately
# rule-based rather than ML). R² reports how much of the variance in
# recent readings that straight line actually explains, so the confidence
# figure shown to the patient is an honest one, not a marketing number.
# ---------------------------------------------------------------------------


class ForecastPosition(str, Enum):
    APPROACHING_THRESHOLD = "approaching_threshold"    # within range, trending toward a bound
    RETURNING_TO_RANGE = "returning_to_range"           # outside range, trending back toward normal
    DRIFTING_FURTHER = "drifting_further"                # outside range, continuing to move further out
    NO_NEAR_TERM_CROSSING = "no_near_term_crossing"      # stable/improving enough that nothing is projected
    LOW_CONFIDENCE = "low_confidence"                    # not enough points, span, or fit quality to forecast


@dataclass
class ForecastResult:
    field: str
    position: ForecastPosition
    days_projected: float | None       # days until crossing (either direction), if applicable
    target_value: float | None         # the boundary value being approached/left
    r_squared: float | None            # goodness-of-fit of the linear trend, 0-1
    summary: str


def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Closed-form least-squares fit. Returns (slope, intercept, r_squared).
    Callers must ensure len(xs) >= 2 and xs has nonzero variance."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    s_xx = sum((x - mean_x) ** 2 for x in xs)
    s_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = s_xy / s_xx
    intercept = mean_y - slope * mean_x

    predicted = [slope * x + intercept for x in xs]
    ss_res = sum((y - p) ** 2 for y, p in zip(ys, predicted))
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    r_squared = 1.0 if ss_res == 0 else (1 - ss_res / ss_tot if ss_tot > 0 else 0.0)

    return slope, intercept, r_squared


def forecast_trend(field_name: str, points: list[DataPoint]) -> ForecastResult:
    cfg = FIELD_CONFIG.get(field_name)
    if cfg is None:
        raise ValueError(f"No trend configuration for field '{field_name}'")

    def low_confidence(reason: str) -> ForecastResult:
        return ForecastResult(
            field=field_name,
            position=ForecastPosition.LOW_CONFIDENCE,
            days_projected=None,
            target_value=None,
            r_squared=None,
            summary=reason,
        )

    if cfg.framing != "clinical" or (cfg.normal_low is None and cfg.normal_high is None):
        return low_confidence(f"No clinical range is defined for {cfg.label.lower()}, so a forecast isn't meaningful.")

    ordered = sorted(points, key=lambda p: p.recorded_at)
    if len(ordered) < MIN_POINTS_FOR_FORECAST:
        return low_confidence(
            f"Not enough {cfg.label.lower()} readings yet for a reliable forecast "
            f"(need at least {MIN_POINTS_FOR_FORECAST})."
        )

    t0 = ordered[0].recorded_at
    xs = [(p.recorded_at - t0).total_seconds() / 86400 for p in ordered]
    ys = [p.value for p in ordered]

    span_days = xs[-1] - xs[0]
    if span_days < MIN_SPAN_DAYS_FOR_FORECAST:
        return low_confidence(
            f"Your {cfg.label.lower()} readings span too short a time to project a trend reliably yet."
        )

    slope, _intercept, r_squared = _linear_regression(xs, ys)

    if r_squared < MIN_R2_FOR_FORECAST:
        return ForecastResult(
            field=field_name,
            position=ForecastPosition.LOW_CONFIDENCE,
            days_projected=None,
            target_value=None,
            r_squared=round(r_squared, 2),
            summary=(
                f"Your {cfg.label.lower()} readings don't follow a clear enough trend line "
                f"(confidence {r_squared:.0%}) to project forward — they may be fluctuating rather than trending."
            ),
        )

    current_value = ys[-1]
    label = cfg.label

    is_below = cfg.normal_low is not None and current_value < cfg.normal_low
    is_above = cfg.normal_high is not None and current_value > cfg.normal_high
    is_within = not is_below and not is_above

    def project(target: float) -> float | None:
        if slope == 0:
            return None
        days = (target - current_value) / slope
        return days if days > 0 else None

    if is_within:
        if slope > 0 and cfg.normal_high is not None:
            days = project(cfg.normal_high)
            target = cfg.normal_high
        elif slope < 0 and cfg.normal_low is not None:
            days = project(cfg.normal_low)
            target = cfg.normal_low
        else:
            days, target = None, None

        if days is not None and days <= FORECAST_HORIZON_DAYS:
            return ForecastResult(
                field=field_name,
                position=ForecastPosition.APPROACHING_THRESHOLD,
                days_projected=round(days, 1),
                target_value=target,
                r_squared=round(r_squared, 2),
                summary=(
                    f"At your current rate of change, {label.lower()} may reach {target:g}{cfg.unit} in "
                    f"approximately {days:.0f} day{'s' if round(days) != 1 else ''} if this trend continues "
                    f"(projection confidence {r_squared:.0%}). This is a projection based on recent readings, "
                    f"not a certainty — continue monitoring, and consider discussing this trend with a "
                    f"qualified healthcare professional."
                ),
            )

        return ForecastResult(
            field=field_name,
            position=ForecastPosition.NO_NEAR_TERM_CROSSING,
            days_projected=None,
            target_value=None,
            r_squared=round(r_squared, 2),
            summary=f"{label} isn't projected to leave the normal range within the next {FORECAST_HORIZON_DAYS} days at its current rate.",
        )

    # Currently outside the normal range — figure out whether the trend is
    # heading back toward it (reassuring) or further away (concerning).
    boundary = cfg.normal_high if is_above else cfg.normal_low
    moving_back = (is_above and slope < 0) or (is_below and slope > 0)

    if moving_back and boundary is not None:
        days = project(boundary)
        if days is not None and days <= FORECAST_HORIZON_DAYS:
            return ForecastResult(
                field=field_name,
                position=ForecastPosition.RETURNING_TO_RANGE,
                days_projected=round(days, 1),
                target_value=boundary,
                r_squared=round(r_squared, 2),
                summary=(
                    f"{label} is currently outside the normal range, but at its current rate of improvement "
                    f"it may return to within {boundary:g}{cfg.unit} in approximately {days:.0f} "
                    f"day{'s' if round(days) != 1 else ''} (projection confidence {r_squared:.0%}) if this "
                    f"trend continues."
                ),
            )

    return ForecastResult(
        field=field_name,
        position=ForecastPosition.DRIFTING_FURTHER,
        days_projected=None,
        target_value=None,
        r_squared=round(r_squared, 2),
        summary=(
            f"{label} is currently outside the normal range and, at its current rate, trending further from "
            f"it rather than back toward it. Consider discussing this with a qualified healthcare professional."
        ),
    )
