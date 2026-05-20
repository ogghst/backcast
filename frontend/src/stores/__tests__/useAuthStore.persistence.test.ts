import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAuthStore } from "../useAuthStore";
import { act } from "@testing-library/react";

const mockRemoveClient = vi.fn();

vi.mock("../../api/auth", () => ({
  refreshAccessToken: vi.fn(),
  logoutUser: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("../../api/queryPersister", () => ({
  createIDBPersister: () => ({
    persistClient: vi.fn(),
    restoreClient: vi.fn(),
    removeClient: mockRemoveClient,
  }),
  shouldDehydrateQuery: () => true,
  setAppPersister: vi.fn(),
  getAppPersister: () => ({ removeClient: mockRemoveClient }),
}));

describe("useAuthStore - Persistence Logout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    act(() => {
      useAuthStore.setState({
        user: null,
        permissions: [],
        token: null,
        refreshToken: null,
        isAuthenticated: false,
      });
    });
  });

  it("clears persisted query cache on logout", async () => {
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

    expect(mockRemoveClient).toHaveBeenCalledOnce();
  });
});
