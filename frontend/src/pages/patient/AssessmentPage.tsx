import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ConditionFilterTabs, type ConditionFilter } from "@/components/ui/ConditionFilterTabs";
import { useAsyncData } from "@/hooks/useAsyncData";
import { patientApi } from "@/services/patientApi";
import { predictionApi } from "@/services/predictionApi";
import { vitalsApi } from "@/services/vitalsApi";
import { CONDITION_ML_VITAL_FIELDS } from "@/types/diseaseAssessment";
import type { DiseaseType, RiskLevel, RiskPrediction } from "@/types/prediction";
import type { VitalTrend } from "@/types/vitals";

const DISEASE_LABELS: Record<DiseaseType, string> = {
  diabetes: "Diabetes",
  hypertension: "Hypertension",
  stroke: "Stroke",
};

const RISK_TONE: Record<RiskLevel, "stable" | "warning" | "critical" | "info"> = {
  low: "stable",
  moderate: "info",
  high: "warning",
  critical: "critical",
};

const STATUS_BY_RISK: Record<RiskLevel, string> = {
  low: "Within expected range",
  moderate: "Monitor",
  high: "Requires attention",
  critical: "Requires urgent attention",
};

function RelevantTrends({ trends }: { trends: VitalTrend[] }) {
  const relevant = trends.filter((t) => t.is_consistently_abnormal || t.direction === "worsening");
  if (relevant.length === 0) return null;
  return (
    <div className="mt-3">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Historical Trend</p>
      <ul className="mt-1 space-y-1">
        {relevant.map((t) => (
          <li key={t.field} className="text-sm text-ink">
            {t.summary}
          </li>
        ))}
      </ul>
    </div>
  );
}

