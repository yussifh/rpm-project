"""
Regenerates docs/roc_curves.png and docs/confusion_matrices.png from the
CURRENTLY TRAINED model artifacts + a fresh held-out split of each
disease's dataset (same random_state as train.py, so the split matches
exactly what training_report.json reports metrics on).

Run with:
    python -m scripts.generate_model_docs
(after `python -m app.ai_engine.train`, so the artifacts these plots
describe are the ones actually shipped)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import joblib
import matplotlib.pyplot as plt
from sklearn.metrics import ConfusionMatrixDisplay, RocCurveDisplay
from sklearn.model_selection import train_test_split

from app.ai_engine.data_synthesis import generate_hypertension_dataset, generate_stroke_dataset
from app.ai_engine.real_data import load_real_diabetes_dataset_augmented
from app.ai_engine.feature_schema import DIABETES_FEATURES, HYPERTENSION_FEATURES, STROKE_FEATURES

DOCS_DIR = Path(__file__).parent.parent.parent / "docs"
MODELS_DIR = Path(__file__).parent.parent / "app" / "ai_engine" / "models"

DISEASES = [
    ("stroke", generate_stroke_dataset, STROKE_FEATURES, "stroke_model.joblib"),
    ("diabetes", load_real_diabetes_dataset_augmented, DIABETES_FEATURES, "diabetes_model.joblib"),
    ("hypertension", generate_hypertension_dataset, HYPERTENSION_FEATURES, "hypertension_model.joblib"),
]


def main():
    DOCS_DIR.mkdir(exist_ok=True)

    fig_roc, axes_roc = plt.subplots(1, 3, figsize=(15, 4.5))
    fig_cm, axes_cm = plt.subplots(1, 3, figsize=(15, 4.5))

    for i, (name, generator, features, filename) in enumerate(DISEASES):
        df = generator()
        X = df[features]
        y = df["target"]
        _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        artifact = joblib.load(MODELS_DIR / filename)
        pipeline = artifact["pipeline"]

        RocCurveDisplay.from_estimator(pipeline, X_test, y_test, ax=axes_roc[i], name=name.title())
        axes_roc[i].plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1)
        axes_roc[i].set_title(f"{name.title()} — ROC (n_test={len(y_test)})")

        y_pred = pipeline.predict(X_test)
        ConfusionMatrixDisplay.from_predictions(
            y_test, y_pred, ax=axes_cm[i], colorbar=False, display_labels=["No event", "Event"]
        )
        axes_cm[i].set_title(f"{name.title()} — Confusion Matrix (cutoff 0.5)")

    fig_roc.suptitle("ROC Curves — trained on updated datasets (see MODEL_CARD.md)", y=1.02)
    fig_roc.tight_layout()
    fig_roc.savefig(DOCS_DIR / "roc_curves.png", dpi=150, bbox_inches="tight")

    fig_cm.suptitle("Confusion Matrices — held-out test set, 0.5 cutoff", y=1.02)
    fig_cm.tight_layout()
    fig_cm.savefig(DOCS_DIR / "confusion_matrices.png", dpi=150, bbox_inches="tight")

    print(f"Wrote {DOCS_DIR / 'roc_curves.png'}")
    print(f"Wrote {DOCS_DIR / 'confusion_matrices.png'}")


if __name__ == "__main__":
    main()
