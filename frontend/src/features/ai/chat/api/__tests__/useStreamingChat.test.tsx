/**
 * Tests for useStreamingChat WebSocket hook
 */

import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { useStreamingChat } from "../useStreamingChat";
import { WSConnectionState } from "../../types";

// Track WebSocket instances
interface MockWebSocketInstance {
  readyState: number;
  url: string;
  sentMessages: string[];
  eventHandlers: Record<string, EventListener[]>;
  dispatchEvent(event: Event): void;
}

let wsInstances: MockWebSocketInstance[] = [];

// Mock WebSocket class
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
    wsInstances.push(this as MockWebSocketInstance);

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

// Mock the global WebSocket
vi.stubGlobal("WebSocket", MockWebSocket);

// Mock the auth store
const mockUseAuthStore = vi.fn();
type AuthStoreSelector<T> = (state: { token: string | null }) => T;
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: <T,>(selector: AuthStoreSelector<T>) => mockUseAuthStore(selector),
}));

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
    mockUseAuthStore.mockImplementation((selector: AuthStoreSelector<{ token: string | null }>) =>
      selector({ token: mockToken })
    );
  });

  afterEach(() => {
    wsInstances = [];
  });

  it("should establish WebSocket connection when mounted with token and assistantId", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
        onToolCall: mockOnToolCall,
        onToolResult: mockOnToolResult,
      })
    );

    // Should start in connecting state
    expect(result.current.connectionState).toBe(WSConnectionState.CONNECTING);

    // Should transition to open
    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    expect(wsInstances).toHaveLength(1);
    expect(wsInstances[0].url).toContain("mock-jwt-token");
  });

  it("should not connect when token is missing", async () => {
    mockUseAuthStore.mockImplementation((selector: AuthStoreSelector<{ token: string | null }>) =>
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

    // Should not connect - stay in closed state
    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.CLOSED);
    });

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

    // Should not connect - stay in closed state
    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.CLOSED);
    });

    expect(wsInstances).toHaveLength(0);
  });

  it("should send chat request when sendMessage is called", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    act(() => {
      result.current.sendMessage("Hello, AI!");
    });

    await waitFor(() => {
      expect(wsInstances[0].sentMessages).toHaveLength(1);
      const sentData = JSON.parse(wsInstances[0].sentMessages[0]);
      expect(sentData).toEqual({
        type: "chat",
        message: "Hello, AI!",
        session_id: null,
        assistant_config_id: mockAssistantId,
      });
    });
  });

  it("should handle token messages", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    // Simulate receiving a token message
    act(() => {
      wsInstances[0].dispatchEvent(
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
      expect(mockOnToken).toHaveBeenCalledWith("Hello", "session-123");
    });
  });

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

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    // Simulate receiving a tool call message
    act(() => {
      wsInstances[0].dispatchEvent(
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
      expect(mockOnToolCall).toHaveBeenCalledWith("list_projects", {
        project_id: "proj-1",
      });
    });
  });

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

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    // Simulate receiving a tool result message
    act(() => {
      wsInstances[0].dispatchEvent(
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
      });
    });
  });

  it("should handle complete messages", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    // Simulate receiving a complete message
    act(() => {
      wsInstances[0].dispatchEvent(
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
      expect(mockOnComplete).toHaveBeenCalledWith("session-123", "msg-456");
    });

    // Connection should close after completion
    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.CLOSED);
    });
  });

  it("should handle error messages", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    // Simulate receiving an error message
    act(() => {
      wsInstances[0].dispatchEvent(
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
      expect(mockOnError).toHaveBeenCalledWith("Error 500: Something went wrong");
    });

    expect(result.current.connectionState).toBe(WSConnectionState.ERROR);
    expect(result.current.error).toBeInstanceOf(Error);
  });

  it("should cancel connection when cancel is called", async () => {
    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    act(() => {
      result.current.cancel();
    });

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.CLOSED);
    });
  });

  it("should handle invalid JSON messages", async () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    // Simulate receiving invalid JSON
    act(() => {
      wsInstances[0].dispatchEvent(
        new MessageEvent("message", {
          data: "invalid json{{{",
        })
      );
    });

    await waitFor(() => {
      expect(mockOnError).toHaveBeenCalledWith("Failed to parse server message");
    });

    consoleSpy.mockRestore();
  });

  it("should handle unknown message types", async () => {
    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    // Simulate receiving unknown message type
    act(() => {
      wsInstances[0].dispatchEvent(
        new MessageEvent("message", {
          data: JSON.stringify({
            type: "unknown_type",
            data: "something",
          }),
        })
      );
    });

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled();
    });

    consoleSpy.mockRestore();
  });

  it("should cleanup on unmount", async () => {
    const { result, unmount } = renderHook(() =>
      useStreamingChat({
        assistantId: mockAssistantId,
        onToken: mockOnToken,
        onComplete: mockOnComplete,
        onError: mockOnError,
      })
    );

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    act(() => {
      unmount();
    });

    // Should close connection on unmount
    await waitFor(() => {
      expect(wsInstances[0].readyState).toBe(MockWebSocket.CLOSED);
    });
  });

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

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    act(() => {
      result.current.sendMessage("Continue our conversation");
    });

    await waitFor(() => {
      expect(wsInstances[0].sentMessages).toHaveLength(1);
      const sentData = JSON.parse(wsInstances[0].sentMessages[0]);
      expect(sentData.session_id).toBe("existing-session-123");
    });
  });
});
