"""
Loader for REAL (non-synthetic) training data.

Currently backs the diabetes model only — see feature_schema.py for why
stroke/hypertension can't use a public dataset directly given this app's
feature set.

Source: Pima Indians Diabetes Dataset — Smith et al., 1988, National
Institute of Diabetes and Digestive and Kidney Diseases. 768 real patients
(all female, Pima Indian heritage, age 21+). Public domain / widely
mirrored (UCI Machine Learning Repository). Local copy at
app/ai_engine/data/pima_diabetes.csv, columns in original order:
Pregnancies, Glucose, BloodPressure (diastolic, mm Hg), SkinThickness,
Insulin, BMI, DiabetesPedigreeFunction, Age, Outcome.

Known dataset quirk: missing values for Glucose, BloodPressure, and BMI
are encoded as 0 (a physiologically impossible value for a living
patient), not NaN. We drop rows where any feature we use is 0, rather
than imputing, so the model only ever trains on values a clinician would
recognize as real. This drops a meaningful fraction of rows (~here 0-BMI
and 0-BP rows are excluded) — better a smaller honest dataset than a
larger one with fabricated zeros baked in as if they were real readings.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from app.ai_engine.feature_schema import DIABETES_FEATURES

DATA_DIR = Path(__file__).parent / "data"
PIMA_CSV = DATA_DIR / "pima_diabetes.csv"

PIMA_COLUMNS = [
    "pregnancies",
    "glucose",
    "diastolic_bp",
    "skin_thickness",
    "insulin",
    "bmi",
    "diabetes_pedigree",
    "age",
    "target",
]


def load_real_diabetes_dataset() -> pd.DataFrame:
    if not PIMA_CSV.exists():
        raise FileNotFoundError(
            f"Real diabetes dataset not found at {PIMA_CSV}. "
            "This should be checked into the repo — see app/ai_engine/data/pima_diabetes.csv."
        )

    df = pd.read_csv(PIMA_CSV, header=None, names=PIMA_COLUMNS)

    # Drop physiologically-impossible zero readings (this dataset's way of
    # encoding "missing") rather than imputing — see module docstring.
    for col in ("glucose", "diastolic_bp", "bmi"):
        df = df[df[col] > 0]

    df = df.reset_index(drop=True)

    out = pd.DataFrame(
        {
            "age": df["age"].astype(float),
            "bmi": df["bmi"].astype(float),
            "glucose": df["glucose"].astype(float),
            "diastolic_bp": df["diastolic_bp"].astype(float),
            "target": df["target"].astype(int),
        }
    )
    assert list(out.columns[:-1]) == DIABETES_FEATURES
    return out


# How many synthetic rows to generate per real row, per class — see
# load_real_diabetes_dataset_augmented() docstring below.
AUGMENTATION_MULTIPLIER = 3
AUGMENTATION_SEED = 42


def load_real_diabetes_dataset_augmented() -> pd.DataFrame:
    """
    Real Pima data (724 usable rows after cleaning) PLUS a bootstrap
    augmentation: each real row is resampled several times with small
    Gaussian jitter added to its own feature values, per-feature std
    scaled to a fraction of that FEATURE'S OWN observed std within its
    class (not an arbitrary noise level) — a standard, well-understood
    technique for stabilizing a small dataset (conceptually similar to
    SMOTE, but simpler: jittered near-duplicates of real points rather
    than interpolated synthetic points between them).

    This is explicitly NOT additional real patient data, and is labeled
    as such everywhere it surfaces (`data_source` on the trained
    artifact, the training report, MODEL_CARD.md) — augmentation changes
    how much a small real dataset can teach a model about the LOCAL shape
    of the decision boundary around real examples, but every one of the
    augmented rows is a jittered copy of a real patient's data, not new
    information from a new patient. 724 real rows remain the true
    information content; this makes the most of them rather than
    pretending there's more independent signal than there is.

    Why bootstrap-jitter rather than a fully independent synthetic
    generator (like stroke/hypertension use): those two diseases have NO
    real dataset compatible with this app's feature set at all (see
    feature_schema.py), so an independent logit-based generator anchored
    to published prevalence is the best available option. Diabetes DOES
    have real, if scarce, ground truth — jittering around it keeps every
    augmented point anchored to an actual observed patient rather than an
    invented one.
    """
    real = load_real_diabetes_dataset()
    rng = np.random.default_rng(AUGMENTATION_SEED)

    feature_cols = DIABETES_FEATURES  # ["age", "bmi", "glucose", "diastolic_bp"]
    augmented_rows = []

    for target_class in (0, 1):
        class_df = real[real["target"] == target_class]
        # Jitter scale: 8% of this class's own per-feature std — enough to
        # generate a genuinely different nearby point, small enough that
        # it stays a plausible variant of the same real patient rather
        # than drifting into a different clinical picture.
        stds = {col: class_df[col].std() * 0.08 for col in feature_cols}

        for _, row in class_df.iterrows():
            for _ in range(AUGMENTATION_MULTIPLIER):
                jittered = {col: row[col] + rng.normal(0, stds[col]) for col in feature_cols}
                jittered["target"] = target_class
                augmented_rows.append(jittered)

    augmented = pd.DataFrame(augmented_rows)
    # Clip back to physiologically plausible ranges after jitter — a
    # negative BMI or glucose is a jitter artifact, not a real possibility.
    augmented["age"] = augmented["age"].clip(lower=18)
    augmented["bmi"] = augmented["bmi"].clip(lower=12)
    augmented["glucose"] = augmented["glucose"].clip(lower=30)
    augmented["diastolic_bp"] = augmented["diastolic_bp"].clip(lower=30)

    combined = pd.concat([real, augmented], ignore_index=True)
    assert list(combined.columns[:-1]) == DIABETES_FEATURES
    return combined
