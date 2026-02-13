import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Can } from "./Can";
import { useAuthStore } from "@/stores/useAuthStore";

// Mock store
vi.mock("@/stores/useAuthStore");

describe("Can Component", () => {
  const mockHasPermission = vi.fn();
  const mockHasAnyPermission = vi.fn();
  const mockHasAllPermissions = vi.fn();
  const mockHasRole = vi.fn();

  beforeEach(() => {
    vi.resetAllMocks();
    // Mock the getState method of the useAuthStore
    // Assuming useAuthStore is a function that also has a getState property
    vi.mocked(useAuthStore).getState = vi.fn(() => ({
      user: null as any,
      permissions: [],
      token: null,
      isAuthenticated: false,
      setToken: vi.fn(),
      hasPermission: vi.fn(),
      hasAnyPermission: vi.fn(),
      hasAllPermissions: vi.fn(),
      hasRole: vi.fn(),
      login: vi.fn(),
      logout: vi.fn(),
      setUser: vi.fn(),
    }));
    // Default mock implementation for the hook itself
    vi.mocked(useAuthStore).mockImplementation((selector: any) => {
      const state = {
        hasPermission: mockHasPermission,
        hasAnyPermission: mockHasAnyPermission,
        hasAllPermissions: mockHasAllPermissions,
        hasRole: mockHasRole,
      };
      return selector(state);
    });
  });

  it("renders children when no permission or role is required", () => {
    render(<Can>Allowed Content</Can>);
    expect(screen.getByText("Allowed Content")).toBeInTheDocument();
  });

  it("renders children when user has required permission", () => {
    mockHasPermission.mockReturnValue(true);
    render(<Can permission="user-read">Allowed Content</Can>);
    expect(screen.getByText("Allowed Content")).toBeInTheDocument();
    expect(mockHasPermission).toHaveBeenCalledWith("user-read");
  });

  it("does not render children when user lacks required permission", () => {
    mockHasPermission.mockReturnValue(false);
    render(<Can permission="user-delete">Protected Content</Can>);
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("renders fallback when user lacks required permission", () => {
    mockHasPermission.mockReturnValue(false);
    render(
      <Can permission="user-delete" fallback={<div>Fallback</div>}>
        Protected Content
      </Can>
    );
    expect(screen.getByText("Fallback")).toBeInTheDocument();
  });

  it("renders children when user has required role", () => {
    mockHasRole.mockReturnValue(true);
    render(<Can role="admin">Allowed Content</Can>);
    expect(screen.getByText("Allowed Content")).toBeInTheDocument();
    expect(mockHasRole).toHaveBeenCalledWith("admin");
  });

  it("combines role and permission checks (AND logic)", () => {
    mockHasRole.mockReturnValue(true);
    mockHasPermission.mockReturnValue(false); // Fail permission

    render(
      <Can role="admin" permission="user-delete">
        Protected Content
      </Can>
    );
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();

    mockHasPermission.mockReturnValue(true); // Now pass both
    render(
      <Can role="admin" permission="user-delete">
        Allowed Content
      </Can>
    );
    expect(screen.getByText("Allowed Content")).toBeInTheDocument();
  });

  it("handles array of permissions (ANY logic by default)", () => {
    mockHasAnyPermission.mockReturnValue(true);
    render(
      <Can permission={["user-read", "user-create"]}>Allowed Content</Can>
    );
    expect(screen.getByText("Allowed Content")).toBeInTheDocument();
    expect(mockHasAnyPermission).toHaveBeenCalledWith([
      "user-read",
      "user-create",
    ]);
  });

  it("handles array of permissions (ALL logic when requireAll=true)", () => {
    mockHasAllPermissions.mockReturnValue(true);
    render(
      <Can permission={["user-read", "user-create"]} requireAll>
        Allowed Content
      </Can>
    );
    expect(screen.getByText("Allowed Content")).toBeInTheDocument();
    expect(mockHasAllPermissions).toHaveBeenCalledWith([
      "user-read",
      "user-create",
    ]);
  });
});
