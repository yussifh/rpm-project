import { Card } from "@/components/ui/Card";
import { DashboardWelcomeBanner } from "@/components/ui/DashboardWelcomeBanner";
import { AlertsList } from "@/components/ui/AlertsList";
import { UsersByRoleChart } from "@/components/charts/UsersByRoleChart";
import { useAuth } from "@/context/useAuth";
import { useAsyncData } from "@/hooks/useAsyncData";
import { adminApi } from "@/services/adminApi";
import { alertApi } from "@/services/alertApi";

export function AdminDashboard() {
  const { user } = useAuth();
  const { data: users, isLoading, error } = useAsyncData(() => adminApi.listUsers(), []);
  const { data: alerts } = useAsyncData(() => alertApi.listAll(), []);

  const adminCount = users?.filter((u) => u.role === "admin").length ?? 0;
  const patientCount = users?.filter((u) => u.role === "patient").length ?? 0;
  const activeAlerts = (alerts ?? []).filter((a) => a.status !== "resolved");

  return (
    <div>
      <DashboardWelcomeBanner variant="admin" name={user?.full_name} subtitle="System overview" />

      {error && <p className="mt-4 text-sm text-status-critical">Couldn't load dashboard data.</p>}

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-4">
        <Card>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Total Admins</p>
          <p className="readout mt-1 text-3xl font-medium text-teal-600">
            {isLoading ? "—" : adminCount}
          </p>
        </Card>
        <Card>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Total Patients</p>
          <p className="readout mt-1 text-3xl font-medium text-teal-600">
            {isLoading ? "—" : patientCount}
          </p>
        </Card>
        <Card>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Total Users</p>
          <p className="readout mt-1 text-3xl font-medium text-teal-600">
            {isLoading ? "—" : users?.length ?? 0}
          </p>
        </Card>
        <Card>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Active Alerts</p>
          <p className="readout mt-1 text-3xl font-medium text-teal-600">{activeAlerts.length}</p>
        </Card>
      </div>

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">Users by Role</h2>
        <div className="mt-4">{isLoading ? <p className="text-sm text-ink-soft">Loading…</p> : <UsersByRoleChart users={users ?? []} />}</div>
      </Card>

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">Recent Alerts</h2>
        <div className="mt-4">
          <AlertsList alerts={activeAlerts.slice(0, 5)} emptyMessage="No active alerts." />
        </div>
      </Card>
    </div>
  );
}
