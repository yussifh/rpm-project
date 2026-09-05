import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { FloatingActionButton } from "@/components/layout/FloatingActionButton";
import { NAV_CONFIG } from "@/routes/navConfig";
import { useAuth } from "@/context/useAuth";
import { useAsyncData } from "@/hooks/useAsyncData";
import { adminApi } from "@/services/adminApi";

const ROLE_LABELS: Record<string, string> = {
  admin: "Administration",
  patient: "My Health",
};

/**
 * ONE layout shell reused across both roles. Restyled to match a
 * reference admin-dashboard look: a full-width teal header on top, a dark
 * navy sidebar (with profile widget + "today" stat tiles) below-left, and
 * a floating action button for the role's most common "create new" action.
 */
export function AppLayout() {
  const { user } = useAuth();

  const { data: adminUsers } = useAsyncData(
    () => (user?.role === "admin" ? adminApi.listUsers() : Promise.resolve(null)),
    [user?.role]
  );

  if (!user) return null;

  const items = NAV_CONFIG[user.role];
  const roleLabel = ROLE_LABELS[user.role];

  const stats =
    user.role === "admin" && adminUsers
      ? [
          { label: "Patients", value: adminUsers.filter((u) => u.role === "patient").length },
          { label: "Admins", value: adminUsers.filter((u) => u.role === "admin").length },
          { label: "Users", value: adminUsers.length },
        ]
      : undefined;

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar items={items} roleLabel={roleLabel} stats={stats} />
        <main className="flex-1 bg-surface-sunken p-8">
          <Outlet />
        </main>
      </div>
      <FloatingActionButton role={user.role} />
    </div>
  );
}
