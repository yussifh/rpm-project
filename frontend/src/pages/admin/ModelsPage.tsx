import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useAsyncData } from "@/hooks/useAsyncData";
import { modelInfoApi } from "@/services/modelInfoApi";
import type { DiseaseType } from "@/types/prediction";

const DISEASES: { type: DiseaseType; label: string }[] = [
  { type: "diabetes", label: "Diabetes" },
  { type: "hypertension", label: "Hypertension" },
  { type: "stroke", label: "Stroke" },
];

const METRIC_LABELS: Record<string, string> = {
  accuracy: "Accuracy",
  precision: "Precision",
  recall: "Recall",
  roc_auc: "ROC-AUC",
  brier_score: "Brier score",
};

const MODEL_TYPE_LABELS: Record<string, string> = {
  logistic_regression: "Logistic Regression",
  random_forest: "Random Forest",
  gradient_boosting: "Gradient Boosting",
};

function ModelCard({ diseaseType, label }: { diseaseType: DiseaseType; label: string }) {
  const { data: info, isLoading, error } = useAsyncData(() => modelInfoApi.get(diseaseType), [diseaseType]);

  if (isLoading) {
    return (
      <Card>
        <h2 className="font-display text-sm font-bold text-ink">{label}</h2>
        <p className="mt-4 text-sm text-ink-soft">Loading…</p>
      </Card>
    );
  }

  if (error || !info) {
    return (
      <Card>
        <h2 className="font-display text-sm font-bold text-ink">{label}</h2>
        <p className="mt-4 text-sm text-status-critical">Model not available.</p>
      </Card>
    );
  }

  const topFeatures = Object.entries(info.feature_importances)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);

  const isSynthetic = info.data_source.toLowerCase().includes("synthetic");
  const isAugmented = info.data_source.toLowerCase().includes("augmented");
  const badgeLabel = isSynthetic ? "Synthetic data" : isAugmented ? "Real + augmented data" : "Real data";
  const selectedModel = info.metrics.model_selected;
  const comparison = info.metrics.model_comparison_cv_roc_auc;

  return (
    <Card>
      <div className="flex items-center justify-between">
        <h2 className="font-display text-sm font-bold text-ink">{label}</h2>
        <Badge tone={isSynthetic ? "warning" : isAugmented ? "info" : "stable"}>{badgeLabel}</Badge>
      </div>
      <p className="mt-1 text-xs text-ink-soft">
        Version {info.model_version} · trained on {info.metrics.train_size} records, tested on{" "}
        {info.metrics.test_size}
      </p>
      <p className="mt-0.5 text-xs text-ink-soft">
        Source: <span className="readout">{info.data_source}</span>
      </p>
      {selectedModel && (
        <p className="mt-1 text-xs text-ink-soft">
          Algorithm: <span className="font-medium text-ink">{MODEL_TYPE_LABELS[selectedModel] ?? selectedModel}</span>
          {" "}(selected by cross-validated comparison)
        </p>
      )}

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {Object.entries(METRIC_LABELS).map(([key, metricLabel]) => {
          const value = info.metrics[key as keyof typeof info.metrics];
          if (typeof value !== "number") return null;
          return (
            <div key={key}>
              <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">{metricLabel}</p>
              <p className="readout mt-0.5 text-lg font-medium text-teal-600">{(value * 100).toFixed(1)}%</p>
            </div>
          );
        })}
      </div>

      <div className="mt-4">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Top contributing factors</p>
        <ul className="mt-2 space-y-1">
          {topFeatures.map(([feature, importance]) => (
            <li key={feature} className="flex items-center justify-between text-sm">
              <span className="text-ink">{feature.replace(/_/g, " ")}</span>
              <span className="readout text-ink-soft">{(importance * 100).toFixed(1)}%</span>
            </li>
          ))}
        </ul>
      </div>

      {comparison && (
        <div className="mt-4">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">
            Algorithm comparison (5-fold CV ROC-AUC)
          </p>
          <ul className="mt-2 space-y-1">
            {Object.entries(comparison)
              .sort(([, a], [, b]) => b - a)
              .map(([name, score]) => (
                <li key={name} className="flex items-center justify-between text-sm">
                  <span className={name === selectedModel ? "font-medium text-ink" : "text-ink-soft"}>
                    {MODEL_TYPE_LABELS[name] ?? name}
                    {name === selectedModel && " ✓"}
                  </span>
                  <span className="readout text-ink-soft">{(score * 100).toFixed(1)}%</span>
                </li>
              ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

/**
 * Admin's view into the ML side of the system — model performance,
 * versions, data provenance, and feature importances for each of the
 * three trained models (diabetes, hypertension, stroke). Read-only:
 * training itself happens offline via `python -m app.ai_engine.train`
 * (see MODEL_CARD.md) — deliberately not a "click to retrain" button,
 * per the spec requirement not to retrain on every vitals submission.
 */
export function ModelsPage() {
  return (
    <div>
      <h1 className="font-display text-2xl font-bold text-ink">AI Models</h1>
      <p className="mt-1 text-sm text-ink-soft">
        Performance, versioning, and transparency for the trained risk-prediction models.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        {DISEASES.map((d) => (
          <ModelCard key={d.type} diseaseType={d.type} label={d.label} />
        ))}
      </div>
    </div>
  );
}
