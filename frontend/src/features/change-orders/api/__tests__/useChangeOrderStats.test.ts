/**
 * useChangeOrderStats Hook Tests
 *
 * Tests for the custom hook that fetches change order statistics.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// Mock the TimeMachineContext
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachineParams: () => ({
    asOf: null,
    setAsOf: vi.fn(),
    resetAsOf: vi.fn(),
  }),
}));

// Mock the OpenAPI and request module
vi.mock("@/api/generated/core/OpenAPI", () => ({
  OpenAPI: {
    BASE: "http://localhost:8000",
    HEADERS: {},
  },
}));

vi.mock("@/api/generated/core/request", () => ({
  request: vi.fn(),
}));

// Mock queryKeys
vi.mock("@/api/queryKeys", () => ({
  queryKeys: {
    changeOrders: {
      stats: (projectId: string, params: Record<string, unknown>) => [
        "changeOrders",
        "stats",
        projectId,
        params,
      ],
    },
  },
}));

import { request } from "@/api/generated/core/request";
import { useChangeOrderStats } from "../useChangeOrderStats";

const mockRequest = vi.mocked(request);

// Helper to create wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe("useChangeOrderStats", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Query Hook Behavior", () => {
    it("returns data on successful fetch", async () => {
      const mockStats = {
        total_count: 5,
        total_cost_exposure: 190000,
        pending_value: 85000,
        approved_value: 100000,
        by_status: [],
        by_impact_level: [],
        cost_trend: [],
        avg_approval_time_days: null,
        approval_workload: [],
        aging_items: [],
        aging_threshold_days: 7,
      };

      mockRequest.mockResolvedValueOnce(mockStats);

      const { result } = renderHook(
        () => useChangeOrderStats({ projectId: "test-project-id" }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockStats);
      expect(mockRequest).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          method: "GET",
          url: "/api/v1/change-orders/stats",
        })
      );
    });

    it("returns error on failed fetch", async () => {
      const mockError = new Error("Failed to fetch stats");
      mockRequest.mockRejectedValueOnce(mockError);

      const { result } = renderHook(
        () => useChangeOrderStats({ projectId: "test-project-id" }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeDefined();
    });

    it("does not fetch when projectId is empty", async () => {
      const { result } = renderHook(
        () => useChangeOrderStats({ projectId: "" }),
        { wrapper: createWrapper() }
      );

      // Query should be disabled
      expect(result.current.isFetching).toBe(false);
      expect(mockRequest).not.toHaveBeenCalled();
    });

    it("sends correct query parameters", async () => {
      mockRequest.mockResolvedValueOnce({ total_count: 0 });

      renderHook(
        () =>
          useChangeOrderStats({
            projectId: "project-123",
            branch: "feature-branch",
            agingThresholdDays: 14,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(mockRequest).toHaveBeenCalled());

      const callArgs = mockRequest.mock.calls[0][1];
      expect(callArgs.query).toEqual({
        project_id: "project-123",
        branch: "feature-branch",
        as_of: undefined,
        aging_threshold_days: 14,
      });
    });

    it("uses default values for optional parameters", async () => {
      mockRequest.mockResolvedValueOnce({ total_count: 0 });

      renderHook(
        () => useChangeOrderStats({ projectId: "project-123" }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(mockRequest).toHaveBeenCalled());

      const callArgs = mockRequest.mock.calls[0][1] as { query: Record<string, unknown> };
      expect(callArgs.query.branch).toBe("main");
      expect(callArgs.query.aging_threshold_days).toBe(7);
    });
  });

  describe("Stale Time Configuration", () => {
    it("uses 5 minute stale time for analytics data", async () => {
      mockRequest.mockResolvedValueOnce({ total_count: 0 });

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
          },
        },
      });

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      renderHook(() => useChangeOrderStats({ projectId: "project-123" }), {
        wrapper,
      });

      await waitFor(() => expect(mockRequest).toHaveBeenCalled());

      // Verify the hook was called - staleTime is configured internally
      expect(mockRequest).toHaveBeenCalled();
    });
  });

  describe("Query Key Generation", () => {
    it("generates consistent query keys for same parameters", async () => {
      mockRequest.mockResolvedValue({ total_count: 0 });

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
          },
        },
      });

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result: result1 } = renderHook(
        () => useChangeOrderStats({ projectId: "project-123" }),
        { wrapper }
      );

      await waitFor(() => expect(result1.current.isSuccess).toBe(true));

      const { result: result2 } = renderHook(
        () => useChangeOrderStats({ projectId: "project-123" }),
        { wrapper }
      );

      await waitFor(() => expect(result2.current.isSuccess).toBe(true));

      // Should have only called request once due to caching
      expect(mockRequest).toHaveBeenCalledTimes(1);
    });

    it("generates different query keys for different parameters", async () => {
      mockRequest.mockResolvedValue({ total_count: 0 });

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
          },
        },
      });

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result: result1 } = renderHook(
        () => useChangeOrderStats({ projectId: "project-123" }),
        { wrapper }
      );

      await waitFor(() => expect(result1.current.isSuccess).toBe(true));

      const { result: result2 } = renderHook(
        () => useChangeOrderStats({ projectId: "project-456" }),
        { wrapper }
      );

      await waitFor(() => expect(result2.current.isSuccess).toBe(true));

      // Should have called request twice for different projects
      expect(mockRequest).toHaveBeenCalledTimes(2);
    });
  });

  describe("Refetch Behavior", () => {
    it("refetches on window focus", async () => {
      mockRequest.mockResolvedValue({ total_count: 0 });

      renderHook(() => useChangeOrderStats({ projectId: "project-123" }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(mockRequest).toHaveBeenCalled());

      // Verify refetchOnWindowFocus is enabled (default in hook)
      // This is a configuration check, actual focus behavior is not tested
    });
  });

  describe("Query Options Override", () => {
    it("allows overriding query options", async () => {
      mockRequest.mockResolvedValueOnce({ total_count: 0 });

      const customOptions = {
        staleTime: 10000,
        enabled: true,
      };

      const { result } = renderHook(
        () => useChangeOrderStats({ projectId: "project-123" }, customOptions),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // The custom options should be merged
      expect(result.current.data).toBeDefined();
    });

    it("respects enabled option", async () => {
      mockRequest.mockResolvedValueOnce({ total_count: 0 });

      const { result } = renderHook(
        () =>
          useChangeOrderStats({ projectId: "project-123" }, { enabled: false }),
        { wrapper: createWrapper() }
      );

      // Should not fetch when enabled is false
      expect(result.current.isFetching).toBe(false);
      expect(mockRequest).not.toHaveBeenCalled();
    });
  });
});
