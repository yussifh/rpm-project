"""
RiskPredictionEngine — loads the trained joblib artifacts and exposes a
single `predict(disease, features)` method.

Design decisions:
- Models are loaded ONCE, lazily, and cached (singleton pattern via
  functools.lru_cache on the module-level getter) — not reloaded from disk
  on every API request. Joblib deserialization of a RandomForest is not
  free; doing it per-request would tank throughput.
- This module has ZERO dependency on FastAPI, SQLAlchemy, or any web
  framework — it takes a plain dict of features and returns a plain dict
  of results. That means it can be unit-tested, reused in a batch/offline
  scoring script, or swapped behind a different API entirely, without any
  changes here.
- Raises a clear, actionable error if a model file is missing (e.g. someone
  cloned the repo but never ran `python -m app.ai_engine.train`) rather
  than a cryptic joblib/pickle stack trace.
"""

import functools
from pathlib import Path
from typing import TypedDict

import joblib
import pandas as pd

from app.ai_engine.feature_schema import DIABETES, FEATURE_SETS, HYPERTENSION, STROKE

MODELS_DIR = Path(__file__).parent / "models"

MODEL_FILENAMES = {
    STROKE: "stroke_model.joblib",
    DIABETES: "diabetes_model.joblib",
    HYPERTENSION: "hypertension_model.joblib",
}

# Risk-level cut points applied to the model's predicted probability.
# These thresholds are a reasonable starting point for a demo system —
# in a real deployment they should be tuned (e.g. via a clinician-reviewed
# precision/recall tradeoff on a validation set) rather than left as flat
# defaults.
RISK_LEVEL_THRESHOLDS = [
    (0.75, "critical"),
    (0.50, "high"),
    (0.25, "moderate"),
    (0.0, "low"),
]


class PredictionResult(TypedDict):
    disease_type: str
    risk_score: float
    risk_level: str
    model_version: str
    feature_names: list[str]
    data_source: str


class ModelNotTrainedError(Exception):
    def __init__(self, disease: str, expected_path: Path):
        super().__init__(
            f"No trained model found for '{disease}' at {expected_path}. "
            f"Run `python -m app.ai_engine.train` to generate model artifacts first."
        )


def _risk_level_for_score(score: float) -> str:
    for threshold, level in RISK_LEVEL_THRESHOLDS:
        if score >= threshold:
            return level
    return "low"  # unreachable given the 0.0 floor, but kept for safety


@functools.lru_cache(maxsize=None)
def _load_artifact(disease: str) -> dict:
    filename = MODEL_FILENAMES.get(disease)
    if filename is None:
        raise ValueError(f"Unknown disease type: '{disease}'")

    path = MODELS_DIR / filename
    if not path.exists():
        raise ModelNotTrainedError(disease, path)

    return joblib.load(path)


class RiskPredictionEngine:
    """Thin, stateless-facing wrapper around the cached model artifacts."""

    def predict(self, disease: str, features: dict) -> PredictionResult:
        artifact = _load_artifact(disease)
        feature_names = artifact["feature_names"]

        missing = [f for f in feature_names if f not in features]
        if missing:
            raise ValueError(f"Missing required features for '{disease}' prediction: {missing}")

        # Preserve exact column order/names the model was trained on — using
        # a DataFrame (not a bare list) avoids an sklearn UserWarning about
        # missing feature names, and is more robust to internal pipeline
        # column-order assumptions.
        ordered_row = pd.DataFrame([[features[name] for name in feature_names]], columns=feature_names)

        pipeline = artifact["pipeline"]
        risk_score = float(pipeline.predict_proba(ordered_row)[0][1])

        return PredictionResult(
            disease_type=disease,
            risk_score=round(risk_score, 4),
            risk_level=_risk_level_for_score(risk_score),
            model_version=artifact["model_version"],
            feature_names=feature_names,
            data_source=artifact.get("data_source", "unknown"),
        )

    def expected_features(self, disease: str) -> list[str]:
        return FEATURE_SETS[disease]

    def is_ready(self, disease: str) -> bool:
        path = MODELS_DIR / MODEL_FILENAMES[disease]
        return path.exists()

    def model_info(self, disease: str) -> dict:
        """
        Everything about a trained model EXCEPT the pipeline object itself —
        model_version, data_source, evaluation metrics, and feature
        importances. Powers the "why did the model flag this" chart and
        the model-transparency panel in the patient/admin UI; also the natural
        source of truth for a model card document.
        """
        artifact = _load_artifact(disease)
        return {
            "disease_type": disease,
            "model_version": artifact["model_version"],
            "data_source": artifact.get("data_source", "unknown"),
            "feature_names": artifact["feature_names"],
            "metrics": artifact.get("metrics", {}),
            "feature_importances": artifact.get("feature_importances", {}),
        }


# Module-level singleton — import and use directly: `from app.ai_engine.inference import risk_engine`
risk_engine = RiskPredictionEngine()
