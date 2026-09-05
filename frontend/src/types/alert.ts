export type AlertSeverity = "info" | "warning" | "critical";
export type AlertStatus = "new" | "acknowledged" | "resolved";

export interface Alert {
  id: string;
  patient_id: string;
  related_vital_id: string | null;
  related_prediction_id: string | null;
  title: string;
  message: string;
  severity: AlertSeverity;
  status: AlertStatus;
  acknowledged_at: string | null;
  resolved_at: string | null;
  emergency_contact_notified: boolean;
  created_at: string;
}
