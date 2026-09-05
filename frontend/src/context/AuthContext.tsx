import {
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { authApi } from "@/services/authApi";
import { registerSessionExpiredHandler } from "@/services/apiClient";
import { tokenStorage } from "@/services/tokenStorage";
import type { LoginCredentials, User } from "@/types/auth";
import { AuthContext, type AuthContextValue } from "@/context/authContextValue";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // Starts true: on first mount we don't yet know if a stored token is
  // still valid, so routes must wait rather than flashing a login screen.
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Wire the apiClient's 401-after-failed-refresh callback to a real logout,
    // without apiClient needing to import React/context (keeps it a plain module).
    registerSessionExpiredHandler(() => {
      setUser(null);
      tokenStorage.clear();
    });

    async function restoreSession() {
      if (!tokenStorage.getAccessToken()) {
        setIsLoading(false);
        return;
      }
      try {
        const me = await authApi.getMe();
        setUser(me);
      } catch {
        tokenStorage.clear();
      } finally {
        setIsLoading(false);
      }
    }

    restoreSession();
  }, []);

  async function login(credentials: LoginCredentials): Promise<User> {
    const tokens = await authApi.login(credentials);
    tokenStorage.setTokens(tokens.access_token, tokens.refresh_token);
    const me = await authApi.getMe();
    setUser(me);
    return me;
  }

  async function logout(): Promise<void> {
    const refreshToken = tokenStorage.getRefreshToken();
    try {
      if (refreshToken) await authApi.logout(refreshToken);
    } finally {
      tokenStorage.clear();
      setUser(null);
    }
  }

  const value: AuthContextValue = {
    user,
    isLoading,
    isAuthenticated: user !== null,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
