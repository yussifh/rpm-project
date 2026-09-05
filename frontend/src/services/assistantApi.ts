import { apiClient } from "./apiClient";
import type { AssistantMessage } from "@/types/assistant";

export const assistantApi = {
  async listMessages(patientId: string): Promise<AssistantMessage[]> {
    const { data } = await apiClient.get<AssistantMessage[]>(`/patients/${patientId}/assistant/messages`);
    return data;
  },

  async sendMessage(patientId: string, content: string): Promise<AssistantMessage> {
    const { data } = await apiClient.post<AssistantMessage>(`/patients/${patientId}/assistant/messages`, {
      content,
    });
    return data;
  },
};
