import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { useAsyncData } from "@/hooks/useAsyncData";
import { adminApi } from "@/services/adminApi";

const inputClass = "rounded-lg border border-surface-border px-3 py-2 text-sm focus:border-teal-500";
const PAGE_SIZE = 50;

export function AuditLogPage() {
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [page, setPage] = useState(0);

  const { data: logs, isLoading, error } = useAsyncData(
    () =>
      adminApi.listAuditLogs({
        action: action || undefined,
        entity_type: entityType || undefined,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    [action, entityType, page]
  );

  return (
    <div>
      <h1 className="font-display text-2xl font-bold text-ink">Audit Log</h1>
      <p className="mt-1 text-sm text-ink-soft">Read-only trail of actions taken across the system.</p>

      <Card className="mt-6">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-xs font-medium uppercase tracking-wide text-ink-soft">Action</label>
            <input
              value={action}
              onChange={(e) => {
                setPage(0);
                setAction(e.target.value);
              }}
              placeholder="e.g. DEACTIVATE_USER"
              className={`${inputClass} mt-1`}
            />
          </div>
          <div>
            <label className="block text-xs font-medium uppercase tracking-wide text-ink-soft">Entity type</label>
            <input
              value={entityType}
              onChange={(e) => {
                setPage(0);
                setEntityType(e.target.value);
              }}
              placeholder="e.g. User"
              className={`${inputClass} mt-1`}
            />
          </div>
        </div>

        {error && <p className="mt-4 text-sm text-status-critical">Couldn't load audit logs.</p>}

        {isLoading ? (
          <p className="mt-4 text-sm text-ink-soft">Loading…</p>
        ) : !logs || logs.length === 0 ? (
          <p className="mt-4 text-sm text-ink-soft">No matching audit entries.</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs uppercase tracking-wide text-ink-soft">
                  <th className="py-2 pr-4 font-medium">When</th>
                  <th className="py-2 pr-4 font-medium">Action</th>
                  <th className="py-2 pr-4 font-medium">Entity</th>
                  <th className="py-2 pr-4 font-medium">Entity ID</th>
                  <th className="py-2 pr-4 font-medium">Actor user ID</th>
                  <th className="py-2 pr-4 font-medium">IP</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b border-surface-border last:border-0">
                    <td className="py-3 pr-4 readout text-ink-soft">{new Date(log.created_at).toLocaleString()}</td>
                    <td className="py-3 pr-4 font-medium text-ink">{log.action}</td>
                    <td className="py-3 pr-4 text-ink-soft">{log.entity_type}</td>
                    <td className="py-3 pr-4 readout text-xs text-ink-soft">{log.entity_id ?? "—"}</td>
                    <td className="py-3 pr-4 readout text-xs text-ink-soft">{log.user_id ?? "—"}</td>
                    <td className="py-3 pr-4 readout text-ink-soft">{log.ip_address ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-4 flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="text-sm font-medium text-teal-600 hover:underline disabled:opacity-40"
          >
            ← Newer
          </button>
          <span className="text-xs text-ink-soft">Page {page + 1}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={!logs || logs.length < PAGE_SIZE}
            className="text-sm font-medium text-teal-600 hover:underline disabled:opacity-40"
          >
            Older →
          </button>
        </div>
      </Card>
    </div>
  );
}
