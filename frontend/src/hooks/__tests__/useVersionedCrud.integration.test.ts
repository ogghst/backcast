/**
 * Integration Tests for Branch Isolation in useVersionedCrud
 *
 * Test IDs from plan:
 * - T-006: Cost element update on change branch creates version on that branch
 * - T-007: Main branch unchanged when editing on change branch
 * - T-008: WBE update on change branch lazy branching
 *
 * These tests verify the fix for the branch isolation bug where mutations
 * were not injecting the branch context from Time Machine.
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, beforeEach, vi } from "vitest";
import React from "react";

// Import the factory we're testing
import { createVersionedResourceHooks, type VersionedApiMethods } from "../useVersionedCrud";
import { queryKeys } from "@/api/queryKeys";
import { TimeMachineProvider } from "@/contexts/TimeMachineContext";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";

/**
 * Integration Test: Branch Isolation for Cost Elements
 *
 * Context: Cost elements are versionable entities that support branching.
 * When editing a cost element while viewing a change order branch, the update
 * should create a new version on the change branch, NOT on the main branch.
 *
 * This is the core bug fix being tested.
 */
describe("T-006, T-007: Cost Element Branch Isolation Integration Tests", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();

    // Reset Time Machine store to clean state
    useTimeMachineStore.getState().setCurrentProject(null);
    useTimeMachineStore.getState().resetToNow();
  });

  /**
   * T-006: Cost element update on change branch creates version on that branch
   *
   * Expected Behavior:
   * 1. When Time Machine is set to a change branch (e.g., BR-CO-2026-016)
   * 2. And we update a cost element
   * 3. The update API should be called with the change branch in the request data
   * 4. This causes the backend to create a new version on the change branch (lazy forking)
   *
   * Acceptance Criterion SC1:
   * "Editing a cost element while viewing a change order branch creates a version
   * on that branch, not main"
   */
  describe("T-006: Cost Element Update on Change Branch", () => {
    it("should call update API with branch parameter from Time Machine context", async () => {
      // Arrange - Set up Time Machine with a change branch
      useTimeMachineStore.getState().setCurrentProject("CO-E2E-ROBOT");
      useTimeMachineStore.getState().selectBranch("BR-CO-2026-016");

      // Mock API service that tracks how it's called
      const mockUpdate = vi.fn();
      const mockApiMethods = {
        update: mockUpdate,
      };

      // Create a test factory with cost element-like API
      const factory = createVersionedResourceHooks(
        "cost-elements",
        queryKeys.costElements,
        mockApiMethods as VersionedApiMethods<unknown, Record<string, unknown>, Record<string, unknown>>,
      );

      // Mock successful update response
      const mockResponse = {
        id: "ce-123",
        cost_element_id: "CE-CTRL-02",
        name: "Updated Control Cabinet",
        branch: "BR-CO-2026-016",
      };
      mockUpdate.mockResolvedValue(mockResponse);

      // Act - Update the cost element while viewing change branch
      const { result } = renderHook(() => factory.useUpdate(), {
        wrapper: ({ children }) =>
          React.createElement(
            QueryClientProvider,
            { client: queryClient },
            React.createElement(TimeMachineProvider, null, children),
          ),
      });

      // Execute mutation with update data (no explicit branch)
      result.current.mutate({
        id: "ce-123",
        data: {
          name: "Updated Control Cabinet",
          budget_allocated: "150000.00",
        },
      });

      // Assert - Verify the API was called with branch from Time Machine
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockUpdate).toHaveBeenCalledWith(
        "ce-123",
        expect.objectContaining({
          name: "Updated Control Cabinet",
          budget_allocated: "150000.00",
          // This is the critical assertion: branch MUST be injected from Time Machine
          branch: "BR-CO-2026-016",
        }),
      );

      // Verify branch was NOT called with "main" (the bug behavior)
      expect(mockUpdate).not.toHaveBeenCalledWith(
        "ce-123",
        expect.objectContaining({
          branch: "main",
        }),
      );
    });

    it("should create new version on change branch, not main branch", async () => {
      // Arrange - Simulating the scenario from the bug report
      useTimeMachineStore.getState().setCurrentProject("CO-E2E-ROBOT");
      useTimeMachineStore.getState().selectBranch("BR-CO-2026-016");

      const mockUpdate = vi.fn();
      const mockApiMethods = {
        update: mockUpdate,
      };

      const factory = createVersionedResourceHooks(
        "cost-elements",
        queryKeys.costElements,
        mockApiMethods as VersionedApiMethods<unknown, Record<string, unknown>, Record<string, unknown>>,
      );

      // Simulate backend response confirming the change branch
      const mockResponse = {
        id: "ce-123",
        cost_element_id: "CE-CTRL-02",
        name: "Updated Control Cabinet",
        branch: "BR-CO-2026-016",
        valid_from: new Date().toISOString(),
        valid_to: null,
      };
      mockUpdate.mockResolvedValue(mockResponse);

      // Act - Perform the update
      const { result } = renderHook(() => factory.useUpdate(), {
        wrapper: ({ children }) =>
          React.createElement(
            QueryClientProvider,
            { client: queryClient },
            React.createElement(TimeMachineProvider, null, children),
          ),
      });

      result.current.mutate({
        id: "ce-123",
        data: { name: "Updated Control Cabinet" },
      });

      // Assert - Verify backend received the correct branch
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // The critical fix: branch must be in the request
      const updateCall = mockUpdate.mock.calls[0];
      const requestData = updateCall[1];

      expect(requestData.branch).toBe("BR-CO-2026-016");
      expect(requestData.branch).not.toBe("main");
    });
  });

  /**
   * T-007: Main branch unchanged when editing on change branch
   *
   * Expected Behavior:
   * 1. When we update a cost element on a change branch
   * 2. The main branch version should remain untouched
   * 3. The backend handles this via lazy forking - creates a copy on the change branch
   *
   * Acceptance Criterion SC2:
   * "Main branch remains unchanged when editing on change order branch"
   */
  describe("T-007: Main Branch Preservation", () => {
    it("should not modify main branch when updating on change branch", async () => {
      // Arrange - Start with a cost element on main branch
      useTimeMachineStore.getState().setCurrentProject("CO-E2E-ROBOT");

      // First, query on main branch to establish baseline
      useTimeMachineStore.getState().selectBranch("main");

      const mockGet = vi.fn();
      const mockUpdate = vi.fn();

      const factory = createVersionedResourceHooks(
        "cost-elements",
        queryKeys.costElements,
        {
          detail: mockGet,
          update: mockUpdate,
      } as VersionedApiMethods<unknown, Record<string, unknown>, Record<string, unknown>>,
      );

      // Mock main branch version
      const mainBranchVersion = {
        id: "ce-123",
        cost_element_id: "CE-CTRL-02",
        name: "Control Cabinet",
        budget_allocated: "100000.00",
        branch: "main",
        valid_from: "2026-01-01T00:00:00Z",
        valid_to: null,
      };
      mockGet.mockResolvedValue(mainBranchVersion);

      // Query main branch version
      const { result: queryResult } = renderHook(
        () => factory.useDetail("ce-123"),
        {
          wrapper: ({ children }) =>
            React.createElement(
              QueryClientProvider,
              { client: queryClient },
              React.createElement(TimeMachineProvider, null, children),
            ),
        },
      );

      await waitFor(() => expect(queryResult.current.isSuccess).toBe(true));
      const mainVersionBefore = queryResult.current.data;

      // Act - Switch to change branch and update
      useTimeMachineStore.getState().selectBranch("BR-CO-2026-016");

      const mockChangeBranchResponse = {
        id: "ce-123",
        cost_element_id: "CE-CTRL-02",
        name: "Control Cabinet - Modified",
        budget_allocated: "150000.00",
        branch: "BR-CO-2026-016",
        valid_from: new Date().toISOString(),
        valid_to: null,
      };
      mockUpdate.mockResolvedValue(mockChangeBranchResponse);

      const { result: mutationResult } = renderHook(
        () => factory.useUpdate(),
        {
          wrapper: ({ children }) =>
            React.createElement(
              QueryClientProvider,
              { client: queryClient },
              React.createElement(TimeMachineProvider, null, children),
            ),
        },
      );

      mutationResult.current.mutate({
        id: "ce-123",
        data: { name: "Control Cabinet - Modified" },
      });

      // Assert - Verify update was sent to change branch
      await waitFor(() => expect(mutationResult.current.isSuccess).toBe(true));

      expect(mockUpdate).toHaveBeenCalledWith(
        "ce-123",
        expect.objectContaining({
          branch: "BR-CO-2026-016",
        }),
      );

      // Main branch version data is unchanged
      expect(mainVersionBefore).toEqual(
        expect.objectContaining({
          name: "Control Cabinet",
          budget_allocated: "100000.00",
          branch: "main",
        }),
      );
    });

    it("should use different query keys for main and change branch", async () => {
      // Arrange - Verify query keys include branch context
      useTimeMachineStore.getState().setCurrentProject("CO-E2E-ROBOT");

      const mockGet = vi.fn();
      const factory = createVersionedResourceHooks(
        "cost-elements",
        queryKeys.costElements,
        {
          detail: mockGet,
      } as VersionedApiMethods<unknown, Record<string, unknown>, Record<string, unknown>>,
      );

      const mockResponse = {
        id: "ce-123",
        name: "Test",
        branch: "main",
      };
      mockGet.mockResolvedValue(mockResponse);

      // Act - Query from main branch
      useTimeMachineStore.getState().selectBranch("main");

      const { result: mainResult } = renderHook(
        () => factory.useDetail("ce-123"),
        {
          wrapper: ({ children }) =>
            React.createElement(
              QueryClientProvider,
              { client: queryClient },
              React.createElement(TimeMachineProvider, null, children),
            ),
        },
      );

      await waitFor(() => expect(mainResult.current.isSuccess).toBe(true));

      // Query from change branch (using a different query client to avoid cache interference)
      const changeQueryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      useTimeMachineStore.getState().selectBranch("BR-CO-2026-016");

      const { result: changeResult } = renderHook(
        () => factory.useDetail("ce-123"),
        {
          wrapper: ({ children }) =>
            React.createElement(
              QueryClientProvider,
              { client: changeQueryClient },
              React.createElement(TimeMachineProvider, null, children),
            ),
        },
      );

      await waitFor(() => expect(changeResult.current.isSuccess).toBe(true));

      // Assert - Query keys include branch context
      const mainCache = queryClient.getQueryCache().getAll();
      const changeCache = changeQueryClient.getQueryCache().getAll();

      // Main branch query key should include branch: "main"
      const mainQuery = mainCache.find(
        (q) => q.queryKey[0] === "cost-elements",
      );
      expect(mainQuery).toBeDefined();
      expect(JSON.stringify(mainQuery!.queryKey)).toContain('"branch":"main"');

      // Change branch query key should include branch: "BR-CO-2026-016"
      const changeQuery = changeCache.find(
        (q) => q.queryKey[0] === "cost-elements",
      );
      expect(changeQuery).toBeDefined();
      expect(JSON.stringify(changeQuery!.queryKey)).toContain('"branch":"BR-CO-2026-016"');

      // Verify the query keys are different
      expect(mainQuery!.queryKey).not.toEqual(changeQuery!.queryKey);
    });
  });

  /**
   * T-008: WBE update on change branch lazy branching
   *
   * Expected Behavior:
   * WBEs (Work Breakdown Elements) also support branching.
   * When updating a WBE on a change branch, the backend performs
   * lazy forking - copies the entity to the change branch then applies changes.
   *
   * Acceptance Criterion SC3:
   * "Behavior consistent across all branchable entities"
   */
  describe("T-008: WBE Lazy Branching Integration", () => {
    it("should inject branch for WBE updates on change branch", async () => {
      // Arrange
      useTimeMachineStore.getState().setCurrentProject("CO-E2E-ROBOT");
      useTimeMachineStore.getState().selectBranch("BR-CO-2026-016");

      const mockUpdate = vi.fn();
      const mockApiMethods = {
        update: mockUpdate,
      };

      const factory = createVersionedResourceHooks(
        "wbes",
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        queryKeys.wbes as any,
        mockApiMethods as VersionedApiMethods<unknown, Record<string, unknown>, Record<string, unknown>>,
      );

      const mockResponse = {
        id: "wbe-123",
        wbe_id: "WBE-001",
        name: "Updated WBE",
        branch: "BR-CO-2026-016",
      };
      mockUpdate.mockResolvedValue(mockResponse);

      // Act
      const { result } = renderHook(() => factory.useUpdate(), {
        wrapper: ({ children }) =>
          React.createElement(
            QueryClientProvider,
            { client: queryClient },
            React.createElement(TimeMachineProvider, null, children),
          ),
      });

      result.current.mutate({
        id: "wbe-123",
        data: { name: "Updated WBE", budget_allocation: "200000.00" },
      });

      // Assert
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockUpdate).toHaveBeenCalledWith(
        "wbe-123",
        expect.objectContaining({
          name: "Updated WBE",
          budget_allocation: "200000.00",
          branch: "BR-CO-2026-016",
        }),
      );
    });
  });

  /**
   * Edge Cases and Error Handling
   */
  describe("Edge Cases: Branch Isolation", () => {
    it("should default to main branch when no Time Machine context", async () => {
      // Arrange - No Time Machine context set
      const mockUpdate = vi.fn();
      const mockApiMethods = {
        update: mockUpdate,
      };

      const factory = createVersionedResourceHooks(
        "cost-elements",
        queryKeys.costElements,
        mockApiMethods as VersionedApiMethods<unknown, Record<string, unknown>, Record<string, unknown>>,
      );

      mockUpdate.mockResolvedValue({ id: "ce-123", branch: "main" });

      // Act
      const { result } = renderHook(() => factory.useUpdate(), {
        wrapper: ({ children }) =>
          React.createElement(
            QueryClientProvider,
            { client: queryClient },
            React.createElement(TimeMachineProvider, null, children),
          ),
      });

      result.current.mutate({
        id: "ce-123",
        data: { name: "Test" },
      });

      // Assert
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockUpdate).toHaveBeenCalledWith(
        "ce-123",
        expect.objectContaining({
          branch: "main",
        }),
      );
    });

    it("should allow explicit branch override even with Time Machine context", async () => {
      // Arrange - Time Machine set to one branch, but explicit override used
      useTimeMachineStore.getState().setCurrentProject("CO-E2E-ROBOT");
      useTimeMachineStore.getState().selectBranch("BR-CO-2026-016");

      const mockUpdate = vi.fn();
      const mockApiMethods = {
        update: mockUpdate,
      };

      const factory = createVersionedResourceHooks(
        "cost-elements",
        queryKeys.costElements,
        mockApiMethods as VersionedApiMethods<unknown, Record<string, unknown>, Record<string, unknown>>,
      );

      mockUpdate.mockResolvedValue({ id: "ce-123", branch: "BR-CUSTOM" });

      // Act - Explicitly override to a different branch
      const { result } = renderHook(() => factory.useUpdate(), {
        wrapper: ({ children }) =>
          React.createElement(
            QueryClientProvider,
            { client: queryClient },
            React.createElement(TimeMachineProvider, null, children),
          ),
      });

      result.current.mutate({
        id: "ce-123",
        data: { name: "Test", branch: "BR-CUSTOM" },
      });

      // Assert
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Explicit branch should override Time Machine branch
      expect(mockUpdate).toHaveBeenCalledWith(
        "ce-123",
        expect.objectContaining({
          branch: "BR-CUSTOM",
        }),
      );

      expect(mockUpdate).not.toHaveBeenCalledWith(
        "ce-123",
        expect.objectContaining({
          branch: "BR-CO-2026-016",
        }),
      );
    });
  });
});
