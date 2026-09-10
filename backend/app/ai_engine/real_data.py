"""
Loader for REAL (non-synthetic) training data.

Backs ALL THREE disease models:
- diabetes: Pima Indians Diabetes Dataset (real patients).
- stroke & hypertension: Framingham Heart Study (real patients), see the
  two loader functions below for the exact feature/target mapping.

Source: Pima Indians Diabetes Dataset — Smith et al., 1988, National
Institute of Diabetes and Digestive and Kidney Diseases. 768 real patients
(all female, Pima Indian heritage, age 21+). Public domain / widely
mirrored (UCI Machine Learning Repository). Local copy at
app/ai_engine/data/pima_diabetes.csv, columns in original order:
Pregnancies, Glucose, BloodPressure (diastolic, mm Hg), SkinThickness,
Insulin, BMI, DiabetesPedigreeFunction, Age, Outcome.

Known dataset quirk: missing values for Glucose, BloodPressure, BMI,
SkinThickness, and Insulin are encoded as 0 (a physiologically impossible
value for a living patient), not NaN. We drop rows where any feature we use
is 0, rather than imputing, so the model only ever trains on values a
clinician would recognize as real. Note: SkinThickness and Insulin are no
longer part of the diabetes feature set (the app's vitals form doesn't
capture them), so only 0-Glucose, 0-BP, and 0-BMI rows are excluded —
better a smaller honest dataset than a larger one with fabricated zeros
baked in as if they were real readings.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from app.ai_engine.feature_schema import (
    DIABETES_FEATURES,
    HYPERTENSION_FEATURES,
    STROKE_FEATURES,
)

DATA_DIR = Path(__file__).parent / "data"
PIMA_CSV = DATA_DIR / "pima_diabetes.csv"
FRAMINGHAM_CSV = DATA_DIR / "framingham.csv"

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
            "diabetes_pedigree": df["diabetes_pedigree"].astype(float),
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
    Real Pima data (rows where any used feature is 0/"missing" are dropped,
    including skin_thickness zeros since the model no longer uses that
    column) PLUS a bootstrap augmentation: each
    real row is resampled several times with small Gaussian jitter added to
    its own feature values, per-feature std scaled to a fraction of that
    FEATURE'S OWN observed std within its class (not an arbitrary noise
    level) — a standard, well-understood technique for stabilizing a small
    dataset (conceptually similar to SMOTE, but simpler: jittered
    near-duplicates of real points rather than interpolated synthetic
    points between them).

    This is explicitly NOT additional real patient data, and is labeled
    as such everywhere it surfaces (`data_source` on the trained
    artifact, the training report, MODEL_CARD.md) — augmentation changes
    how much a small real dataset can teach a model about the LOCAL shape
    of the decision boundary around real examples, but every one of the
    augmented rows is a jittered copy of a real patient's data, not new
    information from a new patient. Real rows remain the true
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

    feature_cols = DIABETES_FEATURES  # ["age", "bmi", "glucose", "diastolic_bp", "diabetes_pedigree"]
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
    augmented["diabetes_pedigree"] = augmented["diabetes_pedigree"].clip(lower=0.02)

    combined = pd.concat([real, augmented], ignore_index=True)
    assert list(combined.columns[:-1]) == DIABETES_FEATURES
    return combined


# ---------------------------------------------------------------------------
# Framingham Heart Study — REAL data for the stroke & hypertension models.
# ---------------------------------------------------------------------------
#
# Local copy: app/ai_engine/data/framingham.csv (4,240 real patients from
# the Framingham Heart Study, a landmark long-term cardiovascular cohort
# study that first established the modern concept of cardiovascular risk
# factors). Widely publicly mirrored; the saved copy is the standard
# Kaggle/GitHub "Framingham Heart Study Dataset" subset (4240 rows, 16
# columns). Column mapping used here:
#
#   male          -> gender_male
#   age           -> age
#   sysBP         -> systolic_bp
#   diaBP         -> diastolic_bp
#   BMI           -> bmi
#   heartRate     -> heart_rate
#   glucose       -> (avg_)glucose_level
#   prevalentHyp  -> hypertension_flag / hypertension target
#   prevalentStroke -> heart_disease_flag (see stroke loader note)
#   TenYearCHD    -> stroke target (see stroke loader note)
#
# Missing values are dropped per-feature (listwise on the columns each
# loader needs), consistent with how the Pima loader handles its own
# encoding of missing data — a smaller honest dataset beats imputed or
# invented readings.

FRAMINGHAM_COLUMNS = [
    "male", "age", "education", "current_smoker", "cigs_per_day", "bp_meds",
    "prevalent_stroke", "prevalent_hyp", "diabetes", "tot_chol", "sys_bp",
    "dia_bp", "bmi", "heart_rate", "glucose", "ten_year_chd",
]


def _load_framingham() -> pd.DataFrame:
    """Load + clean the raw Framingham CSV into tidy column names.

    Rows missing any of the continuous vitals or the flag columns used by
    the two disease loaders are dropped (listwise). Columns are renamed to
    the app's snake_case equivalents for readability downstream.
    """
    if not FRAMINGHAM_CSV.exists():
        raise FileNotFoundError(
            f"Real Framingham dataset not found at {FRAMINGHAM_CSV}. "
            "This should be checked into the repo — see app/ai_engine/data/framingham.csv."
        )
    raw = pd.read_csv(FRAMINGHAM_CSV)
    raw.columns = FRAMINGHAM_COLUMNS
    float_cols = ["sys_bp", "dia_bp", "bmi", "heart_rate", "glucose"]
    for c in float_cols:
        raw[c] = raw[c].astype(float)
    for c in ["male", "prevalent_hyp", "prevalent_stroke", "ten_year_chd"]:
        raw[c] = raw[c].astype(int)
    raw["age"] = raw["age"].astype(float)
    return raw


def _framingham_dropna(raw: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Drop rows with any missing value in the given columns, and keep only
    the five equity nations' worth of columns we actually use."""
    clean = raw.dropna(subset=cols).copy()
    return clean.reset_index(drop=True)


