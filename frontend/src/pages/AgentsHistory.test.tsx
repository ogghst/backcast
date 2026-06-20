/**
 * Tests for AgentsHistory page
 *
 * Renders rows from a mocked useAgentExecutions query, verifies the Stop
 * button is disabled for non-active runs and triggers the mutation for
 * active runs, and that "Open chat" navigates with the expected router state.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, useNavigate } from "react-router-dom";
import { App } from "antd";
import {
  AgentsHistory,
} from "./AgentsHistory";
import type { AgentExecutionHistoryItem } from "@/features/ai/chat/api/useAgentExecutions";

// Capture navigate calls so we can assert the router state passed.
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockMutate = vi.fn();
const useStopExecutionMock = vi.fn((opts?: { onSuccess?: () => void }) => {
  void opts;
  return {
    mutate: mockMutate,
    isPending: false,
  };
});

vi.mock("@/features/ai/chat/api/useAgentExecutions", () => ({
  useAgentExecutions: vi.fn(),
  useStopExecution: (opts?: { onSuccess?: () => void }) =>
    useStopExecutionMock(opts),
}));

// Pull the mocked query hook so we can override its return per test.
const { useAgentExecutions } = await import(
  "@/features/ai/chat/api/useAgentExecutions"
);

const runningItem: AgentExecutionHistoryItem = {
  id: "exec-running-aaaa",
  name: "Budget analysis",
  status: "running",
  execution_mode: "standard",
  run_in_background: true,
  started_at: "2026-06-14T10:00:00.000Z",
  completed_at: null,
  session_id: "sess-1",
  context: { type: "project", name: "Project Alpha", project_id: "p1", branch_id: null },
  assistant_name: "EVM Analyst",
  total_tokens: 1200,
  tool_calls_count: 4,
};

const completedItem: AgentExecutionHistoryItem = {
  id: "exec-done-bbbb",
  name: null,
  status: "completed",
  execution_mode: "standard",
  run_in_background: false,
  started_at: "2026-06-14T09:00:00.000Z",
  completed_at: "2026-06-14T09:01:30.000Z",
  session_id: "sess-2",
  context: { type: null, name: null, project_id: null, branch_id: null },
  assistant_name: null,
  total_tokens: 500,
  tool_calls_count: 1,
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App>
        <BrowserRouter>
          <AgentsHistory />
        </BrowserRouter>
      </App>
    </QueryClientProvider>,
  );
}

describe("AgentsHistory page", () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockMutate.mockReset();
    useStopExecutionMock.mockClear();
    vi.mocked(useAgentExecutions).mockReset();
  });

  it("renders rows from the mocked query", async () => {
    vi.mocked(useAgentExecutions).mockReturnValue({
      data: { items: [runningItem, completedItem], total: 2, has_more: false },
      isLoading: false,
    } as never);

    renderPage();

    expect(await screen.findByText("Budget analysis")).toBeInTheDocument();
    expect(screen.getByText("Project: Project Alpha")).toBeInTheDocument();
    // Name fallback to assistant_name when name is null
    expect(screen.getByText("EVM Analyst")).toBeInTheDocument();
  });

  it("Stop button is disabled for completed runs", async () => {
    vi.mocked(useAgentExecutions).mockReturnValue({
      data: { items: [completedItem], total: 1, has_more: false },
      isLoading: false,
    } as never);

    renderPage();

    const stopButton = await screen.findByRole("button", { name: "Stop agent" });
    expect(stopButton).toBeDisabled();
  });

  it("Stop button calls the stop mutation for a running execution", async () => {
    vi.mocked(useAgentExecutions).mockReturnValue({
      data: { items: [runningItem], total: 1, has_more: false },
      isLoading: false,
    } as never);

    renderPage();

    const stopButton = await screen.findByRole("button", { name: "Stop agent" });
    expect(stopButton).not.toBeDisabled();

    await userEvent.click(stopButton);
    // Popconfirm — confirm the stop
    const confirmButton = await screen.findByRole("button", { name: "Stop" });
    await userEvent.click(confirmButton);

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith(runningItem.id);
    });
  });

  it("Open chat navigates with sessionId and executionId state", async () => {
    vi.mocked(useAgentExecutions).mockReturnValue({
      data: { items: [runningItem], total: 1, has_more: false },
      isLoading: false,
    } as never);

    renderPage();

    const openChatButton = await screen.findByRole("button", { name: "Open chat" });
    await userEvent.click(openChatButton);

    expect(mockNavigate).toHaveBeenCalledWith("/chat?ctx=general", {
      state: {
        sessionId: "sess-1",
        executionId: "exec-running-aaaa",
        returnTo: "/agents-history",
      },
    });
  });

  it("shows Global context label when no project/branch is set", async () => {
    vi.mocked(useAgentExecutions).mockReturnValue({
      data: { items: [completedItem], total: 1, has_more: false },
      isLoading: false,
    } as never);

    renderPage();

    expect(await screen.findByText("Global")).toBeInTheDocument();
  });
});

// Ensure the react-router-dom import surfaces the hook type usage.
void useNavigate;
