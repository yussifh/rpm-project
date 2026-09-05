import { apiClient } from "./apiClient";
import type { DiseaseAssessment, DiseaseAssessmentCreatePayload } from "@/types/diseaseAssessment";

export const assessmentApi = {
  async listForPatient(patientId: string): Promise<DiseaseAssessment[]> {
    const { data } = await apiClient.get<DiseaseAssessment[]>(`/patients/${patientId}/assessments`);
    return data;
  },

  async submit(patientId: string, payload: DiseaseAssessmentCreatePayload): Promise<DiseaseAssessment> {
    const { data } = await apiClient.post<DiseaseAssessment>(`/patients/${patientId}/assessments`, payload);
    return data;
  },
};
