import { apiClient } from "./apiClient";
import type { PatientProfile } from "@/types/patient";

export const patientApi = {
  async getMe(): Promise<PatientProfile> {
    const { data } = await apiClient.get<PatientProfile>("/patients/me");
    return data;
  },

  async updateMe(payload: Partial<PatientProfile>): Promise<PatientProfile> {
    const { data } = await apiClient.patch<PatientProfile>("/patients/me", payload);
    return data;
  },

  async list(): Promise<PatientProfile[]> {
    // Admin-only endpoint — see app/api/v1/patients.py.
    const { data } = await apiClient.get<PatientProfile[]>("/patients");
    return data;
  },

  async getById(patientId: string): Promise<PatientProfile> {
    const { data } = await apiClient.get<PatientProfile>(`/patients/${patientId}`);
    return data;
  },

  async assignCondition(
    patientId: string,
    primaryCondition: "stroke" | "diabetes" | "hypertension"
  ): Promise<PatientProfile> {
    const { data } = await apiClient.patch<PatientProfile>(`/patients/${patientId}/condition`, {
      primary_condition: primaryCondition,
    });
    return data;
  },
};
