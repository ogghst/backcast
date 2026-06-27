/**
 * SidebarContent tests (expanded sidebar body).
 *
 * Mirrors the mock setup style of `AppSidebar.test.tsx` (router hooks,
 * permission, effective chat context, running-executions count). The auth
 * store (`useAuthStore`) is also mocked because the `<Can>` gate component
 * reads its permission/role checks from the store (NOT from `usePermission`).
 *
 * Scope of this file: the Admin/Agents active-highlight regression — landing on
 * `/admin/agent-schedules` (the Agents destination) must NOT light up the Admin
 * header, while a real admin page (`/admin/users`) still must.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

// --- Mocks --------------------------------------------------------------

const mockNavigate = vi.fn();
let mockPathname = "/";

vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ pathname: mockPathname, search: "" }),
  useMatch: () => null,
  useParams: () => ({}),
}));

vi.mock("antd", async () => {
  const actual = await vi.importActual<typeof import("antd")>("antd");
  return {
    ...actual,
    Grid: {
      useBreakpoint: () => ({ md: true }),
    },
  };
});

// `usePermission` powers SidebarContent's can/canAny/hasRole calls directly.
let mockCan: (p: string) => boolean = () => true;
let mockCanAny: (perms: string[]) => boolean = () => true;
let mockHasRole: (role: string) => boolean = () => false;
vi.mock("@/hooks/usePermission", () => ({
  usePermission: () => ({
    can: mockCan,
    canAny: mockCanAny,
    hasRole: mockHasRole,
  }),
}));

// `useAuthStore` powers the <Can> gate component (separate from usePermission).
// Default to an admin user who can read users and manage agent schedules so the
// Admin section AND the Agents row are both visible.
let storeHasPermission: (p: string) => boolean = () => true;
let storeHasAnyPermission: (perms: string[]) => boolean = () => true;
let storeHasRole: (role: string) => boolean = (r) => r === "admin";
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({
      hasPermission: storeHasPermission,
      hasAnyPermission: storeHasAnyPermission,
      hasAllPermissions: () => true,
      hasRole: storeHasRole,
    }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: { full_name: "Admin User", email: "admin@test", role: "admin" },
  }),
}));

// No entity-detail route in these tests.
vi.mock("@/components/navigation/useEntityNav", () => ({
  useEntityNav: () => null,
}));

vi.mock("@/hooks/navigation/useEffectiveChatContext", () => ({
  useEffectiveChatContext: () => ({ type: "general" }),
}));

vi.mock("@/features/ai/chat/api/useAgentExecutions", () => ({
  useRunningExecutionsCount: () => ({ data: 0 }),
}));

import { SidebarContent } from "./SidebarContent";

function resetState() {
  mockNavigate.mockClear();
  mockPathname = "/";
  mockCan = () => true;
  mockCanAny = () => true;
  mockHasRole = (r: string) => r === "admin";
  storeHasPermission = () => true;
  storeHasAnyPermission = () => true;
  storeHasRole = (r: string) => r === "admin";
}

describe("SidebarContent", () => {
  beforeEach(resetState);

  describe("Admin vs Agents active highlight", () => {
    it("highlights Agents (NOT Admin) on /admin/agent-schedules", () => {
      // Admin user who can also manage agent schedules → Agents lands on
      // /admin/agent-schedules, and the Admin section is visible.
      mockPathname = "/admin/agent-schedules";

      render(<SidebarContent />);

      const agents = screen.getByRole("button", {
        name: "Agents",
      }) as HTMLElement;
      const admin = screen.getByRole("button", {
        name: "Admin",
      }) as HTMLElement;

      // Agents IS active (primary left-border).
      expect(agents.style.borderLeft).not.toBe("3px solid transparent");
      // Admin header is NOT active.
      expect(admin.style.borderLeft).toBe("3px solid transparent");
    });

    it("highlights Admin (the header) on /admin/users", () => {
      mockPathname = "/admin/users";

      render(<SidebarContent />);

      const admin = screen.getByRole("button", {
        name: "Admin",
      }) as HTMLElement;

      // Admin header IS active on a real admin page.
      expect(admin.style.borderLeft).not.toBe("3px solid transparent");
    });
  });
});
