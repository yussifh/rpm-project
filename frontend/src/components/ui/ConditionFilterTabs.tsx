import type { DiseaseType } from "@/types/prediction";

export type ConditionFilter = DiseaseType | "all";

const OPTIONS: { value: ConditionFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "diabetes", label: "Diabetes" },
  { value: "hypertension", label: "Hypertension" },
  { value: "stroke", label: "Stroke" },
];

/**
 * "All / Diabetes / Hypertension / Stroke" filter, shared by the Trends
 * card and the AI Health Assessment page. Defaults to "all" wherever it's
 * used — a multi-condition patient still needs the combined view by
 * default; this only lets them narrow it down on request, it never
 * forces the narrower view (see the reasoning for keeping "All" as
 * default: history/trends stay useful for a patient managing more than
 * one condition at once).
 */
export function ConditionFilterTabs({
  value,
  onChange,
}: {
  value: ConditionFilter;
  onChange: (next: ConditionFilter) => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-surface-border p-0.5">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
            value === opt.value ? "bg-teal-500 text-white" : "text-ink-soft hover:text-ink"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
