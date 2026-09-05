import { apiClient } from "./apiClient";
import type { Notification } from "@/types/notification";

export const notificationApi = {
  async list(unreadOnly = false): Promise<Notification[]> {
    const { data } = await apiClient.get<Notification[]>("/notifications", {
      params: unreadOnly ? { unread_only: true } : undefined,
    });
    return data;
  },

  async markRead(notificationId: string): Promise<Notification> {
    const { data } = await apiClient.patch<Notification>(`/notifications/${notificationId}/read`);
    return data;
  },
};
