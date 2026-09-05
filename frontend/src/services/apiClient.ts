import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { tokenStorage } from "./tokenStorage";

/**
 * Design decision: a SINGLE axios instance for the whole app, with two
 * interceptors:
 *   1. Request interceptor attaches the current access token.
 *   2. Response interceptor catches a 401, attempts exactly ONE silent
 *      refresh (using the refresh token), retries the original request,
 *      and only logs the user out if the refresh itself fails. This keeps
 *      "session expired" friction to a minimum without ever silently
 *      retrying in a loop.
 *
 * `_retry` is a custom flag on the request config so we never attempt a
 * second refresh for the same original request (which would infinite-loop
 * if the refresh token itself were invalid).
 */

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let onSessionExpired: (() => void) | null = null;

/** Called once by AuthContext on mount so this module can trigger a
 * logout without importing React/context (keeps this a plain module). */
export function registerSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler;
}

let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) throw new Error("No refresh token available");

  const response = await axios.post(
    `${import.meta.env.VITE_API_BASE_URL}/auth/refresh`,
    null,
    { params: { refresh_token: refreshToken } }
  );
  const newAccessToken = response.data.access_token as string;
  tokenStorage.setAccessToken(newAccessToken);
  return newAccessToken;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableConfig | undefined;

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        // Coalesce concurrent 401s into a single in-flight refresh call.
        refreshPromise ??= refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
        const newAccessToken = await refreshPromise;

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);
      } catch {
        tokenStorage.clear();
        onSessionExpired?.();
      }
    }

    return Promise.reject(error);
  }
);
