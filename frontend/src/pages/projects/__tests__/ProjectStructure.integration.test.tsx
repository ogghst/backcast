// @ts-nocheck — test file uses mock data that does not match full generated types
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProjectStructure } from "../ProjectStructure";

// Mock navigate function
const mockNavigate = vi.fn();

// Mock react-router-dom
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useParams: () => ({ projectId: "test-project-123" }),
    useNavigate: () => mockNavigate,
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

// Mock ProjectTree component
vi.mock("@/components/hierarchy/ProjectTree", () => ({
  ProjectTree: ({ projectId, onSelect }: { projectId: string; onSelect: (node: unknown) => void }) => (
    <div data-testid="project-tree" data-project-id={projectId}>
      <div data-testid="tree-node-project">Test Project Node</div>
      <div data-testid="tree-node-wbe">WBS Element Node</div>
      <button
        data-testid="trigger-select-project"
        onClick={() => onSelect({ type: "project", project_id: projectId })}
      >
        Select Project
      </button>
      <button
        data-testid="trigger-select-wbe"
        onClick={() => onSelect({ type: "wbs_element", wbs_element_id: "wbe-1" })}
      >
        Select WBE
      </button>
      <button
        data-testid="trigger-select-cost-element"
        onClick={() => onSelect({ type: "cost_element", cost_element_id: "ce-1" })}
      >
        Select Cost Element
      </button>
    </div>
  ),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe("ProjectStructure Integration Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Test that ProjectStructure renders with ProjectTree component
   */
  it("renders ProjectStructure with tree component", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Card title should be rendered
    expect(screen.getByText("Project Structure")).toBeInTheDocument();
    // ProjectTree mock should be rendered
    expect(screen.getByTestId("project-tree")).toBeInTheDocument();
    expect(screen.getByTestId("project-tree")).toHaveAttribute("data-project-id", "test-project-123");
  });

  /**
   * Test that ProjectStructure passes projectId to ProjectTree
   */
  it("passes projectId to ProjectTree", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByTestId("project-tree")).toHaveAttribute("data-project-id", "test-project-123");
  });

  /**
   * Test navigation on select - WBE node
   */
  it("calls navigate when WBE node is selected", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Click to trigger WBE selection
    screen.getByTestId("trigger-select-wbe").click();
    expect(mockNavigate).toHaveBeenCalledWith("/projects/test-project-123/wbs-elements/wbe-1");
  });

  /**
   * Test navigation on select - Cost Element node
   */
  it("calls navigate when Cost Element node is selected", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Click to trigger Cost Element selection
    screen.getByTestId("trigger-select-cost-element").click();
    expect(mockNavigate).toHaveBeenCalledWith("/cost-elements/ce-1");
  });

  /**
   * Test navigation on select - Project node
   */
  it("calls navigate when Project node is selected", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Click to trigger project selection
    screen.getByTestId("trigger-select-project").click();
    expect(mockNavigate).toHaveBeenCalledWith("/projects/test-project-123");
  });
});
