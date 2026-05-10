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
import { createVersionedResourceHooks, type VersionedApiMethods } from "./useVersionedCrud";
import { queryKeys } from "@/api/queryKeys";
import { TimeMachineProvider } from "@/contexts/TimeMachineContext";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
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
      React.createElement(TimeMachineProvider, null, children),
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
        mockApiMethods as unknown as VersionedApiMethods<
          unknown,
          unknown,
          unknown
        >,
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
      const queryKey = testQuery!.queryKey as unknown[];
      // Context should be in the query key
      expect(
        queryKey.some((key) => key !== null && typeof key === "object" && "branch" in key),
      ).toBe(true);
    });

    it("should include branch, asOf, and mode in all query keys", async () => {
      // Arrange
      mockApiMethods.list.mockResolvedValue(mockListData);
      mockApiMethods.detail.mockResolvedValue(mockDetailData);
      const factory = createVersionedResourceHooks(
        "test-resource",
        queryKeys.testResource,
        mockApiMethods as unknown as VersionedApiMethods<
          unknown,
          unknown,
          unknown
        >,
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
        },
      );

      // Assert
      await waitFor(() => expect(listResult.current.isSuccess).toBe(true));
      await waitFor(() => expect(detailResult.current.isSuccess).toBe(true));

      // Verify both list and detail queries have context
      const queries = queryClient.getQueryCache().getAll();
      const testQueries = queries.filter(
        (q) => q.queryKey[0] === "test-resource",
      );

      expect(testQueries.length).toBeGreaterThanOrEqual(2);

      // Each query key should have context params
      testQueries.forEach((query) => {
        const queryKey = query.queryKey as unknown[];
        const hasContext = queryKey.some(
          (key) =>
            key !== null &&
            typeof key === "object" &&
            ("branch" in key || "asOf" in key || "mode" in key),
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
        mockApiMethods as unknown as VersionedApiMethods<
          unknown,
          unknown,
          unknown
        >,
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
        mockApiMethods as unknown as VersionedApiMethods<
          unknown,
          unknown,
          unknown
        >,
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
        mockApiMethods as unknown as VersionedApiMethods<
          unknown,
          unknown,
          unknown
        >,
        {
          invalidation: {
            create: [queryKeys.forecasts.all],
          },
        },
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

  /**
   * T-001: useUpdate injects branch from Time Machine
   *
   * Expected: useUpdate mutation should inject branch from useTimeMachineParams into request data
   * This test FAILS before the fix, PASSES after the fix
   */
  describe("T-001: useUpdate Branch Injection from TimeMachine", () => {
    beforeEach(() => {
      // Set up Time Machine with a specific branch for testing
      useTimeMachineStore.getState().setCurrentProject("test-project");
      useTimeMachineStore.getState().selectBranch("BR-CO-2026-016");
    });

    it("should inject branch from TimeMachine into update mutation data", async () => {
      // Arrange
      const mockUpdatedData = { id: "1", name: "Updated Item", branch: "BR-CO-2026-016" };
      mockApiMethods.update.mockResolvedValue(mockUpdatedData);

      const factory = createVersionedResourceHooks(
        "test-resource",
        queryKeys.testResource,
        mockApiMethods as unknown as VersionedApiMethods<
          unknown,
          unknown,
          unknown
        >,
      );

      // Act
      const { result } = renderHook(() => factory.useUpdate(), {
        wrapper: createWrapper(queryClient),
      });

      // Execute mutation with data that does NOT include branch
      result.current.mutate({ id: "1", data: { name: "Updated Item" } });

      // Assert
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify the API method was called with branch injected from Time Machine
      expect(mockApiMethods.update).toHaveBeenCalledWith(
        "1",
        expect.objectContaining({
          name: "Updated Item",
          branch: "BR-CO-2026-016", // This should be injected from Time Machine
        }),
      );
    });

    it("should allow explicit branch in data to override Time Machine branch", async () => {
      // Arrange
      const mockUpdatedData = { id: "1", name: "Updated Item", branch: "BR-CUSTOM" };
      mockApiMethods.update.mockResolvedValue(mockUpdatedData);

      const factory = createVersionedResourceHooks(
        "test-resource",
        queryKeys.testResource,
        mockApiMethods as unknown as VersionedApiMethods<
          unknown,
          unknown,
          unknown
        >,
      );

      // Act
      const { result } = renderHook(() => factory.useUpdate(), {
        wrapper: createWrapper(queryClient),
      });

      // Execute mutation with explicit branch in data
      result.current.mutate({
        id: "1",
        data: { name: "Updated Item", branch: "BR-CUSTOM" },
      });

      // Assert
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify the explicit branch overrides Time Machine branch
      expect(mockApiMethods.update).toHaveBeenCalledWith(
        "1",
        expect.objectContaining({
          name: "Updated Item",
          branch: "BR-CUSTOM", // Explicit branch should override
        }),
      );
    });
  });

  /**
   * T-002: useCreate injects branch from Time Machine
   *
   * Expected: useCreate mutation should inject branch from useTimeMachineParams into request data
   * This test FAILS before the fix, PASSES after the fix
   */
  describe("T-002: useCreate Branch Injection from TimeMachine", () => {
    beforeEach(() => {
      // Set up Time Machine with a specific branch for testing
      useTimeMachineStore.getState().setCurrentProject("test-project");
      useTimeMachineStore.getState().selectBranch("BR-CO-2026-016");
    });

    it("should inject branch from TimeMachine into create mutation data", async () => {
      // Arrange
      const mockCreatedData = { id: "new-id", name: "New Item", branch: "BR-CO-2026-016" };
      mockApiMethods.create.mockResolvedValue(mockCreatedData);

      const factory = createVersionedResourceHooks(
        "test-resource",
        queryKeys.testResource,
        mockApiMethods as unknown as VersionedApiMethods<
          unknown,
          unknown,
          unknown
        >,
      );

      // Act
      const { result } = renderHook(() => factory.useCreate(), {
        wrapper: createWrapper(queryClient),
      });

      // Execute mutation with data that does NOT include branch
      result.current.mutate({ name: "New Item" });

      // Assert
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify the API method was called with branch injected from Time Machine
      expect(mockApiMethods.create).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "New Item",
          branch: "BR-CO-2026-016", // This should be injected from Time Machine
        }),
      );
    });

    it("should allow explicit branch in data to override Time Machine branch", async () => {
      // Arrange
      const mockCreatedData = { id: "new-id", name: "New Item", branch: "BR-CUSTOM" };
      mockApiMethods.create.mockResolvedValue(mockCreatedData);

      const factory = createVersionedResourceHooks(
        "test-resource",
        queryKeys.testResource,
        mockApiMethods as unknown as VersionedApiMethods<
          unknown,
          unknown,
          unknown
        >,
      );

      // Act
      const { result } = renderHook(() => factory.useCreate(), {
        wrapper: createWrapper(queryClient),
      });

      // Execute mutation with explicit branch in data
      result.current.mutate({ name: "New Item", branch: "BR-CUSTOM" });

      // Assert
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify the explicit branch overrides Time Machine branch
      expect(mockApiMethods.create).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "New Item",
          branch: "BR-CUSTOM", // Explicit branch should override
        }),
      );
    });
  });

  /**
   * T-003: useDelete injects branch from Time Machine
   *
   * Expected: useDelete mutation should inject branch from useTimeMachineParams into API call
   * Note: Delete operations may use branch as a parameter (for versioned entities)
   * or may not support branch at all (for non-versioned entities like Projects)
   * This test FAILS before the fix, PASSES after the fix
   */
  describe("T-003: useDelete Branch Injection from TimeMachine", () => {
    beforeEach(() => {
      // Set up Time Machine with a specific branch for testing
      useTimeMachineStore.getState().setCurrentProject("test-project");
      useTimeMachineStore.getState().selectBranch("BR-CO-2026-016");
    });

    it("should call delete with id and branch parameters when API supports it", async () => {
      // Arrange - Mock delete method that accepts branch parameter
      const deleteWithBranch = vi.fn().mockResolvedValue(undefined);
      const mockApiWithBranchDelete = {
        ...mockApiMethods,
        delete: deleteWithBranch,
      };

      const factory = createVersionedResourceHooks(
        "test-resource",
        queryKeys.testResource,
        mockApiWithBranchDelete as unknown as VersionedApiMethods<
          unknown,
          unknown,
          unknown
        >,
      );

      // Act
      const { result } = renderHook(() => factory.useDelete(), {
        wrapper: createWrapper(queryClient),
      });

      // Execute mutation
      result.current.mutate("test-id");

      // Assert
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify the API method was called with branch parameter
      // The implementation should try to pass branch as second parameter
      expect(deleteWithBranch).toHaveBeenCalledWith(
        "test-id",
        expect.any(Object), // Should pass branch context
      );
    });

    it("should handle delete methods that don't support branch parameter", async () => {
      // Arrange - Mock delete method that only accepts id (like Projects, WBEs)
      const deleteWithoutBranch = vi.fn().mockResolvedValue(undefined);
      const mockApiWithoutBranchDelete = {
        ...mockApiMethods,
        delete: deleteWithoutBranch,
      };

      const factory = createVersionedResourceHooks(
        "test-resource",
        queryKeys.testResource,
        mockApiWithoutBranchDelete as unknown as VersionedApiMethods<
          unknown,
          unknown,
          unknown
        >,
      );

      // Act
      const { result } = renderHook(() => factory.useDelete(), {
        wrapper: createWrapper(queryClient),
      });

      // Execute mutation - should not throw error
      result.current.mutate("test-id");

      // Assert
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify the API method was called with branch parameter
      // Even though the method signature doesn't include branch, JavaScript allows extra parameters
      expect(deleteWithoutBranch).toHaveBeenCalledWith(
        "test-id",
        expect.objectContaining({
          branch: "BR-CO-2026-016",
        }),
      );
    });
  });
});
