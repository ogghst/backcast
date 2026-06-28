/**
 * Tests for useRunningExecutionsCount gating.
 *
 * The running-count endpoint requires the `ai-chat` permission. Callers MUST
 * pass `enabled: <user can see agents>` so unauthorized users don't trigger a
 * 403 storm. These tests pin that contract: the query fetches when enabled and
 * is completely inert (no network) when disabled.
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { server } from "@/mocks/server";
import { useRunningExecutionsCount } from "../useAgentExecutions";

describe("useRunningExecutionsCount", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  afterEach(() => server.resetHandlers());

  it("fetches the running count when enabled", async () => {
    const endpoint = vi.fn(() => HttpResponse.json({ count: 3 }));
    server.use(
      http.get("*/api/v1/ai/chat/executions/running-count", () => endpoint()),
    );

    const { result } = renderHook(
      () => useRunningExecutionsCount({ enabled: true }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBe(3);
    expect(endpoint).toHaveBeenCalledTimes(1);
  });

  it("does NOT fetch when disabled (no 403 storm for limited-permission users)", async () => {
    const endpoint = vi.fn(() => HttpResponse.json({ count: 0 }));
    server.use(
      http.get("*/api/v1/ai/chat/executions/running-count", () => endpoint()),
    );

    const { result } = renderHook(
      () => useRunningExecutionsCount({ enabled: false }),
      { wrapper },
    );

    // Give the query a tick to prove it never starts.
    await new Promise((r) => setTimeout(r, 50));

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
    expect(endpoint).not.toHaveBeenCalled();
  });
});
