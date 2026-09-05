"""
Tests for app.ai_engine — trains small, FAST models into a temporary
directory (monkeypatching MODELS_DIR) rather than depending on whatever
artifacts happen to be pre-built in app/ai_engine/models/. This makes the
suite self-contained: it passes on a fresh clone before anyone has ever
run `python -m app.ai_engine.train`.
"""

import pytest

from app.ai_engine import inference as inference_module
from app.ai_engine.data_synthesis import (
    generate_hypertension_dataset,
    generate_stroke_dataset,
)
from app.ai_engine.feature_schema import (
    DIABETES_FEATURES,
    HYPERTENSION,
    STROKE,
    STROKE_FEATURES,
)
from app.ai_engine.real_data import load_real_diabetes_dataset


class TestDataSynthesis:
    def test_stroke_dataset_has_expected_columns(self):
        df = generate_stroke_dataset(n=200)
        assert list(df.columns[:-1]) == STROKE_FEATURES
        assert "target" in df.columns

    def test_diabetes_dataset_target_is_binary(self):
        # Diabetes trains on the real Pima Indians Diabetes dataset now,
        # not a synthetic generator — see real_data.py. Nothing to
        # parameterize (fixed 768-row CSV), just confirm it loads cleanly
        # and the label is what train.py expects.
        df = load_real_diabetes_dataset()
        assert list(df.columns[:-1]) == DIABETES_FEATURES
        assert set(df["target"].unique()).issubset({0, 1})
        assert len(df) > 0

    def test_dataset_is_reproducible_with_same_seed(self):
        df1 = generate_stroke_dataset(n=100, seed=7)
        df2 = generate_stroke_dataset(n=100, seed=7)
        assert df1.equals(df2)

    def test_higher_risk_factors_correlate_with_higher_target_rate(self):
        # Not a strict guarantee for any single row, but should hold in aggregate:
        # older, hypertensive, heart-disease patients should have a higher
        # stroke-positive rate than young, healthy ones in a large sample.
        df = generate_stroke_dataset(n=8000)
        high_risk = df[(df["age"] > 60) & (df["hypertension_flag"] == 1) & (df["heart_disease_flag"] == 1)]
        low_risk = df[(df["age"] < 30) & (df["hypertension_flag"] == 0) & (df["heart_disease_flag"] == 0)]
        assert high_risk["target"].mean() > low_risk["target"].mean()


@pytest.fixture()
def trained_models_dir(tmp_path, monkeypatch):
    """Trains small, fast models into a temp directory and points both the
    training module and the inference engine at it, then clears the
    inference engine's lru_cache so it doesn't leak state between tests."""
    from app.ai_engine import train as train_module

    monkeypatch.setattr(train_module, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(inference_module, "MODELS_DIR", tmp_path)
    inference_module._load_artifact.cache_clear()

    # Scope the synthetic generators down to a small n. train_one() reads
    # DISEASE_CONFIG's generator at call time, so overriding the entries is
    # enough — otherwise this fixture would train the FULL production
    # models (30k rows × 3 candidates × 5-fold CV each), turning a "small,
    # fast" test fixture into a multi-minute bottleneck. Diabetes keeps its
    # real-data loader (2172 rows — already fast).
    monkeypatch.setitem(
        train_module.DISEASE_CONFIG,
        STROKE,
        {**train_module.DISEASE_CONFIG[STROKE], "generator": lambda: generate_stroke_dataset(n=1200)},
    )
    monkeypatch.setitem(
        train_module.DISEASE_CONFIG,
        HYPERTENSION,
        {**train_module.DISEASE_CONFIG[HYPERTENSION], "generator": lambda: generate_hypertension_dataset(n=1200)},
    )

    # Small n + few trees for test speed — full quality isn't the point here.
    for disease in train_module.DISEASE_CONFIG:
        train_module.train_one(disease)

    yield tmp_path
    inference_module._load_artifact.cache_clear()


class TestInferenceEngine:
    def test_predict_returns_expected_shape(self, trained_models_dir):
        engine = inference_module.RiskPredictionEngine()
        result = engine.predict(
            "stroke",
            {
                "age": 65,
                "gender_male": 1,
                "hypertension_flag": 1,
                "heart_disease_flag": 1,
                "avg_glucose_level": 180,
                "bmi": 30,
                "systolic_bp": 160,
                "heart_rate": 85,
            },
        )
        assert 0.0 <= result["risk_score"] <= 1.0
        assert result["risk_level"] in {"low", "moderate", "high", "critical"}
        assert result["disease_type"] == "stroke"

    def test_missing_feature_raises_value_error(self, trained_models_dir):
        engine = inference_module.RiskPredictionEngine()
        with pytest.raises(ValueError, match="Missing required features"):
            engine.predict("stroke", {"age": 40})

    def test_unknown_disease_raises_value_error(self, trained_models_dir):
        engine = inference_module.RiskPredictionEngine()
        with pytest.raises(ValueError, match="Unknown disease type"):
            engine.predict("flu", {})

    def test_model_not_trained_raises_clear_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(inference_module, "MODELS_DIR", tmp_path)
        inference_module._load_artifact.cache_clear()
        engine = inference_module.RiskPredictionEngine()
        with pytest.raises(inference_module.ModelNotTrainedError, match="diabetes"):
            engine.predict("diabetes", {f: 0 for f in DIABETES_FEATURES})
        inference_module._load_artifact.cache_clear()

    def test_higher_risk_profile_scores_higher_than_lower_risk_profile(self, trained_models_dir):
        engine = inference_module.RiskPredictionEngine()
        high_risk = engine.predict(
            "stroke",
            {
                "age": 70, "gender_male": 1, "hypertension_flag": 1, "heart_disease_flag": 1,
                "avg_glucose_level": 200, "bmi": 33, "systolic_bp": 170, "heart_rate": 90,
            },
        )
        low_risk = engine.predict(
            "stroke",
            {
                "age": 22, "gender_male": 0, "hypertension_flag": 0, "heart_disease_flag": 0,
                "avg_glucose_level": 85, "bmi": 21, "systolic_bp": 108, "heart_rate": 65,
            },
        )
        assert high_risk["risk_score"] > low_risk["risk_score"]
