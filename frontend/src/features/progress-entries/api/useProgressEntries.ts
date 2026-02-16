import {
  useMutation,
  useQueryClient,
  UseMutationOptions,
  useQuery,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";

import {
  ProgressEntriesService,
  type ProgressEntryRead,
  type ProgressEntryCreate,
  type ProgressEntryUpdate,
} from "@/api/generated";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";

/**
 * Progress Entry API parameters for filtering, pagination, and sorting.
 */
interface ProgressEntryListParams {
  cost_element_id?: string;
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
 * Progress entries are NOT branchable but support time-travel queries.
 */
export const useProgressEntries = (params?: ProgressEntryListParams) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<PaginatedResponse<ProgressEntryRead>>({
    queryKey: queryKeys.progressEntries.list(params?.cost_element_id || "", {
      asOf: params?.asOf || asOf,
    }),
    queryFn: async () => {
      const { cost_element_id, page = 1, perPage = 20 } = params || {};

      const res = await ProgressEntriesService.getProgressEntries(
        page,
        perPage,
        cost_element_id,
        params?.asOf || asOf || undefined,
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
    enabled: !!params?.cost_element_id,
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
        control_date: asOf || data.control_date || null,
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
    ...mutationOptions,
  });
};

/**
 * Custom update hook for progress entries.
 * Creates a new version of the progress entry with updated values.
 * Includes optimistic updates with rollback on error.
 */
export const useUpdateProgressEntry = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ProgressEntryRead,
      Error,
      { id: string; data: ProgressEntryUpdate },
      { previousEntry?: ProgressEntryRead }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation<
    ProgressEntryRead,
    Error,
    { id: string; data: ProgressEntryUpdate },
    { previousEntry?: ProgressEntryRead }
  >({
    mutationFn: ({ id, data }: { id: string; data: ProgressEntryUpdate }) => {
      // Add control_date to data
      const payload: ProgressEntryUpdate = {
        ...data,
        control_date: asOf || null,
      };
      return ProgressEntriesService.updateProgressEntry(id, payload);
    },
    onMutate: async ({ id, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: queryKeys.progressEntries.detail(id, { asOf }),
      });
      await queryClient.cancelQueries({
        queryKey: queryKeys.progressEntries.lists(),
      });

      // Snapshot previous value
      const previousEntry = queryClient.getQueryData(
        queryKeys.progressEntries.detail(id, { asOf }),
      );

      // Optimistically update
      if (previousEntry) {
        queryClient.setQueryData(
          queryKeys.progressEntries.detail(id, { asOf }),
          (old: ProgressEntryRead) => ({
            ...old,
            ...data,
          }),
        );
      }

      return { previousEntry };
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.progressEntries.all,
      });
      toast.success("Progress entry updated successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, variables, context) => {
      // Rollback
      if (context?.previousEntry) {
        queryClient.setQueryData(
          queryKeys.progressEntries.detail(variables.id, { asOf }),
          context.previousEntry,
        );
      }
      toast.error(`Error updating progress entry: ${error.message}`);
      mutationOptions?.onError?.(error, variables, context, undefined);
    },
    ...mutationOptions,
  });
};

/**
 * Custom delete hook for progress entries.
 * Soft deletes the progress entry (preserves in history).
 * Includes confirmation modal via App.useApp().
 */
export const useDeleteProgressEntry = (
  mutationOptions?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (progressEntryId: string) => {
      return ProgressEntriesService.deleteProgressEntry(progressEntryId);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.progressEntries.all,
      });
      toast.success("Progress entry deleted successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting progress entry: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};
