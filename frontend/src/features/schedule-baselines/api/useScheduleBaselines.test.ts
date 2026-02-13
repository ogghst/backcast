/**
 * Tests for direct schedule baseline API hooks
 *
 * Tests for direct endpoints (not nested under cost elements)
 */

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScheduleBaselinesService } from "@/api/generated";
import {
  useCreateScheduleBaseline,
  useUpdateScheduleBaseline,
  useDeleteScheduleBaseline,
} from "./useScheduleBaselines";

// Mock TimeMachine context BEFORE importing hooks
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachineParams: () => ({
    asOf: undefined,
    mode: "current",
    branch: "main",
  }),
  TimeMachineProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock the ScheduleBaselinesService
vi.mock("@/api/generated", () => ({
  ScheduleBaselinesService: {
    createScheduleBaseline: vi.fn(),
    updateScheduleBaseline: vi.fn(),
    deleteScheduleBaseline: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  // eslint-disable-next-line @typescript-eslint/ban-types
  return ({ children }: { children: React.ReactNode }) => {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
};

describe("useScheduleBaselines - Direct API Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("useCreateScheduleBaseline - POST", () => {
    it("should create schedule baseline with control_date from TimeMachine", async () => {
      const mockBaseline = {
        schedule_baseline_id: "baseline-new",
        cost_element_id: "ce-123",
        name: "New Schedule",
        start_date: "2026-01-01T00:00:00",
        end_date: "2026-04-01T00:00:00",
        progression_type: "LINEAR",
        branch: "main",
        created_by: "user-123",
      };

      vi.mocked(ScheduleBaselinesService.createScheduleBaseline).mockResolvedValue(mockBaseline);

      const { result } = renderHook(() => useCreateScheduleBaseline(), {
        wrapper: createWrapper(),
      });

      const createData = {
        cost_element_id: "ce-123",
        name: "New Schedule",
        start_date: "2026-01-01T00:00:00",
        end_date: "2026-04-01T00:00:00",
        progression_type: "LINEAR" as const,
      };

      result.current.mutate(createData);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(ScheduleBaselinesService.createScheduleBaseline).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "New Schedule",
          branch: "main",
          control_date: undefined,
          cost_element_id: "ce-123",
        })
      );
    });

    it("should include custom branch in payload", async () => {
      const mockBaseline = {
        schedule_baseline_id: "baseline-new",
        cost_element_id: "ce-123",
        name: "New Schedule",
        start_date: "2026-01-01T00:00:00",
        end_date: "2026-04-01T00:00:00",
        progression_type: "LINEAR",
        branch: "feature-branch",
        created_by: "user-123",
      };

      vi.mocked(ScheduleBaselinesService.createScheduleBaseline).mockResolvedValue(mockBaseline);

      const { result } = renderHook(() => useCreateScheduleBaseline(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        cost_element_id: "ce-123",
        name: "New Schedule",
        start_date: "2026-01-01T00:00:00",
        end_date: "2026-04-01T00:00:00",
        branch: "feature-branch",
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(ScheduleBaselinesService.createScheduleBaseline).toHaveBeenCalledWith(
        expect.objectContaining({
          branch: "feature-branch",
        })
      );
    });
  });

  describe("useUpdateScheduleBaseline - PUT", () => {
    it("should update schedule baseline with branch and control_date", async () => {
      const mockBaseline = {
        schedule_baseline_id: "baseline-123",
        cost_element_id: "ce-123",
        name: "Updated Schedule",
        start_date: "2026-01-15T00:00:00",
        end_date: "2026-04-15T00:00:00",
        progression_type: "GAUSSIAN",
        branch: "main",
        created_by: "user-123",
      };

      vi.mocked(ScheduleBaselinesService.updateScheduleBaseline).mockResolvedValue(mockBaseline);

      const { result } = renderHook(() => useUpdateScheduleBaseline(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        id: "baseline-123",
        data: {
          name: "Updated Schedule",
          progression_type: "GAUSSIAN",
        },
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(ScheduleBaselinesService.updateScheduleBaseline).toHaveBeenCalledWith(
        "baseline-123",
        expect.objectContaining({
          name: "Updated Schedule",
          progression_type: "GAUSSIAN",
          branch: "main",
          control_date: undefined,
        })
      );
    });

    it("should include custom branch in update payload", async () => {
      const mockBaseline = {
        schedule_baseline_id: "baseline-123",
        cost_element_id: "ce-123",
        name: "Updated Schedule",
        start_date: "2026-01-15T00:00:00",
        end_date: "2026-04-15T00:00:00",
        progression_type: "GAUSSIAN",
        branch: "feature-branch",
        created_by: "user-123",
      };

      vi.mocked(ScheduleBaselinesService.updateScheduleBaseline).mockResolvedValue(mockBaseline);

      const { result } = renderHook(() => useUpdateScheduleBaseline(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        id: "baseline-123",
        data: {
          name: "Updated Schedule",
          branch: "feature-branch",
        },
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(ScheduleBaselinesService.updateScheduleBaseline).toHaveBeenCalledWith(
        "baseline-123",
        expect.objectContaining({
          branch: "feature-branch",
        })
      );
    });
  });

  describe("useDeleteScheduleBaseline - DELETE", () => {
    it("should delete schedule baseline with control_date query param", async () => {
      vi.mocked(ScheduleBaselinesService.deleteScheduleBaseline).mockResolvedValue(undefined);

      const { result } = renderHook(() => useDeleteScheduleBaseline(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        id: "baseline-123",
        branch: "main",
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(ScheduleBaselinesService.deleteScheduleBaseline).toHaveBeenCalledWith(
        "baseline-123",
        "main",
        undefined
      );
    });

    it("should include custom branch in delete call", async () => {
      vi.mocked(ScheduleBaselinesService.deleteScheduleBaseline).mockResolvedValue(undefined);

      const { result } = renderHook(() => useDeleteScheduleBaseline(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        id: "baseline-123",
        branch: "feature-branch",
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(ScheduleBaselinesService.deleteScheduleBaseline).toHaveBeenCalledWith(
        "baseline-123",
        "feature-branch",
        undefined
      );
    });
  });
});
