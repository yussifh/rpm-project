import { apiClient } from "./apiClient";
import type { DiseaseType, RiskPrediction } from "@/types/prediction";

export const predictionApi = {
  async list(patientId: string, disease?: DiseaseType): Promise<RiskPrediction[]> {
    const { data } = await apiClient.get<RiskPrediction[]>(`/patients/${patientId}/predictions`, {
      params: disease ? { disease_type: disease } : undefined,
    });
    return data;
  },

  async generate(patientId: string, disease: DiseaseType): Promise<RiskPrediction> {
    const { data } = await apiClient.post<RiskPrediction>(
      `/patients/${patientId}/predictions/${disease}`
    );
    return data;
  },
};
