/**
 * Tests for useNotificationStream
 *
 * Verifies the WebSocket message handling: badge_update writes the
 * authoritative count to the cache; notification frame shows a toast,
 * invalidates the list, and optimistically bumps the unread count. Also
 * verifies 4008 close code suppresses reconnection.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useNotificationStream } from "./useNotificationStream";
import { queryKeys } from "@/api/queryKeys";

// ---- Mocks ---------------------------------------------------------------

const toastMock = {
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
  success: vi.fn(),
  __default: vi.fn(),
};
vi.mock("sonner", () => ({
  toast: Object.assign(
    (...args: unknown[]) => toastMock.__default(args),
    {
      error: (...args: unknown[]) => toastMock.error(args),
      warning: (...args: unknown[]) => toastMock.warning(args),
      info: (...args: unknown[]) => toastMock.info(args),
      success: (...args: unknown[]) => toastMock.success(args),
    },
  ),
}));

// Auth store: provide a stable token.
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: (selector: (s: { token: string }) => string) =>
    selector({ token: "test-jwt" }),
}));

// Controllable WebSocket mock.
type Listener = (event: { data?: string; code?: number }) => void;
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static LAST: MockWebSocket | null = null;
  url: string;
  readyState = 1; // OPEN
  private listeners: Record<string, Listener[]> = {};
  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    MockWebSocket.LAST = this;
    // Immediately "open"
    queueMicrotask(() => this.dispatch("open", {}));
  }
  addEventListener(type: string, cb: Listener) {
    (this.listeners[type] ??= []).push(cb);
  }
  removeEventListener(type: string, cb: Listener) {
    this.listeners[type] = (this.listeners[type] ?? []).filter((l) => l !== cb);
  }
  dispatch(type: string, event: { data?: string; code?: number }) {
    (this.listeners[type] ?? []).forEach((cb) => cb(event));
  }
  close() {
    this.readyState = 3;
  }
  send() {
    /* no-op */
  }
}

function makeWrapper(client: QueryClient) {
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe("useNotificationStream", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.instances = [];
    MockWebSocket.LAST = null;
    Object.values(toastMock).forEach((m) => m.mockClear());
    // globalThis.WebSocket is read-only in jsdom — define it.
    Object.defineProperty(globalThis, "WebSocket", {
      configurable: true,
      writable: true,
      value: MockWebSocket,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("writes the authoritative count on badge_update", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    renderHook(() => useNotificationStream(), { wrapper: makeWrapper(client) });

    // Let the microtask open fire.
    await vi.advanceTimersByTimeAsync(0);

    const ws = MockWebSocket.LAST!;
    ws.dispatch("message", {
      data: JSON.stringify({ type: "badge_update", unread_count: 7 }),
    });

    const cached = client.getQueryData<{ count: number }>(
      queryKeys.notifications.unreadCount(),
    );
    expect(cached?.count).toBe(7);
  });

  it("toasts + invalidates + bumps count on a notification frame", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    // Seed a list query so invalidation is observable via a spy.
    const listKey = queryKeys.notifications.list({ page: 1, pageSize: 20 });
    client.setQueryData(listKey, { items: [], total: 0, page: 1, per_page: 20 });
    const invalidateSpy = vi.spyOn(client, "invalidateQueries");

    // Seed the unread count.
    client.setQueryData(queryKeys.notifications.unreadCount(), { count: 3 });

    renderHook(() => useNotificationStream(), { wrapper: makeWrapper(client) });
    await vi.advanceTimersByTimeAsync(0);

    const ws = MockWebSocket.LAST!;
    ws.dispatch("message", {
      data: JSON.stringify({
        type: "notification",
        notification: {
          title: "Build failed",
          message: "EVM step errored",
          severity: "urgent",
          category: "agent",
        },
      }),
    });

    // Urgent severity -> error toast.
    expect(toastMock.error).toHaveBeenCalled();
    // List invalidated.
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: queryKeys.notifications.lists(),
    });
    // Count optimistically bumped to 4.
    const cached = client.getQueryData<{ count: number }>(
      queryKeys.notifications.unreadCount(),
    );
    expect(cached?.count).toBe(4);
  });

  it("does NOT reconnect on close code 4008 (token expired)", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    renderHook(() => useNotificationStream(), { wrapper: makeWrapper(client) });
    await vi.advanceTimersByTimeAsync(0);

    const firstCount = MockWebSocket.instances.length;
    const ws = MockWebSocket.LAST!;
    ws.readyState = 3;
    ws.dispatch("close", { code: 4008 });

    // Advance well past the max backoff chain.
    await vi.advanceTimersByTimeAsync(60000);
    expect(MockWebSocket.instances.length).toBe(firstCount);
  });
});
