"""
Unit tests for app.services.recommendation_engine — pure functions, no
DB/ORM required (mirrors test_trend_analysis.py's approach).
"""

from app.models.enums import DiseaseType, RiskLevel
from app.services.recommendation_engine import MAX_RECOMMENDATIONS, generate_recommendations

FORBIDDEN_PHRASES = [
    "stop taking",
    "start taking",
    "increase your dose",
    "decrease your dose",
    "increase your dosage",
    "decrease your dosage",
    "take more",
    "take less",
]


class TestCapAndPriority:
    def test_never_exceeds_max_recommendations(self):
        recs = generate_recommendations(
            disease=DiseaseType.DIABETES,
            risk_level=RiskLevel.HIGH,
            features={"avg_glucose_level": 220, "glucose": 220, "bmi": 33, "diastolic_bp": 88},
            recent_glucose=[220, 195, 205, 140, 130],
            recent_bp=[],
            missed_medication_count=3,
        )
        assert len(recs) <= MAX_RECOMMENDATIONS

    def test_high_risk_always_includes_professional_referral(self):
        recs = generate_recommendations(
            disease=DiseaseType.HYPERTENSION,
            risk_level=RiskLevel.HIGH,
            features={"systolic_bp": 145, "diastolic_bp": 92, "heart_rate": 80},
            recent_glucose=[],
            recent_bp=[],
            missed_medication_count=0,
        )
        assert any("healthcare professional" in r.lower() for r in recs)

    def test_no_duplicate_recommendations(self):
        recs = generate_recommendations(
            disease=DiseaseType.STROKE,
            risk_level=RiskLevel.CRITICAL,
            features={"systolic_bp": 190, "avg_glucose_level": 210, "glucose": 210, "hypertension_flag": 1},
            recent_glucose=[210, 205],
            recent_bp=[(190, 115), (188, 112)],
            missed_medication_count=0,
        )
        assert len(recs) == len(set(recs))


class TestDynamicBehavior:
    """The core requirement: different data -> different (not static) output."""

    def test_high_glucose_and_healthy_glucose_produce_different_output(self):
        high = generate_recommendations(
            disease=DiseaseType.DIABETES,
            risk_level=RiskLevel.MODERATE,
            features={"avg_glucose_level": 210, "glucose": 210, "bmi": 24, "diastolic_bp": 78},
            recent_glucose=[210],
            recent_bp=[],
            missed_medication_count=0,
        )
        healthy = generate_recommendations(
            disease=DiseaseType.DIABETES,
            risk_level=RiskLevel.LOW,
            features={"avg_glucose_level": 90, "glucose": 90, "bmi": 24, "diastolic_bp": 78},
            recent_glucose=[90],
            recent_bp=[],
            missed_medication_count=0,
        )
        assert high != healthy
        assert any("glucose" in r.lower() for r in high)

    def test_same_inputs_are_deterministic(self):
        kwargs = dict(
            disease=DiseaseType.HYPERTENSION,
            risk_level=RiskLevel.MODERATE,
            features={"systolic_bp": 142, "diastolic_bp": 91, "heart_rate": 88},
            recent_glucose=[],
            recent_bp=[(142, 91), (140, 90)],
            missed_medication_count=0,
        )
        assert generate_recommendations(**kwargs) == generate_recommendations(**kwargs)

    def test_missed_medication_only_flagged_at_two_or_more(self):
        zero_missed = generate_recommendations(
            disease=DiseaseType.DIABETES,
            risk_level=RiskLevel.LOW,
            features={"avg_glucose_level": 95, "glucose": 95, "bmi": 22, "diastolic_bp": 76},
            recent_glucose=[95],
            recent_bp=[],
            missed_medication_count=1,
        )
        assert not any("missed" in r.lower() for r in zero_missed)

        two_missed = generate_recommendations(
            disease=DiseaseType.DIABETES,
            risk_level=RiskLevel.LOW,
            features={"avg_glucose_level": 95, "glucose": 95, "bmi": 22, "diastolic_bp": 76},
            recent_glucose=[95],
            recent_bp=[],
            missed_medication_count=2,
        )
        assert any("missed" in r.lower() for r in two_missed)

    def test_low_risk_no_flags_gets_maintenance_fallback_not_empty_list(self):
        recs = generate_recommendations(
            disease=DiseaseType.HYPERTENSION,
            risk_level=RiskLevel.LOW,
            features={"systolic_bp": 118, "diastolic_bp": 76, "heart_rate": 70},
            recent_glucose=[],
            recent_bp=[(118, 76), (115, 74)],
            missed_medication_count=0,
        )
        assert len(recs) >= 1


class TestSafetyRules:
    """These recommendations must NEVER contain medication start/stop/
    dosage guidance — only lifestyle, monitoring, and professional
    referral. See the module's docstring for why."""

    def test_no_medication_dosage_language_across_high_risk_scenarios(self):
        scenarios = [
            generate_recommendations(
                disease=DiseaseType.DIABETES,
                risk_level=RiskLevel.CRITICAL,
                features={"avg_glucose_level": 300, "glucose": 300, "bmi": 40, "diastolic_bp": 95},
                recent_glucose=[300, 290, 280],
                recent_bp=[],
                missed_medication_count=5,
            ),
            generate_recommendations(
                disease=DiseaseType.HYPERTENSION,
                risk_level=RiskLevel.CRITICAL,
                features={"systolic_bp": 200, "diastolic_bp": 130, "heart_rate": 120},
                recent_glucose=[],
                recent_bp=[(200, 130), (195, 128), (198, 129)],
                missed_medication_count=3,
            ),
            generate_recommendations(
                disease=DiseaseType.STROKE,
                risk_level=RiskLevel.CRITICAL,
                features={
                    "systolic_bp": 185,
                    "avg_glucose_level": 250,
                    "glucose": 250,
                    "hypertension_flag": 1,
                    "heart_disease_flag": 1,
                },
                recent_glucose=[250, 245],
                recent_bp=[(185, 110), (180, 108)],
                missed_medication_count=4,
            ),
        ]
        for recs in scenarios:
            for rec in recs:
                for phrase in FORBIDDEN_PHRASES:
                    assert phrase not in rec.lower(), f"Forbidden phrase '{phrase}' found in: {rec}"

    def test_missed_medication_wording_is_adherence_not_dosage_change(self):
        recs = generate_recommendations(
            disease=DiseaseType.DIABETES,
            risk_level=RiskLevel.MODERATE,
            features={"avg_glucose_level": 150, "glucose": 150, "bmi": 27, "diastolic_bp": 80},
            recent_glucose=[150],
            recent_bp=[],
            missed_medication_count=4,
        )
        missed_rec = next(r for r in recs if "missed" in r.lower())
        assert "prescriber" in missed_rec.lower() or "raising with" in missed_rec.lower()
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in missed_rec.lower()
