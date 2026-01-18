/**
 * Tests for nested schedule baseline API hooks (1:1 relationship)
 *
 * RED Phase: These tests are written FIRST and will FAIL initially.
 * They define the expected behavior of the new nested API structure.
 */

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { request as __request } from "@/api/generated/core/request";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import {
  useCostElementScheduleBaseline,
  useCreateCostElementScheduleBaseline,
  useUpdateCostElementScheduleBaseline,
  useDeleteCostElementScheduleBaseline,
} from "./useCostElementScheduleBaseline";

// Mock TimeMachine context BEFORE importing hooks
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachineParams: () => ({
    asOf: undefined,
    mode: "current",
    branch: "main",
  }),
  TimeMachineProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock the OpenAPI request function
vi.mock("@/api/generated/core/request", () => ({
  request: vi.fn(),
}));

// Mock OpenAPI
vi.mock("@/api/generated/core/OpenAPI", () => ({
  OpenAPI: {
    BASE: "http://localhost:8000",
    TOKEN: undefined,
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  // eslint-disable-next-line @typescript-eslint/ban-types
  return ({ children }: { children: React.ReactNode }) => {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
};

describe("useCostElementScheduleBaseline - Nested API Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("useCostElementScheduleBaseline - GET", () => {
    it("should fetch schedule baseline for a cost element", async () => {
      const mockBaseline = {
        schedule_baseline_id: "baseline-123",
        cost_element_id: "ce-123",
        name: "Default Schedule",
        start_date: "2026-01-01T00:00:00",
        end_date: "2026-04-01T00:00:00",
        progression_type: "LINEAR",
        description: "Test baseline",
        cost_element_code: "CE-001",
        cost_element_name: "Test Cost Element",
        branch: "main",
        created_by: "user-123",
      };

      vi.mocked(__request).mockResolvedValue(mockBaseline);

      const { result } = renderHook(
        () => useCostElementScheduleBaseline("ce-123", "main"),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(__request).toHaveBeenCalledWith(
        OpenAPI,
        expect.objectContaining({
          method: "GET",
          url: "/api/v1/cost-elements/ce-123/schedule-baseline",
          query: { branch: "main", as_of: undefined },
        })
      );

      expect(result.current.data).toEqual(mockBaseline);
    });

    it("should handle 404 when baseline not found", async () => {
      const error = new Error("Not Found");
      (error as any).status = 404;
      vi.mocked(__request).mockRejectedValue(error);

      const { result } = renderHook(
        () => useCostElementScheduleBaseline("ce-123", "main"),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toEqual(error);
    });

    it("should include branch and asOf parameters", async () => {
      vi.mocked(__request).mockResolvedValue({});

      const { result } = renderHook(
        () => useCostElementScheduleBaseline("ce-123", "feature-branch"),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(__request).toHaveBeenCalledWith(
        OpenAPI,
        expect.objectContaining({
          query: { branch: "feature-branch", as_of: undefined },
        })
      );
    });
  });

  describe("useCreateCostElementScheduleBaseline - POST", () => {
    it("should create schedule baseline for cost element", async () => {
      const mockCreatedBaseline = {
        schedule_baseline_id: "baseline-new",
        cost_element_id: "ce-123",
        name: "New Schedule",
        start_date: "2026-01-01T00:00:00",
        end_date: "2026-04-01T00:00:00",
        progression_type: "LINEAR",
        branch: "main",
        created_by: "user-123",
      };

      vi.mocked(__request).mockResolvedValue(mockCreatedBaseline);

      const { result } = renderHook(
        () => useCreateCostElementScheduleBaseline(),
        { wrapper: createWrapper() }
      );

      const createData = {
        costElementId: "ce-123",
        name: "New Schedule",
        start_date: "2026-01-01T00:00:00",
        end_date: "2026-04-01T00:00:00",
        progression_type: "LINEAR" as const,
      };

      result.current.mutate(createData);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(__request).toHaveBeenCalledWith(
        OpenAPI,
        expect.objectContaining({
          method: "POST",
          url: "/api/v1/cost-elements/ce-123/schedule-baseline",
          query: { branch: "main" },
          body: expect.objectContaining({
            name: "New Schedule",
            start_date: "2026-01-01T00:00:00",
            end_date: "2026-04-01T00:00:00",
            progression_type: "LINEAR",
          }),
        })
      );
    });

    it("should handle duplicate baseline error (400)", async () => {
      const error = new Error("Baseline already exists");
      (error as any).status = 400;
      vi.mocked(__request).mockRejectedValue(error);

      const { result } = renderHook(
        () => useCreateCostElementScheduleBaseline(),
        { wrapper: createWrapper() }
      );

      result.current.mutate({
        costElementId: "ce-123",
        name: "Duplicate",
        start_date: "2026-01-01T00:00:00",
        end_date: "2026-04-01T00:00:00",
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toEqual(error);
    });
  });

  describe("useUpdateCostElementScheduleBaseline - PUT", () => {
    it("should update schedule baseline for cost element", async () => {
      const mockUpdatedBaseline = {
        schedule_baseline_id: "baseline-123",
        cost_element_id: "ce-123",
        name: "Updated Schedule",
        start_date: "2026-01-15T00:00:00",
        end_date: "2026-04-15T00:00:00",
        progression_type: "GAUSSIAN",
        branch: "main",
        created_by: "user-123",
      };

      vi.mocked(__request).mockResolvedValue(mockUpdatedBaseline);

      const { result } = renderHook(
        () => useUpdateCostElementScheduleBaseline(),
        { wrapper: createWrapper() }
      );

      const updateData = {
        costElementId: "ce-123",
        baselineId: "baseline-123",
        data: {
          name: "Updated Schedule",
          start_date: "2026-01-15T00:00:00",
          end_date: "2026-04-15T00:00:00",
          progression_type: "GAUSSIAN" as const,
        },
      };

      result.current.mutate(updateData);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(__request).toHaveBeenCalledWith(
        OpenAPI,
        expect.objectContaining({
          method: "PUT",
          url: "/api/v1/cost-elements/ce-123/schedule-baseline/baseline-123",
          query: { branch: "main" },
          body: expect.objectContaining({
            name: "Updated Schedule",
            progression_type: "GAUSSIAN",
          }),
        })
      );
    });

    it("should handle partial updates (only provided fields)", async () => {
      const mockUpdatedBaseline = {
        schedule_baseline_id: "baseline-123",
        cost_element_id: "ce-123",
        name: "Default Schedule",
        start_date: "2026-01-01T00:00:00",
        end_date: "2026-04-01T00:00:00",
        progression_type: "LINEAR",
        branch: "main",
        created_by: "user-123",
      };

      vi.mocked(__request).mockResolvedValue(mockUpdatedBaseline);

      const { result } = renderHook(
        () => useUpdateCostElementScheduleBaseline(),
        { wrapper: createWrapper() }
      );

      const updateData = {
        costElementId: "ce-123",
        baselineId: "baseline-123",
        data: {
          name: "Only Name Changed",
        },
      };

      result.current.mutate(updateData);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(__request).toHaveBeenCalledWith(
        OpenAPI,
        expect.objectContaining({
          body: expect.objectContaining({
            name: "Only Name Changed",
          }),
        })
      );
    });
  });

  describe("useDeleteCostElementScheduleBaseline - DELETE", () => {
    it("should soft delete schedule baseline", async () => {
      vi.mocked(__request).mockResolvedValue(undefined);

      const { result } = renderHook(
        () => useDeleteCostElementScheduleBaseline(),
        { wrapper: createWrapper() }
      );

      const deleteData = {
        costElementId: "ce-123",
        baselineId: "baseline-123",
      };

      result.current.mutate(deleteData);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(__request).toHaveBeenCalledWith(
        OpenAPI,
        expect.objectContaining({
          method: "DELETE",
          url: "/api/v1/cost-elements/ce-123/schedule-baseline/baseline-123",
          query: { branch: "main", control_date: undefined },
        })
      );
    });

    it("should handle 404 when baseline not found", async () => {
      const error = new Error("Baseline not found");
      (error as any).status = 404;
      vi.mocked(__request).mockRejectedValue(error);

      const { result } = renderHook(
        () => useDeleteCostElementScheduleBaseline(),
        { wrapper: createWrapper() }
      );

      result.current.mutate({
        costElementId: "ce-123",
        baselineId: "baseline-123",
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toEqual(error);
    });
  });

  describe("Branch Isolation", () => {
    it("should respect branch parameter in all operations", async () => {
      vi.mocked(__request).mockResolvedValue({});

      const { result: getResult } = renderHook(
        () => useCostElementScheduleBaseline("ce-123", "feature-branch"),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(getResult.current.isSuccess).toBe(true));
      expect(__request).toHaveBeenCalledWith(
        OpenAPI,
        expect.objectContaining({
          query: { branch: "feature-branch", as_of: undefined },
        })
      );

      vi.clearAllMocks();

      const { result: createResult } = renderHook(
        () => useCreateCostElementScheduleBaseline(),
        { wrapper: createWrapper() }
      );

      createResult.current.mutate({
        costElementId: "ce-123",
        branch: "feature-branch",
        name: "Test",
        start_date: "2026-01-01T00:00:00",
        end_date: "2026-04-01T00:00:00",
      });

      await waitFor(() => expect(createResult.current.isSuccess).toBe(true));
      expect(__request).toHaveBeenCalledWith(
        OpenAPI,
        expect.objectContaining({
          query: { branch: "feature-branch" },
        })
      );
    });
  });
});
