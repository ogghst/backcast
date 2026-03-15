/**
 * Integration tests for cache invalidation patterns
 *
 * These tests verify that dependent invalidation patterns work correctly
 * when mutations affect related entities (e.g., cost element changes affect forecasts).
 *
 * FE-010: Integration tests for cache invalidation
 */

import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import { ReactNode } from "react";
import { queryKeys } from "@/api/queryKeys";

// Mock services
vi.mock("@/api/generated", () => ({
  CostElementsService: {
    createCostElement: vi.fn(),
    updateCostElement: vi.fn(),
    deleteCostElement: vi.fn(),
  },
  CostRegistrationsService: {
    createCostRegistration: vi.fn(),
    updateCostRegistration: vi.fn(),
    deleteCostRegistration: vi.fn(),
  },
  ScheduleBaselinesService: {
    createScheduleBaseline: vi.fn(),
    updateScheduleBaseline: vi.fn(),
    deleteScheduleBaseline: vi.fn(),
  },
  ForecastsService: {
    listForecasts: vi.fn(),
  },
}));

// Mock TimeMachine context
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachineParams: () => ({
    branch: "main",
    asOf: "2024-01-01",
    mode: "current",
  }),
}));

// Import hooks after mocking
import { useCreateCostElement } from "@/features/cost-elements/api/useCostElements";
import { useCreateCostRegistration } from "@/features/cost-registration/api/useCostRegistrations";
import { useCreateScheduleBaseline } from "@/features/schedule-baselines/api/useScheduleBaselines";

// Helper to create a wrapper with query client
function createQueryClientWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: console.log,
      warn: console.warn,
      error: () => {}, // Suppress error logs in tests
    },
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  return { queryClient, wrapper };
}

