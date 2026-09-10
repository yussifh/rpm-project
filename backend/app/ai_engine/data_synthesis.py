"""
Synthetic training data generator — RETIRED for STROKE and HYPERTENSION.
(Diabetes has always trained on real data; see real_data.py.)

As of model version v2.1.0, the stroke and hypertension models train on the
REAL Framingham Heart Study dataset — see real_data.py
(load_real_framingham_stroke_dataset / load_real_framingham_hypertension_dataset)
and feature_schema.py. The generators below are preserved ONLY for
reproducibility/audit of the retired synthetic models (backed up under
app/ai_engine/models/backup_synthetic/) and are no longer wired into
train.py.

*** THESE TWO DATASETS ARE NOT REAL PATIENT DATA. ***

Each generator produces clinically-INFORMED but artificially-sampled data:
features are drawn from plausible ranges, then combined into a weighted
"risk logit" using directionally-correct coefficients (e.g. higher glucose
increases stroke risk), passed through a sigmoid, and used as a
probability to sample a binary label with added noise. This produces a
dataset with a learnable, medically-sensible signal — enough to validate
the full pipeline (preprocessing -> training -> inference -> API) end to
end — WITHOUT requiring a real clinical dataset for this student project.

The label-noise term and base rates below are deliberately anchored to
published figures rather than picked arbitrarily:
- Stroke prevalence ~4.9% and hypertension/heart-disease comorbidity
  rates (~9.2% / ~4.95%) are taken from the widely-used Kaggle
  "Stroke Prediction Dataset" (fedesoriano / Sakthi Kumar Karuppasamy),
  which itself draws on real (if unlicensed-for-redistribution) patient
  records. We use its *aggregate statistics* to calibrate our synthetic
  generator's intercept and flag rates, without redistributing its rows.
- The per-sample noise term was reduced from the previous version
  (0.6 -> 0.35 std) because injecting that much label noise on top of an
  already-modest signal was artificially capping achievable precision —
  real biological risk isn't that noisy sample-to-sample; measurement and
  omitted-variable noise is real but shouldn't dominate the signal.
- Default sample size raised from 8,000 to 30,000 per disease. At ~4-5%
  positive prevalence, 8,000 rows yielded only ~340-370 positive
  examples per model after the train/test split — too few for a
  RandomForest (or any model) to learn a stable minority-class decision
  boundary; precision at the standard 0.5 cutoff was sitting around
  11-18%, an unreliable basis for a "risk assessment" a patient sees.
  30,000 rows yields ~1,300-1,400 positive examples, a meaningfully
  larger and more stable sample for the minority class without materially
  changing generation time (a few seconds either way).

Before any real-world use, replace these generators with a loader for a
real, ethically-sourced, IRB/consent-appropriate clinical dataset, and
re-run `train.py` unchanged (it only depends on getting back a DataFrame
with the expected feature columns + a `target` column).
"""

import numpy as np
import pandas as pd

from app.ai_engine.feature_schema import (
    HYPERTENSION_FEATURES,
    STROKE_FEATURES,
)

# Reduced from 0.6 in the original version — see module docstring.
LABEL_NOISE_STD = 0.35

RANDOM_SEED = 42


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))


def _sample_labels(rng: np.random.Generator, logits: np.ndarray) -> np.ndarray:
    probabilities = _sigmoid(logits)
    return rng.binomial(1, probabilities)


def generate_stroke_dataset(n: int = 30000, seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    age = rng.uniform(18, 90, n)
    gender_male = rng.binomial(1, 0.49, n)
    # Comorbidity rates anchored to the Kaggle stroke cohort's published
    # aggregates (~9.2% hypertension, ~4.95% heart disease) rather than
    # arbitrary round numbers — see module docstring.
    hypertension_flag = rng.binomial(1, 0.092, n)
    heart_disease_flag = rng.binomial(1, 0.0495, n)
    avg_glucose_level = rng.normal(105, 35, n).clip(60, 300)
    bmi = rng.normal(27, 6, n).clip(15, 55)
    systolic_bp = rng.normal(125, 18, n).clip(85, 220)
    heart_rate = rng.normal(75, 12, n).clip(45, 160)

    # Weighted, standardized-ish contributions (illustrative, not clinically
    # derived coefficients). Intercept tuned so the sampled prevalence lands
    # close to the ~4.9% stroke rate reported for the reference cohort.
    logits = (
        -6.6
        + 0.045 * age
        + 0.30 * gender_male
        + 0.85 * hypertension_flag
        + 1.10 * heart_disease_flag
        + 0.012 * (avg_glucose_level - 100)
        + 0.03 * (bmi - 25)
        + 0.02 * (systolic_bp - 120)
        + 0.01 * (heart_rate - 75)
        + rng.normal(0, LABEL_NOISE_STD, n)
    )
    target = _sample_labels(rng, logits)

    df = pd.DataFrame(
        {
            "age": age,
            "gender_male": gender_male,
            "hypertension_flag": hypertension_flag,
            "heart_disease_flag": heart_disease_flag,
            "avg_glucose_level": avg_glucose_level,
            "bmi": bmi,
            "systolic_bp": systolic_bp,
            "heart_rate": heart_rate,
            "target": target,
        }
    )
    assert list(df.columns[:-1]) == STROKE_FEATURES
    return df


def generate_hypertension_dataset(n: int = 30000, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """
    Label framing: risk of a HYPERTENSION-RELATED ADVERSE OUTCOME (e.g.
    hypertensive crisis, poor control requiring intervention) given a
    patient's CURRENT vitals + demographics — not "will develop
    hypertension" (which would make using BP as a feature circular). This
    matches how the RPM system actually uses this model: assessing
    severity/risk for an already-monitored patient, not screening a
    hypertension-naive population.
    """
    rng = np.random.default_rng(seed)

    age = rng.uniform(18, 90, n)
    bmi = rng.normal(28, 6, n).clip(15, 55)
    gender_male = rng.binomial(1, 0.49, n)
    systolic_bp = rng.normal(128, 20, n).clip(85, 220)
    diastolic_bp = rng.normal(82, 12, n).clip(50, 140)
    heart_rate = rng.normal(76, 12, n).clip(45, 160)
    glucose = rng.normal(105, 28, n).clip(60, 300)

    # Intercept re-tuned after reducing LABEL_NOISE_STD: the previous
    # -8.0 intercept relied on a wide noise term to push enough samples
    # over the decision boundary, so cutting the noise (see module
    # docstring) collapsed prevalence to under 1% — an unintended and
    # unrealistic side effect, not a deliberate epidemiological choice.
    # -6.2 restores a ~8-10% positive rate, a more learnable and more
    # plausible rate for a "high-severity reading" outcome.
    logits = (
        -6.2
        + 0.02 * age
        + 0.05 * (bmi - 25)
        + 0.20 * gender_male
        + 0.06 * (systolic_bp - 120)
        + 0.07 * (diastolic_bp - 80)
        + 0.015 * (heart_rate - 75)
        + 0.01 * (glucose - 100)
        + rng.normal(0, LABEL_NOISE_STD, n)
    )
    target = _sample_labels(rng, logits)

    df = pd.DataFrame(
        {
            "age": age,
            "bmi": bmi,
            "gender_male": gender_male,
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "heart_rate": heart_rate,
            "glucose": glucose,
            "target": target,
        }
    )
    assert list(df.columns[:-1]) == HYPERTENSION_FEATURES
    return df
