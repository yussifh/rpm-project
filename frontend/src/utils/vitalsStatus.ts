export type VitalStatus = "stable" | "warning" | "critical" | "info";

/**
 * Maps a raw vital value to a display status using the same warning/
 * critical cut points as the backend's threshold rules
 * (backend/app/services/alert_rules.py) — kept in sync deliberately so a
 * value that shows "critical" on the patient dashboard is the same value
 * that would have triggered a backend alert.
 */
export function statusForRange(
  value: number | null | undefined,
  warningMin: number,
  criticalMin: number
): VitalStatus {
  if (value === null || value === undefined) return "info";
  if (value >= criticalMin) return "critical";
  if (value >= warningMin) return "warning";
  return "stable";
}

/** SpO2 is inverted (LOWER is worse), so it gets its own helper rather than
 * forcing statusForRange's "higher is worse" shape to fit both cases. */
export function statusForSpo2(value: number | null | undefined): VitalStatus {
  if (value === null || value === undefined) return "info";
  if (value < 90) return "critical";
  if (value < 95) return "warning";
  return "stable";
}
