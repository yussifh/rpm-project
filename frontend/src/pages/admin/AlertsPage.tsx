import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { AlertsList } from "@/components/ui/AlertsList";
import { useAsyncData } from "@/hooks/useAsyncData";
import { alertApi } from "@/services/alertApi";

/**
 * Admin's alert triage view. Acknowledge/resolve is admin-only — there is
 * no doctor role in this system, so closing out an alert is treated as a
 * data-quality/triage action on the system's own output (see
 * AlertService docstring on the backend).
 */
export function AlertsPage() {
  const { data: alerts, isLoading, error, refetch } = useAsyncData(() => alertApi.listAll(), []);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function handleAcknowledge(alertId: string) {
    setActionError(null);
    setPendingId(alertId);
    try {
      await alertApi.acknowledge(alertId);
      refetch();
    } catch {
      setActionError("Couldn't acknowledge that alert. Please try again.");
    } finally {
      setPendingId(null);
    }
  }

  async function handleResolve(alertId: string) {
    setActionError(null);
    setPendingId(alertId);
    try {
      await alertApi.resolve(alertId);
      refetch();
    } catch {
      setActionError("Couldn't resolve that alert. Please try again.");
    } finally {
      setPendingId(null);
    }
  }

  const active = (alerts ?? []).filter((a) => a.status !== "resolved");
  const resolved = (alerts ?? []).filter((a) => a.status === "resolved");

  return (
    <div>
      <h1 className="font-display text-2xl font-bold text-ink">Alerts</h1>
      <p className="mt-1 text-sm text-ink-soft">
        Threshold and AI-triggered alerts across all patients.
      </p>

      {error && <p className="mt-4 text-sm text-status-critical">Couldn't load alerts.</p>}
      {actionError && <p className="mt-4 text-sm text-status-critical">{actionError}</p>}

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">Active</h2>
        <div className="mt-4">
          {isLoading ? (
            <p className="text-sm text-ink-soft">Loading…</p>
          ) : (
            <AlertsList
              alerts={active}
              onAcknowledge={handleAcknowledge}
              onResolve={handleResolve}
              pendingId={pendingId}
              emptyMessage="No active alerts."
            />
          )}
        </div>
      </Card>

      {resolved.length > 0 && (
        <Card className="mt-6">
          <h2 className="font-display text-sm font-bold text-ink">Resolved</h2>
          <div className="mt-4">
            <AlertsList alerts={resolved} />
          </div>
        </Card>
      )}
    </div>
  );
}
