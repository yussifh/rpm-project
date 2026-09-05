import { apiClient } from "./apiClient";
import type {
  Medication,
  MedicationCreatePayload,
  MedicationLog,
  MedicationLogCreatePayload,
} from "@/types/medication";

export const medicationApi = {
  async listForPatient(patientId: string, activeOnly = false): Promise<Medication[]> {
    const { data } = await apiClient.get<Medication[]>(`/patients/${patientId}/medications`, {
      params: activeOnly ? { active_only: true } : undefined,
    });
    return data;
  },

  async prescribe(patientId: string, payload: MedicationCreatePayload): Promise<Medication> {
    const { data } = await apiClient.post<Medication>(`/patients/${patientId}/medications`, payload);
    return data;
  },

  async logDose(medicationId: string, payload: MedicationLogCreatePayload): Promise<MedicationLog> {
    const { data } = await apiClient.post<MedicationLog>(`/medications/${medicationId}/logs`, payload);
    return data;
  },

  async listLogs(medicationId: string): Promise<MedicationLog[]> {
    const { data } = await apiClient.get<MedicationLog[]>(`/medications/${medicationId}/logs`);
    return data;
  },
};
