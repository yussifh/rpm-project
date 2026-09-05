import { apiClient } from "./apiClient";
import type { MedicalHistoryCreatePayload, MedicalHistoryEntry } from "@/types/medicalHistory";

export const medicalHistoryApi = {
  async listForPatient(patientId: string): Promise<MedicalHistoryEntry[]> {
    const { data } = await apiClient.get<MedicalHistoryEntry[]>(`/patients/${patientId}/medical-history`);
    return data;
  },

  async addEntry(patientId: string, payload: MedicalHistoryCreatePayload): Promise<MedicalHistoryEntry> {
    const { data } = await apiClient.post<MedicalHistoryEntry>(`/patients/${patientId}/medical-history`, payload);
    return data;
  },
};
