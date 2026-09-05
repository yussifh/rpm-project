"""
Unit tests for app.services.trend_analysis — pure functions, no DB/ORM
required (mirrors test_alert_rules.py's approach).
"""

from datetime import datetime, timedelta

from app.services.trend_analysis import DataPoint, TrendDirection, classify_trend

BASE = datetime(2026, 1, 1)


def points(values: list[float], spacing_days: int = 3) -> list[DataPoint]:
    return [DataPoint(recorded_at=BASE + timedelta(days=i * spacing_days), value=v) for i, v in enumerate(values)]


class TestInsufficientData:
    def test_fewer_than_three_points_is_insufficient(self):
        result = classify_trend("blood_pressure_systolic", points([120, 122]))
        assert result.direction == TrendDirection.INSUFFICIENT_DATA
        assert result.earliest_average is None

    def test_zero_points_is_insufficient(self):
        result = classify_trend("blood_pressure_systolic", [])
        assert result.direction == TrendDirection.INSUFFICIENT_DATA
        assert result.sample_size == 0


class TestClinicalFieldImproving:
    def test_glucose_trending_toward_normal_is_improving(self):
        # Started well above normal (140 high), moving down toward it
        result = classify_trend("blood_glucose_mg_dl", points([260, 250, 240, 200, 190, 180]))
        assert result.direction == TrendDirection.IMPROVING
        assert not result.is_consistently_abnormal or result.direction == TrendDirection.IMPROVING

    def test_bp_trending_toward_normal_is_improving(self):
        result = classify_trend("blood_pressure_systolic", points([170, 165, 160, 140, 135, 125]))
        assert result.direction == TrendDirection.IMPROVING


class TestClinicalFieldWorsening:
    def test_bp_trending_away_from_normal_is_worsening(self):
        result = classify_trend("blood_pressure_systolic", points([125, 130, 135, 150, 160, 172]))
        assert result.direction == TrendDirection.WORSENING
        assert "qualified healthcare professional" in result.summary

    def test_spo2_declining_is_worsening(self):
        # SpO2: lower is worse — declining values should register as worsening,
        # not "decreasing" (that framing is reserved for neutral fields like weight)
        result = classify_trend("spo2_percent", points([98, 97, 96, 93, 91, 89]))
        assert result.direction == TrendDirection.WORSENING


class TestClinicalFieldStable:
    def test_readings_near_normal_with_small_variation_are_stable(self):
        result = classify_trend("heart_rate_bpm", points([72, 74, 71, 73, 75, 72]))
        assert result.direction == TrendDirection.STABLE

    def test_stable_summary_has_no_professional_nudge(self):
        result = classify_trend("heart_rate_bpm", points([72, 74, 71, 73, 75, 72]))
        assert "qualified healthcare professional" not in result.summary


class TestClinicalFieldFluctuating:
    def test_large_swings_with_no_net_direction_are_fluctuating(self):
        result = classify_trend("blood_pressure_systolic", points([115, 155, 118, 152, 116, 154]))
        assert result.direction == TrendDirection.FLUCTUATING


class TestConsistentlyAbnormal:
    def test_persistently_high_bp_is_flagged_abnormal(self):
        result = classify_trend("blood_pressure_systolic", points([145, 148, 150, 149, 152, 151]))
        assert result.is_consistently_abnormal is True
        assert "outside the normal range" in result.summary

    def test_mostly_normal_readings_are_not_flagged_abnormal(self):
        result = classify_trend("blood_pressure_systolic", points([118, 122, 119, 121, 117, 120]))
        assert result.is_consistently_abnormal is False


class TestNeutralField:
    def test_weight_increasing_is_reported_without_improving_worsening_judgment(self):
        result = classify_trend("weight_kg", points([70, 71, 72, 74, 75, 77]))
        assert result.direction == TrendDirection.INCREASING
        assert result.is_consistently_abnormal is False

    def test_weight_decreasing(self):
        result = classify_trend("weight_kg", points([80, 79, 78, 76, 75, 73]))
        assert result.direction == TrendDirection.DECREASING

    def test_weight_stable(self):
        result = classify_trend("weight_kg", points([70, 70.2, 69.8, 70.1, 69.9, 70]))
        assert result.direction == TrendDirection.STABLE


