import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAuthStore } from "./useAuthStore";
import { act } from "@testing-library/react";

// Mock the auth API functions
vi.mock("../api/auth", () => ({
  refreshAccessToken: vi.fn(),
  logoutUser: vi.fn(),
}));

describe("useAuthStore - Refresh Token", () => {
  beforeEach(() => {
    act(() => {
      useAuthStore.setState({
        user: null,
        permissions: [],
        token: null,
        refreshToken: null,
        isAuthenticated: false,
      });
    });
    vi.clearAllMocks();
  });

  it("stores refresh token", () => {
    act(() => {
      useAuthStore.getState().setRefreshToken("test-refresh-token");
    });

    const state = useAuthStore.getState();
    expect(state.refreshToken).toBe("test-refresh-token");
  });

  it("sets both tokens together", () => {
    const mockUser = {
      id: "1",
      user_id: "1",
      email: "test@example.com",
      full_name: "Test User",
      role: "admin" as const,
      is_active: true,
      permissions: ["user-read"],
    };

    act(() => {
      useAuthStore.getState().setUser(mockUser);
      useAuthStore.getState().setTokens("access-token", "refresh-token");
    });

    const state = useAuthStore.getState();
    expect(state.token).toBe("access-token");
    expect(state.refreshToken).toBe("refresh-token");
    expect(state.isAuthenticated).toBe(true);
  });

  it("refreshes access token successfully", async () => {
    const { refreshAccessToken } = await import("../api/auth");
    vi.mocked(refreshAccessToken).mockResolvedValue({
      access_token: "new-access-token",
      token_type: "bearer",
    });

    act(() => {
      useAuthStore.getState().setRefreshToken("test-refresh-token");
    });

    const result = await useAuthStore.getState().refreshAccessToken();

    expect(result).toBe(true);
    expect(useAuthStore.getState().token).toBe("new-access-token");
    expect(refreshAccessToken).toHaveBeenCalledWith("test-refresh-token");
  });

  it("returns false when refresh token is missing", async () => {
    const { refreshAccessToken } = await import("../api/auth");

    const result = await useAuthStore.getState().refreshAccessToken();

    expect(result).toBe(false);
    expect(refreshAccessToken).not.toHaveBeenCalled();
  });

  it("returns false on refresh failure", async () => {
    const { refreshAccessToken } = await import("../api/auth");
    vi.mocked(refreshAccessToken).mockRejectedValue(new Error("Network error"));

    act(() => {
      useAuthStore.getState().setRefreshToken("test-refresh-token");
    });

    const result = await useAuthStore.getState().refreshAccessToken();

    expect(result).toBe(false);
  });

  it("logs out and revokes refresh token", async () => {
    const { logoutUser } = await import("../api/auth");
    vi.mocked(logoutUser).mockResolvedValue(undefined);

    act(() => {
      useAuthStore.getState().setTokens("access-token", "refresh-token");
      useAuthStore.getState().setUser({
        id: "1",
        user_id: "1",
        email: "test@example.com",
        full_name: "Test User",
        role: "admin" as const,
        is_active: true,
        permissions: ["user-read"],
      });
    });

    await act(async () => {
      await useAuthStore.getState().logout();
    });

    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().refreshToken).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(logoutUser).toHaveBeenCalledWith("refresh-token");
  });

  it("continues logout even if API call fails", async () => {
    const { logoutUser } = await import("../api/auth");
    vi.mocked(logoutUser).mockRejectedValue(new Error("API error"));

    act(() => {
      useAuthStore.getState().setTokens("access-token", "refresh-token");
    });

    await act(async () => {
      await useAuthStore.getState().logout();
    });

    // State should still be cleared
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().refreshToken).toBeNull();
  });
});
