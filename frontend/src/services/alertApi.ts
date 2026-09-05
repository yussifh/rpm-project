import { apiClient } from "./apiClient";
import type { Alert, AlertStatus } from "@/types/alert";

export const alertApi = {
  /** GET /alerts is role-scoped server-side: a patient gets only their
   * own alerts, admin gets every patient's alerts (see AlertService.
   * list_for_current_user on the backend) — so this same call serves
   * both the patient dashboard's "my alerts" and the admin triage page's
   * "all alerts" via one endpoint. */
  async listMine(statusFilter?: AlertStatus): Promise<Alert[]> {
    const { data } = await apiClient.get<Alert[]>("/alerts", {
      params: statusFilter ? { status_filter: statusFilter } : undefined,
    });
    return data;
  },

  async listAll(statusFilter?: AlertStatus): Promise<Alert[]> {
    return alertApi.listMine(statusFilter);
  },

  async acknowledge(alertId: string): Promise<Alert> {
    const { data } = await apiClient.patch<Alert>(`/alerts/${alertId}/acknowledge`);
    return data;
  },

  async resolve(alertId: string): Promise<Alert> {
    const { data } = await apiClient.patch<Alert>(`/alerts/${alertId}/resolve`);
    return data;
  },
};
