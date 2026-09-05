import type { DiseaseType, RiskPrediction } from "@/types/prediction";

export type VitalSource = "manual" | "device" | "clinic";

export interface VitalReading {
  id: string;
  patient_id: string;
  recorded_at: string;
  source: VitalSource;
  blood_pressure_systolic: number | null;
  blood_pressure_diastolic: number | null;
  heart_rate_bpm: number | null;
  blood_glucose_mg_dl: number | null;
  spo2_percent: number | null;
  temperature_celsius: number | null;
  respiratory_rate: number | null;
  weight_kg: number | null;
  notes: string | null;
  created_at: string;
}

export interface VitalReadingCreatePayload {
  recorded_at?: string;
  source?: VitalSource;
  /** Which condition(s) this submission should be assessed for — drives
   * which ML model(s) run. See app/ai_engine/feature_schema.py
   * (CONDITION_VITAL_FIELDS) on the backend for the source of truth this
   * must stay in sync with. */
  conditions?: DiseaseType[];
  blood_pressure_systolic?: number;
  blood_pressure_diastolic?: number;
  heart_rate_bpm?: number;
  blood_glucose_mg_dl?: number;
  spo2_percent?: number;
  temperature_celsius?: number;
  respiratory_rate?: number;
  weight_kg?: number;
  notes?: string;
}

export interface SkippedPrediction {
  disease_type: DiseaseType;
  reason: string;
}

/** Response for POST /vitals — the saved reading plus a separate
 * RiskPrediction for each condition selected on the submission (never a
 * combined multi-disease result), and any selected condition that
 * couldn't be assessed this time (e.g. missing BMI). */
export interface VitalSubmissionResult {
  vital: VitalReading;
  predictions: RiskPrediction[];
  skipped: SkippedPrediction[];
}

export type TrendDirection =
  | "improving"
  | "worsening"
  | "stable"
  | "fluctuating"
  | "increasing"
  | "decreasing"
  | "insufficient_data";

export interface TrendDataPoint {
  recorded_at: string;
  value: number;
}

export type ForecastPosition =
  | "approaching_threshold"
  | "returning_to_range"
  | "drifting_further"
  | "no_near_term_crossing"
  | "low_confidence";

/** Predictive forecast — projects whether/when a vital may cross a
 * clinical threshold if its current trajectory continues. See
 * app/services/trend_analysis.py forecast_trend() for the confidence
 * gating: this fails safe (position="low_confidence") rather than ever
 * guessing when there isn't enough data or a clear enough trend. */
export interface VitalForecast {
  position: ForecastPosition;
  days_projected: number | null;
  target_value: number | null;
  r_squared: number | null;
  summary: string;
}

export interface VitalTrend {
  field: string;
  label: string;
  unit: string;
  direction: TrendDirection;
  is_consistently_abnormal: boolean;
  sample_size: number;
  earliest_average: number | null;
  recent_average: number | null;
  summary: string;
  data_points: TrendDataPoint[];
  forecast: VitalForecast | null;
}

export interface VitalTrendsResponse {
  period_days: number;
  trends: VitalTrend[];
}
