import { LogOut, Settings } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/useAuth";
import type { NavItem } from "@/routes/navConfig";

interface SidebarStat {
  label: string;
  value: string | number;
}

interface SidebarProps {
  items: NavItem[];
  roleLabel: string;
  stats?: SidebarStat[];
}

/**
 * Restyled to match a reference admin-dashboard look: a dark navy sidebar
 * with a profile widget (avatar, name, quick-action icons) and a small
 * row of "today at a glance" stat tiles above the nav — rather than the
 * light sidebar + separate topbar-avatar split from v1. The Header
 * component above this no longer shows the user's identity; it lives
 * here instead, matching the reference image exactly.
 */
export function Sidebar({ items, roleLabel, stats }: SidebarProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const initials = user?.full_name
    ? user.full_name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase()
    : "?";

  async function handleLogout() {
    await logout();
    navigate("/", { replace: true });
  }

  return (
    <aside className="flex h-screen w-64 flex-col bg-navy-500 text-white/90">
      {/* Profile widget */}
      <div className="border-b border-white/10 px-6 py-6 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-teal-500 font-display text-xl font-bold text-white">
          {initials}
        </div>
        <p className="mt-3 text-xs text-white/50">Welcome</p>
        <p className="font-display text-sm font-bold text-white">{user?.full_name}</p>

        <div className="mt-3 flex items-center justify-center gap-3 text-white/50">
          <button aria-label="Settings" className="hover:text-white" onClick={() => navigate(`/${user?.role}/settings`)}>
            <Settings size={15} />
          </button>
          <button aria-label="Log out" onClick={handleLogout} className="hover:text-status-critical">
            <LogOut size={15} />
          </button>
        </div>
      </div>

      {/* "Today at a glance" stat tiles */}
      {stats && stats.length > 0 && (
        <div className="border-b border-white/10 px-4 py-4">
          <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-wide text-white/40">
            Today
          </p>
          <div className="grid grid-cols-3 gap-2">
            {stats.map((s) => (
              <div key={s.label} className="rounded-lg bg-white/5 px-1 py-2 text-center">
                <p className="readout text-base font-semibold text-white">{s.value}</p>
                <p className="mt-0.5 text-[10px] text-white/50">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="px-6 pt-5 pb-2 text-[11px] font-semibold uppercase tracking-wide text-white/40">
        {roleLabel}
      </p>

      <nav className="flex-1 space-y-1 px-3 overflow-y-auto">
        {items.map(({ label, path, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path.split("/").length <= 2}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg border-l-2 px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "border-teal-400 bg-white/10 text-white"
                  : "border-transparent text-white/60 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            <Icon size={18} strokeWidth={2} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
