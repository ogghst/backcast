/**
 * Nested Schedule Baseline API hooks (1:1 relationship with Cost Elements)
 *
 * These hooks use the new nested API structure where schedule baselines
 * are accessed via cost elements, enforcing the 1:1 relationship.
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
import { queryKeys } from "@/api/queryKeys";

// Domain types for Schedule Baseline (matching backend schemas)
export interface ScheduleBaselineRead {
  schedule_baseline_id: string;
  cost_element_id: string;
  name: string;
  start_date: string; // ISO 8601 datetime
  end_date: string; // ISO 8601 datetime
  progression_type: "LINEAR" | "GAUSSIAN" | "LOGARITHMIC";
  description?: string;
  cost_element_code?: string;
  cost_element_name?: string;
  branch: string;
  created_by: string;
}

export interface ScheduleBaselineCreate {
  name: string;
  start_date: string; // ISO 8601 datetime
  end_date: string; // ISO 8601 datetime
  progression_type?: "LINEAR" | "GAUSSIAN" | "LOGARITHMIC";
  description?: string;
}

export interface ScheduleBaselineUpdate {
  name?: string;
  start_date?: string;
  end_date?: string;
  progression_type?: "LINEAR" | "GAUSSIAN" | "LOGARITHMIC";
  description?: string;
}

// Extended types for Branch support
export type CreateWithBranch = ScheduleBaselineCreate & { branch?: string };
export type UpdateWithBranch = ScheduleBaselineUpdate & { branch?: string };

/**
 * Fetch the schedule baseline for a specific cost element.
 *
 * Uses the new nested endpoint: GET /api/v1/cost-elements/{id}/schedule-baseline
 *
 * @param costElementId - The cost element ID to fetch baseline for
 * @param branch - Branch to query (default: "main")
 * @param queryOptions - Additional TanStack Query options
 */
export const useCostElementScheduleBaseline = (
  costElementId: string,
  branch: string = "main",
  queryOptions?: Omit<
    UseQueryOptions<ScheduleBaselineRead>,
    "queryKey" | "queryFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<ScheduleBaselineRead>({
    queryKey: queryKeys.scheduleBaselines.byCostElement(
      costElementId,
      branch,
      asOf,
    ),
    queryFn: async () => {
      const res = await __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/cost-elements/${costElementId}/schedule-baseline`,
        query: {
          branch,
          as_of: asOf || undefined,
        },
      });
      return res as ScheduleBaselineRead;
    },
    enabled: !!costElementId,
    ...queryOptions,
  });
};

/**
 * Create a new schedule baseline for a cost element.
 *
 * Uses the new nested endpoint: POST /api/v1/cost-elements/{id}/schedule-baseline
 *
 * @param mutationOptions - Additional TanStack Query mutation options
 */
export const useCreateCostElementScheduleBaseline = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ScheduleBaselineRead,
      Error,
      {
        costElementId: string;
        name: string;
        start_date: string;
        end_date: string;
        progression_type?: "LINEAR" | "GAUSSIAN" | "LOGARITHMIC";
        description?: string;
        branch?: string;
      }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      costElementId,
      branch,
      ...data
    }: {
      costElementId: string;
      name: string;
      start_date: string;
      end_date: string;
      progression_type?: "LINEAR" | "GAUSSIAN" | "LOGARITHMIC";
      description?: string;
      branch?: string;
    }) => {
      const payload = {
        ...data,
        branch: branch || "main",
        control_date: asOf || null,
      };

      return (await __request(OpenAPI, {
        method: "POST",
        url: `/api/v1/cost-elements/${costElementId}/schedule-baseline`,
        body: payload,
      })) as Promise<ScheduleBaselineRead>;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.scheduleBaselines.all,
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });

      toast.success("Schedule Baseline created successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating Schedule Baseline: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Update an existing schedule baseline for a cost element.
 *
 * Uses the new nested endpoint: PUT /api/v1/cost-elements/{id}/schedule-baseline/{baseline_id}
 *
 * @param mutationOptions - Additional TanStack Query mutation options
 */
export const useUpdateCostElementScheduleBaseline = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ScheduleBaselineRead,
      Error,
      {
        costElementId: string;
        baselineId: string;
        data: ScheduleBaselineUpdate;
        branch?: string;
      }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      costElementId,
      baselineId,
      data,
      branch,
    }: {
      costElementId: string;
      baselineId: string;
      data: ScheduleBaselineUpdate;
      branch?: string;
    }) => {
      const payload = {
        ...data,
        branch: branch || "main",
        control_date: asOf || null,
      };

      return (await __request(OpenAPI, {
        method: "PUT",
        url: `/api/v1/cost-elements/${costElementId}/schedule-baseline/${baselineId}`,
        body: payload,
      })) as Promise<ScheduleBaselineRead>;
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
  });
};

/**
 * Soft delete a schedule baseline for a cost element.
 *
 * Uses the new nested endpoint: DELETE /api/v1/cost-elements/{id}/schedule-baseline/{baseline_id}
 *
 * @param mutationOptions - Additional TanStack Query mutation options
 */
export const useDeleteCostElementScheduleBaseline = (
  mutationOptions?: Omit<
    UseMutationOptions<
      void,
      Error,
      {
        costElementId: string;
        baselineId: string;
        branch?: string;
      }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      costElementId,
      baselineId,
      branch,
    }: {
      costElementId: string;
      baselineId: string;
      branch?: string;
    }) => {
      (await __request(OpenAPI, {
        method: "DELETE",
        url: `/api/v1/cost-elements/${costElementId}/schedule-baseline/${baselineId}`,
        query: {
          branch: branch || "main",
          control_date: asOf || undefined,
        },
      })) as Promise<void>;
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
  });
};