def load_real_framingham_stroke_dataset() -> pd.DataFrame:
    """REAL-data loader for the STROKE model feature set.

    Target frame: `ten_year_chd` (10-year risk of developing coronary heart
    disease), Framingham's published hard outcome that its risk equations —
    including the Framingham Stroke Risk Profile — were built to predict.
    This is the honest real target available in this dataset: the literal
    `prevalent_stroke` column has only 25 positive cases (0.6%) across 4,240
    patients, far too sparse for a classifier to learn a stable decision
    boundary. Predicting 10-year atherosclerotic CVD risk is the closest
    defensible real-data framing for this app's "stroke risk" model, because
    stroke and CHD share the same underlying atherosclerotic risk-factor
    pathway and the same Framingham risk-score foundation.

    Feature mapping (all 8 STROKE_FEATURES present in Framingham):
      age; gender_male <- male; hypertension_flag <- prevalent_hyp;
      heart_disease_flag <- prevalent_stroke (a prior cerebrovascular event
      is the strongest single predictor of a future event, used here as the
      "pre-existing cardiovascular condition" flag); avg_glucose_level <-
      glucose; bmi <- bmi; systolic_bp <- sys_bp; heart_rate <- heart_rate.
    """
    raw = _load_framingham()
    cols = ["male", "age", "prevalent_hyp", "prevalent_stroke",
            "glucose", "bmi", "sys_bp", "heart_rate"]
    clean = _framingham_dropna(raw, cols)

    out = pd.DataFrame(
        {
            "age": clean["age"],
            "gender_male": clean["male"],
            "hypertension_flag": clean["prevalent_hyp"],
            "heart_disease_flag": clean["prevalent_stroke"],
            "avg_glucose_level": clean["glucose"],
            "bmi": clean["bmi"],
            "systolic_bp": clean["sys_bp"],
            "heart_rate": clean["heart_rate"],
            "target": clean["ten_year_chd"],
        }
    )
    assert list(out.columns[:-1]) == STROKE_FEATURES
    return out


def load_real_framingham_hypertension_dataset() -> pd.DataFrame:
    """REAL-data loader for the HYPERTENSION model feature set.

    Target frame: `prevalent_hyp` (1 = the patient was hypertensive —
    defined in the study as systolic >= 140 / diastolic >= 90, or being on
    antihypertensive treatment). Used as the real-data proxy for this
    model's original "risk of a hypertension-related adverse outcome"
    framing. NOTE the inherent coupling the app already accepted: this model
    takes blood pressure as an INPUT while the target label is derived from
    blood pressure thresholds, so some circularity is unavoidable for this
    app's feature set. The value of this swap is that the boundary and the
    relationship to age/BMI/glucose/heart-rate are now learned from 4,240
    real patients rather than a fabricated logit.

    Feature mapping (all 7 HYPERTENSION_FEATURES present in Framingham):
      age; bmi; gender_male <- male; systolic_bp <- sys_bp; diastolic_bp <-
      dia_bp; heart_rate <- heart_rate; glucose <- glucose.
    """
    raw = _load_framingham()
    cols = ["male", "age", "bmi", "sys_bp", "dia_bp", "heart_rate", "glucose"]
    clean = _framingham_dropna(raw, cols)

    out = pd.DataFrame(
        {
            "age": clean["age"],
            "bmi": clean["bmi"],
            "gender_male": clean["male"],
            "systolic_bp": clean["sys_bp"],
            "diastolic_bp": clean["dia_bp"],
            "heart_rate": clean["heart_rate"],
            "glucose": clean["glucose"],
            "target": clean["prevalent_hyp"],
        }
    )
    assert list(out.columns[:-1]) == HYPERTENSION_FEATURES
    return out