function AssessmentCard({ diseaseType, prediction, trends, onRefresh, isRefreshing, refreshError }: {
  diseaseType: DiseaseType;
  prediction: RiskPrediction | undefined;
  trends: VitalTrend[];
  onRefresh: () => void;
  isRefreshing: boolean;
  refreshError: string | null;
}) {
  // Scope trends to only the fields THIS disease's model actually uses —
  // without this, a worsening heart-rate trend (relevant to hypertension
  // and stroke, but not diabetes) would show up on every card regardless
  // of relevance. Mirrors the same rule the vitals-entry workflow already
  // follows: don't mix unrelated condition history.
  const relevantFields = new Set(CONDITION_ML_VITAL_FIELDS[diseaseType]);
  const scopedTrends = trends.filter((t) => relevantFields.has(t.field));

  if (!prediction) {
    return (
      <Card>
        <div className="flex items-center justify-between">
          <h2 className="font-display text-sm font-bold text-ink">{DISEASE_LABELS[diseaseType]}</h2>
          <button
            type="button"
            onClick={onRefresh}
            disabled={isRefreshing}
            className="rounded-lg border border-surface-border px-2 py-1 text-xs hover:border-teal-500 disabled:opacity-60"
          >
            {isRefreshing ? "Generating…" : "Generate"}
          </button>
        </div>
        <p className="mt-3 text-sm text-ink-soft">
          No assessment yet. Log a vitals reading, then generate one here.
        </p>
        {refreshError && <p className="mt-2 text-xs text-status-critical">{refreshError}</p>}
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between">
        <h2 className="font-display text-sm font-bold text-ink">{DISEASE_LABELS[diseaseType]}</h2>
        <Badge tone={RISK_TONE[prediction.risk_level]}>{prediction.risk_level} risk</Badge>
      </div>

      <p className="mt-3 text-sm text-ink">
        The ML model estimates a <span className="font-medium">{prediction.risk_level}</span> risk associated
        with {DISEASE_LABELS[diseaseType].toLowerCase()}
        {" "}
        <span className="readout text-ink-soft">(score {(prediction.risk_score * 100).toFixed(0)}%)</span>.
      </p>

      {prediction.reasons.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Important Factors</p>
          <ul className="mt-1 list-inside list-disc space-y-1">
            {prediction.reasons.map((reason) => (
              <li key={reason} className="text-sm text-ink">
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      <RelevantTrends trends={scopedTrends} />

      {prediction.recommendations.length > 0 && (
        <div className="mt-3 rounded-lg bg-teal-50 p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-teal-700">AI Recommendation</p>
          <ul className="mt-1 list-inside list-disc space-y-1">
            {prediction.recommendations.map((rec) => (
              <li key={rec} className="text-sm text-ink">
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-surface-border pt-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Status</p>
          <p className="text-sm font-medium text-ink">{STATUS_BY_RISK[prediction.risk_level]}</p>
        </div>
        <p className="text-xs text-ink-soft">
          {new Date(prediction.predicted_at).toLocaleDateString()} · model {prediction.model_version}
        </p>
      </div>

      <button
        type="button"
        onClick={onRefresh}
        disabled={isRefreshing}
        className="mt-3 text-xs text-teal-600 hover:underline disabled:opacity-60"
      >
        {isRefreshing ? "Refreshing…" : "Refresh assessment with latest vitals"}
      </button>
      {refreshError && <p className="mt-2 text-xs text-status-critical">{refreshError}</p>}
    </Card>
  );
}

/**
 * The patient-facing "AI Health Assessment" — one card per disease,
 * following the Condition / Current Risk / Prediction / Historical Trend
 * / Important Factors / Status shape from the project spec. Pulls the
 * latest RiskPrediction per disease (ML output — score, level, reasons)
 * plus the Phase 2 trend analysis for the historical-trend line; this
 * page does not calculate anything itself, only presents what the model
 * and trend classifier already produced.
 */
export function AssessmentPage() {
  const { data: profile, error: profileError } = useAsyncData(() => patientApi.getMe(), []);
  const { data: predictions, isLoading, error, refetch } = useAsyncData(
    () => (profile ? predictionApi.list(profile.id) : Promise.resolve([])),
    [profile?.id]
  );
  const { data: trendsResponse } = useAsyncData(
    () => (profile ? vitalsApi.trends(profile.id, 90) : Promise.resolve(null)),
    [profile?.id]
  );
  const trends = trendsResponse?.trends ?? [];

  const [refreshingDisease, setRefreshingDisease] = useState<DiseaseType | null>(null);
  const [refreshErrors, setRefreshErrors] = useState<Partial<Record<DiseaseType, string>>>({});
  const [filter, setFilter] = useState<ConditionFilter>("all");

  async function handleRefresh(diseaseType: DiseaseType) {
    if (!profile) return;
    setRefreshingDisease(diseaseType);
    setRefreshErrors((prev) => ({ ...prev, [diseaseType]: undefined }));
    try {
      await predictionApi.generate(profile.id, diseaseType);
      refetch();
    } catch (err) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Couldn't generate an assessment. Make sure you have vitals and profile data logged.";
      setRefreshErrors((prev) => ({ ...prev, [diseaseType]: detail }));
    } finally {
      setRefreshingDisease(null);
    }
  }

  const latestByDisease: Partial<Record<DiseaseType, RiskPrediction>> = {};
  for (const p of predictions ?? []) {
    if (!latestByDisease[p.disease_type]) latestByDisease[p.disease_type] = p;
  }

  const diseasesToShow = (Object.keys(DISEASE_LABELS) as DiseaseType[]).filter(
    (d) => filter === "all" || filter === d
  );

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-xl font-bold text-ink">AI Health Assessment</h1>
          <p className="mt-1 text-sm text-ink-soft">
            Risk estimates from the trained ML models, explained in plain language. Not a diagnosis.
          </p>
        </div>
        <ConditionFilterTabs value={filter} onChange={setFilter} />
      </div>

      {error && <p className="mt-4 text-sm text-status-critical">Couldn't load your assessment.</p>}
      {profileError && (
        <p className="mt-4 rounded-lg bg-status-critical/10 px-3 py-2 text-sm text-status-critical">
          Couldn't load your profile. Try refreshing the page.
        </p>
      )}

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        {isLoading ? (
          <p className="text-sm text-ink-soft">Loading…</p>
        ) : (
          diseasesToShow.map((diseaseType) => (
            <AssessmentCard
              key={diseaseType}
              diseaseType={diseaseType}
              prediction={latestByDisease[diseaseType]}
              trends={trends}
              onRefresh={() => handleRefresh(diseaseType)}
              isRefreshing={refreshingDisease === diseaseType}
              refreshError={refreshErrors[diseaseType] ?? null}
            />
          ))
        )}
      </div>
    </div>
  );
}
