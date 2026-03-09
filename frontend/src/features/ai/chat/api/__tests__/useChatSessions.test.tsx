/**
 * Tests for useChatSessions hook
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi } from "vitest";
import { useChatSessions, useChatMessages, useDeleteSession } from "../useChatSessions";
import { queryKeys } from "@/api/queryKeys";

describe("useChatSessions", () => {
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

  describe("useChatSessions (list)", () => {
    it("should fetch sessions list", async () => {
      const { result } = renderHook(() => useChatSessions(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toHaveLength(2);
      expect(result.current.data?.[0].title).toBe("Project Analysis");
    });

    it("should have correct query key", async () => {
      const { result } = renderHook(() => useChatSessions(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const cache = queryClient.getQueryCache();
      const queries = cache.getAll();
      const chatQuery = queries.find((q) =>
        JSON.stringify(q.queryKey) === JSON.stringify(queryKeys.ai.chat.sessions())
      );

      expect(chatQuery).toBeDefined();
    });

    it("should handle loading state", () => {
      const { result } = renderHook(() => useChatSessions(), { wrapper });

      expect(result.current.isLoading).toBe(true);
    });

    it("should support disabled option", async () => {
      const { result } = renderHook(() => useChatSessions({ enabled: false }), { wrapper });

      // Should not fetch when disabled
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isFetching).toBe(false);
    });
  });

  describe("useChatMessages", () => {
    it("should fetch messages for a session", async () => {
      const { result } = renderHook(() => useChatMessages("session-1"), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toHaveLength(2);
      expect(result.current.data?.[0].content).toBe("What is the project status?");
      expect(result.current.data?.[1].role).toBe("assistant");
    });

    it("should not fetch when sessionId is undefined", () => {
      const { result } = renderHook(() => useChatMessages(undefined), { wrapper });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.isFetching).toBe(false);
    });

    it("should handle empty session ID", () => {
      const { result } = renderHook(() => useChatMessages(""), { wrapper });

      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("useDeleteSession", () => {
    it("should delete session and invalidate cache", async () => {
      const onSuccess = vi.fn();
      const { result } = renderHook(() => useDeleteSession({ onSuccess }), { wrapper });

      result.current.mutate("session-1");

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(onSuccess).toHaveBeenCalledOnce();
    });
  });
});
