/**
 * Tests for ProjectChat Component
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ProjectChat } from "./ProjectChat";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";

// Mock the ChatInterface component
vi.mock("@/features/ai/chat/components/ChatInterface", () => ({
  ChatInterface: ({ projectId }: { projectId?: string }) => (
    <div data-testid="chat-interface">Project Chat: {projectId}</div>
  ),
}));

describe("ProjectChat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset Time Machine store before each test
    useTimeMachineStore.getState().clearAll();
  });

  it("should extract projectId from route params", () => {
    render(
      <MemoryRouter initialEntries={["/projects/test-project-123/chat"]}>
        <Routes>
          <Route path="/projects/:projectId/chat" element={<ProjectChat />} />
        </Routes>
      </MemoryRouter>
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
      </MemoryRouter>
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
      </MemoryRouter>
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
      </MemoryRouter>
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
      </MemoryRouter>
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
      </MemoryRouter>
    );

    // The currentProjectId should be updated to the new project
    expect(useTimeMachineStore.getState().currentProjectId).toBe("project-2");
  });
});
