import { describe, it, expect, beforeEach } from "vitest";
import { useAuthStore } from "./useAuthStore";
import { act } from "@testing-library/react";

describe("useAuthStore", () => {
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
  });

  it("sets user and permissions correctly", () => {
    const mockUser = {
      id: "1",
      user_id: "1",
      email: "test@example.com",
      full_name: "Test User",
      role: "admin",
      is_active: true,
      permissions: ["user-read", "user-create"],
      created_at: null,
    };

    act(() => {
      useAuthStore.getState().setUser(mockUser);
    });

    const state = useAuthStore.getState();
    expect(state.user).toEqual(mockUser);
    expect(state.permissions).toEqual(["user-read", "user-create"]);
    expect(state.isAuthenticated).toBe(true);
  });

  it("checks permissions correctly", () => {
    act(() => {
      useAuthStore.setState({
        permissions: ["user-read", "user-create"],
      });
    });

    const state = useAuthStore.getState();
    expect(state.hasPermission("user-read")).toBe(true);
    expect(state.hasPermission("user-delete")).toBe(false);
  });

  it("checks any permissions correctly", () => {
    act(() => {
      useAuthStore.setState({
        permissions: ["user-read"],
      });
    });

    const state = useAuthStore.getState();
    expect(state.hasAnyPermission(["user-read", "user-delete"])).toBe(true);
    expect(state.hasAnyPermission(["user-delete"])).toBe(false);
  });

  it("checks all permissions correctly", () => {
    act(() => {
      useAuthStore.setState({
        permissions: ["user-read", "user-create"],
      });
    });

    const state = useAuthStore.getState();
    expect(state.hasAllPermissions(["user-read", "user-create"])).toBe(true);
    expect(state.hasAllPermissions(["user-read", "user-delete"])).toBe(false);
  });

  it("checks roles correctly", () => {
    const mockUser = {
      id: "1",
      user_id: "1",
      email: "test@example.com",
      full_name: "Test User",
      role: "admin",
      is_active: true,
      permissions: [],
      created_at: null,
    };

    act(() => {
      useAuthStore.getState().setUser(mockUser);
    });

    const state = useAuthStore.getState();
    expect(state.hasRole("admin")).toBe(true);
    expect(state.hasRole("manager")).toBe(false);
    expect(state.hasRole(["admin", "manager"])).toBe(true);
  });
});
