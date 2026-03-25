import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProjectOverview } from "./ProjectOverview";
import { ConfigProvider } from "antd";

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

vi.mock("@/features/wbes/api/useWBEs", () => ({
  useWBEs: () => ({
    data: { items: [] },
    isLoading: false,
    refetch: vi.fn(),
  }),
  useCreateWBE: () => ({ mutateAsync: vi.fn() }),
  useUpdateWBE: () => ({ mutateAsync: vi.fn() }),
  useDeleteWBE: () => ({ mutate: vi.fn() }),
}));

vi.mock("@/hooks/useEntityHistory", () => ({
  useEntityHistory: () => ({
    data: [],
    isLoading: false,
  }),
}));

// Mock Can component to always render children
vi.mock("@/components/auth/Can", () => ({
  Can: ({ children }: { children: React.ReactNode }) => children,
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const createWrapper = () => {
  const queryClient = createTestQueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider>
        <MemoryRouter initialEntries={["/projects/123"]}>{children}</MemoryRouter>
      </ConfigProvider>
    </QueryClientProvider>
  );
};

describe("ProjectOverview", () => {
  /**
   * T-Overview-001: test_project_overview_renders_project_details_and_wbes
   *
   * Acceptance Criterion:
   * - ProjectOverview renders project summary and root WBEs
   * - Does NOT render change orders card (moved to separate page)
   *
   * Purpose:
   * Verify that ProjectOverview displays the expected content
   * and that change orders are not displayed inline.
   *
   * Expected Behavior:
   * - Renders page title "Project Details"
   * - Renders "Root Work Breakdown Elements" card
   * - Does NOT render "Change Orders" card
   */
  it("test_project_overview_renders_project_details_and_wbes", () => {
    // Arrange & Act
    const Wrapper = createWrapper();
    render(<ProjectOverview />, { wrapper: Wrapper });

    // Assert
    expect(screen.getByText("Project Details")).toBeInTheDocument();
    expect(screen.getByText("Root Work Breakdown Elements")).toBeInTheDocument();
    // Change Orders card should NOT be present
    expect(screen.queryByText("Change Orders")).not.toBeInTheDocument();
  });
});
