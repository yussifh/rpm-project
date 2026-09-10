import { useMemo } from "react";
import { Activity, CalendarCheck2, Flame, Minus, TrendingDown, TrendingUp, AlertCircle } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useAsyncData } from "@/hooks/useAsyncData";
import { patientApi } from "@/services/patientApi";
import { vitalsApi } from "@/services/vitalsApi";
import type { TrendDirection, VitalTrend } from "@/types/vitals";

/**
 * "My Progress" — the patient-facing picture of how their measurements are
 * changing over time. Pure presentation over two existing endpoints:
 *   GET /vitals/trends  (classified direction + averages + sparkline points)
 *   GET /vitals         (raw readings — adds BMI / diabetes pedigree trends,
 *                        which the trend service intentionally doesn't judge,
 *                        plus logging-consistency stats)
 * No new backend work; backend trend_analysis is the rule-based source of
 * truth for what "improving / worsening / stable" means.
 */

const DIRECTION_TONE: Record<TrendDirection, "stable" | "warning" | "critical" | "info" | "neutral"> = {
  improving: "stable",
  worsening: "critical",
  stable: "neutral",
  fluctuating: "warning",
  increasing: "neutral",
  decreasing: "neutral",
  insufficient_data: "neutral",
};

const DIRECTION_LABEL: Record<TrendDirection, string> = {
  improving: "Improving",
  worsening: "Worsening",
  stable: "Stable",
  fluctuating: "Fluctuating",
  increasing: "Increasing",
  decreasing: "Decreasing",
  insufficient_data: "",
};

function DirectionBadge({ direction }: { direction: TrendDirection }) {
  if (direction === "insufficient_data") return null;
  return (
    <Badge tone={DIRECTION_TONE[direction]}>{DIRECTION_LABEL[direction]}</Badge>
  );
}

/** Tiny dependency-free sparkline drawn as an inline SVG with a
 * normalized polyline — trend.shapes are too irregular for a real chart lib
 * and a progress card just needs the shape, not an axis system. */