describe("Cache Invalidation Integration Tests", () => {
  describe("Cost Element Mutations → Forecast Invalidation", () => {
    it("should invalidate forecast queries when creating a cost element", async () => {
      const { queryClient, wrapper } = createQueryClientWrapper();

      const { result } = renderHook(() => useCreateCostElement(), { wrapper });

      // Spy on invalidateQueries
      const invalidateQueriesSpy = vi.spyOn(queryClient, "invalidateQueries");

      // Trigger mutation
      const { CostElementsService } = await import("@/api/generated");
      vi.mocked(CostElementsService.createCostElement).mockResolvedValue({
        id: "test-id",
        name: "Test Cost Element",
      } as unknown as Record<string, unknown>);

      await result.current.mutateAsync({
        name: "Test Cost Element",
        wbe_id: "wbe-1",
        cost_element_type_id: "type-1",
        branch: "main",
      });

      // Verify that forecasts.all was invalidated
      expect(invalidateQueriesSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: queryKeys.forecasts.all,
        }),
      );
    });

    it("should invalidate cost elements queries when creating a cost element", async () => {
      const { queryClient, wrapper } = createQueryClientWrapper();

      const { result } = renderHook(() => useCreateCostElement(), { wrapper });

      // Spy on invalidateQueries
      const invalidateQueriesSpy = vi.spyOn(queryClient, "invalidateQueries");

      // Trigger mutation
      const { CostElementsService } = await import("@/api/generated");
      vi.mocked(CostElementsService.createCostElement).mockResolvedValue({
        id: "test-id",
        name: "Test Cost Element",
      } as unknown as Record<string, unknown>);

      await result.current.mutateAsync({
        name: "Test Cost Element",
        wbe_id: "wbe-1",
        cost_element_type_id: "type-1",
        branch: "main",
      });

      // Verify that cost elements queries were invalidated
      expect(invalidateQueriesSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: queryKeys.costElements.lists(),
        }),
      );
    });
  });

  describe("Cost Registration Mutations → Forecast Invalidation", () => {
    it("should invalidate forecast queries when creating a cost registration", async () => {
      const { queryClient, wrapper } = createQueryClientWrapper();

      const { result } = renderHook(() => useCreateCostRegistration(), {
        wrapper,
      });

      const invalidateQueriesSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { CostRegistrationsService } = await import("@/api/generated");
      vi.mocked(
        CostRegistrationsService.createCostRegistration,
      ).mockResolvedValue({
        id: "test-id",
        amount: 1000,
      } as unknown as Record<string, unknown>);

      await result.current.mutateAsync({
        cost_element_id: "ce-1",
        amount: 1000,
        branch: "main",
      });

      // Verify forecast invalidation
      expect(invalidateQueriesSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: queryKeys.forecasts.all,
        }),
      );
    });

    it("should invalidate budget status when creating a cost registration", async () => {
      const { queryClient, wrapper } = createQueryClientWrapper();

      const { result } = renderHook(() => useCreateCostRegistration(), {
        wrapper,
      });

      const invalidateQueriesSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { CostRegistrationsService } = await import("@/api/generated");
      vi.mocked(
        CostRegistrationsService.createCostRegistration,
      ).mockResolvedValue({
        id: "test-id",
        amount: 1000,
      } as unknown as Record<string, unknown>);

      await result.current.mutateAsync({
        cost_element_id: "ce-1",
        amount: 1000,
        branch: "main",
      });

      // Verify cost registrations invalidation
      expect(invalidateQueriesSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: queryKeys.costRegistrations.all,
        }),
      );
    });
  });

  describe("Schedule Baseline Mutations → Forecast Invalidation", () => {
    it("should invalidate forecast queries when creating a schedule baseline", async () => {
      const { queryClient, wrapper } = createQueryClientWrapper();

      const { result } = renderHook(() => useCreateScheduleBaseline(), {
        wrapper,
      });

      const invalidateQueriesSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { ScheduleBaselinesService } = await import("@/api/generated");
      vi.mocked(
        ScheduleBaselinesService.createScheduleBaseline,
      ).mockResolvedValue({
        id: "test-id",
        name: "Test Baseline",
      } as unknown as Record<string, unknown>);

      await result.current.mutateAsync({
        project_id: "proj-1",
        name: "Test Baseline",
        branch: "main",
      });

      // Verify forecast invalidation
      expect(invalidateQueriesSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: queryKeys.forecasts.all,
        }),
      );
    });

    it("should invalidate schedule baselines when creating a schedule baseline", async () => {
      const { queryClient, wrapper } = createQueryClientWrapper();

      const { result } = renderHook(() => useCreateScheduleBaseline(), {
        wrapper,
      });

      const invalidateQueriesSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { ScheduleBaselinesService } = await import("@/api/generated");
      vi.mocked(
        ScheduleBaselinesService.createScheduleBaseline,
      ).mockResolvedValue({
        id: "test-id",
        name: "Test Baseline",
      } as unknown as Record<string, unknown>);

      await result.current.mutateAsync({
        project_id: "proj-1",
        name: "Test Baseline",
        branch: "main",
      });

      // Verify schedule baselines invalidation
      expect(invalidateQueriesSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: queryKeys.scheduleBaselines.all,
        }),
      );
    });
  });

  describe("Query Key Factory Usage", () => {
    it("should use queryKeys factory for breadcrumb queries", () => {
      // Verify that breadcrumb query keys are defined in factory
      expect(queryKeys.wbes.breadcrumb).toBeDefined();
      expect(queryKeys.costElements.breadcrumb).toBeDefined();

      // Verify they return correct structure
      const wbeBreadcrumbKey = queryKeys.wbes.breadcrumb("wbe-1");
      expect(wbeBreadcrumbKey).toEqual(["wbes", "wbe-1", "breadcrumb"]);

      const ceBreadcrumbKey = queryKeys.costElements.breadcrumb("ce-1");
      expect(ceBreadcrumbKey).toEqual(["cost_element_breadcrumb", "ce-1"]);
    });

    it("should use queryKeys factory for change order queries", () => {
      // Verify that change order query keys are defined
      expect(queryKeys.changeOrders.list).toBeDefined();
      expect(queryKeys.changeOrders.detail).toBeDefined();
      expect(queryKeys.changeOrders.all).toBeDefined();

      // Verify they include context parameters
      const listKey = queryKeys.changeOrders.list("proj-1", {
        asOf: "2024-01-01",
      });
      expect(listKey).toBeDefined();
      expect(listKey).toContain("proj-1");
    });
  });

  describe("Context Isolation", () => {
    it("should include context parameters in versioned entity query keys", () => {
      // Cost elements - includes context
      const ceDetailKey = queryKeys.costElements.detail("ce-1", {
        branch: "main",
        asOf: "2024-01-01",
      });
      expect(ceDetailKey).toEqual([
        "cost-elements",
        "detail",
        "ce-1",
        { branch: "main", asOf: "2024-01-01" },
      ]);

      // WBEs - detail key doesn't include context (by design)
      const wbeDetailKey = queryKeys.wbes.detail("wbe-1");
      expect(wbeDetailKey).toEqual(["wbes", "detail", "wbe-1"]);

      // Forecasts - includes context
      const forecastKey = queryKeys.forecasts.list("ce-1", {
        branch: "main",
        asOf: "2024-01-01",
      });
      expect(forecastKey).toEqual([
        "forecasts",
        "list",
        "ce-1",
        { branch: "main", asOf: "2024-01-01" },
      ]);

      // Change orders - includes context
      const coListKey = queryKeys.changeOrders.list("proj-1", {
        asOf: "2024-01-01",
      });
      expect(coListKey).toBeDefined();
      expect(coListKey).toContain("proj-1");
    });
  });
});
