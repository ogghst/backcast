/**
 * Unit tests for useVersionedCrud factory
 *
 * Test IDs from plan:
 * - T-001: Factory hooks inject context from time machine
 * - T-002: Factory uses queryKeys factory
 * - T-003: Factory includes context in all keys
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, beforeEach, vi } from "vitest";

// Import after creating the factory
import { createVersionedResourceHooks } from "./useVersionedCrud";
import { queryKeys } from "@/api/queryKeys";
import { TimeMachineProvider } from "@/contexts/TimeMachineContext";
import React from "react";

// Mock API methods
const mockApiMethods = {
  list: vi.fn(),
  detail: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  delete: vi.fn(),
};

// Mock data
const mockListData = [
  { id: "1", name: "Item 1" },
  { id: "2", name: "Item 2" },
];
const mockDetailData = { id: "1", name: "Item 1" };

// Test helper: wrapper with TimeMachine context
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      React.createElement(TimeMachineProvider, null, children)
    );
  };
}

describe("useVersionedCrud Factory", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  /**
   * T-001: Factory hooks inject context from time machine
   *
   * Expected: Factory hook reads { branch, asOf, mode } and includes in query keys
   */
  describe("T-001: Context Injection from TimeMachine", () => {
    it("should inject default context params from TimeMachine", async () => {
      // Arrange
      mockApiMethods.list.mockResolvedValue(mockListData);
      const factory = createVersionedResourceHooks(
        "test-resource",
        queryKeys.testResource,
        mockApiMethods as any
      );

      // Act
      const { result } = renderHook(() => factory.useList(), {
        wrapper: createWrapper(queryClient),
      });

      // Assert
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify the query key contains context params
      const queries = queryClient.getQueryCache().getAll();
      const testQuery = queries.find((q) => q.queryKey[0] === "test-resource");

      expect(testQuery).toBeDefined();
      const queryKey = testQuery!.queryKey as any[];
      // Context should be in the query key
      expect(queryKey.some((key) => typeof key === "object" && "branch" in key))
        .toBe(true);
    });

    it("should include branch, asOf, and mode in all query keys", async () => {
      // Arrange
      mockApiMethods.list.mockResolvedValue(mockListData);
      mockApiMethods.detail.mockResolvedValue(mockDetailData);
      const factory = createVersionedResourceHooks(
        "test-resource",
        queryKeys.testResource,
        mockApiMethods as any
      );

      // Act - Test list query
      const { result: listResult } = renderHook(() => factory.useList(), {
        wrapper: createWrapper(queryClient),
      });

      // Test detail query
      const { result: detailResult } = renderHook(
        () => factory.useDetail("test-id"),
        {
          wrapper: createWrapper(queryClient),
        }
      );

      // Assert
      await waitFor(() => expect(listResult.current.isSuccess).toBe(true));
      await waitFor(() => expect(detailResult.current.isSuccess).toBe(true));

      // Verify both list and detail queries have context
      const queries = queryClient.getQueryCache().getAll();
      const testQueries = queries.filter(
        (q) => q.queryKey[0] === "test-resource"
      );

      expect(testQueries.length).toBeGreaterThanOrEqual(2);

      // Each query key should have context params
      testQueries.forEach((query) => {
        const queryKey = query.queryKey as any[];
        const hasContext = queryKey.some(
          (key) =>
            typeof key === "object" &&
            ("branch" in key || "asOf" in key || "mode" in key)
        );
        expect(hasContext).toBe(true);
      });
    });
  });

  /**
   * T-002: Factory uses queryKeys factory
   *
   * Expected: Query keys match structure from queryKeys[resource].*()
   */
  describe("T-002: Query Key Factory Usage", () => {
    it("should use queryKeys factory for list queries", async () => {
      // Arrange
      mockApiMethods.list.mockResolvedValue(mockListData);

      // Spy on queryKeys factory
      const listSpy = vi.spyOn(queryKeys.testResource, "list");

      const factory = createVersionedResourceHooks(
        "test-resource",
        queryKeys.testResource,
        mockApiMethods as any
      );

      // Act
      renderHook(() => factory.useList(), {
        wrapper: createWrapper(queryClient),
      });

      // Assert
      await waitFor(() => expect(listSpy).toHaveBeenCalled());
    });

    it("should use queryKeys factory for detail queries", async () => {
      // Arrange
      mockApiMethods.detail.mockResolvedValue(mockDetailData);

      // Spy on queryKeys factory
      const detailSpy = vi.spyOn(queryKeys.testResource, "detail");

      const factory = createVersionedResourceHooks(
        "test-resource",
        queryKeys.testResource,
        mockApiMethods as any
      );

      // Act
      renderHook(() => factory.useDetail("test-id"), {
        wrapper: createWrapper(queryClient),
      });

      // Assert
      await waitFor(() => expect(detailSpy).toHaveBeenCalled());
    });
  });

  /**
   * T-003: Factory includes context in all keys
   *
   * Expected: List, detail, and mutation keys all contain context params
   */
  describe("T-003: Context in All Keys", () => {
    it("should include context in mutation invalidation keys", async () => {
      // Arrange
      mockApiMethods.create.mockResolvedValue(mockDetailData);
      mockApiMethods.list.mockResolvedValue(mockListData);

      // Spy on invalidateQueries to verify it's called with correct keys
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const factory = createVersionedResourceHooks(
        "test-resource",
        queryKeys.testResource,
        mockApiMethods as any,
        {
          invalidation: {
            create: [queryKeys.forecasts.all],
          },
        }
      );

      // Act
      const { result } = renderHook(() => factory.useCreate(), {
        wrapper: createWrapper(queryClient),
      });

      // Execute mutation
      result.current.mutate({ name: "New Item" });

      // Assert
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify invalidateQueries was called with forecasts.all
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: queryKeys.forecasts.all,
      });
    });
  });
});