function Sparkline({ points, color }: { points: { value: number }[]; color: string }) {
  const w = 220;
  const h = 56;
  const vals = points.map((p) => p.value);
  if (vals.length < 2) return null;
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const span = max - min || 1;
  const stepX = w / (vals.length - 1);
  const pts = vals.map((v, i) => `${(i * stepX).toFixed(1)},${(h - 4 - ((v - min) / span) * (h - 8)).toFixed(1)}`).join(" ");
  const fillPts = `0,${h} ${pts} ${w},${h}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-14 w-full" preserveAspectRatio="xMidYMid meet" aria-hidden>
      <polygon points={fillPts} fill={color} opacity="0.12" />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

interface MetricCard {
  key: string;
  label: string;
  unit: string;
  direction: TrendDirection;
  earliest: number | null;
  recent: number | null;
  sampleSize: number;
  summary: string;
  spark: { value: number }[];
  forecastSummary?: string | null;
}

const CLINICAL_FIELDS = new Set([
  "blood_pressure_systolic",
  "blood_pressure_diastolic",
  "heart_rate_bpm",
  "blood_glucose_mg_dl",
  "spo2_percent",
]);

function pctChange(earliest: number | null, recent: number | null): number | null {
  if (earliest == null || recent == null || earliest === 0) return null;
  return ((recent - earliest) / earliest) * 100;
}

function formatDelta(recent: number | null, earliest: number | null, unit: string): string {
  if (recent == null || earliest == null) return "—";
  const d = recent - earliest;
  const sign = d > 0 ? "+" : d < 0 ? "−" : "";
  return `${sign}${Math.abs(d).toFixed(1)} ${unit}`;
}

/** Build a pseudo-trend for fields the trend service doesn't classify
 * (BMI, diabetes pedigree): same earlier-vs-recent average split, reported
 * neutrally (no improving/worsening judgment). */
function clientTrend(readings: { recorded_at: string }[], field: "bmi" | "diabetes_pedigree_function") {
  const pts = readings
    .filter((r) => (r as Record<string, unknown>)[field] != null)
    .map((r) => ({ recorded_at: r.recorded_at, value: (r as Record<string, unknown>)[field] as number }))
    .sort((a, b) => a.recorded_at.localeCompare(b.recorded_at));
  if (pts.length < 2) {
    return {
      direction: "insufficient_data" as TrendDirection,
      earliest: null,
      recent: null,
      sampleSize: pts.length,
      spark: pts,
      summary: pts.length === 0 ? "No readings logged yet." : "Log more readings to see a trend here.",
    };
  }
  const mid = Math.floor(pts.length / 2);
  const early = pts.slice(0, mid);
  const recent = pts.slice(mid);
  const avg = (arr: typeof pts) => arr.reduce((s, p) => s + p.value, 0) / arr.length;
  const e = avg(early);
  const r = avg(recent);
  const direction: TrendDirection =
    Math.abs(r - e) < 0.1 * Math.abs(e || 1) ? "stable" : r > e ? "increasing" : "decreasing";
  return {
    direction,
    earliest: e,
    recent: r,
    sampleSize: pts.length,
    spark: pts,
    summary: `${field === "bmi" ? "BMI" : "Diabetes pedigree"} averaged ${e.toFixed(1)} across your first ${
      early.length
    } readings and ${r.toFixed(1)} across the last ${recent.length}.`,
  };
}

export function ProgressPage() {
  const { data: profile } = useAsyncData(() => patientApi.getMe(), []);
  const { data: trendsData } = useAsyncData(
    () => (profile ? vitalsApi.trends(profile.id, 90) : Promise.resolve(null)),
    [profile?.id]
  );
  const { data: readings, isLoading } = useAsyncData(
    () => (profile ? vitalsApi.list(profile.id) : Promise.resolve([])),
    [profile?.id]
  );

  const byField = useMemo(() => new Map((trendsData?.trends ?? []).map((t) => [t.field, t])), [trendsData]);

  const metrics = useMemo<MetricCard[]>(() => {
    const list: MetricCard[] = [];
    const pushTrend = (key: string) => {
      const t = byField.get(key) as VitalTrend | undefined;
      if (!t) return;
      list.push({
        key,
        label: t.label,
        unit: t.unit,
        direction: t.direction,
        earliest: t.earliest_average,
        recent: t.recent_average,
        sampleSize: t.sample_size,
        summary: t.summary,
        spark: t.data_points,
        forecastSummary: t.forecast?.summary ?? null,
      });
    };
    for (const k of [
      "blood_glucose_mg_dl",
      "blood_pressure_systolic",
      "blood_pressure_diastolic",
      "heart_rate_bpm",
      "spo2_percent",
      "weight_kg",
    ]) {
      pushTrend(k);
    }
    // Client-computed, neutral-framing extras
    const bmi = clientTrend(readings ?? [], "bmi");
    list.push({ key: "bmi", label: "BMI", unit: "", direction: bmi.direction, earliest: bmi.earliest, recent: bmi.recent, sampleSize: bmi.sampleSize, summary: bmi.summary, spark: bmi.spark });
    const ped = clientTrend(readings ?? [], "diabetes_pedigree_function");
    list.push({ key: "diabetes_pedigree_function", label: "Diabetes pedigree", unit: "", direction: ped.direction, earliest: ped.earliest, recent: ped.recent, sampleSize: ped.sampleSize, summary: ped.summary, spark: ped.spark });
    return list;
  }, [byField, readings]);

  const stats = useMemo(() => {
    const rows = readings ?? [];
    const dates = [...new Set(rows.map((r) => r.recorded_at.slice(0, 10)))].sort();
    const now = new Date();
    let run = 0;
    let longest = 0;
    let prev: Date | null = null;
    for (const d of dates) {
      const date = new Date(d + "T00:00:00Z");
      if (prev && (date.getTime() - prev.getTime()) / 86400000 === 1) run += 1;
      else run = 1;
      longest = Math.max(longest, run);
      prev = date;
    }
    const last7 = dates.filter((d) => {
      const t = new Date(d + "T00:00:00Z");
      return now.getTime() - t.getTime() <= 7 * 86400000;
    }).length;
    const improving = metrics.filter((m) => m.direction === "improving").length;
    const worsening = metrics.filter((m) => m.direction === "worsening").length;
    const abnormal = metrics.filter((m) => CLINICAL_FIELDS.has(m.key) && byField.get(m.key)?.is_consistently_abnormal).length;
    return { total: rows.length, last7, streak: run, longest, improving, worsening, abnormal };
  }, [readings, metrics, byField]);

  const headline = useMemo(() => {
    if (!metrics.length) return "Log your first vitals and your progress picture will build itself here.";
    if (isLoading) return "Loading your progress…";
    if (stats.worsening > stats.improving)
      return `${stats.worsening} of your tracked measurements are moving away from their normal ranges, and ${stats.improving} are improving. Keep monitoring — small daily habits really do show up in the numbers.`;
    if (stats.improving > 0)
      return `Good work — ${stats.improving} of your tracked measurements are trending toward their normal ranges. Keep it up!`;
    return "Your measurements are holding steady. Consistency is what keeps them that way.";
  }, [metrics.length, isLoading, stats]);

  return (
    <div>
      <div>
        <h1 className="font-display text-2xl font-bold text-ink">My Progress</h1>
        <p className="mt-1 text-sm text-ink-soft">
          How your measurements are changing over the last {trendsData?.period_days ?? 90} days — and how consistently
          you're logging them.
        </p>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Logs total</p>
          <p className="readout mt-1 text-3xl font-medium text-teal-600">{stats.total}</p>
        </Card>
        <Card>
          <div className="flex items-center gap-2">
            <CalendarCheck2 size={16} className="text-ink-soft" />
            <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Last 7 days</p>
          </div>
          <p className="readout mt-1 text-3xl font-medium text-teal-600">{stats.last7}</p>
          <p className="text-xs text-ink-soft">days with a reading</p>
        </Card>
        <Card>
          <div className="flex items-center gap-2">
            <Flame size={16} className="text-ink-soft" />
            <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Longest streak</p>
          </div>
          <p className="readout mt-1 text-3xl font-medium text-teal-600">{stats.longest}</p>
          <p className="text-xs text-ink-soft">consecutive days</p>
        </Card>
        <Card>
          <div className="flex items-center gap-2">
            <AlertCircle size={16} className="text-ink-soft" />
            <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Consistently abnormal</p>
          </div>
          <p className="readout mt-1 text-3xl font-medium text-teal-600">{stats.abnormal}</p>
          <p className="text-xs text-ink-soft">measurements out of range</p>
        </Card>
      </div>

      <Card className="mt-6">
        <div className="flex items-center gap-3">
          <Activity size={18} className="text-teal-600" />
          <p className="text-sm font-medium text-ink">{headline}</p>
        </div>
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map((m) => {
          const pct = pctChange(m.earliest, m.recent);
          const dir = m.direction;
          const color =
            dir === "improving"
              ? "#3E8E5B"
              : dir === "worsening"
                ? "#C0463C"
                : dir === "fluctuating"
                  ? "#E2A63B"
                  : "#9AA6AD";
          return (
            <Card key={m.key}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-ink">{m.label}</p>
                  <p className="text-xs text-ink-soft">
                    {m.sampleSize > 0 ? `${m.sampleSize} readings` : ""}
                  </p>
                </div>
                <DirectionBadge direction={dir} />
              </div>

              <div className="mt-3 flex items-baseline gap-2">
                <span className="font-display text-xl font-bold text-ink">
                  {m.recent == null ? "—" : `${m.recent}${m.unit ? ` ${m.unit}` : ""}`}
                </span>
                {(m.earliest != null || m.recent != null) && (
                  <span className="text-xs text-ink-soft">
                    was {m.earliest == null ? "—" : `${m.earliest}${m.unit ? ` ${m.unit}` : ""}`}
                  </span>
                )}
              </div>

              <div className="mt-1 flex items-center gap-2 text-xs">
                {dir === "improving" || (dir === "decreasing" && m.key === "bmi") ? (
                  <TrendingDown size={14} className="text-status-stable" />
                ) : dir === "worsening" ? (
                  <TrendingUp size={14} className="text-status-critical" />
                ) : dir === "fluctuating" ? (
                  <Activity size={14} className="text-status-warning" />
                ) : (
                  <Minus size={14} className="text-ink-soft" />
                )}
                <span className={dir === "worsening" ? "text-status-critical" : dir === "improving" ? "text-status-stable" : "text-ink-soft"}>
                  {formatDelta(m.recent, m.earliest, m.unit)}
                </span>
                {pct != null && (
                  <span className="text-ink-soft">
                    ({pct > 0 ? "+" : ""}
                    {pct.toFixed(0)}%)
                  </span>
                )}
              </div>

              <div className="mt-3">
                <Sparkline points={m.spark} color={color} />
              </div>

              <p className="mt-3 text-xs leading-relaxed text-ink-soft">{m.summary}</p>
              {m.forecastSummary && (
                <p className="mt-2 border-l-2 border-teal-400 pl-2 text-xs leading-relaxed text-ink-soft">
                  {m.forecastSummary}
                </p>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}