/**
 * Schedule Baseline API hooks
 *
 * Provides TanStack Query hooks for Schedule Baseline CRUD operations,
 * including the specialized Planned Value (PV) calculation endpoint.
 */

import {
  useMutation,
  useQueryClient,
  type UseMutationOptions,
  useQuery,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { request as __request } from "@/api/generated/core/request";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";
import { ScheduleBaselinesService } from "@/api/generated";

// Domain types for Schedule Baseline (matching backend schemas)
export interface ScheduleBaselineRead {
  id: string;
  schedule_baseline_id: string;
  cost_element_id: string;
  name: string;
  start_date: string; // ISO 8601 datetime
  end_date: string; // ISO 8601 datetime
  progression_type: "LINEAR" | "GAUSSIAN" | "LOGARITHMIC";
  description?: string;
  created_by: string;
  branch: string;
}

export interface ScheduleBaselineCreate {
  name: string;
  start_date: string; // ISO 8601 datetime
  end_date: string; // ISO 8601 datetime
  progression_type?: "LINEAR" | "GAUSSIAN" | "LOGARITHMIC";
  description?: string;
  cost_element_id: string;
}

export interface ScheduleBaselineUpdate {
  name?: string;
  start_date?: string;
  end_date?: string;
  progression_type?: "LINEAR" | "GAUSSIAN" | "LOGARITHMIC";
  description?: string;
}

// Planned Value calculation response
export interface PlannedValueResponse {
  schedule_baseline_id: string;
  current_date: string;
  bac: string;
  progress: number;
  pv: string;
  progression_type: string;
}

// Extended types for Branch support
export type CreateWithBranch = ScheduleBaselineCreate & { branch?: string };
export type UpdateWithBranch = ScheduleBaselineUpdate & { branch?: string };

/**
 * Schedule Baseline API parameters for filtering and pagination.
 */
interface ScheduleBaselineListParams {
  branch?: string;
  cost_element_id?: string;
  pagination?: { current?: number; pageSize?: number };
  queryOptions?: Partial<
    UseQueryOptions<PaginatedResponse<ScheduleBaselineRead>, Error>
  >;
}

/**
 * Fetch schedule baselines for a cost element with optional filtering.
 */
export const useScheduleBaselines = (params?: ScheduleBaselineListParams) => {
  const { asOf, mode, branch: tmBranch } = useTimeMachineParams();

  return useQuery<PaginatedResponse<ScheduleBaselineRead>>({
    queryKey: queryKeys.scheduleBaselines.list(
      params?.cost_element_id || "global",
      {
        ...params,
        asOf,
        mode,
        branch: tmBranch,
      },
    ),
    queryFn: async () => {
      const {
        branch = tmBranch || "main",
        cost_element_id,
        pagination,
      } = params || {};
      const page = pagination?.current || 1;
      const perPage = pagination?.pageSize || 20;

      // Manual request to support all query parameters
      const res = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/schedule-baselines",
        query: {
          page,
          per_page: perPage,
          branch,
          cost_element_id: cost_element_id,
          as_of: asOf || undefined,
        },
      });

      if (Array.isArray(res)) {
        return {
          items: res,
          total: res.length,
          page: 1,
          per_page: res.length,
        };
      }
      return res as unknown as PaginatedResponse<ScheduleBaselineRead>;
    },
    ...params?.queryOptions,
  });
};

/**
 * Fetch a single schedule baseline by ID.
 */
export const useScheduleBaseline = (
  scheduleBaselineId: string,
  branch: string = "main",
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<ScheduleBaselineRead>({
    queryKey: queryKeys.scheduleBaselines.detail(scheduleBaselineId, {
      branch,
      asOf,
    }),
    queryFn: async () => {
      const res = await __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/schedule-baselines/${scheduleBaselineId}`,
        query: {
          branch,
          as_of: asOf || undefined,
        },
      });
      return res as ScheduleBaselineRead;
    },
    enabled: !!scheduleBaselineId,
  });
};

/**
 * Calculate Planned Value (PV) for a schedule baseline.
 *
 * PV = BAC × Progress
 *
 * @param scheduleBaselineId The baseline to calculate PV for
 * @param currentDate The date to calculate progress for
 * @param bac Budget at Completion amount
 * @param branch Branch to query (default: "main")
 */
export const usePlannedValue = (
  scheduleBaselineId: string,
  currentDate: string,
  bac: string,
  branch: string = "main",
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<PlannedValueResponse>({
    queryKey: queryKeys.scheduleBaselines.pv(scheduleBaselineId, {
      currentDate,
      bac,
      branch,
      asOf,
    }),
    queryFn: async () => {
      const res = await __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/schedule-baselines/${scheduleBaselineId}/pv`,
        query: {
          current_date: currentDate,
          bac,
          branch,
          as_of: asOf || undefined,
        },
      });
      return res as PlannedValueResponse;
    },
    enabled: !!scheduleBaselineId && !!currentDate && !!bac,
  });
};

/**
 * Create a new schedule baseline.
 */
export const useCreateScheduleBaseline = (
  mutationOptions?: Omit<
    UseMutationOptions<ScheduleBaselineRead, Error, CreateWithBranch>,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateWithBranch) => {
      const { branch, ...rest } = data;
      const payload: ScheduleBaselineCreate = {
        ...rest,
        branch: branch || "main",
        control_date: asOf || undefined,
      };
      return ScheduleBaselinesService.createScheduleBaseline(payload);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.scheduleBaselines.all,
      });
      // Invalidate forecasts as PV changes affect EV metrics
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });
      toast.success("Schedule Baseline created successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating Schedule Baseline: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};

/**
 * Update an existing schedule baseline (creates new version).
 */
export const useUpdateScheduleBaseline = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ScheduleBaselineRead,
      Error,
      { id: string; data: UpdateWithBranch }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateWithBranch }) => {
      const { branch, ...rest } = data;
      const payload: ScheduleBaselineUpdate = {
        ...rest,
        branch: branch || "main",
        control_date: asOf || undefined,
      };
      return ScheduleBaselinesService.updateScheduleBaseline(id, payload);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.scheduleBaselines.all,
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });
      toast.success("Schedule Baseline updated successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating Schedule Baseline: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};

/**
 * Soft delete a schedule baseline.
 */
export const useDeleteScheduleBaseline = (
  mutationOptions?: Omit<
    UseMutationOptions<void, Error, { id: string; branch?: string }>,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, branch }: { id: string; branch?: string }) => {
      // Service.deleteScheduleBaseline(id, branch, control_date)
      return ScheduleBaselinesService.deleteScheduleBaseline(
        id,
        branch || "main",
        asOf || undefined,
      );
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.scheduleBaselines.all,
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });
      toast.success("Schedule Baseline deleted successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting Schedule Baseline: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};

/**
 * Get version history for a schedule baseline.
 */
export const useScheduleBaselineHistory = (scheduleBaselineId: string) => {
  return useQuery<ScheduleBaselineRead[]>({
    queryKey: queryKeys.scheduleBaselines.history(scheduleBaselineId),
    queryFn: async () => {
      const res = await __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/schedule-baselines/${scheduleBaselineId}/history`,
      });
      return res as ScheduleBaselineRead[];
    },
    enabled: !!scheduleBaselineId,
  });
};
