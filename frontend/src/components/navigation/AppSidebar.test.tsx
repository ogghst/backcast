/**
 * AppSidebar tests.
 *
 * The shared `SidebarContent`/`SidebarFlyout` are mocked to isolate the rail's
 * own behavior (primary nav rendering, navigation, RBAC chat gate, entity gate,
 * active highlighting). Router hooks, permission, breakpoints, and the nav
 * store are mocked directly.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// --- Mocks --------------------------------------------------------------

const mockNavigate = vi.fn();
let mockPathname = "/";
let mockScreens: Record<string, boolean> = { md: true }; // desktop by default

vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ pathname: mockPathname, search: "" }),
}));

vi.mock("antd", async () => {
  const actual = await vi.importActual<typeof import("antd")>("antd");
  return {
    ...actual,
    Grid: {
      useBreakpoint: () => mockScreens,
    },
  };
});

let mockCan: (p: string) => boolean = () => true;
vi.mock("@/hooks/usePermission", () => ({
  usePermission: () => ({ can: mockCan, hasRole: () => false }),
}));

// Mock the nav store with mutable state. The store must expose state AND
// actions via the selector pattern (the component reads actions like
// `useNavigationStore((s) => s.setFlyout)`).
let storeState: {
  expanded: boolean;
  flyout: "chat" | "account" | "entity" | null;
  toggleExpanded: () => void;
  setFlyout: (f: "chat" | "account" | "entity" | null) => void;
};
const toggleExpanded = vi.fn(() => {
  storeState = { ...storeState, expanded: !storeState.expanded };
});
const setFlyout = vi.fn((f: "chat" | "account" | "entity" | null) => {
  storeState = { ...storeState, flyout: f };
});
storeState = { expanded: false, flyout: null, toggleExpanded, setFlyout };
vi.mock("@/stores/useNavigationStore", () => ({
  useNavigationStore: (selector: (s: typeof storeState) => unknown) =>
    selector(storeState),
}));

let mockEntityNav: { label: string; items: unknown[] } | null = null;
vi.mock("@/components/navigation/useEntityNav", () => ({
  useEntityNav: () => mockEntityNav,
}));

// Mock the heavy shared pieces so the rail is tested in isolation.
vi.mock("@/components/navigation/SidebarContent", () => ({
  SidebarContent: () => <div data-testid="sidebar-content" />,
}));
vi.mock("@/components/navigation/SidebarFlyout", () => ({
  SidebarFlyout: () => <div data-testid="sidebar-flyout" />,
}));

import { AppSidebar } from "./AppSidebar";

function resetState() {
  mockNavigate.mockClear();
  toggleExpanded.mockClear();
  setFlyout.mockClear();
  mockPathname = "/";
  mockScreens = { md: true };
  mockCan = () => true;
  storeState = { expanded: false, flyout: null, toggleExpanded, setFlyout };
  mockEntityNav = null;
}

describe("AppSidebar", () => {
  beforeEach(resetState);

  it("returns null on mobile (!screens.md)", () => {
    mockScreens = { md: false };
    const { container } = render(<AppSidebar />);
    expect(container.firstChild).toBeNull();
  });

  describe("desktop rail mode", () => {
    it("renders Dashboard and Projects rail buttons", () => {
      render(<AppSidebar />);
      expect(screen.getByRole("button", { name: "Dashboard" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Projects" })).toBeInTheDocument();
    });

    it("clicking Projects navigates to /projects", async () => {
      const user = userEvent.setup();
      render(<AppSidebar />);
      await user.click(screen.getByRole("button", { name: "Projects" }));
      expect(mockNavigate).toHaveBeenCalledWith("/projects");
    });

    it("hides the Chat rail button when the user lacks ai-chat permission", () => {
      mockCan = (p: string) => p !== "ai-chat";
      render(<AppSidebar />);
      expect(screen.queryByRole("button", { name: "Chat" })).toBeNull();
    });

    it("shows the Chat rail button when ai-chat is permitted", () => {
      render(<AppSidebar />);
      expect(screen.getByRole("button", { name: "Chat" })).toBeInTheDocument();
    });

    it("hides the entity rail button on a non-entity route", () => {
      mockEntityNav = null;
      render(<AppSidebar />);
      // No entity-specific labeled button (e.g. "Project") present.
      expect(screen.queryByRole("button", { name: "Project" })).toBeNull();
    });

    it("shows the entity rail button (labeled with the entity type) on an entity route", () => {
      mockEntityNav = { label: "WBS Element", items: [] };
      render(<AppSidebar />);
      expect(
        screen.getByRole("button", { name: "WBS Element" }),
      ).toBeInTheDocument();
    });

    it("toggling the Chat flyout calls setFlyout (opens when closed)", async () => {
      const user = userEvent.setup();
      render(<AppSidebar />);
      await user.click(screen.getByRole("button", { name: "Chat" }));
      expect(setFlyout).toHaveBeenCalledWith("chat");
    });

    // NOTE: there is intentionally NO in-sidebar expand/collapse control —
    // expand/collapse is owned by the header toggle in `AppLayout`, so nothing
    // sits under the account avatar. The Account rail button is the last rail
    // element (verified below).

    it("Account is the last rail button (no expand chevron under the avatar)", () => {
      render(<AppSidebar />);
      // No in-sidebar expand/collapse affordance exists.
      expect(screen.queryByRole("button", { name: "Expand sidebar" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Collapse sidebar" })).toBeNull();
      // …but the Account button is present (the bottom rail element).
      expect(screen.getByRole("button", { name: "Account" })).toBeInTheDocument();
    });

    it("clicking the Account avatar expands the sidebar (not a flyout)", async () => {
      const user = userEvent.setup();
      render(<AppSidebar />);
      await user.click(screen.getByRole("button", { name: "Account" }));
      // Expands the sidebar…
      expect(toggleExpanded).toHaveBeenCalled();
      // …and does NOT open an account flyout.
      expect(setFlyout).not.toHaveBeenCalled();
    });

    it("Dashboard button highlights when active (/)", () => {
      mockPathname = "/";
      render(<AppSidebar />);
      const dash = screen.getByRole("button", {
        name: "Dashboard",
      }) as HTMLButtonElement;
      // Active state is applied as an inline style on the rail button: a
      // 3px primary right-border. Assert it is present (vs. transparent when
      // inactive).
      expect(dash.style.borderRight).not.toBe("");
      expect(dash.style.borderRight).not.toBe("3px solid transparent");
    });

    it("Projects button is NOT active-highlighted on the Dashboard route", () => {
      mockPathname = "/";
      render(<AppSidebar />);
      const projects = screen.getByRole("button", {
        name: "Projects",
      }) as HTMLButtonElement;
      expect(projects.style.borderRight).toBe("3px solid transparent");
    });

    it("Projects button highlights when on /projects", () => {
      mockPathname = "/projects";
      render(<AppSidebar />);
      const projects = screen.getByRole("button", {
        name: "Projects",
      }) as HTMLButtonElement;
      expect(projects.style.borderRight).not.toBe("3px solid transparent");
    });
  });

  describe("desktop expanded mode", () => {
    it("renders the shared SidebarContent when expanded", () => {
      storeState = { expanded: true, flyout: null, toggleExpanded, setFlyout };
      render(<AppSidebar />);
      expect(screen.getByTestId("sidebar-content")).toBeInTheDocument();
      // Rail-only buttons are not rendered in expanded mode.
      expect(screen.queryByRole("button", { name: "Projects" })).toBeNull();
    });
  });
});
