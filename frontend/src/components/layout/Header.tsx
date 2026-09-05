import { Bell, Flag, Settings } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAsyncData } from "@/hooks/useAsyncData";
import { useAuth } from "@/context/useAuth";
import { notificationApi } from "@/services/notificationApi";
import { Logo } from "@/components/ui/Logo";
import { GlobalSearch } from "@/components/layout/GlobalSearch";
import type { UserRole } from "@/types/auth";

/** Where the flag icon takes each role — the closest thing each role has
 * to a "needs attention" shortcut: admin's audit trail, or a patient's
 * notifications (alerts arrive there — see VitalsService). */
const FLAG_DESTINATION: Record<UserRole, string> = {
  admin: "/admin/audit",
  patient: "/patient/notifications",
};

/**
 * Full-width teal header bar — brand + global search + notification
 * badges — matching the reference admin-dashboard image. User identity/
 * logout now lives in the Sidebar's profile widget instead (see
 * Sidebar.tsx), so this bar stays uncluttered.
 */
export function Header() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: notifications } = useAsyncData(() => notificationApi.list(true), []);
  const unreadCount = notifications?.length ?? 0;

  const role = user?.role;

  return (
    <header className="flex h-16 items-center gap-4 bg-teal-header px-6 shadow-sm">
      <Logo variant="light" />

      {role && role !== "patient" ? (
        <GlobalSearch role={role} />
      ) : (
        // Patients have no patient list to search — keep the flex spacer
        // so the right-side icons stay pinned right instead of the layout
        // jumping, without showing a search box with nothing to search.
        <div className="flex-1" />
      )}

      <div className="ml-auto flex items-center gap-5 text-white">
        <button
          aria-label="Notifications"
          className="relative"
          onClick={() => role && navigate(`/${role}/notifications`)}
        >
          <Bell size={19} />
          {unreadCount > 0 && (
            <span className="absolute -right-1.5 -top-1.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-status-critical px-1 text-[10px] font-bold">
              {unreadCount}
            </span>
          )}
        </button>
        <button
          aria-label="Flagged items"
          className="relative"
          onClick={() => role && navigate(FLAG_DESTINATION[role])}
        >
          <Flag size={18} />
        </button>
        <button aria-label="Settings" onClick={() => role && navigate(`/${role}/settings`)}>
          <Settings size={18} />
        </button>
      </div>
    </header>
  );
}
