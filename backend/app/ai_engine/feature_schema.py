"""
Feature schema definitions — the single source of truth for which features
each disease model expects, and in what order.

Design decision: feature lists are DELIBERATELY constrained to data this
system actually captures (PatientProfile + VitalReading + MedicalHistoryEntry
flags), rather than mirroring public datasets feature-for-feature (e.g. the
classic stroke dataset also has smoking_status/work_type, which we don't
collect). Keeping the feature list matched to real captured data means the
model can run in production the day this system launches, not just on a
one-off imported dataset.

IMPORTANT — data source disclosure (per disease):
- DIABETES: trained on the real, public Pima Indians Diabetes dataset
  (768 real patient records; UCI Machine Learning Repository / National
  Institute of Diabetes and Digestive and Kidney Diseases). This is real
  patient data, not synthetic — see app/ai_engine/data/pima_diabetes.csv
  and app/ai_engine/real_data.py. Its features (age, bmi, glucose,
  diastolic_bp, diabetes_pedigree) map one-to-one to that dataset's
  columns (skin_thickness and insulin are intentionally excluded — the
  app's vitals form doesn't capture them), which is why this list differs
  slightly from the other two diseases.
- STROKE and HYPERTENSION: previously SYNTHETIC (see data_synthesis.py for
  the retired generators). Both have been RETRAINED on the REAL, public
  Framingham Heart Study dataset (4,240 real patients) — the landmark
  cardiovascular cohort that first established the modern concept of
  cardiovascular risk factors. Local copy at
  app/ai_engine/data/framingham.csv, loaders in real_data.py
  (load_real_framingham_stroke_dataset / _hypertension_dataset). These
  loaders map Framingham's continuous vitals (sysBP, diaBP, BMI, heartRate,
  glucose) onto this app's exact feature lists, so every STROKE_FEATURES /
  HYPERTENSION_FEATURES column is now backed by real measured values rather
  than simulated ones. Two honest caveats about target framing:
    * HYPERTENSION target = Framingham's `prevalentHyp` (patient was
      hypertensive / on BP meds). Since the model takes blood pressure as an
      input, some circularity is inherent to this app's design — the value of
      the swap is that the decision boundary and its relationship to age,
      BMI, glucose and heart-rate are now learned from 4,240 real patients.
    * STROKE target = Framingham's `TenYearCHD` (10-year atherosclerotic CVD
      risk), the dataset's published hard outcome, because its literal
      `prevalentStroke` column has only 25 positives (0.6%) — too sparse to
      train on. Stroke and CHD share the same atherosclerotic risk-factor
      pathway and the same Framingham risk-score foundation, so this is the
      closest defensible real framing for this app's "stroke risk" model.
- The retired synthetic generators remain in data_synthesis.py and the old
  synthetic model artifacts are preserved under
  app/ai_engine/models/backup_synthetic/ for reproducibility/audit.

None of these three models are clinically validated. Though all three now
train on real patient data, each has population-specific limitations that
prevent direct clinical generalization: the diabetes model comes from 768
Pima Indian women (Arizona, ~1988 NIDDK study); the stroke/hypertension
models come from the Framingham cohort (mostly white, middle-class
Massachusetts residents, mid-20th century). Before any real-world clinical
use, these models must be reviewed/validated by a qualified clinician and
biostatistician, and ideally retrained on a dataset representative of the
target patient population. This is a student/portfolio project — treat the
shipped models as a working demonstration of the ARCHITECTURE and of good
MLOps practice (real data where available, documented provenance,
calibration), not as medical-grade predictors ready for patient-facing
clinical decisions.
"""

# Order matters — must match the column order used at training time.
#
# Note on systolic_bp (not diastolic_bp) here: this isn't an arbitrary
# choice. The Framingham Stroke Risk Profile (Wolf et al., 1991) — the
# standard clinical stroke-risk equation — uses systolic BP specifically,
# not diastolic, as its blood-pressure input. Clinically, isolated
# systolic hypertension (systolic rises with arterial stiffening while
# diastolic plateaus or falls) becomes the dominant BP pattern with age,
# and it's systolic elevation specifically that correlates most strongly
# with stroke risk in the age range stroke risk is mainly relevant for.
# Contrast with HYPERTENSION_FEATURES below, which needs BOTH — a blood
# pressure reading is diagnosed from the pair together (e.g. 140/90), so
# dropping either number there would be the arbitrary choice.
STROKE_FEATURES = [
    "age",
    "gender_male",           # 1 if male, 0 if female/other
    "hypertension_flag",     # 1 if patient has a hypertension history entry
    "heart_disease_flag",    # 1 if patient has a cardiac history entry
    "avg_glucose_level",
    "bmi",
    "systolic_bp",
    "heart_rate",
]

DIABETES_FEATURES = [
    "age",
    "bmi",
    "glucose",
    "diastolic_bp",
    "diabetes_pedigree",
]

HYPERTENSION_FEATURES = [
    "age",
    "bmi",
    "gender_male",
    "systolic_bp",
    "diastolic_bp",
    "heart_rate",
    "glucose",
]

# Plain string keys — the AI engine is intentionally decoupled from the
# SQLAlchemy/ORM layer (app.models) so it can be trained, tested, and run
# standalone (e.g. `python -m app.ai_engine.train`) without needing a
# database driver installed at all. `DiseaseType` (the ORM-facing enum)
# and these string keys are bridged in one place: app/services/prediction_service.py.
STROKE = "stroke"
DIABETES = "diabetes"
HYPERTENSION = "hypertension"

FEATURE_SETS: dict[str, list[str]] = {
    STROKE: STROKE_FEATURES,
    DIABETES: DIABETES_FEATURES,
    HYPERTENSION: HYPERTENSION_FEATURES,
}

# --- Condition-based vitals entry (see app/services/vitals_service.py) ---
#
# Maps each disease to the RAW VitalReading form fields its ML model needs
# — NOT the same list as FEATURE_SETS above, which is post-derivation ML
# feature names (e.g. "avg_glucose_level" and "glucose" both derive from
# the same blood_glucose_mg_dl column; age/bmi/gender/history flags come
# from PatientProfile, not a single vitals submission). This mapping is
# what drives "when the patient selects Diabetes, show only the vitals
# fields diabetes prediction actually needs" — a submission covering
# multiple selected conditions naturally captures each shared field (e.g.
# blood glucose) only once, since VitalReading is one flat row.
#
# Kept as plain string keys mirroring VitalReadingCreate's field names so
# this can be validated against a raw payload dict without importing the
# ORM/pydantic layer here (keeping this module framework-agnostic, per
# the module docstring above).
CONDITION_VITAL_FIELDS: dict[str, list[str]] = {
    DIABETES: [
        "blood_glucose_mg_dl",
        "blood_pressure_diastolic",
        "diabetes_pedigree_function",
    ],
    HYPERTENSION: ["blood_pressure_systolic", "blood_pressure_diastolic", "heart_rate_bpm", "blood_glucose_mg_dl"],
    STROKE: ["blood_glucose_mg_dl", "blood_pressure_systolic", "heart_rate_bpm"],
}

# Overall pipeline/architecture version. All three models now train on REAL
# patient data (diabetes -> Pima; stroke/hypertension -> Framingham), with
# dataset-specific framing caveats documented in the module docstring and in
# each artifact's "data_source" field (see train.py).
MODEL_VERSION = "v2.3.0-real-provenance"
