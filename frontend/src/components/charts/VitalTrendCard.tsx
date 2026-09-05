import { Badge } from "@/components/ui/Badge";
import type { ForecastPosition, TrendDirection, VitalTrend } from "@/types/vitals";

const DIRECTION_TONE: Record<TrendDirection, "stable" | "warning" | "critical" | "info" | "neutral"> = {
  improving: "stable",
  decreasing: "info",
  stable: "info",
  fluctuating: "warning",
  worsening: "critical",
  increasing: "warning",
  insufficient_data: "neutral",
};

const DIRECTION_LABEL: Record<TrendDirection, string> = {
  improving: "Improving",
  worsening: "Worsening",
  stable: "Stable",
  fluctuating: "Fluctuating",
  increasing: "Increasing",
  decreasing: "Decreasing",
  insufficient_data: "Not enough data",
};

// Only these forecast positions are worth a visible callout — the other
// two (no_near_term_crossing, low_confidence) are non-events by design
// (see forecast_trend()'s confidence gating) and would just be noise here.
const FORECAST_TONE: Partial<Record<ForecastPosition, "critical" | "warning" | "stable">> = {
  approaching_threshold: "warning",
  drifting_further: "critical",
  returning_to_range: "stable",
};

/**
 * One vital field's trend — direction badge + the rule-based narrative
 * text from app.services.trend_analysis (see that module's docstring for
 * why this is template-generated rather than LLM-generated: it's a
 * straightforward statistical classification, not something that
 * benefits from a language model's judgment) — plus, when confidence
 * allows, a forward-looking forecast (projected days until a threshold
 * crossing, with its own R² confidence shown alongside it rather than
 * hidden behind the projection).
 */
export function VitalTrendCard({ trend }: { trend: VitalTrend }) {
  const forecastTone = trend.forecast ? FORECAST_TONE[trend.forecast.position] : undefined;

  return (
    <div className="rounded-lg border border-surface-border p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-display text-sm font-bold text-ink">{trend.label}</h3>
        <div className="flex items-center gap-2">
          {trend.is_consistently_abnormal && <Badge tone="critical">Persistently abnormal</Badge>}
          <Badge tone={DIRECTION_TONE[trend.direction]}>{DIRECTION_LABEL[trend.direction]}</Badge>
        </div>
      </div>

      {trend.direction !== "insufficient_data" && (
        <p className="mt-2 text-xs text-ink-soft">
          Recent average: <span className="readout font-medium text-ink">{trend.recent_average}{trend.unit}</span>
          {" · "}
          Earlier average: <span className="readout font-medium text-ink">{trend.earliest_average}{trend.unit}</span>
          {" · "}
          {trend.sample_size} readings
        </p>
      )}

      <p className="mt-2 text-sm text-ink">{trend.summary}</p>

      {forecastTone && (
        <div className={`mt-3 rounded-lg border-l-2 pl-3 ${
          forecastTone === "critical" ? "border-status-critical" : forecastTone === "warning" ? "border-status-warning" : "border-status-stable"
        }`}>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-ink-soft">Forecast</span>
            {trend.forecast?.r_squared != null && (
              <span className="readout text-xs text-ink-soft">{(trend.forecast.r_squared * 100).toFixed(0)}% confidence</span>
            )}
          </div>
          <p className="mt-1 text-sm text-ink">{trend.forecast?.summary}</p>
        </div>
      )}
    </div>
  );
}
