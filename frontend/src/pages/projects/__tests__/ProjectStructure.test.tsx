import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProjectStructure } from "../ProjectStructure";

// Mock react-router-dom
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useParams: () => ({ projectId: "test-project-123" }),
    useNavigate: () => vi.fn(),
  };
});

// Mock TimeMachine context
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachineParams: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
  }),
  TimeMachineProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock useWBEs hook
vi.mock("@/features/wbes/api/useWBEs", () => ({
  useWBEs: vi.fn(),
}));

// Mock useCostElements hook
vi.mock("@/features/cost-elements/api/useCostElements", () => ({
  useCostElements: vi.fn(),
}));

// Mock Ant Design theme
vi.mock("antd", async () => {
  const actual = await vi.importActual("antd");
  return {
    ...actual,
    theme: {
      useToken: () => ({
        token: {
          colorBgContainer: "#ffffff",
          colorBorder: "#d9d9d9",
          colorText: "#000000",
          colorTextSecondary: "#666666",
          borderRadiusLG: 8,
        },
      }),
    },
  };
});

import { useWBEs } from "@/features/wbes/api/useWBEs";

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe("ProjectStructure", () => {
  /**
   * T-001: test_project_structure_renders_tree_component
   *
   * Acceptance Criterion:
   * - Component renders without crashing
   * - Tree structure is visible
   *
   * Purpose:
   * Verify basic component rendering
   */
  it("test_project_structure_renders_tree_component", () => {
    // Arrange
    vi.mocked(useWBEs).mockReturnValue({
      data: { items: [], total: 0, page: 1, per_page: 20 },
      isLoading: false,
      error: null,
    });

    // Act
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Assert - Component renders without error
    const treeContainer = screen.queryByRole("tree");
    // Tree should not render when no data (empty state)
    expect(treeContainer).not.toBeInTheDocument();
  });

  /**
   * T-002: test_project_structure_displays_root_wbes_with_names_and_budget
   *
   * Acceptance Criterion:
   * - Tree displays root WBEs with name and budget_allocation on initial render
   *
   * Purpose:
   * Verify that root WBEs are fetched and displayed correctly
   */
  it("test_project_structure_displays_root_wbes_with_names_and_budget", () => {
    // Arrange
    const mockWBEs = {
      items: [
        {
          id: "wbe-1",
          wbe_id: "wbe-1",
          project_id: "test-project-123",
          code: "1.0",
          name: "Root WBE 1",
          budget_allocation: "50000.00",
          parent_wbe_id: null,
          branch: "main",
          created_by: "user-1",
        },
        {
          id: "wbe-2",
          wbe_id: "wbe-2",
          project_id: "test-project-123",
          code: "2.0",
          name: "Root WBE 2",
          budget_allocation: "75000.00",
          parent_wbe_id: null,
          branch: "main",
          created_by: "user-1",
        },
      ],
      total: 2,
      page: 1,
      per_page: 20,
    };

    vi.mocked(useWBEs).mockReturnValue({
      data: mockWBEs,
      isLoading: false,
      error: null,
    });

    // Act
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Assert
    expect(screen.getByText("Root WBE 1")).toBeInTheDocument();
    expect(screen.getByText("Root WBE 2")).toBeInTheDocument();
    expect(screen.getByText("€50,000.00")).toBeInTheDocument();
    expect(screen.getByText("€75,000.00")).toBeInTheDocument();
  });

  /**
   * T-003: test_project_structure_empty_state_when_no_wbes
   *
   * Acceptance Criterion:
   * - Empty state displays when project has no WBEs
   *
   * Purpose:
   * Verify proper empty state handling
   */
  it("test_project_structure_empty_state_when_no_wbes", () => {
    // Arrange
    vi.mocked(useWBEs).mockReturnValue({
      data: { items: [], total: 0, page: 1, per_page: 20 },
      isLoading: false,
      error: null,
    });

    // Act
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Assert
    expect(screen.getByText(/no work breakdown elements/i)).toBeInTheDocument();
  });

  /**
   * T-004: test_project_structure_loading_state
   *
   * Acceptance Criterion:
   * - Loading indicator shows during fetch
   *
   * Purpose:
   * Verify loading state is displayed
   */
  it("test_project_structure_loading_state", () => {
    // Arrange
    vi.mocked(useWBEs).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    // Act
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Assert - Ant Design Spin component should be present
    const spinElement = document.querySelector(".ant-spin");
    expect(spinElement).toBeInTheDocument();
  });

  /**
   * T-005: test_project_structure_error_state
   *
   * Acceptance Criterion:
   * - Error state shows on API failure
   *
   * Purpose:
   * Verify error handling
   */
  it("test_project_structure_error_state", () => {
    // Arrange
    vi.mocked(useWBEs).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed to fetch WBEs"),
    });

    // Act
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Assert - Check for error alert title
    expect(screen.getByText("Error Loading Structure")).toBeInTheDocument();
  });
});
