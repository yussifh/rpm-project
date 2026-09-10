export type DiseaseType = "stroke" | "diabetes" | "hypertension";

/** Which VitalReading fields each condition's trained ML model actually
 * needs — must mirror app/ai_engine/feature_schema.py's
 * CONDITION_VITAL_FIELDS on the backend exactly. This is narrower and
 * more literal than VITALS_BY_DISEASE below: this one drives which
 * fields the condition-based vitals entry form REQUIRES/shows for a
 * risk prediction to run, not just which fields are emphasized. */
export const CONDITION_ML_VITAL_FIELDS: Record<DiseaseType, string[]> = {
  // Every condition requires the complete core vitals (BP, heart rate,
  // glucose, BMI, age) plus any condition-specific extra measurement —
  // all three disease models take BMI + age, and the vitals form shows the
  // full set for every condition selected.
  diabetes: [
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
    "heart_rate_bpm",
    "blood_glucose_mg_dl",
    "bmi",
    "age_years",
    "diabetes_pedigree_function",
  ],
  hypertension: [
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
    "heart_rate_bpm",
    "blood_glucose_mg_dl",
    "bmi",
    "age_years",
  ],
  stroke: [
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
    "heart_rate_bpm",
    "blood_glucose_mg_dl",
    "bmi",
    "age_years",
  ],
};

/** Which vitals fields matter for each condition — per the RPM workflow
 * spec's "shared vital signs" table. Drives which input fields the
 * patient's vitals-logging form shows front-and-center. All fields
 * remain loggable regardless (a patient can still note anything unusual),
 * this just changes what's emphasized. */
export const VITALS_BY_DISEASE: Record<
  DiseaseType,
  { key: string; label: string; unit: string }[]
> = {
  stroke: [
    { key: "blood_pressure", label: "Blood Pressure", unit: "mmHg" },
    { key: "heart_rate_bpm", label: "Heart Rate", unit: "bpm" },
    { key: "spo2_percent", label: "SpO2", unit: "%" },
    { key: "temperature_celsius", label: "Temperature", unit: "°C" },
    { key: "respiratory_rate", label: "Respiratory Rate", unit: "breaths/min" },
    { key: "weight_kg", label: "Weight", unit: "kg" },
  ],
  diabetes: [
    { key: "blood_glucose_mg_dl", label: "Blood Glucose", unit: "mg/dL" },
    { key: "blood_pressure", label: "Blood Pressure", unit: "mmHg" },
    { key: "heart_rate_bpm", label: "Heart Rate", unit: "bpm" },
    { key: "temperature_celsius", label: "Temperature", unit: "°C" },
    { key: "weight_kg", label: "Weight", unit: "kg" },
  ],
  hypertension: [
    { key: "blood_pressure", label: "Blood Pressure", unit: "mmHg" },
    { key: "heart_rate_bpm", label: "Heart Rate", unit: "bpm" },
    { key: "respiratory_rate", label: "Respiratory Rate", unit: "breaths/min" },
    { key: "spo2_percent", label: "SpO2", unit: "%" },
    { key: "weight_kg", label: "Weight", unit: "kg" },
  ],
};

export interface DiseaseAssessment {
  id: string;
  patient_id: string;
  disease_type: DiseaseType;
  symptoms: Record<string, boolean | string>;
  created_at: string;
}

export interface DiseaseAssessmentCreatePayload {
  disease_type: DiseaseType;
  symptoms: Record<string, boolean | string>;
}

/** Disease-specific symptom checklists, per the RPM workflow spec —
 * only the relevant checklist is shown once a patient's primary
 * condition is known. */
export const SYMPTOM_CHECKLISTS: Record<DiseaseType, { key: string; label: string }[]> = {
  stroke: [
    { key: "face_drooping", label: "Face drooping" },
    { key: "arm_weakness", label: "Arm weakness" },
    { key: "leg_weakness", label: "Leg weakness" },
    { key: "speech_difficulty", label: "Speech difficulty" },
    { key: "vision_changes", label: "Vision changes" },
    { key: "difficulty_swallowing", label: "Difficulty swallowing" },
    { key: "balance_problems", label: "Balance problems" },
    { key: "fall_occurred", label: "Fall occurred" },
  ],
  diabetes: [
    { key: "insulin_taken", label: "Insulin taken today" },
    { key: "medication_taken", label: "Medication taken today" },
    { key: "foot_ulcer", label: "Foot ulcer present" },
    { key: "tingling_or_numbness", label: "Tingling or numbness" },
    { key: "blurred_vision", label: "Blurred vision" },
    { key: "frequent_urination", label: "Frequent urination" },
    { key: "excessive_thirst", label: "Excessive thirst" },
    { key: "dizziness", label: "Dizziness" },
  ],
  hypertension: [
    { key: "severe_headache", label: "Severe headache" },
    { key: "chest_pain", label: "Chest pain" },
    { key: "shortness_of_breath", label: "Shortness of breath" },
    { key: "blurred_vision", label: "Blurred vision" },
    { key: "dizziness", label: "Dizziness" },
    { key: "medication_taken", label: "Medication taken today" },
  ],
};
