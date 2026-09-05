type BadgeTone = "stable" | "warning" | "critical" | "info" | "neutral";

const TONE_CLASSES: Record<BadgeTone, string> = {
  stable: "bg-status-stable/10 text-status-stable",
  warning: "bg-status-warning/10 text-status-warning",
  critical: "bg-status-critical/10 text-status-critical",
  info: "bg-status-info/10 text-status-info",
  neutral: "bg-surface-sunken text-ink-soft",
};

/** Small rounded status pill — used anywhere a status/severity/role needs
 * a compact, colored label (tables, list rows, cards). */
export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: BadgeTone }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${TONE_CLASSES[tone]}`}
    >
      {children}
    </span>
  );
}
