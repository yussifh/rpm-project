import type { ReactNode } from "react";

type Accent = "teal" | "blue" | "purple" | "amber" | "red";

const ACCENT_BORDER: Record<Accent, string> = {
  teal: "border-l-accent-teal",
  blue: "border-l-accent-blue",
  purple: "border-l-accent-purple",
  amber: "border-l-accent-amber",
  red: "border-l-accent-red",
};

interface CardProps {
  children: ReactNode;
  className?: string;
  /** Optional colored left border — echoes the reference design's
   * multi-colored event/alert list rows. Omit for a plain card. */
  accent?: Accent;
}

export function Card({ children, className = "", accent }: CardProps) {
  const accentClasses = accent ? `border-l-4 ${ACCENT_BORDER[accent]}` : "";
  return (
    <div className={`rounded-xl border border-surface-border bg-surface p-6 shadow-sm ${accentClasses} ${className}`}>
      {children}
    </div>
  );
}
