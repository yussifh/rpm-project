interface VitalReadoutProps {
  label: string;
  value: string | number;
  unit?: string;
  status?: "stable" | "warning" | "critical" | "info";
}

const STATUS_COLOR: Record<NonNullable<VitalReadoutProps["status"]>, string> = {
  stable: "text-status-stable",
  warning: "text-status-warning",
  critical: "text-status-critical",
  info: "text-status-info",
};

/**
 * The one deliberately "themed" UI element in this system: vitals render
 * as a monospace, tabular-figure readout — a visual nod to a bedside
 * monitor display, used consistently anywhere a live vital sign appears
 * (dashboards, patient detail views, alert cards).
 */
export function VitalReadout({ label, value, unit, status = "info" }: VitalReadoutProps) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">{label}</p>
      <p className={`readout mt-1 text-3xl font-medium ${STATUS_COLOR[status]}`}>
        {value}
        {unit && <span className="ml-1 text-base text-ink-soft">{unit}</span>}
      </p>
    </div>
  );
}
