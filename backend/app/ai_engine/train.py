"""
Training pipeline for the stroke, diabetes, and hypertension risk models.

Run with:
    python -m app.ai_engine.train

Design decisions:
- Each model is a scikit-learn Pipeline(StandardScaler -> classifier),
  saved as ONE joblib artifact so inference never has to remember to apply
  scaling separately — the Pipeline guarantees preprocessing and model stay
  in sync.
- MODEL COMPARISON: for each disease, several candidate algorithms
  (Logistic Regression, Random Forest, Gradient Boosting) are evaluated
  via 5-fold stratified cross-validation on the TRAINING split, scored by
  ROC-AUC, and the best-performing one is refit on the full training set
  and used as that disease's model. This isn't "try everything and hope" —
  it's the standard candidate set for tabular binary classification at
  this dataset scale, evaluated the same way for every disease so the
  comparison is apples-to-apples. Every candidate's CV score is kept in
  the training report, so the choice is auditable, not just asserted.
- Artifacts are saved as {"pipeline": ..., "feature_names": [...], "model_version": ...,
  "metrics": {...}} — everything inference needs is self-contained in one file.
"""

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ai_engine.data_synthesis import (
    generate_hypertension_dataset,
    generate_stroke_dataset,
)
from app.ai_engine.real_data import load_real_diabetes_dataset_augmented
from app.ai_engine.feature_schema import (
    DIABETES,
    DIABETES_FEATURES,
    HYPERTENSION,
    HYPERTENSION_FEATURES,
    MODEL_VERSION,
    STROKE,
    STROKE_FEATURES,
)

MODELS_DIR = Path(__file__).parent / "models"

# Candidate algorithms compared for every disease — see module docstring.
# class_weight="balanced" on the two that support it directly compensates
# for stroke/hypertension's ~4-5% positive prevalence; GradientBoosting
# doesn't expose that param, so it instead gets a matching sample_weight
# at fit time (handled in train_one).
CANDIDATE_MODELS = {
    "logistic_regression": lambda: LogisticRegression(
        class_weight="balanced", max_iter=2000, random_state=42
    ),
    "random_forest": lambda: RandomForestClassifier(
        n_estimators=200, max_depth=6, min_samples_leaf=10, random_state=42, class_weight="balanced"
    ),
    "gradient_boosting": lambda: GradientBoostingClassifier(
        n_estimators=200, max_depth=3, learning_rate=0.05, random_state=42
    ),
}

DISEASE_CONFIG = {
    STROKE: {
        "generator": generate_stroke_dataset,
        "features": STROKE_FEATURES,
        "filename": "stroke_model.joblib",
        "data_source": "synthetic-epidemiologically-informed-n30000",
    },
    DIABETES: {
        "generator": load_real_diabetes_dataset_augmented,
        "features": DIABETES_FEATURES,
        "filename": "diabetes_model.joblib",
        "data_source": "real-pima-n724+bootstrap-augmented-n2172",
    },
    HYPERTENSION: {
        "generator": generate_hypertension_dataset,
        "features": HYPERTENSION_FEATURES,
        "filename": "hypertension_model.joblib",
        "data_source": "synthetic-epidemiologically-informed-n30000",
    },
}


def _sample_weight_for(y) -> "list[float] | None":
    """Balanced sample weights, equivalent in effect to class_weight=
    'balanced' — used for GradientBoostingClassifier, which doesn't accept
    that constructor param directly."""
    y = np.asarray(y)
    n = len(y)
    n_pos = y.sum()
    n_neg = n - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    weight_pos = n / (2 * n_pos)
    weight_neg = n / (2 * n_neg)
    return [weight_pos if label == 1 else weight_neg for label in y]


def _compare_and_select_model(X_train, y_train) -> tuple[str, dict]:
    """5-fold stratified CV, scored on ROC-AUC, per candidate. Returns
    (best_model_name, {name: mean_cv_auc for every candidate})."""
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores: dict[str, float] = {}

    for name, factory in CANDIDATE_MODELS.items():
        pipeline = Pipeline(steps=[("scaler", StandardScaler()), ("classifier", factory())])
        scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="roc_auc")
        cv_scores[name] = round(float(scores.mean()), 4)

    best_name = max(cv_scores, key=cv_scores.get)
    return best_name, cv_scores


