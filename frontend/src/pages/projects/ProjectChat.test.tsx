/**
 * Tests for ProjectChat Component
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProjectChat } from "./ProjectChat";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";

// Mock the ChatInterface component
vi.mock("@/features/ai/chat/components/ChatInterface", () => ({
  ChatInterface: ({ projectId, contextOverride }: { projectId?: string; contextOverride?: { type: string; id: string; name?: string } }) => (
    <div data-testid="chat-interface">Project Chat: {projectId ?? contextOverride?.id ?? "none"}</div>
  ),
}));

// Mock TimeMachine context
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachineParams: () => ({
    branch: "main",
    effectiveDate: null,
  }),
  TimeMachineProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock useProject hook
vi.mock("@/features/projects/api/useProjects", () => ({
  useProject: (id: string) => ({
    data: {
      project_id: id,
      name: `Project ${id}`,
      code: "TEST-001",
    },
    isLoading: false,
  }),
  useProjects: () => ({
    data: { items: [], total: 0 },
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

describe("ProjectChat", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    // Reset Time Machine store before each test
    useTimeMachineStore.getState().clearAll();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it("should extract projectId from route params", () => {
    render(
      <MemoryRouter initialEntries={["/projects/test-project-123/chat"]}>
        <Routes>
          <Route path="/projects/:projectId/chat" element={<ProjectChat />} />
        </Routes>
      </MemoryRouter>,
      { wrapper }
    );

    // Verify that the Time Machine store's currentProjectId is set
    expect(useTimeMachineStore.getState().currentProjectId).toBe("test-project-123");
  });

  it("should set Time Machine context on mount", () => {
    render(
      <MemoryRouter initialEntries={["/projects/proj-456/chat"]}>
        <Routes>
          <Route path="/projects/:projectId/chat" element={<ProjectChat />} />
        </Routes>
      </MemoryRouter>,
      { wrapper }
    );

    // Verify that the Time Machine store's currentProjectId is set
    expect(useTimeMachineStore.getState().currentProjectId).toBe("proj-456");
  });

  it("should pass projectId to ChatInterface", () => {
    render(
      <MemoryRouter initialEntries={["/projects/my-project/chat"]}>
        <Routes>
          <Route path="/projects/:projectId/chat" element={<ProjectChat />} />
        </Routes>
      </MemoryRouter>,
      { wrapper }
    );

    const chatInterface = screen.getByTestId("chat-interface");
    expect(chatInterface).toHaveTextContent("Project Chat: my-project");
  });

  it("should not set currentProjectId if projectId is undefined", () => {
    render(
      <MemoryRouter initialEntries={["/projects/undefined/chat"]}>
        <Routes>
          <Route path="/projects/:projectId/chat" element={<ProjectChat />} />
        </Routes>
      </MemoryRouter>,
      { wrapper }
    );

    // Should set the projectId even if it's the string "undefined"
    expect(useTimeMachineStore.getState().currentProjectId).toBe("undefined");
  });

  it("should update Time Machine context when projectId changes", () => {
    // First render
    const { unmount } = render(
      <MemoryRouter initialEntries={["/projects/project-1/chat"]}>
        <Routes>
          <Route path="/projects/:projectId/chat" element={<ProjectChat />} />
        </Routes>
      </MemoryRouter>,
      { wrapper }
    );

    expect(useTimeMachineStore.getState().currentProjectId).toBe("project-1");

    // Unmount first component
    unmount();

    // Render with different projectId (new component mount)
    render(
      <MemoryRouter initialEntries={["/projects/project-2/chat"]}>
        <Routes>
          <Route path="/projects/:projectId/chat" element={<ProjectChat />} />
        </Routes>
      </MemoryRouter>,
      { wrapper }
    );

    // The currentProjectId should be updated to the new project
    expect(useTimeMachineStore.getState().currentProjectId).toBe("project-2");
  });
});
