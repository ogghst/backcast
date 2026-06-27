/**
 * useAdminNavItems tests.
 *
 * The hook filters its 11 candidate admin items by per-item gate only. The
 * section-level `hasRole("admin")` guard lives in the sidebar (SidebarContent),
 * NOT here — so a non-admin who holds a granular permission still receives
 * that item from this hook. Each test asserts that contract.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { App } from "antd";

let mockCan: (p: string) => boolean = () => false;
let mockHasRole: (r: string) => boolean = () => false;

vi.mock("@/hooks/usePermission", () => ({
  usePermission: () => ({ can: mockCan, hasRole: mockHasRole }),
}));

import { useAdminNavItems } from "./adminNavItems";

// The hook renders icons (React elements), so wrap in antd App for theme.
function renderHookWithTheme<T>(fn: () => T) {
  return renderHook(fn, {
    wrapper: ({ children }) => <App>{children}</App>,
  });
}

const ALL_LABELS = [
  "Users",
  "Role Assignments",
  "Organizational Units",
  "Cost Element Types",
  "Cost Event Types",
  "AI Providers",
  "AI Assistants",
  "MCP Servers",
  "RBAC Configuration",
  "Change Order Config",
  "System Admin",
] as const;

const ALL_PATHS = [
  "/admin/users",
  "/admin/role-assignments",
  "/admin/organizational-units",
  "/admin/cost-element-types",
  "/admin/cost-event-types",
  "/admin/ai-providers",
  "/admin/ai-assistants",
  "/admin/mcp-servers",
  "/admin/rbac",
  "/admin/change-order-config",
  "/admin/system",
] as const;

function resetState() {
  mockCan = () => false;
  mockHasRole = () => false;
}

describe("useAdminNavItems", () => {
  beforeEach(resetState);

  it("full-admin (all gates pass) → all 11 items, in order, key===path", () => {
    mockCan = () => true;
    mockHasRole = () => true;

    const { result } = renderHookWithTheme(() => useAdminNavItems());

    expect(result.current.map((i) => i.label)).toEqual([...ALL_LABELS]);
    expect(result.current.map((i) => i.key)).toEqual([...ALL_PATHS]);
    expect(result.current.map((i) => i.path)).toEqual([...ALL_PATHS]);
    // key === path invariant (matches the original account-menu convention)
    for (const item of result.current) {
      expect(item.key).toBe(item.path);
      expect(item.icon).toBeTruthy();
    }
  });

  it("admin role with only user-read → Users + the two role-gated items", () => {
    // Role-gated items (Role Assignments, RBAC Configuration) use
    // hasRole("admin"), not can(...). So a user whose only `can` permission is
    // user-read but who IS an admin receives exactly: Users (user-read) plus
    // the two role-gated entries.
    mockCan = (p: string) => p === "user-read";
    mockHasRole = () => true;

    const { result } = renderHookWithTheme(() => useAdminNavItems());

    expect(result.current.map((i) => i.label)).toEqual([
      "Users",
      "Role Assignments",
      "RBAC Configuration",
    ]);
    expect(result.current[0].path).toBe("/admin/users");
  });

  it("does NOT enforce the admin-role section gate — non-admin still gets permitted items", () => {
    // Every per-item `can(...)` gate passes, but hasRole("admin") is false.
    // The hook must still return all 11 (the two `hasRole("admin")` items —
    // Role Assignments and RBAC Configuration — are gated by role and thus
    // drop out; the other 9 survive).
    mockCan = () => true;
    mockHasRole = () => false;

    const { result } = renderHookWithTheme(() => useAdminNavItems());

    expect(result.current.map((i) => i.label)).toEqual([
      "Users",
      "Organizational Units",
      "Cost Element Types",
      "Cost Event Types",
      "AI Providers",
      "AI Assistants",
      "MCP Servers",
      "Change Order Config",
      "System Admin",
    ]);
  });

  it("all per-item gates false → empty array", () => {
    mockCan = () => false;
    mockHasRole = () => false;

    const { result } = renderHookWithTheme(() => useAdminNavItems());

    expect(result.current).toEqual([]);
  });
});