def train_one(disease: str) -> dict:
    config = DISEASE_CONFIG[disease]
    df = config["generator"]()
    feature_names = config["features"]

    X = df[feature_names]
    y = df["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    best_model_name, cv_scores = _compare_and_select_model(X_train, y_train)

    classifier = CANDIDATE_MODELS[best_model_name]()
    pipeline = Pipeline(steps=[("scaler", StandardScaler()), ("classifier", classifier)])

    if best_model_name == "gradient_boosting":
        sample_weight = _sample_weight_for(y_train)
        pipeline.fit(X_train, y_train, classifier__sample_weight=sample_weight)
    else:
        pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    # The app doesn't actually act on a bare 0.5 cutoff — it buckets
    # risk_score into low/moderate/high/critical (see inference.py
    # RISK_LEVEL_THRESHOLDS). Precision/recall AT 0.5 is a standard
    # sklearn default, not the operating point clinicians actually see, so
    # we also report precision/recall at the 0.25 "moderate-or-above" and
    # 0.5 "high-or-above" cutoffs for a fair picture of real-world behavior.
    threshold_metrics = {}
    for cutoff, label in [(0.25, "at_moderate_plus_0.25"), (0.5, "at_high_plus_0.5")]:
        preds_at_cutoff = (y_proba >= cutoff).astype(int)
        threshold_metrics[label] = {
            "precision": round(precision_score(y_test, preds_at_cutoff, zero_division=0), 4),
            "recall": round(recall_score(y_test, preds_at_cutoff, zero_division=0), 4),
        }

    metrics = {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, y_proba), 4),
        # Brier score: mean squared error between predicted probability and
        # actual outcome (0 = perfect calibration, 0.25 = coin-flip-level
        # uncertainty). Reported because risk_score is shown to clinicians
        # as a probability-like number — accuracy/precision alone don't
        # tell you whether that number is trustworthy as a probability.
        "brier_score": round(brier_score_loss(y_test, y_proba), 4),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "positive_rate_train": round(float(y_train.mean()), 4),
        "threshold_metrics": threshold_metrics,
        "model_selected": best_model_name,
        "model_comparison_cv_roc_auc": cv_scores,
    }

    if best_model_name == "logistic_regression":
        # Logistic Regression has coefficients, not feature_importances_ —
        # use absolute standardized coefficient magnitude as the closest
        # equivalent (features are scaled, so coefficients are comparable
        # to each other), then normalize to proportions of their own sum.
        # Without this, these values don't sum to ~1 the way tree-based
        # feature_importances_ does, and the UI (which renders every
        # model's importances as "% of total") would show nonsensical
        # numbers like "103%" for whichever algorithm happened to be
        # selected for a given disease.
        raw = abs(pipeline.named_steps["classifier"].coef_[0])
        importances = raw / raw.sum()
    else:
        importances = pipeline.named_steps["classifier"].feature_importances_
    feature_importances = dict(zip(feature_names, importances.round(4).tolist()))

    artifact = {
        "pipeline": pipeline,
        "feature_names": feature_names,
        "model_version": MODEL_VERSION,
        "disease_type": disease,
        "data_source": config["data_source"],
        "metrics": metrics,
        "feature_importances": feature_importances,
    }

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = MODELS_DIR / config["filename"]
    joblib.dump(artifact, output_path)

    return {
        "disease": disease,
        "path": str(output_path),
        "data_source": config["data_source"],
        **metrics,
        "feature_importances": feature_importances,
    }


def main():
    report = []
    for disease in DISEASE_CONFIG:
        result = train_one(disease)
        report.append(result)
        print(f"\n=== {disease.upper()} MODEL ===")
        print(f"  Selected: {result['model_selected']}  (CV ROC-AUC comparison: {result['model_comparison_cv_roc_auc']})")
        print(f"  Saved to: {result['path']}")
        print(f"  Train/test size: {result['train_size']}/{result['test_size']}  |  Positive rate: {result['positive_rate_train']}")
        print(f"  Accuracy: {result['accuracy']}  |  ROC-AUC: {result['roc_auc']}")
        print(f"  Precision: {result['precision']}  |  Recall: {result['recall']}")
        print(f"  Feature importances: {result['feature_importances']}")

    report_path = MODELS_DIR / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull training report written to {report_path}")


if __name__ == "__main__":
    main()
