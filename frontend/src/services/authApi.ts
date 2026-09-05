import { apiClient } from "./apiClient";
import type { LoginCredentials, TokenResponse, User } from "@/types/auth";

export const authApi = {
  async login({ email, password }: LoginCredentials): Promise<TokenResponse> {
    // The backend's /auth/login uses OAuth2PasswordRequestForm (form-encoded,
    // "username" field carries the email) — see backend/app/api/v1/auth.py.
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);

    const { data } = await apiClient.post<TokenResponse>("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    return data;
  },

  async getMe(): Promise<User> {
    const { data } = await apiClient.get<User>("/auth/me");
    return data;
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<User> {
    const { data } = await apiClient.patch<User>("/auth/me/password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return data;
  },

  async logout(refreshToken: string): Promise<void> {
    await apiClient.post("/auth/logout", null, { params: { refresh_token: refreshToken } });
  },
};
