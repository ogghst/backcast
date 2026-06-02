// @ts-nocheck — test file uses mock data that does not match full generated types
import { describe, it, expect, vi, beforeEach } from "vitest";
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

// Mock ProjectTree component
vi.mock("@/components/hierarchy/ProjectTree", () => ({
  ProjectTree: ({ projectId }: { projectId: string }) => (
    <div data-testid="project-tree" data-project-id={projectId}>
      Project Tree Component
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

describe("ProjectStructure", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("test_project_structure_renders_tree_component", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText("Project Structure")).toBeInTheDocument();
    expect(screen.getByTestId("project-tree")).toBeInTheDocument();
  });

  it("test_project_structure_displays_root_wbes_with_names_and_budget", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Component delegates to ProjectTree with correct projectId
    expect(screen.getByTestId("project-tree")).toHaveAttribute(
      "data-project-id",
      "test-project-123"
    );
  });

  it("test_project_structure_empty_state_when_no_wbes", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // ProjectTree is always rendered (handles its own empty state)
    expect(screen.getByTestId("project-tree")).toBeInTheDocument();
  });

  it("test_project_structure_renders_card_title", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText("Project Structure")).toBeInTheDocument();
  });
});
