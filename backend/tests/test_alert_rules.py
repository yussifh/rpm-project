"""
Unit tests for app.services.alert_rules — pure functions, no DB/ORM
required. I ran this logic ad hoc against a range of inputs while building
Module 6; these formalize that verification into the permanent suite.
"""

from app.services.alert_rules import evaluate_vital_thresholds


class TestBloodPressureThresholds:
    def test_hypertensive_crisis_triggers_critical(self):
        alerts = evaluate_vital_thresholds(systolic_bp=190, diastolic_bp=125)
        assert any(a["severity"] == "critical" and "Hypertensive Crisis" in a["title"] for a in alerts)

    def test_elevated_bp_triggers_warning_not_critical(self):
        alerts = evaluate_vital_thresholds(systolic_bp=145, diastolic_bp=92)
        assert any(a["severity"] == "warning" for a in alerts)
        assert not any(a["severity"] == "critical" for a in alerts)

    def test_normal_bp_triggers_nothing(self):
        alerts = evaluate_vital_thresholds(systolic_bp=115, diastolic_bp=75)
        assert alerts == []


class TestGlucoseThresholds:
    def test_severe_hypoglycemia_is_critical(self):
        alerts = evaluate_vital_thresholds(glucose=40)
        assert any(a["severity"] == "critical" and "Hypoglycemia" in a["title"] for a in alerts)

    def test_mild_hypoglycemia_is_warning(self):
        alerts = evaluate_vital_thresholds(glucose=65)
        assert any(a["severity"] == "warning" and "Low Blood Glucose" in a["title"] for a in alerts)

    def test_severe_hyperglycemia_is_critical(self):
        alerts = evaluate_vital_thresholds(glucose=320)
        assert any(a["severity"] == "critical" and "Hyperglycemia" in a["title"] for a in alerts)

    def test_normal_glucose_triggers_nothing(self):
        assert evaluate_vital_thresholds(glucose=95) == []


class TestSpo2Thresholds:
    def test_severe_hypoxemia_is_critical(self):
        alerts = evaluate_vital_thresholds(spo2=85)
        assert any(a["severity"] == "critical" for a in alerts)

    def test_normal_spo2_triggers_nothing(self):
        assert evaluate_vital_thresholds(spo2=98) == []


class TestHeartRateThresholds:
    def test_critical_tachycardia(self):
        alerts = evaluate_vital_thresholds(heart_rate=190)
        assert any(a["severity"] == "critical" for a in alerts)

    def test_critical_bradycardia(self):
        alerts = evaluate_vital_thresholds(heart_rate=35)
        assert any(a["severity"] == "critical" for a in alerts)

    def test_normal_heart_rate_triggers_nothing(self):
        assert evaluate_vital_thresholds(heart_rate=72) == []


class TestCombinedVitals:
    def test_multiple_abnormal_vitals_produce_multiple_alerts(self):
        alerts = evaluate_vital_thresholds(
            systolic_bp=190, diastolic_bp=125, heart_rate=190, glucose=40, spo2=85
        )
        assert len(alerts) == 4  # BP, heart rate, glucose, spo2 each fire once

    def test_all_normal_vitals_produce_no_alerts(self):
        alerts = evaluate_vital_thresholds(
            systolic_bp=115, diastolic_bp=75, heart_rate=70, glucose=90, spo2=98
        )
        assert alerts == []

    def test_missing_values_are_skipped_not_errored(self):
        # Only some vitals provided — should not raise, should only evaluate what's given.
        alerts = evaluate_vital_thresholds(heart_rate=72)
        assert alerts == []
