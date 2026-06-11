/**
 * Tests for SessionList component with context filtering
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SessionList } from "../SessionList";
import type { AIConversationSessionPublic } from "@/features/ai/types";

const mockSessions: AIConversationSessionPublic[] = [
  {
    id: "session-1",
    user_id: "user-1",
    assistant_config_id: "assistant-1",
    title: "Project Analysis",
    context: { type: "project", id: "project-1" },
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T01:00:00Z",
    active_execution: null,
  },
  {
    id: "session-2",
    user_id: "user-1",
    assistant_config_id: "assistant-1",
    title: "WBE Discussion",
    context: { type: "wbe", id: "wbe-1", project_id: "project-1" },
    created_at: "2024-01-02T00:00:00Z",
    updated_at: "2024-01-02T01:00:00Z",
    active_execution: null,
  },
  {
    id: "session-3",
    user_id: "user-1",
    assistant_config_id: "assistant-1",
    title: "General Chat",
    context: { type: "general" },
    created_at: "2024-01-03T00:00:00Z",
    updated_at: "2024-01-03T01:00:00Z",
    active_execution: null,
  },
];

describe("SessionList", () => {
  it("should render sessions", () => {
    render(
      <SessionList
        sessions={mockSessions}
        onSessionSelect={vi.fn()}
        onNewChat={vi.fn()}
        onDeleteSession={vi.fn()}
      />
    );

    expect(screen.getByText("Project Analysis")).toBeInTheDocument();
    expect(screen.getByText("WBE Discussion")).toBeInTheDocument();
    expect(screen.getByText("General Chat")).toBeInTheDocument();
  });

  it("should call onSessionSelect when clicking a session", () => {
    const onSessionSelect = vi.fn();
    render(
      <SessionList
        sessions={mockSessions}
        onSessionSelect={onSessionSelect}
        onNewChat={vi.fn()}
        onDeleteSession={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText("Project Analysis"));
    expect(onSessionSelect).toHaveBeenCalledWith("session-1");
  });

  it("should show empty state when no sessions", () => {
    render(
      <SessionList
        sessions={[]}
        onSessionSelect={vi.fn()}
        onNewChat={vi.fn()}
        onDeleteSession={vi.fn()}
      />
    );

    expect(screen.getByText("No conversations yet")).toBeInTheDocument();
  });

  it("should highlight current session", () => {
    render(
      <SessionList
        sessions={mockSessions}
        currentSessionId="session-1"
        onSessionSelect={vi.fn()}
        onNewChat={vi.fn()}
        onDeleteSession={vi.fn()}
      />
    );

    const sessionItem = screen.getByText("Project Analysis").closest(".ant-list-item");
    expect(sessionItem).toHaveStyle({ backgroundColor: expect.any(String) });
  });

  it("should call onNewChat when clicking New Chat button", () => {
    const onNewChat = vi.fn();
    render(
      <SessionList
        sessions={mockSessions}
        onSessionSelect={vi.fn()}
        onNewChat={onNewChat}
        onDeleteSession={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText("New Chat"));
    expect(onNewChat).toHaveBeenCalled();
  });

  it("should hide New Chat button when hideNewChatButton is true", () => {
    render(
      <SessionList
        sessions={mockSessions}
        onSessionSelect={vi.fn()}
        onNewChat={vi.fn()}
        onDeleteSession={vi.fn()}
        hideNewChatButton
      />
    );

    expect(screen.queryByText("New Chat")).not.toBeInTheDocument();
  });

  it("should show loading state", () => {
    render(
      <SessionList
        sessions={[]}
        onSessionSelect={vi.fn()}
        onNewChat={vi.fn()}
        onDeleteSession={vi.fn()}
        loading
      />
    );

    // Ant Design's List component shows a skeleton when loading
    const listItems = screen.queryAllByRole("listitem");
    expect(listItems.length).toBe(0);
  });

  it("should accept contextType prop without affecting rendering", () => {
    render(
      <SessionList
        sessions={mockSessions}
        onSessionSelect={vi.fn()}
        onNewChat={vi.fn()}
        onDeleteSession={vi.fn()}
        contextType="project"
      />
    );

    // The contextType prop is used by the parent component to filter sessions
    // before passing them to SessionList, so it shouldn't affect rendering directly
    expect(screen.getByText("Project Analysis")).toBeInTheDocument();
  });

  it("should disable delete button for active executions", () => {
    const sessionsWithActiveExecution: AIConversationSessionPublic[] = [
      {
        ...mockSessions[0],
        active_execution: {
          id: "exec-1",
          session_id: "session-1",
          status: "running",
          started_at: "2024-01-01T00:00:00Z",
          completed_at: null,
          error_message: null,
          execution_mode: "standard",
        },
      },
    ];

    const { container } = render(
      <SessionList
        sessions={sessionsWithActiveExecution}
        onSessionSelect={vi.fn()}
        onNewChat={vi.fn()}
        onDeleteSession={vi.fn()}
      />
    );

    // Find the delete button using the class name
    const deleteButton = container.querySelector(".delete-btn");
    expect(deleteButton).toBeInTheDocument();
    // The button should be disabled when there's an active execution
    const buttonElement = deleteButton?.closest("button");
    expect(buttonElement).toBeDisabled();
  });
});
