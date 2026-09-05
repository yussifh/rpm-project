import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlertTriangle,
  Bell,
  BrainCircuit,
  ClipboardList,
  LayoutDashboard,
  MessageCircle,
  Pill,
  Users,
} from "lucide-react";
import type { UserRole } from "@/types/auth";

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
}

export const NAV_CONFIG: Record<UserRole, NavItem[]> = {
  admin: [
    { label: "Dashboard", path: "/admin", icon: LayoutDashboard },
    { label: "Patients", path: "/admin/patients", icon: Users },
    { label: "AI Models", path: "/admin/models", icon: BrainCircuit },
    { label: "Alerts", path: "/admin/alerts", icon: AlertTriangle },
    { label: "Audit Log", path: "/admin/audit", icon: ClipboardList },
    { label: "Notifications", path: "/admin/notifications", icon: Bell },
  ],
  patient: [
    { label: "Dashboard", path: "/patient", icon: LayoutDashboard },
    { label: "My Vitals", path: "/patient/vitals", icon: Activity },
    { label: "AI Assessment", path: "/patient/assessment", icon: BrainCircuit },
    { label: "Medications", path: "/patient/medications", icon: Pill },
    { label: "AI Assistant", path: "/patient/assistant", icon: MessageCircle },
    { label: "Notifications", path: "/patient/notifications", icon: Bell },
  ],
};
