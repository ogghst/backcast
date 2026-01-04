import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { usePermission } from "./usePermission";
import { useAuthStore } from "@/stores/useAuthStore";

// Mock store
vi.mock("@/stores/useAuthStore");

describe("usePermission Hook", () => {
  const mockHasPermission = vi.fn();
  const mockHasAnyPermission = vi.fn();
  const mockHasAllPermissions = vi.fn();
  const mockHasRole = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (
      useAuthStore as unknown as {
        getState: () => { user: null; permissions: [] };
      }
    ).getState = vi.fn(() => ({
      user: null,
      permissions: [],
    }));
    vi.mocked(useAuthStore).mockImplementation(
      (selector: (state: unknown) => unknown) => {
        const state = {
          hasPermission: mockHasPermission,
          hasAnyPermission: mockHasAnyPermission,
          hasAllPermissions: mockHasAllPermissions,
          hasRole: mockHasRole,
        };
        return selector(state);
      }
    );
  });

  it("exposes permission check methods", () => {
    const { result } = renderHook(() => usePermission());

    expect(result.current.can).toBeDefined();
    expect(result.current.canAny).toBeDefined();
    expect(result.current.canAll).toBeDefined();
    expect(result.current.hasRole).toBeDefined();
  });

  it("calls store methods correctly", () => {
    const { result } = renderHook(() => usePermission());

    result.current.can("user-read");
    expect(mockHasPermission).toHaveBeenCalledWith("user-read");

    result.current.canAny(["user-read"]);
    expect(mockHasAnyPermission).toHaveBeenCalledWith(["user-read"]);

    result.current.canAll(["user-read"]);
    expect(mockHasAllPermissions).toHaveBeenCalledWith(["user-read"]);

    result.current.hasRole("admin");
    expect(mockHasRole).toHaveBeenCalledWith("admin");
  });
});
