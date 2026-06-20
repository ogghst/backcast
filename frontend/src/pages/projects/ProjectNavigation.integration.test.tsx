import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import { ProjectLayout } from "./ProjectLayout";
import { ProjectOverview } from "./ProjectOverview";
import { ProjectChangeOrdersPage } from "./ProjectChangeOrdersPage";

// Mock the hooks
vi.mock("@/features/projects/api/useProjects", () => ({
  useProject: () => ({
    data: {
      project_id: "123",
      code: "TEST-001",
      name: "Test Project",
      budget: 100000,
    },
    isLoading: false,
  }),
  useUpdateProject: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useDeleteProject: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

// Mock Can component
vi.mock("@/components/auth/Can", () => ({
  Can: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("@/features/wbs-elements/api/useWBSElements", () => ({
  useWBSElements: () => ({
    data: { items: [] },
    isLoading: false,
    refetch: vi.fn(),
  }),
  useCreateWBSElement: () => ({ mutateAsync: vi.fn() }),
  useUpdateWBSElement: () => ({ mutateAsync: vi.fn() }),
  useDeleteWBSElement: () => ({ mutate: vi.fn() }),
}));

vi.mock("@/hooks/useEntityHistory", () => ({
  useEntityHistory: () => ({
    data: [],
    isLoading: false,
  }),
}));

vi.mock("@/features/change-orders", () => ({
  ChangeOrderList: () => <div data-testid="change-order-list">Change Orders List</div>,
}));

// Mock TimeMachine context
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachineParams: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
  }),
  useTimeMachine: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
    isHistorical: false,
    invalidateQueries: vi.fn(),
  }),
  TimeMachineProvider: ({ children }: { children: React.ReactNode }) => children,
}));

describe("Project Navigation Integration", () => {
  /**
   * T-Integration-001: test_full_navigation_flow_with_tab_clicking
   *
   * Acceptance Criterion:
   * - User clicks tab → URL updates → content changes
   *
   * Purpose:
   * Verify the complete navigation flow when user clicks on tabs.
   *
   * Expected Behavior:
   * - Starting on overview tab
   * - Clicking Change Orders tab navigates to /projects/123/change-orders
   * - Page content changes to change orders view
   */
  it("test_full_navigation_flow_with_tab_clicking", async () => {
    // Arrange
    const user = userEvent.setup();
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    // Act - Start on overview page
    render(
      <QueryClientProvider client={queryClient}>
        <ConfigProvider>
          <MemoryRouter initialEntries={["/projects/123"]}>
            <Routes>
              <Route path="/projects/:projectId" element={<ProjectLayout />}>
                <Route index element={<ProjectOverview />} />
                <Route path="change-orders" element={<ProjectChangeOrdersPage />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </ConfigProvider>
      </QueryClientProvider>
    );

    // Wait for initial render
    await waitFor(() => {
      // "Project Details" appears as both breadcrumb crumb and PageHeader title
      expect(screen.getAllByText("Project Details").length).toBeGreaterThan(0);
    });

    // Click on Change Orders tab
    const changeOrdersTab = screen.getByRole("tab", { name: "Change Orders" });
    await user.click(changeOrdersTab);

    // Assert - Navigation occurred and content changed
    await waitFor(() => {
      expect(screen.getAllByText("Change Orders").length).toBeGreaterThan(0);
      expect(screen.getByTestId("change-order-list")).toBeInTheDocument();
    });
  });

  /**
   * T-Integration-002: test_direct_url_navigation_shows_correct_tab
   *
   * Acceptance Criterion:
   * - Direct URL navigation shows correct active tab
   *
   * Purpose:
   * Verify that navigating directly to a URL activates the correct tab.
   *
   * Expected Behavior:
   * - When navigating directly to /projects/123/change-orders
   * - Change Orders tab is active
   * - Change Orders content is shown
   */
  it("test_direct_url_navigation_shows_correct_tab", async () => {
    // Arrange & Act - Navigate directly to change orders page
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <ConfigProvider>
          <MemoryRouter initialEntries={["/projects/123/change-orders"]}>
            <Routes>
              <Route path="/projects/:projectId" element={<ProjectLayout />}>
                <Route index element={<ProjectOverview />} />
                <Route path="change-orders" element={<ProjectChangeOrdersPage />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </ConfigProvider>
      </QueryClientProvider>
    );

    // Assert - Change Orders tab should be active
    await waitFor(() => {
      const changeOrdersTab = screen.getByRole("tab", { name: "Change Orders" });
      expect(changeOrdersTab).toHaveAttribute("aria-selected", "true");

      const overviewTab = screen.getByRole("tab", { name: "Overview" });
      expect(overviewTab).toHaveAttribute("aria-selected", "false");

      expect(screen.getByTestId("change-order-list")).toBeInTheDocument();
    });
  });
});
