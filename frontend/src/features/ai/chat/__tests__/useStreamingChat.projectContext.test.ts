/**
 * useStreamingChat project_context_change dispatcher test.
 *
 * Asserts the WS message dispatcher routes a `project_context_change` event to
 * the `onProjectContextChange` callback (mirroring the temporal handler).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { WSConnectionState } from "../types";
import { useStreamingChat } from "../api/useStreamingChat";

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
    wsInstances.push(this as MockWebSocketInstance);

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

const mockUseAuthStore = vi.fn();
const mockUseTimeMachineStore = vi.fn();

type AuthStoreSelector<T> = (
  state: { token: string | null; user?: { user_id: string } }
) => T;
type TimeMachineStoreSelector<T> = (state: Record<string, unknown>) => T;

vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: <T,>(selector: AuthStoreSelector<T>) =>
    mockUseAuthStore(selector),
}));

vi.mock("@/stores/useTimeMachineStore", () => ({
  useTimeMachineStore: <T,>(selector: TimeMachineStoreSelector<T>) =>
    mockUseTimeMachineStore(selector),
}));

describe("useStreamingChat project_context_change dispatch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    wsInstances = [];

    mockUseAuthStore.mockImplementation(
      (selector: AuthStoreSelector<unknown>) =>
        selector({
          token: "test-jwt-token",
          user: { user_id: "user-123", email: "test@example.com" },
        })
    );

    mockUseTimeMachineStore.mockImplementation(
      (selector: TimeMachineStoreSelector<unknown>) =>
        selector({
          getSelectedTime: () => null,
          getSelectedBranch: () => "main",
          getViewMode: () => "merged",
        })
    );
  });

  const getLastWsInstance = () => wsInstances[wsInstances.length - 1];

  it("routes project_context_change to onProjectContextChange", async () => {
    const onProjectContextChange = vi.fn();

    const { result } = renderHook(() =>
      useStreamingChat({
        assistantId: "assistant-1",
        projectId: "project-abc",
        activeExecutionId: "exec-1",
        onProjectContextChange,
      })
    );

    await waitFor(() => {
      expect(result.current.connectionState).toBe(WSConnectionState.OPEN);
    });

    act(() => {
      getLastWsInstance().dispatchEvent({
        type: "message",
        data: JSON.stringify({
          type: "project_context_change",
          project_id: "proj-new",
          project_name: "Alpha Line",
          project_code: "ALPHA-01",
        }),
      } as MessageEvent);
    });

    expect(onProjectContextChange).toHaveBeenCalledTimes(1);
    expect(onProjectContextChange).toHaveBeenCalledWith({
      type: "project_context_change",
      project_id: "proj-new",
      project_name: "Alpha Line",
      project_code: "ALPHA-01",
    });
  });
});
