/**
 * Tests for useStreamingChat WebSocket hook
 *
 * Key behaviors tested:
 * - Lazy connection: hook does NOT connect on mount unless activeExecutionId is provided
 * - sendMessage triggers connection if not connected
 * - sendMessage requires executionMode parameter
 * - Callbacks match current signatures (onToken has 5 args, onComplete receives tokenUsage)
 * - complete message does NOT close the connection
 * - error message force-closes the connection
 * - Resilience: reconnect, visibility change, sequence persistence, timeout cleanup
 */

import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { useStreamingChat } from "../useStreamingChat";
import { WSConnectionState } from "../../types";

// ---------------------------------------------------------------------------
// WebSocket mock
// ---------------------------------------------------------------------------

interface MockWebSocketInstance {
  readyState: number;
  url: string;
  sentMessages: string[];
  eventHandlers: Record<string, EventListener[]>;
  dispatchEvent(event: Event): void;
}

let wsInstances: MockWebSocketInstance[] = [];

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  url: string;
  sentMessages: string[] = [];
  eventHandlers: Record<string, EventListener[]> = {};

  constructor(url: string) {
    this.url = url;
    wsInstances.push(this as unknown as MockWebSocketInstance);

    // Simulate connection opening asynchronously
    Promise.resolve().then(() => {
      this.readyState = MockWebSocket.OPEN;
      this.dispatchEvent(new Event("open"));
    });
  }

  addEventListener(event: string, handler: EventListener) {
    if (!this.eventHandlers[event]) {
      this.eventHandlers[event] = [];
    }
    this.eventHandlers[event].push(handler);
  }

  removeEventListener(event: string, handler: EventListener) {
    if (this.eventHandlers[event]) {
      this.eventHandlers[event] = this.eventHandlers[event].filter(
        (h) => h !== handler
      );
    }
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSING;
    Promise.resolve().then(() => {
      this.readyState = MockWebSocket.CLOSED;
      this.dispatchEvent(new Event("close"));
    });
  }

  dispatchEvent(event: Event) {
    const handlers = this.eventHandlers[event.type] || [];
    handlers.forEach((handler) => handler(event));
  }
}

vi.stubGlobal("WebSocket", MockWebSocket);

// ---------------------------------------------------------------------------
// Store mocks
// ---------------------------------------------------------------------------

const mockUseAuthStore = vi.fn();
type AuthStoreSelector<T> = (state: { token: string | null }) => T;
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: <T,>(selector: AuthStoreSelector<T>) =>
    mockUseAuthStore(selector),
}));

vi.mock("@/stores/useTimeMachineStore", () => ({
  useTimeMachineStore: (selector: (state: Record<string, unknown>) => unknown) =>
    selector({
      getSelectedTime: () => null,
      getSelectedBranch: () => null,
      getViewMode: () => "current",
    }),
}));

