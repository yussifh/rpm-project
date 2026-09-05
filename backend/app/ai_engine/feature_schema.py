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
  diastolic_bp) were chosen to match exactly what that dataset provides,
  which is why this list differs slightly from the other two diseases.
- STROKE and HYPERTENSION: still trained on SYNTHETICALLY GENERATED data
  (see data_synthesis.py). Real public datasets exist (e.g. the Kaggle
  "Stroke Prediction Dataset") but record risk factors as binary flags
  (hypertension: yes/no, heart_disease: yes/no) rather than the continuous
  vitals (systolic_bp, heart_rate) this RPM system actually collects and
  needs for day-to-day monitoring, so a direct swap isn't possible without
  either redesigning what the app collects or losing signal. The synthetic
  generators for these two are informed by published prevalence rates
  (e.g. ~4.9% stroke rate, ~9% hypertension comorbidity, ~5% heart disease
  comorbidity in the Kaggle stroke cohort) rather than arbitrary numbers,
  but they are still simulated, not real patient outcomes.

None of these three models are clinically validated. Before any real-world
clinical use, the stroke and hypertension models must be retrained on a
proper labeled clinical dataset (e.g. a licensed EHR extract) and ALL
THREE models — including the diabetes model despite using real data —
must be reviewed/validated by a qualified clinician and biostatistician,
since 768 records from one population (Pima Indian women, Arizona, 1988-ish
NIDDK study) does not generalize to a general patient population either.
This is a student/portfolio project — treat the shipped models as a
working demonstration of the ARCHITECTURE and of good MLOps practice
(real data where available, documented provenance, calibration), not as
medical-grade predictors ready for patient-facing clinical decisions.
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
    DIABETES: ["blood_glucose_mg_dl", "blood_pressure_diastolic"],
    HYPERTENSION: ["blood_pressure_systolic", "blood_pressure_diastolic", "heart_rate_bpm", "blood_glucose_mg_dl"],
    STROKE: ["blood_glucose_mg_dl", "blood_pressure_systolic", "heart_rate_bpm"],
}

# Overall pipeline/architecture version. Per-model data provenance is
# recorded separately in each artifact's "data_source" field (see train.py)
# since diabetes now trains on real data while stroke/hypertension remain
# synthetic — a single flat version string can't honestly describe both.
MODEL_VERSION = "v2.0.0-mixed-provenance"
