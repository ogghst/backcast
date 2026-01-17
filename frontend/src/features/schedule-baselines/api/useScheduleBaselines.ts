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
} from "@tanstack/react-query";
import { toast } from "sonner";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { request as __request } from "@/api/generated/core/request";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import type { PaginatedResponse } from "@/types/api";

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
  queryOptions?: any;
}

/**
 * Fetch schedule baselines for a cost element with optional filtering.
 */
export const useScheduleBaselines = (params?: ScheduleBaselineListParams) => {
  const { asOf, mode, branch: tmBranch } = useTimeMachineParams();

  return useQuery<PaginatedResponse<ScheduleBaselineRead>>({
    queryKey: ["schedule_baselines", params, { asOf, mode, branch: tmBranch }],
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
  branch: string = "main"
) => {
  const { asOf, mode } = useTimeMachineParams();

  return useQuery<ScheduleBaselineRead>({
    queryKey: ["schedule_baselines", scheduleBaselineId, branch, { asOf, mode }],
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
  branch: string = "main"
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<PlannedValueResponse>({
    queryKey: ["schedule_baselines", scheduleBaselineId, "pv", { currentDate, bac, branch, asOf }],
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
  >
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateWithBranch) => {
      const { branch, ...rest } = data;
      const payload = {
        ...rest,
        control_date: asOf || null,
      };
      return __request(OpenAPI, {
        method: "POST",
        url: "/api/v1/schedule-baselines",
        query: { branch: branch || "main" },
        body: payload,
      }) as Promise<ScheduleBaselineRead>;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ["schedule_baselines"] });
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
  >
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateWithBranch }) => {
      const { branch, ...rest } = data;
      const payload = {
        ...rest,
        control_date: asOf || null,
      };
      return __request(OpenAPI, {
        method: "PUT",
        url: `/api/v1/schedule-baselines/${id}`,
        query: { branch: branch || "main" },
        body: payload,
      }) as Promise<ScheduleBaselineRead>;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ["schedule_baselines"] });
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
  mutationOptions?: Omit<UseMutationOptions<void, Error, { id: string; branch?: string }>, "mutationFn">
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, branch = "main" }: { id: string; branch?: string }) => {
      return __request(OpenAPI, {
        method: "DELETE",
        url: `/api/v1/schedule-baselines/${id}`,
        query: {
          branch,
          control_date: asOf || undefined,
        },
      }) as Promise<void>;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ["schedule_baselines"] });
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
    queryKey: ["schedule_baselines", scheduleBaselineId, "history"],
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
