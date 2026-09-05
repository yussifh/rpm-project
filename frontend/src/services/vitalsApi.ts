import { apiClient } from "./apiClient";
import type { VitalReading, VitalReadingCreatePayload, VitalSubmissionResult, VitalTrendsResponse } from "@/types/vitals";

export const vitalsApi = {
  async list(patientId: string): Promise<VitalReading[]> {
    const { data } = await apiClient.get<VitalReading[]>(`/patients/${patientId}/vitals`);
    return data;
  },

  async record(patientId: string, payload: VitalReadingCreatePayload): Promise<VitalSubmissionResult> {
    const { data } = await apiClient.post<VitalSubmissionResult>(`/patients/${patientId}/vitals`, payload);
    return data;
  },

  async trends(patientId: string, days = 90): Promise<VitalTrendsResponse> {
    const { data } = await apiClient.get<VitalTrendsResponse>(`/patients/${patientId}/vitals/trends`, {
      params: { days },
    });
    return data;
  },
};
