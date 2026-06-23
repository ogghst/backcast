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
let mockCanAny: (perms: string[]) => boolean = () => true;
vi.mock("@/hooks/usePermission", () => ({
  usePermission: () => ({ can: mockCan, canAny: mockCanAny, hasRole: () => false }),
}));

// The effective chat context is serialized into the /chat nav URL. Default to
// general; per-test overrides scope it (e.g. to a project).
let mockEffectiveCtx: {
  type: "general" | "project" | "wbe" | "cost_element" | "work_package";
  id?: string;
  project_id?: string;
} = { type: "general" };
vi.mock("@/hooks/navigation/useEffectiveChatContext", () => ({
  useEffectiveChatContext: () => mockEffectiveCtx,
}));

// The Agents rail button polls running executions. Default to 0 (badge hidden).
let mockRunningCount = 0;
vi.mock("@/features/ai/chat/api/useAgentExecutions", () => ({
  useRunningExecutionsCount: () => ({ data: mockRunningCount }),
}));

// Mock the nav store with mutable state. The store must expose state AND
// actions via the selector pattern (the component reads actions like
// `useNavigationStore((s) => s.setFlyout)`).
let storeState: {
  expanded: boolean;
  flyout: "account" | "entity" | null;
  toggleExpanded: () => void;
  setFlyout: (f: "account" | "entity" | null) => void;
};
const toggleExpanded = vi.fn(() => {
  storeState = { ...storeState, expanded: !storeState.expanded };
});
const setFlyout = vi.fn((f: "account" | "entity" | null) => {
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
  mockCanAny = () => true;
  mockRunningCount = 0;
  storeState = { expanded: false, flyout: null, toggleExpanded, setFlyout };
  mockEntityNav = null;
  mockEffectiveCtx = { type: "general" };
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

    it("clicking Chat navigates to /chat with the serialized ctx and returnTo state", async () => {
      const user = userEvent.setup();
      render(<AppSidebar />);
      await user.click(screen.getByRole("button", { name: "Chat" }));
      expect(mockNavigate).toHaveBeenCalledWith("/chat?ctx=general", {
        state: { returnTo: "/" },
      });
      expect(setFlyout).not.toHaveBeenCalled();
    });

    it("clicking Chat on a project route carries the project ctx in the URL", async () => {
      mockPathname = "/projects/p1";
      mockEffectiveCtx = { type: "project", id: "p1", project_id: "p1" };
      const user = userEvent.setup();
      render(<AppSidebar />);
      await user.click(screen.getByRole("button", { name: "Chat" }));
      expect(mockNavigate).toHaveBeenCalledWith("/chat?ctx=project:p1", {
        state: { returnTo: "/projects/p1" },
      });
    });

    it("clicking Chat on a wbs-element route carries the wbe ctx in the URL", async () => {
      mockPathname = "/projects/p1/wbs-elements/w1";
      mockEffectiveCtx = { type: "wbe", id: "w1", project_id: "p1" };
      const user = userEvent.setup();
      render(<AppSidebar />);
      await user.click(screen.getByRole("button", { name: "Chat" }));
      expect(mockNavigate).toHaveBeenCalledWith("/chat?ctx=wbe:w1&p=p1", {
        state: { returnTo: "/projects/p1/wbs-elements/w1" },
      });
    });

    it("clicking Chat on a work-package route carries the work_package ctx in the URL", async () => {
      mockPathname = "/projects/p1/work-packages/wp1";
      mockEffectiveCtx = { type: "work_package", id: "wp1", project_id: "p1" };
      const user = userEvent.setup();
      render(<AppSidebar />);
      await user.click(screen.getByRole("button", { name: "Chat" }));
      expect(mockNavigate).toHaveBeenCalledWith(
        "/chat?ctx=work_package:wp1&p=p1",
        { state: { returnTo: "/projects/p1/work-packages/wp1" } },
      );
    });

    it("clicking Chat while already on /chat is a no-op", async () => {
      mockPathname = "/chat";
      const user = userEvent.setup();
      render(<AppSidebar />);
      await user.click(screen.getByRole("button", { name: "Chat" }));
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    describe("Agents rail button", () => {
      it("is shown when the user has ai-chat (and lacks agent-schedule-manage) and navigates to /agents-history", async () => {
        // ai-chat yes, agent-schedule-manage no → chat-only destination.
        mockCan = (p: string) => p === "ai-chat";
        mockCanAny = (perms: string[]) => perms.includes("ai-chat");
        const user = userEvent.setup();
        render(<AppSidebar />);
        await user.click(screen.getByRole("button", { name: "Agents" }));
        expect(mockNavigate).toHaveBeenCalledWith("/agents-history");
      });

      it("navigates to /admin/agent-schedules when the user has agent-schedule-manage", async () => {
        mockCan = (p: string) => p === "agent-schedule-manage";
        mockCanAny = (perms: string[]) => perms.includes("agent-schedule-manage");
        const user = userEvent.setup();
        render(<AppSidebar />);
        await user.click(screen.getByRole("button", { name: "Agents" }));
        expect(mockNavigate).toHaveBeenCalledWith("/admin/agent-schedules");
      });

      it("is hidden for a viewer (neither permission)", () => {
        mockCan = () => false;
        mockCanAny = () => false;
        render(<AppSidebar />);
        expect(screen.queryByRole("button", { name: "Agents" })).toBeNull();
      });

      it("is active-highlighted when on /admin/agent-schedules", () => {
        mockPathname = "/admin/agent-schedules";
        render(<AppSidebar />);
        const agents = screen.getByRole("button", {
          name: "Agents",
        }) as HTMLButtonElement;
        expect(agents.style.borderRight).not.toBe("3px solid transparent");
      });

      it("is active-highlighted when on /agents-history", () => {
        mockPathname = "/agents-history";
        render(<AppSidebar />);
        const agents = screen.getByRole("button", {
          name: "Agents",
        }) as HTMLButtonElement;
        expect(agents.style.borderRight).not.toBe("3px solid transparent");
      });
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
