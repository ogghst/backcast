/**
 * Quality Event API hooks - TanStack Query integration.
 *
 * Quality events track rework costs and quality issues against cost elements.
 * They are versionable but NOT branchable (quality events are global facts).
 */

import {
  useMutation,
  useQueryClient,
  UseMutationOptions,
  useQuery,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { toast } from "sonner";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import {
  QualityEventsService,
  type QualityEventRead,
  type QualityEventCreate,
  type QualityEventUpdate,
} from "@/api/generated";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";

/**
 * Quality Event API parameters for filtering, pagination, and sorting.
 *
 * Filtering hierarchy: cost_element_id > wbe_id > project_id.
 * At least one of cost_element_id, wbe_id, or project_id should be provided
 * for scoped queries.
 */
interface QualityEventListParams {
  cost_element_id?: string;
  wbe_id?: string;
  project_id?: string;
  event_type?: string;
  severity?: string;
  page?: number;
  perPage?: number;
  asOf?: string;
  queryOptions?: Omit<
    UseQueryOptions<PaginatedResponse<QualityEventRead>>,
    "queryKey" | "queryFn"
  >;
}

/**
 * Hook to fetch quality events with pagination.
 *
 * Supports filtering by cost_element_id, wbe_id, or project_id.
 * Filtering hierarchy: cost_element_id > wbe_id > project_id.
 *
 * @param params - Query parameters including at least one filter id
 * @returns TanStack Query result with paginated quality events
 */
export const useQualityEvents = (params?: QualityEventListParams) => {
  const { asOf, branch, mode } = useTimeMachineParams();
  const filterId =
    params?.cost_element_id || params?.wbe_id || params?.project_id || "";

  return useQuery<PaginatedResponse<QualityEventRead>>({
    queryKey: queryKeys.qualityEvents.list(filterId, {
      ...params,
      asOf: params?.asOf || asOf,
      branch,
      mode,
    }),
    queryFn: async () => {
      const {
        cost_element_id,
        wbe_id,
        project_id,
        event_type,
        severity,
        page = 1,
        perPage = 20,
      } = params || {};

      // Use __request to pass all filter parameters
      const result = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/quality-events",
        query: {
          page,
          per_page: perPage,
          branch,
          mode,
          cost_element_id: cost_element_id || undefined,
          wbe_id: wbe_id || undefined,
          project_id: project_id || undefined,
          event_type: event_type || undefined,
          severity: severity || undefined,
          as_of: params?.asOf || asOf || undefined,
        },
        errors: { 422: "Validation Error" },
      });

      if (Array.isArray(result)) {
        return {
          items: result,
          total: result.length,
          page: 1,
          per_page: result.length,
        };
      }
      return result as unknown as PaginatedResponse<QualityEventRead>;
    },
    enabled:
      !!params?.cost_element_id ||
      !!params?.wbe_id ||
      !!params?.project_id,
    ...params?.queryOptions,
  });
};

/**
 * Hook to get a single quality event by ID.
 * Supports time-travel queries via asOf parameter.
 */
export const useQualityEvent = (
  qualityEventId: string,
  asOf?: string
) => {
  const { asOf: tmAsOf } = useTimeMachineParams();

  return useQuery<QualityEventRead>({
    queryKey: queryKeys.qualityEvents.detail(qualityEventId, {
      asOf: asOf || tmAsOf,
    }),
    queryFn: async () => {
      return await QualityEventsService.getQualityEvent(
        qualityEventId,
        asOf || tmAsOf || undefined,
      );
    },
    enabled: !!qualityEventId,
  });
};

/**
 * Hook to get quality event history.
 *
 * @param qualityEventId - The quality event ID to get history for
 * @returns TanStack Query result with version history
 */
export const useQualityEventHistory = (qualityEventId: string) => {
  return useQuery({
    queryKey: queryKeys.qualityEvents.history(qualityEventId),
    queryFn: async () => {
      return await QualityEventsService.getQualityEventHistory(
        qualityEventId,
      );
    },
    enabled: !!qualityEventId,
  });
};

/**
 * Hook to get total quality event costs for a cost element.
 *
 * @param costElementId - The cost element ID to get total for
 * @returns TanStack Query result with total cost impact
 */
export const useQualityEventTotal = (costElementId: string) => {
  const { asOf } = useTimeMachineParams();

  return useQuery({
    queryKey: queryKeys.qualityEvents.total(costElementId, { asOf }),
    queryFn: async () => {
      return await QualityEventsService.getQualityEventTotal(
        costElementId,
        asOf || undefined,
      );
    },
    enabled: !!costElementId,
  });
};

