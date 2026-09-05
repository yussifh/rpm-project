export type DiseaseType = "stroke" | "diabetes" | "hypertension";
export type RiskLevel = "low" | "moderate" | "high" | "critical";

export interface RiskPrediction {
  id: string;
  patient_id: string;
  source_vital_id: string | null;
  disease_type: DiseaseType;
  risk_score: number;
  risk_level: RiskLevel;
  model_version: string;
  data_source: string;
  input_features: Record<string, number>;
  reasons: string[];
  recommendations: string[];
  predicted_at: string;
}
