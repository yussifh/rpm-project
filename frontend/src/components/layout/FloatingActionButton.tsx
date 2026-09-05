import { Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import type { UserRole } from "@/types/auth";

const PRIMARY_ACTION: Record<UserRole, { path: string; label: string }> = {
  admin: { path: "/admin/patients", label: "Add a patient" },
  patient: { path: "/patient/vitals", label: "Log vitals" },
};

/**
 * The reference design's circular teal "+" button, bottom-right. Its
 * destination is role-contextual — the single most common "start
 * something new" action for whoever's looking at it — rather than a
 * generic modal-launcher, since each role's "add new" action goes to a
 * different place entirely.
 */
export function FloatingActionButton({ role }: { role: UserRole }) {
  const navigate = useNavigate();
  const action = PRIMARY_ACTION[role];

  return (
    <button
      onClick={() => navigate(action.path)}
      aria-label={action.label}
      title={action.label}
      className="fixed bottom-8 right-8 flex h-14 w-14 items-center justify-center rounded-full bg-teal-500 text-white shadow-lg transition-transform hover:scale-105 hover:bg-teal-600"
    >
      <Plus size={26} />
    </button>
  );
}