/**
 * Hook to get quality events aggregated by time period.
 *
 * @param costElementId - Cost element ID
 * @param period - Aggregation period (daily, weekly, monthly)
 * @param startDate - Start date for aggregation
 * @param endDate - Optional end date
 * @returns TanStack Query result with aggregated quality events
 */
export const useQualityEventsByPeriod = (
  costElementId: string,
  period: "daily" | "weekly" | "monthly",
  startDate: string,
  endDate?: string,
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery({
    queryKey: queryKeys.qualityEvents.byPeriod(costElementId, {
      period,
      startDate,
      endDate,
      asOf,
    }),
    queryFn: async () => {
      return await QualityEventsService.getQualityEventsByPeriod(
        costElementId,
        period,
        startDate,
        endDate || undefined,
        asOf || undefined,
      );
    },
    enabled: !!costElementId && !!startDate,
  });
};

/**
 * Hook to create a new quality event.
 *
 * Automatically invalidates quality_events queries on success.
 * Automatically injects control_date from TimeMachine context.
 */
export const useCreateQualityEvent = (
  mutationOptions?: Omit<
    UseMutationOptions<QualityEventRead, Error, QualityEventCreate>,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: QualityEventCreate) => {
      const payload = { ...data, control_date: asOf || null };
      return QualityEventsService.createQualityEvent(payload);
    },
    onSuccess: (...args) => {
      // Invalidate related queries
      const costElementId = args[0].cost_element_id;
      queryClient.invalidateQueries({
        queryKey: queryKeys.qualityEvents.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.qualityEvents.list(costElementId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.qualityEvents.total(costElementId),
      });

      toast.success("Quality event created successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating quality event: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Hook to update an existing quality event.
 *
 * Automatically invalidates quality_events queries on success.
 * Automatically injects control_date from TimeMachine context.
 */
export const useUpdateQualityEvent = (
  mutationOptions?: Omit<
    UseMutationOptions<
      QualityEventRead,
      Error,
      { id: string; data: QualityEventUpdate },
      { previousEvent?: QualityEventRead }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation<
    QualityEventRead,
    Error,
    { id: string; data: QualityEventUpdate },
    { previousEvent?: QualityEventRead }
  >({
    mutationFn: ({ id, data }: { id: string; data: QualityEventUpdate }) => {
      const payload = { ...data, control_date: asOf || null };
      return QualityEventsService.updateQualityEvent(id, payload);
    },
    onMutate: async ({ id, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: queryKeys.qualityEvents.detail(id, { asOf }),
      });
      await queryClient.cancelQueries({
        queryKey: queryKeys.qualityEvents.lists(),
      });

      // Snapshot previous value
      const previousEvent = queryClient.getQueryData(
        queryKeys.qualityEvents.detail(id, { asOf }),
      );

      // Optimistically update
      if (previousEvent) {
        queryClient.setQueryData(
          queryKeys.qualityEvents.detail(id, { asOf }),
          (old: QualityEventRead) => ({
            ...old,
            ...data,
          }),
        );
      }

      return { previousEvent };
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.qualityEvents.all,
      });
      toast.success("Quality event updated successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, variables, context) => {
      // Rollback
      if (context?.previousEvent) {
        queryClient.setQueryData(
          queryKeys.qualityEvents.detail(variables.id, { asOf }),
          context.previousEvent,
        );
      }
      toast.error(`Error updating quality event: ${error.message}`);
      mutationOptions?.onError?.(error, variables, context, undefined);
    },
  });
};

/**
 * Hook to delete (soft delete) a quality event.
 *
 * Automatically invalidates quality_events queries on success.
 */
export const useDeleteQualityEvent = (
  mutationOptions?: Omit<
    UseMutationOptions<void, Error, { id: string; costElementId: string }>,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id }: { id: string; costElementId: string }) => {
      return QualityEventsService.deleteQualityEvent(
        id,
        asOf || undefined,
      );
    },
    onSuccess: (...args) => {
      const variables = args[1];
      const costElementId = variables.costElementId;

      queryClient.invalidateQueries({
        queryKey: queryKeys.qualityEvents.all,
      });
      if (costElementId) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.qualityEvents.list(costElementId),
        });
        queryClient.invalidateQueries({
          queryKey: queryKeys.qualityEvents.total(costElementId),
        });
      }

      toast.success("Quality event deleted successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting quality event: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};
