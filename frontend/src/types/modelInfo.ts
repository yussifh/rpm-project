import type { DiseaseType } from "./prediction";

export interface ModelMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  roc_auc: number;
  brier_score: number;
  train_size: number;
  test_size: number;
  positive_rate_train: number;
  threshold_metrics?: Record<string, { precision: number; recall: number }>;
  /** Which candidate algorithm was selected (logistic_regression |
   * random_forest | gradient_boosting) after cross-validated comparison —
   * see app/ai_engine/train.py _compare_and_select_model(). */
  model_selected?: string;
  /** Mean 5-fold CV ROC-AUC for every candidate that was compared, so the
   * selection is auditable rather than just asserted. */
  model_comparison_cv_roc_auc?: Record<string, number>;
}

export interface ModelInfo {
  disease_type: DiseaseType;
  model_version: string;
  data_source: string;
  feature_names: string[];
  metrics: ModelMetrics;
  feature_importances: Record<string, number>;
}
