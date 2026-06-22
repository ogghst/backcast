import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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
   * T-Integration-001: test_overview_route_renders_project_content
   *
   * Purpose:
   * Verify the index route renders ProjectOverview content via the layout
   * Outlet. Entity-detail navigation is sidebar-owned (Phase 3 nav redesign),
   * so there is no in-page tab strip to click; this test asserts the Outlet
   * wiring still delivers the correct child content per route.
   *
   * Expected Behavior:
   * - On /projects/123, ProjectOverview content renders
   * - No in-page navigation tabs are present
   */
  it("test_overview_route_renders_project_content", async () => {
    // Arrange
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

    // Assert - overview content renders via the Outlet
    await waitFor(() => {
      expect(screen.getAllByText("Project Details").length).toBeGreaterThan(0);
    });

    // Assert - no in-page tab strip (nav is sidebar-owned)
    expect(screen.queryByRole("tab", { name: "Change Orders" })).not.toBeInTheDocument();
  });

  /**
   * T-Integration-002: test_direct_url_navigation_renders_correct_content
   *
   * Purpose:
   * Verify that navigating directly to a child URL renders the correct child
   * content via the layout Outlet.
   *
   * Expected Behavior:
   * - When navigating directly to /projects/123/change-orders
   * - Change Orders content is shown
   * - No in-page tab strip is present
   */
  it("test_direct_url_navigation_renders_correct_content", async () => {
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

    // Assert - change orders content rendered via the Outlet
    await waitFor(() => {
      expect(screen.getByTestId("change-order-list")).toBeInTheDocument();
    });

    // Assert - no in-page tab strip (nav is sidebar-owned)
    expect(screen.queryByRole("tab", { name: "Change Orders" })).not.toBeInTheDocument();
  });
});
