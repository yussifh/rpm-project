import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useAsyncData } from "@/hooks/useAsyncData";
import { notificationApi } from "@/services/notificationApi";

export function NotificationsPage() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const { data: notifications, isLoading, error, refetch } = useAsyncData(
    () => notificationApi.list(unreadOnly),
    [unreadOnly]
  );
  const [pendingId, setPendingId] = useState<string | null>(null);

  async function markRead(id: string) {
    setPendingId(id);
    try {
      await notificationApi.markRead(id);
      refetch();
    } finally {
      setPendingId(null);
    }
  }

  return (
    <div>
      <h1 className="font-display text-2xl font-bold text-ink">Notifications</h1>
      <p className="mt-1 text-sm text-ink-soft">Updates about your care.</p>

      <div className="mt-4">
        <label className="inline-flex items-center gap-2 text-sm text-ink-soft">
          <input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} />
          Unread only
        </label>
      </div>

      {error && <p className="mt-4 text-sm text-status-critical">Couldn't load notifications.</p>}

      <div className="mt-4 space-y-3">
        {isLoading ? (
          <p className="text-sm text-ink-soft">Loading…</p>
        ) : !notifications || notifications.length === 0 ? (
          <Card>
            <p className="text-sm text-ink-soft">You're all caught up.</p>
          </Card>
        ) : (
          notifications.map((n) => (
            <Card key={n.id} className={n.is_read ? "" : "border-l-4 border-l-accent-teal"}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-ink">{n.title}</p>
                    {!n.is_read && <Badge tone="info">New</Badge>}
                  </div>
                  <p className="mt-1 text-sm text-ink-soft">{n.message}</p>
                  <p className="mt-1 text-xs text-ink-soft">{new Date(n.created_at).toLocaleString()}</p>
                </div>
                {!n.is_read && (
                  <button
                    onClick={() => markRead(n.id)}
                    disabled={pendingId === n.id}
                    className="shrink-0 text-xs font-medium text-teal-600 hover:underline disabled:opacity-60"
                  >
                    Mark read
                  </button>
                )}
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
