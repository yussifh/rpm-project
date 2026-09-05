import { beforeEach, describe, expect, it } from "vitest";
import { tokenStorage } from "@/services/tokenStorage";

describe("tokenStorage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns null when no tokens are stored", () => {
    expect(tokenStorage.getAccessToken()).toBeNull();
    expect(tokenStorage.getRefreshToken()).toBeNull();
  });

  it("stores and retrieves both tokens together", () => {
    tokenStorage.setTokens("access-123", "refresh-456");
    expect(tokenStorage.getAccessToken()).toBe("access-123");
    expect(tokenStorage.getRefreshToken()).toBe("refresh-456");
  });

  it("updates only the access token without touching the refresh token", () => {
    tokenStorage.setTokens("access-123", "refresh-456");
    tokenStorage.setAccessToken("access-789");
    expect(tokenStorage.getAccessToken()).toBe("access-789");
    expect(tokenStorage.getRefreshToken()).toBe("refresh-456");
  });

  it("clears both tokens", () => {
    tokenStorage.setTokens("access-123", "refresh-456");
    tokenStorage.clear();
    expect(tokenStorage.getAccessToken()).toBeNull();
    expect(tokenStorage.getRefreshToken()).toBeNull();
  });
});