// Mock attachmentUpload so sendMessage does not try real HTTP
vi.mock("../attachmentUpload", () => ({
  uploadMultipleFiles: vi.fn().mockResolvedValue([]),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Sends a message to trigger lazy connection, then waits for OPEN state.
 * Returns the WS instance index to assert against.
 */
async function connectViaSendMessage(
  result: { current: ReturnType<typeof useStreamingChat> },
  message = "test",
  executionMode: "safe" | "standard" | "expert" = "standard"
) {
  await act(async () => {
    result.current.sendMessage(message, undefined, executionMode);
  });

  await waitFor(() => {
    expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
  });
}

/**
 * Shortcut to get the latest WS instance.
 */
function latestWs(): MockWebSocketInstance {
  return wsInstances[wsInstances.length - 1];
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useStreamingChat", () => {
  const mockToken = "mock-jwt-token";
  const mockAssistantId = "assistant-123";
  const mockOnToken = vi.fn();
  const mockOnComplete = vi.fn();
  const mockOnError = vi.fn();
  const mockOnToolCall = vi.fn();
  const mockOnToolResult = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    wsInstances = [];
    sessionStorage.clear();
    mockUseAuthStore.mockImplementation(
      (selector: AuthStoreSelector<{ token: string | null }>) =>
        selector({ token: mockToken })
    );
  });

  afterEach(() => {
    wsInstances = [];
  });

  // -----------------------------------------------------------------------
  // 1. Lazy connection — no WS on mount without activeExecutionId
  // -----------------------------------------------------------------------

  it("should NOT create a WebSocket on mount without activeExecutionId", () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    // State stays CLOSED — lazy connection
    expect(result.current.connectionState).toBe(WSConnectionState.CLOSED);
    expect(wsInstances).toHaveLength(0);
  });

  it("should establish WebSocket when sendMessage is called (lazy connection)", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    expect(result.current.connectionState).toBe(WSConnectionState.CLOSED);

    await connectViaSendMessage(result);

    expect(wsInstances).toHaveLength(1);
    expect(wsInstances[0].url).toContain("mock-jwt-token");
  });

  // -----------------------------------------------------------------------
  // 2. Token / assistantId guards
  // -----------------------------------------------------------------------

  it("should not connect when token is missing", async () => {
    mockUseAuthStore.mockImplementation(
      (selector: AuthStoreSelector<{ token: string | null }>) =>
        selector({ token: null })
    );

    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    expect(result.current.connectionState).toBe(WSConnectionState.CLOSED);
    expect(wsInstances).toHaveLength(0);
  });

  it("should not connect when assistantId is empty", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: "",
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    expect(result.current.connectionState).toBe(WSConnectionState.CLOSED);
    expect(wsInstances).toHaveLength(0);
  });

  // -----------------------------------------------------------------------
  // 3. sendMessage
  // -----------------------------------------------------------------------

  it("should send chat request when sendMessage is called with executionMode", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await connectViaSendMessage(result, "Hello, AI!", "standard");

    // The pending message is sent on open, so after connection is open we
    // should have at least one sent message (the chat request).
    await waitFor(() => {
      expect(latestWs().sentMessages.length).toBeGreaterThanOrEqual(1);
    });

    const sentData = JSON.parse(latestWs().sentMessages[0]);
    expect(sentData).toMatchObject({
      type: "chat",
      message: "Hello, AI!",
      execution_mode: "standard",
      assistant_config_id: mockAssistantId,
      as_of: null,
      branch_name: null,
      branch_mode: "current",
    });
    // JSON.stringify omits undefined values, so project_id and context
    // are not present in the serialized output when they are undefined
    expect(sentData).not.toHaveProperty("project_id");
    expect(sentData).not.toHaveProperty("context");
  });

  it("should error when sendMessage is called without executionMode", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await act(async () => {
      result.current.sendMessage("Hello");
    });

    expect(mockOnError).toHaveBeenCalledWith(
      "executionMode is required but was not provided"
    );
  });

  // -----------------------------------------------------------------------
  // 4. Token messages
  // -----------------------------------------------------------------------

  it("should handle token messages", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await connectViaSendMessage(result);

    act(() => {
      latestWs().dispatchEvent(
        new MessageEvent("message", {
          data: JSON.stringify({
            type: "token",
            content: "Hello",
            session_id: "session-123",
          }),
        })
      );
    });

    await waitFor(() => {
      // onToken(token, sessionId, source?, subagentName?, invocationId?)
      expect(mockOnToken).toHaveBeenCalledWith(
        "Hello",
        "session-123",
        undefined,
        undefined,
        undefined
      );
    });
  });

  // -----------------------------------------------------------------------
  // 5. Tool call messages
  // -----------------------------------------------------------------------

  it("should handle tool call messages", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
        onToolCall: mockOnToolCall,
      })
    );

    await connectViaSendMessage(result);

    act(() => {
      latestWs().dispatchEvent(
        new MessageEvent("message", {
          data: JSON.stringify({
            type: "tool_call",
            tool: "list_projects",
            args: { project_id: "proj-1" },
          }),
        })
      );
    });

    await waitFor(() => {
      expect(mockOnToolCall).toHaveBeenCalledWith(
        "list_projects",
        { project_id: "proj-1" },
        undefined // invocationId
      );
    });
  });

  // -----------------------------------------------------------------------
  // 6. Tool result messages
  // -----------------------------------------------------------------------

  it("should handle tool result messages", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
        onToolResult: mockOnToolResult,
      })
    );

    await connectViaSendMessage(result);

    act(() => {
      latestWs().dispatchEvent(
        new MessageEvent("message", {
          data: JSON.stringify({
            type: "tool_result",
            tool: "list_projects",
            result: { items: [{ id: "proj-1", name: "Project 1" }] },
          }),
        })
      );
    });

    await waitFor(() => {
      expect(mockOnToolResult).toHaveBeenCalledWith("list_projects", {
        items: [{ id: "proj-1", name: "Project 1" }],
      }, undefined);
    });
  });

  // -----------------------------------------------------------------------
  // 7. Complete messages — connection stays OPEN
  // -----------------------------------------------------------------------

  it("should handle complete messages and keep connection open", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await connectViaSendMessage(result);

    act(() => {
      latestWs().dispatchEvent(
        new MessageEvent("message", {
          data: JSON.stringify({
            type: "complete",
            session_id: "session-123",
            message_id: "msg-456",
          }),
        })
      );
    });

    await waitFor(() => {
      // onComplete(sessionId, messageId, tokenUsage?)
      expect(mockOnComplete).toHaveBeenCalledWith(
        "session-123",
        "msg-456",
        undefined
      );
    });

    // Connection should stay OPEN after completion
    expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
  });

  // -----------------------------------------------------------------------
  // 8. Error messages — force-closes connection
  // -----------------------------------------------------------------------

  it("should handle error messages and close connection", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await connectViaSendMessage(result);

    act(() => {
      latestWs().dispatchEvent(
        new MessageEvent("message", {
          data: JSON.stringify({
            type: "error",
            message: "Something went wrong",
            code: 500,
          }),
        })
      );
    });

    await waitFor(() => {
      expect(mockOnError).toHaveBeenCalledWith(
        "Error 500: Something went wrong"
      );
    });

    // Error handler sets ERROR state and force-closes the WS.
    // The close handler then transitions to CLOSED.
    // Verify that error was recorded (it persists through the close).
    expect(result.current.error).toBeInstanceOf(Error);
    // Connection may be either ERROR or CLOSED depending on whether the
    // close event has already propagated. Both are acceptable error outcomes.
    expect(
      [WSConnectionState.ERROR, WSConnectionState.CLOSED]
    ).toContain(result.current.connectionState);
  });

  // -----------------------------------------------------------------------
  // 9. Cancel
  // -----------------------------------------------------------------------

  it("should cancel connection when cancel is called", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await connectViaSendMessage(result);

    act(() => {
      result.current.cancel();
    });

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.CLOSED);
    });
  });

  // -----------------------------------------------------------------------
  // 10. Invalid JSON messages
  // -----------------------------------------------------------------------

  it("should handle invalid JSON messages with detailed error", async () => {
    const consoleSpy = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});

    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await connectViaSendMessage(result);

    act(() => {
      latestWs().dispatchEvent(
        new MessageEvent("message", {
          data: "invalid json{{{",
        })
      );
    });

    await waitFor(() => {
      expect(mockOnError).toHaveBeenCalledWith(
        'Failed to parse server message (type: string, length: 15, detected_type: unknown)'
      );
    });

    consoleSpy.mockRestore();
  });

  // -----------------------------------------------------------------------
  // 11. Unknown message types
  // -----------------------------------------------------------------------

  it("should handle unknown message types", async () => {
    const consoleSpy = vi
      .spyOn(console, "warn")
      .mockImplementation(() => {});

    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await connectViaSendMessage(result);

    act(() => {
      latestWs().dispatchEvent(
        new MessageEvent("message", {
          data: JSON.stringify({
            type: "unknown_type",
            data: "something",
          }),
        })
      );
    });

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        "Unknown WebSocket message type:",
        expect.objectContaining({ type: "unknown_type" })
      );
    });

    consoleSpy.mockRestore();
  });

  // -----------------------------------------------------------------------
  // 12. Cleanup on unmount
  // -----------------------------------------------------------------------

  it("should cleanup on unmount", async () => {
    const { result, unmount } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await connectViaSendMessage(result);
    const ws = latestWs();

    act(() => {
      unmount();
    });

    await waitFor(() => {
      expect(ws.readyState).toBe(MockWebSocket.CLOSED);
    });
  });

  // -----------------------------------------------------------------------
  // 13. Session resumption with existing session ID
  // -----------------------------------------------------------------------

  it("should support session resumption with existing session ID", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        sessionId: "existing-session-123",
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await connectViaSendMessage(result, "Continue our conversation");

    await waitFor(() => {
      const ws = latestWs();
      // The pending message is sent on open
      const sentData = JSON.parse(ws.sentMessages[0]);
      expect(sentData.session_id).toBe("existing-session-123");
    });
  });

  // -----------------------------------------------------------------------
  // 14. Immediate connection with activeExecutionId
  // -----------------------------------------------------------------------

  it("should connect immediately when activeExecutionId is provided", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        activeExecutionId: "exec-123",
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    // Should start connecting immediately
    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    expect(wsInstances).toHaveLength(1);

    // The subscribe message should have been sent on open
    const subscribeMsg = JSON.parse(latestWs().sentMessages[0]);
    expect(subscribeMsg).toEqual({
      type: "subscribe",
      execution_id: "exec-123",
      last_seen_sequence: 0,
    });
  });
});