class TestUnsupportedField:
    def test_unknown_field_raises(self):
        import pytest

        with pytest.raises(ValueError):
            classify_trend("not_a_real_field", points([1, 2, 3]))


class TestForecastApproachingThreshold:
    def test_projects_days_until_crossing_normal_high(self):
        from app.services.trend_analysis import ForecastPosition, forecast_trend

        result = forecast_trend("blood_pressure_systolic", points([100, 104, 108, 112, 116]))
        assert result.position == ForecastPosition.APPROACHING_THRESHOLD
        assert result.target_value == 120
        assert result.days_projected is not None and result.days_projected > 0
        assert result.r_squared == 1.0

    def test_projects_days_until_crossing_normal_low_for_declining_field(self):
        from app.services.trend_analysis import ForecastPosition, forecast_trend

        result = forecast_trend("spo2_percent", points([99, 98.5, 98, 97.5, 97]))
        assert result.position == ForecastPosition.APPROACHING_THRESHOLD
        assert result.target_value == 95


class TestForecastAlreadyAbnormal:
    def test_returning_to_range_when_improving_from_above(self):
        from app.services.trend_analysis import ForecastPosition, forecast_trend

        result = forecast_trend("blood_pressure_systolic", points([160, 150, 140, 132, 125]))
        assert result.position == ForecastPosition.RETURNING_TO_RANGE
        assert result.target_value == 120
        assert result.days_projected is not None and result.days_projected > 0

    def test_drifting_further_when_worsening_from_above(self):
        from app.services.trend_analysis import ForecastPosition, forecast_trend

        result = forecast_trend("blood_pressure_systolic", points([130, 140, 150, 160, 172]))
        assert result.position == ForecastPosition.DRIFTING_FURTHER
        assert result.days_projected is None


class TestForecastFailsSafe:
    def test_too_few_points(self):
        from app.services.trend_analysis import ForecastPosition, forecast_trend

        result = forecast_trend("blood_pressure_systolic", points([115, 120, 125]))
        assert result.position == ForecastPosition.LOW_CONFIDENCE
        assert result.days_projected is None

    def test_span_too_short(self):
        from datetime import timedelta

        from app.services.trend_analysis import DataPoint, ForecastPosition, forecast_trend

        close_points = [DataPoint(recorded_at=BASE + timedelta(hours=i), value=v) for i, v in enumerate([110, 112, 114, 116])]
        result = forecast_trend("blood_pressure_systolic", close_points)
        assert result.position == ForecastPosition.LOW_CONFIDENCE

    def test_low_r_squared_suppresses_forecast(self):
        from app.services.trend_analysis import ForecastPosition, forecast_trend

        result = forecast_trend("blood_pressure_systolic", points([115, 155, 118, 152, 116, 154]))
        assert result.position == ForecastPosition.LOW_CONFIDENCE
        assert result.days_projected is None
        assert result.r_squared is not None and result.r_squared < 0.3

    def test_stable_flat_trend_yields_no_crossing_projection(self):
        from app.services.trend_analysis import ForecastPosition, forecast_trend

        result = forecast_trend("heart_rate_bpm", points([72, 74, 71, 73, 75, 72]))
        # Near-flat values -> weak linear fit -> low confidence, not a
        # false-precision forecast.
        assert result.position == ForecastPosition.LOW_CONFIDENCE

    def test_neutral_field_has_no_forecast(self):
        from app.services.trend_analysis import ForecastPosition, forecast_trend

        result = forecast_trend("weight_kg", points([70, 71, 72, 74, 75]))
        assert result.position == ForecastPosition.LOW_CONFIDENCE
        assert "no clinical range" in result.summary.lower() or "not meaningful" in result.summary.lower()

    def test_unknown_field_raises(self):
        import pytest

        from app.services.trend_analysis import forecast_trend

        with pytest.raises(ValueError):
            forecast_trend("not_a_real_field", points([1, 2, 3, 4]))
