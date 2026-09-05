import { apiClient } from "./apiClient";
import type { User, UserRole } from "@/types/auth";
import type { PatientCreatePayload } from "@/types/admin";
import type { AuditLog } from "@/types/audit";
import type { PatientProfile } from "@/types/patient";

export const adminApi = {
  async listUsers(role?: UserRole): Promise<User[]> {
    const { data } = await apiClient.get<User[]>("/admin/users", {
      params: role ? { role } : undefined,
    });
    return data;
  },

  async createPatient(payload: PatientCreatePayload): Promise<User> {
    const { data } = await apiClient.post<User>("/admin/users/patient", payload);
    return data;
  },

  async deactivateUser(userId: string): Promise<User> {
    const { data } = await apiClient.patch<User>(`/admin/users/${userId}/deactivate`);
    return data;
  },

  async activateUser(userId: string): Promise<User> {
    const { data } = await apiClient.patch<User>(`/admin/users/${userId}/activate`);
    return data;
  },

  async updateUser(userId: string, payload: { full_name?: string; email?: string; phone_number?: string }): Promise<User> {
    const { data } = await apiClient.patch<User>(`/admin/users/${userId}`, payload);
    return data;
  },

  async updatePatient(
    patientId: string,
    payload: {
      date_of_birth?: string;
      gender?: string;
      blood_group?: string;
      height_cm?: number;
      weight_kg?: number;
      emergency_contact_name?: string;
      emergency_contact_phone?: string;
      chronic_conditions_summary?: string;
    }
  ): Promise<PatientProfile> {
    const { data } = await apiClient.patch(`/admin/patients/${patientId}`, payload);
    return data;
  },

  async listAuditLogs(params?: { action?: string; entity_type?: string; skip?: number; limit?: number }): Promise<AuditLog[]> {
    const { data } = await apiClient.get<AuditLog[]>("/admin/audit-logs", { params });
    return data;
  },
};
