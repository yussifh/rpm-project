/** Human-readable labels for the raw feature keys the models train on —
 * keeps the chart readable without leaking snake_case internals into the
 * clinician-facing UI. */
const FEATURE_LABELS: Record<string, string> = {
  age: "Age",
  bmi: "BMI",
  glucose: "Blood Glucose",
  avg_glucose_level: "Avg. Blood Glucose",
  diastolic_bp: "Diastolic BP",
  systolic_bp: "Systolic BP",
  heart_rate: "Heart Rate",
  gender_male: "Gender (Male)",
  hypertension_flag: "Hypertension History",
  heart_disease_flag: "Heart Disease History",
};

function labelFor(key: string): string {
  return FEATURE_LABELS[key] ?? key;
}

/** Pure transform, split out from the chart so it can be unit tested
 * without needing to render Recharts' SVG output (which requires real
 * layout dimensions jsdom doesn't provide). Kept in its own module (not
 * re-exported from the component) so fast-refresh lint stays happy. */
export function toChartData(importances: Record<string, number>) {
  return Object.entries(importances)
    .map(([key, value]) => ({ feature: labelFor(key), value: Math.round(value * 1000) / 10 }))
    .sort((a, b) => b.value - a.value);
}