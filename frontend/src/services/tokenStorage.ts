/**
 * Centralized token storage — the ONLY module that touches localStorage
 * directly. Every other module (apiClient, AuthContext) goes through this,
 * so if storage strategy ever changes (e.g. httpOnly cookies via a BFF),
 * it's a one-file change.
 */

const ACCESS_TOKEN_KEY = "rpm_access_token";
const REFRESH_TOKEN_KEY = "rpm_refresh_token";

export const tokenStorage = {
  getAccessToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: () => localStorage.getItem(REFRESH_TOKEN_KEY),

  setTokens: (accessToken: string, refreshToken: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },

  setAccessToken: (accessToken: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  },

  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};
