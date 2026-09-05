import { Badge } from "@/components/ui/Badge";
import type { Alert, AlertSeverity } from "@/types/alert";

const SEVERITY_TONE: Record<AlertSeverity, "info" | "warning" | "critical"> = {
  info: "info",
  warning: "warning",
  critical: "critical",
};

interface AlertsListProps {
  alerts: Alert[];
  onAcknowledge?: (alertId: string) => void;
  onResolve?: (alertId: string) => void;
  pendingId?: string | null;
  emptyMessage?: string;
}

/** Shared alert list — used on both the patient dashboard (read-only) and
 * the admin alerts view (with acknowledge/resolve actions, since alert
 * lifecycle management is admin-only — see AlertService docstring). */
export function AlertsList({ alerts, onAcknowledge, onResolve, pendingId, emptyMessage }: AlertsListProps) {
  if (alerts.length === 0) {
    return <p className="text-sm text-ink-soft">{emptyMessage ?? "No alerts."}</p>;
  }

  return (
    <ul className="space-y-2">
      {alerts.map((alert) => (
        <li key={alert.id} className="rounded-lg border border-surface-border p-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Badge tone={SEVERITY_TONE[alert.severity]}>{alert.severity}</Badge>
                <span className="text-sm font-medium text-ink">{alert.title}</span>
                {alert.emergency_contact_notified && <Badge tone="info">Family notified</Badge>}
              </div>
              <p className="mt-1 text-sm text-ink-soft">{alert.message}</p>
              <p className="mt-1 text-xs text-ink-soft">
                {new Date(alert.created_at).toLocaleString()} · {alert.status}
              </p>
            </div>
            {(onAcknowledge || onResolve) && alert.status !== "resolved" && (
              <div className="flex shrink-0 gap-2">
                {onAcknowledge && alert.status === "new" && (
                  <button
                    type="button"
                    disabled={pendingId === alert.id}
                    onClick={() => onAcknowledge(alert.id)}
                    className="rounded-lg border border-surface-border px-2 py-1 text-xs hover:border-teal-500 disabled:opacity-60"
                  >
                    Acknowledge
                  </button>
                )}
                {onResolve && (
                  <button
                    type="button"
                    disabled={pendingId === alert.id}
                    onClick={() => onResolve(alert.id)}
                    className="rounded-lg bg-teal-500 px-2 py-1 text-xs text-white hover:bg-teal-600 disabled:opacity-60"
                  >
                    Resolve
                  </button>
                )}
              </div>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
