import { apiClient } from "./apiClient";
import type { DiseaseType } from "@/types/prediction";
import type { ModelInfo } from "@/types/modelInfo";

export const modelInfoApi = {
  async get(diseaseType: DiseaseType): Promise<ModelInfo> {
    const { data } = await apiClient.get<ModelInfo>(`/model-info/${diseaseType}`);
    return data;
  },
};
