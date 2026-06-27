/**
 * SidebarFlyout tests.
 *
 * Regression coverage for the rail-mode entity flyout. The expanded sidebar
 * renders entity nav via `SidebarContent`'s `NavRow` (which navigates) and was
 * never affected; only the collapsed rail flyout (`EntityPanel`) is exercised
 * here. Router hooks, the entity-nav resolver, and the nav store are mocked
 * directly to isolate the flyout's own navigation/close behavior.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// --- Mocks --------------------------------------------------------------

const mockNavigate = vi.fn();
let mockPathname = "/projects/p1/structure";

vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ pathname: mockPathname, search: "" }),
}));

// Resolve the active entity nav from the mocked route. Mirrors the shape
// returned by `useEntityNav()` for a project-detail route (pure
// { key, label, path } items, NO embedded onClick — that is the point).
let mockEntityNav: { label: string; items: unknown[] } | null = {
  label: "Project",
  items: [
    { key: "dashboard", label: "Dashboard", path: "/projects/p1/dashboard" },
    { key: "overview", label: "Overview", path: "/projects/p1" },
    { key: "structure", label: "Structure", path: "/projects/p1/structure" },
    { key: "schedule", label: "Schedule", path: "/projects/p1/schedule" },
  ],
};
vi.mock("@/components/navigation/useEntityNav", () => ({
  useEntityNav: () => mockEntityNav,
}));

// Mock the admin nav items the AdminPanel consumes. Default to a non-empty
// list so the panel renders its menu; tests override to [] for the empty-state
// branch. Each item carries an icon (the AdminPanel forwards it to the Menu).
let mockAdminItems: { key: string; label: string; path: string; icon: unknown }[] =
  [
    { key: "/admin/users", label: "Users", path: "/admin/users", icon: null },
    { key: "/admin/rbac", label: "RBAC Configuration", path: "/admin/rbac", icon: null },
  ];
vi.mock("@/components/navigation/adminNavItems", () => ({
  useAdminNavItems: () => mockAdminItems,
}));

// Mock the nav store with mutable state. `setFlyout` actually mutates the
// shared `storeState` so the component's next selector read observes the new
// `flyout` value (mirrors AppSidebar.test.tsx).
let storeState: {
  expanded: boolean;
  flyout: "account" | "entity" | "admin" | null;
  toggleExpanded: () => void;
  setFlyout: (f: "account" | "entity" | "admin" | null) => void;
};
const toggleExpanded = vi.fn(() => {
  storeState = { ...storeState, expanded: !storeState.expanded };
});
const setFlyout = vi.fn((f: "account" | "entity" | "admin" | null) => {
  storeState = { ...storeState, flyout: f };
});
storeState = { expanded: false, flyout: "entity", toggleExpanded, setFlyout };
vi.mock("@/stores/useNavigationStore", () => ({
  useNavigationStore: (selector: (s: typeof storeState) => unknown) =>
    selector(storeState),
}));

import { SidebarFlyout } from "./SidebarFlyout";

function resetState() {
  mockNavigate.mockClear();
  setFlyout.mockClear();
  toggleExpanded.mockClear();
  mockPathname = "/projects/p1/structure";
  storeState = { expanded: false, flyout: "entity", toggleExpanded, setFlyout };
  mockEntityNav = {
    label: "Project",
    items: [
      { key: "dashboard", label: "Dashboard", path: "/projects/p1/dashboard" },
      { key: "overview", label: "Overview", path: "/projects/p1" },
      { key: "structure", label: "Structure", path: "/projects/p1/structure" },
      { key: "schedule", label: "Schedule", path: "/projects/p1/schedule" },
    ],
  };
  mockAdminItems = [
    { key: "/admin/users", label: "Users", path: "/admin/users", icon: null },
    { key: "/admin/rbac", label: "RBAC Configuration", path: "/admin/rbac", icon: null },
  ];
}

describe("SidebarFlyout", () => {
  beforeEach(resetState);

  it("does not render when the flyout is null", () => {
    storeState = { expanded: false, flyout: null, toggleExpanded, setFlyout };
    const { container } = render(<SidebarFlyout />);
    expect(container.firstChild).toBeNull();
  });

  it("renders the entity panel header label when flyout is 'entity'", () => {
    render(<SidebarFlyout />);
    expect(screen.getByText("Project")).toBeInTheDocument();
  });

  it("renders the 'No entity on this route.' fallback when useEntityNav is null", () => {
    mockEntityNav = null;
    render(<SidebarFlyout />);
    expect(
      screen.getByText("No entity on this route."),
    ).toBeInTheDocument();
  });

  it("navigates to the clicked item's path and closes the flyout (regression)", async () => {
    const user = userEvent.setup();
    render(<SidebarFlyout />);

    // Clicking a sub-link (e.g. "Schedule") must navigate to its path…
    await user.click(screen.getByText("Schedule"));
    expect(mockNavigate).toHaveBeenCalledWith("/projects/p1/schedule");

    // …and dismiss the flyout (store `flyout` becomes null).
    expect(setFlyout).toHaveBeenCalledWith(null);
    expect(storeState.flyout).toBeNull();
  });

  it("navigates to the overview/index path (no trailing segment) on click", async () => {
    const user = userEvent.setup();
    render(<SidebarFlyout />);

    await user.click(screen.getByText("Overview"));
    expect(mockNavigate).toHaveBeenCalledWith("/projects/p1");
    expect(setFlyout).toHaveBeenCalledWith(null);
  });

  describe("admin panel", () => {
    beforeEach(() => {
      storeState = { expanded: false, flyout: "admin", toggleExpanded, setFlyout };
    });

    it("renders the 'Admin' header label when flyout is 'admin'", () => {
      render(<SidebarFlyout />);
      expect(screen.getByText("Admin")).toBeInTheDocument();
      expect(screen.getByText("Users")).toBeInTheDocument();
    });

    it("navigates to the clicked admin path and closes the flyout", async () => {
      const user = userEvent.setup();
      render(<SidebarFlyout />);

      await user.click(screen.getByText("RBAC Configuration"));
      expect(mockNavigate).toHaveBeenCalledWith("/admin/rbac");
      expect(setFlyout).toHaveBeenCalledWith(null);
      expect(storeState.flyout).toBeNull();
    });

    it("renders the 'No admin pages available.' fallback when there are no items", () => {
      mockAdminItems = [];
      render(<SidebarFlyout />);
      expect(
        screen.getByText("No admin pages available."),
      ).toBeInTheDocument();
    });
  });
});
