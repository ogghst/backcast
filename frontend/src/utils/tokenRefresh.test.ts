import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useAuthStore } from "@/stores/useAuthStore";
import { useTokenRefreshTimer } from "./tokenRefresh";

describe("useTokenRefreshTimer", () => {
  beforeEach(() => {
    // Reset auth store
    useAuthStore.setState({
      user: null,
      permissions: [],
      token: null,
      refreshToken: null,
      isAuthenticated: false,
    });
    vi.clearAllMocks();
  });

  it("does not throw when not authenticated", () => {
    expect(() => renderHook(() => useTokenRefreshTimer())).not.toThrow();
  });

  it("does not throw when authenticated with valid token", () => {
    // Create a token that expires in 10 minutes
    const futureExpiry = Math.floor(Date.now() / 1000) + 600;
    const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
    const payload = btoa(
      JSON.stringify({ exp: futureExpiry, sub: "test@example.com" })
    );
    const signature = btoa("signature");
    const token = `${header}.${payload}.${signature}`;

    useAuthStore.setState({
      token,
      isAuthenticated: true,
      refreshToken: "refresh-token",
    });

    expect(() => renderHook(() => useTokenRefreshTimer())).not.toThrow();
  });

  it("handles unmount without errors", () => {
    // Create a token that expires in 10 minutes
    const futureExpiry = Math.floor(Date.now() / 1000) + 600;
    const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
    const payload = btoa(
      JSON.stringify({ exp: futureExpiry, sub: "test@example.com" })
    );
    const signature = btoa("signature");
    const token = `${header}.${payload}.${signature}`;

    useAuthStore.setState({
      token,
      isAuthenticated: true,
      refreshToken: "refresh-token",
    });

    const { unmount } = renderHook(() => useTokenRefreshTimer());

    expect(() => unmount()).not.toThrow();
  });
});
