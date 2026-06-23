/**
 * ChatInterface terminal-status reset test
 *
 * Verifies the latent terminal-event fix: when the WS sends an
 * `execution_status` event with status "stopped" or "error" (which the
 * backend's stop path emits WITHOUT a follow-up `complete`), ChatInterface
 * must reset the streaming UI just like handleComplete does. Without this,
 * a real Stop would hang the UI in the streaming state.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { App } from "antd";

// Capture the callbacks handed to useStreamingChat so the test can fire them.
let capturedCallbacks: {
  onExecutionStatus?: (executionId: string, status: string, sessionId: string) => void;
  onComplete?: (sessionId: string, messageId: string | null, tokenUsage?: unknown) => void;
} = {};

// Capture callbacks registered by the component under test via a
// callback-capturing factory.
vi.mock("../../api/useStreamingChat", () => ({
  useStreamingChat: (opts: Record<string, unknown>) => {
    capturedCallbacks = {
      onExecutionStatus: opts.onExecutionStatus as typeof capturedCallbacks.onExecutionStatus,
      onComplete: opts.onComplete as typeof capturedCallbacks.onComplete,
    };
    return {
      sendMessage: vi.fn(),
      sendApprovalResponse: vi.fn(),
      sendAskUserResponse: vi.fn(),
      cancel: vi.fn(),
      connectionState: "open" as const,
      error: null,
      isReplaying: false,
    };
  },
}));

vi.mock("../../api/useChatSessions", () => ({
  useChatMessages: () => ({ data: [], isLoading: false }),
  useDeleteSession: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("../../api/useChatSessionsPaginated", () => ({
  useChatSessionsPaginated: () => ({
    data: { sessions: [], has_more: false, total_count: 0 },
    isLoading: false,
    loadMore: vi.fn(),
    hasMore: false,
  }),
}));

vi.mock("../../api/useAgentExecutions", () => ({
  useStopExecution: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/features/ai/api/useAIAssistants", () => ({
  useAIAssistants: () => ({
    data: [{ id: "a1", name: "Assistant", is_active: true, agent_type: "main" }],
  }),
}));

vi.mock("@/hooks/useLastAssistantId", () => ({
  useLastAssistantId: () => ({ lastAssistantId: "a1", setLastAssistantId: vi.fn() }),
}));

// The Briefing components import a lot; stub them to keep the render light.
vi.mock("../BriefingRail", () => ({ BriefingRail: () => null }));
vi.mock("../BriefingRailToggleTab", () => ({ BriefingRailToggleTab: () => null }));
vi.mock("../BriefingPeekBar", () => ({ BriefingPeekBar: () => null }));
vi.mock("../WebSocketDebugPanel", () => ({
  WebSocketDebugPanel: () => null,
}));

import { ChatInterface } from "../ChatInterface";

function renderChat() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App>
        <BrowserRouter>
          <ChatInterface context={{ type: "general" }} />
        </BrowserRouter>
      </App>
    </QueryClientProvider>,
  );
}

describe("ChatInterface terminal-status reset", () => {
  beforeEach(() => {
    capturedCallbacks = {};
  });

  it("resets streaming UI when an execution_status 'stopped' event arrives", async () => {
    renderChat();

    // Sanity: default (non-streaming) input shows the Send affordance.
    expect(screen.getByRole("button", { name: "Send message" })).toBeInTheDocument();

    const onExecutionStatus = capturedCallbacks.onExecutionStatus;
    expect(onExecutionStatus).toBeDefined();

    // Simulate the backend stop path: a terminal status with NO complete event.
    onExecutionStatus!("exec-1", "stopped", "sess-1");

    // The streaming UI must be reset — the Send affordance should remain/be present
    // (i.e. the UI is NOT stuck in a streaming state waiting for a complete event).
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Send message" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Stop generation" })).not.toBeInTheDocument();
    });
  });

  it("resets streaming UI when an execution_status 'error' event arrives", async () => {
    renderChat();

    const onExecutionStatus = capturedCallbacks.onExecutionStatus;
    expect(onExecutionStatus).toBeDefined();

    onExecutionStatus!("exec-2", "error", "sess-2");

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Send message" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Stop generation" })).not.toBeInTheDocument();
    });
  });
});

describe("ChatInterface in-content toolbar", () => {
  beforeEach(() => {
    capturedCallbacks = {};
  });

  it("renders the Back button in the in-content toolbar", () => {
    // Validates the toolbar surgery: the Back button (ported from the retired
    // ChatSlimHeader) now renders in-content rather than via a header portal.
    renderChat();
    expect(screen.getByRole("button", { name: "Back" })).toBeInTheDocument();
  });
});
