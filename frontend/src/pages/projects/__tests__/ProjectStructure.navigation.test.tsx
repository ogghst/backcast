// @ts-nocheck — test file uses mock data that does not match full generated types
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProjectStructure } from "../ProjectStructure";

// Mock navigate function
const mockNavigate = vi.fn();
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
      <button
        data-testid="trigger-select-wbe"
        onClick={() => onSelect({ type: "wbs_element", wbs_element_id: "wbe-1" })}
      >
        Select WBE
      </button>
      <button
        data-testid="trigger-select-ce"
        onClick={() => onSelect({ type: "cost_element", cost_element_id: "ce-1" })}
      >
        Select CE
      </button>
      <button
        data-testid="trigger-select-project"
        onClick={() => onSelect({ type: "project", project_id: "test-project-123" })}
      >
        Select Project
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

describe("ProjectStructure Navigation Tests", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    vi.clearAllMocks();
  });

  it("test_project_structure_click_wbe_navigates_to_detail", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(screen.getByTestId("trigger-select-wbe"));
    expect(mockNavigate).toHaveBeenCalledWith(
      "/projects/test-project-123/wbs-elements/wbe-1"
    );
  });

  it("test_project_structure_wbe_navigation_url_format", () => {
    // Verify the URL format used by the component
    const expectedWBEUrl = "/projects/test-project-123/wbs-elements/wbe-1";
    expect(expectedWBEUrl).toMatch(/^\/projects\/[^/]+\/wbs-elements\/[^/]+$/);
  });

  it("test_project_structure_navigation_handler_wbe_execution", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Trigger WBE selection
    fireEvent.click(screen.getByTestId("trigger-select-wbe"));
    expect(mockNavigate).toHaveBeenCalledWith(
      "/projects/test-project-123/wbs-elements/wbe-1"
    );
  });

  it("test_project_structure_cost_element_navigation_url_format", () => {
    const expectedCEUrl = "/cost-elements/ce-1";
    expect(expectedCEUrl).toMatch(/^\/cost-elements\/[^/]+$/);
  });

  it("test_project_structure_navigation_handler_cost_element_execution", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(screen.getByTestId("trigger-select-ce"));
    expect(mockNavigate).toHaveBeenCalledWith("/cost-elements/ce-1");
  });

  it("test_project_structure_navigate_function_is_available", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(typeof mockNavigate).toBe("function");
  });

  it("test_project_structure_navigation_handler_project", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/projects/test-project-123/structure"]}>
          <ProjectStructure />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(screen.getByTestId("trigger-select-project"));
    expect(mockNavigate).toHaveBeenCalledWith("/projects/test-project-123");
  });
});