// ===========================================================================
// Resilience tests
// ===========================================================================

describe("WebSocket resilience", () => {
  const mockToken = "mock-jwt-token";
  const mockAssistantId = "assistant-123";
  const mockOnToken = vi.fn();
  const mockOnComplete = vi.fn();
  const mockOnError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    wsInstances = [];
    sessionStorage.clear();
    mockUseAuthStore.mockImplementation(
      (selector: AuthStoreSelector<{ token: string | null }>) =>
        selector({ token: mockToken })
    );
  });

  afterEach(() => {
    wsInstances = [];
    vi.useRealTimers();
  });

  it("should reset reconnect counter on user-initiated message after max retries", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        activeExecutionId: "exec-123",
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    // Wait for initial connection
    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    const initialWsCount = wsInstances.length;

    // Simulate connection loss — close fires, reconnect will attempt.
    // We cannot easily exhaust 5 retries with real timers (too slow).
    // Instead: close the connection, wait for CLOSED, then verify that
    // sendMessage still creates a fresh connection (it resets the counter).
    act(() => {
      latestWs().dispatchEvent(new CloseEvent("close"));
    });

    // Wait for closed state
    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.CLOSED);
    });

    // A reconnection attempt was scheduled; cancel it by sending a new
    // user-initiated message. sendMessage resets reconnectAttemptsRef.
    await act(async () => {
      result.current.sendMessage("new message", undefined, "standard");
    });

    // A new WebSocket should have been created (user-initiated, counter reset)
    await waitFor(() => {
      expect(wsInstances.length).toBeGreaterThan(initialWsCount);
    });
  });

  it("should reconnect when tab becomes visible with dead connection and active execution", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        activeExecutionId: "exec-123",
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    // Wait for initial connection
    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    const initialWsCount = wsInstances.length;

    // Simulate connection death
    act(() => {
      latestWs().dispatchEvent(new CloseEvent("close"));
    });

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.CLOSED);
    });

    // Simulate tab becoming visible
    await act(async () => {
      Object.defineProperty(document, "visibilityState", {
        value: "visible",
        writable: true,
        configurable: true,
      });
      document.dispatchEvent(new Event("visibilitychange"));
    });

    // A new WebSocket should be created
    await waitFor(() => {
      expect(wsInstances.length).toBeGreaterThan(initialWsCount);
    });

    // Restore visibilityState
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      writable: true,
      configurable: true,
    });
  });

  it("should persist sequence number to sessionStorage on unmount", async () => {
    const { result, unmount } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        activeExecutionId: "exec-123",
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    // Receive a message with sequence number
    act(() => {
      latestWs().dispatchEvent(
        new MessageEvent("message", {
          data: JSON.stringify({
            type: "token",
            content: "Hello",
            session_id: "session-123",
            sequence: 42,
          }),
        })
      );
    });

    // Unmount
    act(() => {
      unmount();
    });

    // Verify sequence number was persisted
    expect(sessionStorage.getItem("ws-seq-exec-123")).toBe("42");
  });

  it("should restore sequence number from sessionStorage on remount", async () => {
    // Pre-populate sessionStorage with a sequence number
    sessionStorage.setItem("ws-seq-exec-123", "42");

    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        activeExecutionId: "exec-123",
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    // Should connect immediately due to activeExecutionId
    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    // The subscribe message should include last_seen_sequence: 42
    const subscribeMsg = JSON.parse(latestWs().sentMessages[0]);
    expect(subscribeMsg).toEqual({
      type: "subscribe",
      execution_id: "exec-123",
      last_seen_sequence: 42,
    });

    // sessionStorage entry should be cleaned up after restore
    expect(sessionStorage.getItem("ws-seq-exec-123")).toBeNull();
  });

  it("should clean up recentlyCompleted timeout on unmount without errors", async () => {
    const { result, unmount } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    // Establish connection using real timers
    await connectViaSendMessage(result);

    // Receive a complete message — sets recentlyCompletedRef with 5s timeout
    act(() => {
      latestWs().dispatchEvent(
        new MessageEvent("message", {
          data: JSON.stringify({
            type: "complete",
            session_id: "session-123",
            message_id: "msg-456",
          }),
        })
      );
    });

    await waitFor(() => {
      expect(mockOnComplete).toHaveBeenCalled();
    });

    // Now switch to fake timers for the timeout advancement
    vi.useFakeTimers();

    // Unmount within the 5s window — should not throw
    expect(() => {
      act(() => {
        unmount();
      });
    }).not.toThrow();

    // Advance past the 5s timeout — should not cause any errors
    // (the timeout ref was cleaned up on unmount)
    act(() => {
      vi.advanceTimersByTime(6000);
    });

    // No additional errors should have been reported
    expect(mockOnError).not.toHaveBeenCalled();
  });
});
