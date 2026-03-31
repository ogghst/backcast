/**
 * Tests for useChatSessionsPaginated hook
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, beforeEach } from "vitest";
import { useChatSessionsPaginated } from "../useChatSessionsPaginated";
import { queryKeys } from "@/api/queryKeys";

describe("useChatSessionsPaginated", () => {
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

  it("should initialize with default values", () => {
    const { result } = renderHook(() => useChatSessionsPaginated(), { wrapper });

    expect(result.current.hasMore).toBe(false);
    expect(result.current.totalCount).toBe(0);
    expect(result.current.loadMore).toBeDefined();
    expect(result.current.reset).toBeDefined();
  });

  it("should load sessions on mount", async () => {
    const { result } = renderHook(() => useChatSessionsPaginated({ limit: 10 }), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.sessions).toHaveLength(10);
    expect(result.current.data?.has_more).toBe(true);
    expect(result.current.data?.total_count).toBe(25);
    expect(result.current.hasMore).toBe(true);
  });

  it("should have correct query key", async () => {
    const { result } = renderHook(() => useChatSessionsPaginated({ limit: 10 }), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const cache = queryClient.getQueryCache();
    const queries = cache.getAll();
    const chatQuery = queries.find((q) =>
      JSON.stringify(q.queryKey) === JSON.stringify(queryKeys.ai.chat.sessionsPaginated(0, 10))
    );

    expect(chatQuery).toBeDefined();
  });

  it("should handle loading state", () => {
    const { result } = renderHook(() => useChatSessionsPaginated({ limit: 10 }), { wrapper });

    expect(result.current.isLoading).toBe(true);
  });

  it("should increment skip when loadMore is called", async () => {
    const { result } = renderHook(() => useChatSessionsPaginated({ limit: 10 }), { wrapper });

    // Wait for initial load
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Call loadMore
    result.current.loadMore();

    // Wait for next page to load
    await waitFor(() => {
      expect(result.current.data?.sessions).toBeDefined();
    });

    // Should have loaded the second page
    const cache = queryClient.getQueryCache();
    const queries = cache.getAll();
    const secondPageQuery = queries.find((q) =>
      JSON.stringify(q.queryKey) === JSON.stringify(queryKeys.ai.chat.sessionsPaginated(10, 10))
    );

    expect(secondPageQuery).toBeDefined();
  });

  it("should reset skip when reset is called", async () => {
    const { result } = renderHook(() => useChatSessionsPaginated({ limit: 10 }), { wrapper });

    // Wait for initial load
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Load more
    result.current.loadMore();

    // Reset
    result.current.reset();

    // Wait for reset to take effect
    await waitFor(() => {
      const cache = queryClient.getQueryCache();
      const queries = cache.getAll();
      const resetQuery = queries.find((q) =>
        JSON.stringify(q.queryKey) === JSON.stringify(queryKeys.ai.chat.sessionsPaginated(0, 10))
      );
      expect(resetQuery).toBeDefined();
    });
  });

  it("should handle custom initialSkip", async () => {
    const { result } = renderHook(
      () => useChatSessionsPaginated({ initialSkip: 10, limit: 10 }),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const cache = queryClient.getQueryCache();
    const queries = cache.getAll();
    const customSkipQuery = queries.find((q) =>
      JSON.stringify(q.queryKey) === JSON.stringify(queryKeys.ai.chat.sessionsPaginated(10, 10))
    );

    expect(customSkipQuery).toBeDefined();
  });

  it("should handle custom limit", async () => {
    const { result } = renderHook(
      () => useChatSessionsPaginated({ limit: 5 }),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.sessions).toHaveLength(5);
  });
});
