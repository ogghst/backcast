import {
  useMutation,
  useQueryClient,
  UseMutationOptions,
  useQuery,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";

import {
  ProgressEntriesService,
  type ProgressEntryRead,
  type ProgressEntryCreate,
} from "@/api/generated";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";

/**
 * Progress Entry API parameters for filtering, pagination, and sorting.
 *
 * Filtering hierarchy: cost_element_id > wbe_id > project_id.
 * At least one filter is recommended for scoped queries.
 * cost_element_id is now optional - wbe_id or project_id can be used instead.
 */
interface ProgressEntryListParams {
  cost_element_id?: string;
  wbe_id?: string;
  project_id?: string;
  page?: number;
  perPage?: number;
  asOf?: string;
  queryOptions?: Omit<
    UseQueryOptions<PaginatedResponse<ProgressEntryRead>>,
    "queryKey" | "queryFn"
  >;
}

/**
 * Custom hook to get progress entries with pagination and filtering.
 *
 * Supports filtering by cost_element_id, wbe_id, or project_id.
 * Progress entries are NOT branchable but support time-travel queries.
 */
export const useProgressEntries = (params?: ProgressEntryListParams) => {
  const { asOf, branch, mode } = useTimeMachineParams();
  const filterId =
    params?.cost_element_id || params?.wbe_id || params?.project_id || "";

  return useQuery<PaginatedResponse<ProgressEntryRead>>({
    queryKey: queryKeys.progressEntries.list(filterId, {
      asOf: params?.asOf || asOf,
      branch,
      mode,
      wbe_id: params?.wbe_id,
      project_id: params?.project_id,
    }),
    queryFn: async () => {
      const {
        cost_element_id,
        wbe_id,
        project_id,
        page = 1,
        perPage = 20,
      } = params || {};

      // Use __request to pass wbe_id and project_id which are not yet
      // in the generated client.
      const res = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/progress-entries",
        query: {
          page,
          per_page: perPage,
          branch,
          mode,
          cost_element_id: cost_element_id || undefined,
          wbe_id: wbe_id || undefined,
          project_id: project_id || undefined,
          as_of: params?.asOf || asOf || undefined,
        },
        errors: { 422: "Validation Error" },
      });

      if (Array.isArray(res)) {
        return {
          items: res,
          total: res.length,
          page: 1,
          per_page: res.length,
        };
      }
      return res as unknown as PaginatedResponse<ProgressEntryRead>;
    },
    enabled:
      !!params?.cost_element_id ||
      !!params?.wbe_id ||
      !!params?.project_id,
    ...params?.queryOptions,
  });
};

/**
 * Hook to get a single progress entry by ID.
 * Supports time-travel queries via asOf parameter.
 */
export const useProgressEntry = (progressEntryId: string, asOf?: string) => {
  const { asOf: tmAsOf } = useTimeMachineParams();

  return useQuery<ProgressEntryRead>({
    queryKey: queryKeys.progressEntries.detail(progressEntryId, {
      asOf: asOf || tmAsOf,
    }),
    queryFn: async () => {
      return await ProgressEntriesService.getProgressEntry(
        progressEntryId,
        asOf || tmAsOf || undefined,
      );
    },
    enabled: !!progressEntryId,
  });
};

/**
 * Hook to get the latest progress entry for a cost element.
 * Supports time-travel queries via asOf parameter.
 */
export const useLatestProgress = (costElementId: string, asOf?: string) => {
  const { asOf: tmAsOf } = useTimeMachineParams();

  return useQuery<ProgressEntryRead | null>({
    queryKey: queryKeys.progressEntries.latest(costElementId, {
      asOf: asOf || tmAsOf,
    }),
    queryFn: async () => {
      return await ProgressEntriesService.getLatestProgress(
        costElementId,
        asOf || tmAsOf || undefined,
      );
    },
    enabled: !!costElementId,
    staleTime: 60000, // Consider fresh for 1 minute
  });
};

/**
 * Hook to get progress history for a cost element.
 * Returns all progress entries ordered by valid_time descending.
 */
export const useProgressHistory = (
  costElementId: string,
  page: number = 1,
  perPage: number = 20,
) => {
  return useQuery<PaginatedResponse<ProgressEntryRead>>({
    queryKey: queryKeys.progressEntries.history(costElementId),
    queryFn: async () => {
      const res = await ProgressEntriesService.getProgressHistory(
        costElementId,
        page,
        perPage,
      );

      if (Array.isArray(res)) {
        return {
          items: res,
          total: res.length,
          page: 1,
          per_page: res.length,
        };
      }
      return res as unknown as PaginatedResponse<ProgressEntryRead>;
    },
    enabled: !!costElementId,
  });
};

/**
 * Custom create hook for progress entries.
 * Progress entries are NOT branchable (global facts).
 */
export const useCreateProgressEntry = (
  mutationOptions?: Omit<
    UseMutationOptions<ProgressEntryRead, Error, ProgressEntryCreate>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();
  const { asOf } = useTimeMachineParams();

  return useMutation<ProgressEntryRead, Error, ProgressEntryCreate>({
    mutationFn: (data: ProgressEntryCreate) => {
      // Add control_date from Time Machine if available
      const payload: ProgressEntryCreate = {
        ...data,
        control_date: data.control_date || asOf || null,
      };
      return ProgressEntriesService.createProgressEntry(payload);
    },
    onSuccess: (data, variables) => {
      // Invalidate related queries
      queryClient.invalidateQueries({
        queryKey: queryKeys.progressEntries.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.progressEntries.latest(
          variables.cost_element_id,
          {},
        ),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.costElements.evmMetrics(
          variables.cost_element_id,
          {},
        ),
      });
      toast.success("Progress entry created successfully");
      mutationOptions?.onSuccess?.(data, variables, undefined);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating progress entry: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};
