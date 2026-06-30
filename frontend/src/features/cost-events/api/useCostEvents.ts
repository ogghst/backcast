/**
 * Cost Event API hooks - TanStack Query integration.
 *
 * Cost Events track cost and schedule impacts of external events
 * on a project. They are versionable but NOT branchable (costs are global facts).
 * Each event can optionally break down costs to specific WBS Elements/CostElements.
 *
 * This was formerly the "Work Package" feature (cost collector role).
 */

import {
  useMutation,
  useQueryClient,
  useQuery,
  type UseQueryOptions,
  type UseMutationOptions,
} from "@tanstack/react-query";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { toast } from "sonner";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { CostEventTypesService } from "@/api/generated/services/CostEventTypesService";
import type {
  CostEventRead,
  CostEventCreate,
  CostEventUpdate,
  CostEventSummary,
  QualityCostAllocation,
  QualityCostAllocationRead,
  COQMetrics,
  COQTrendResponse,
} from "@/api/generated";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type { QualityCostAllocation, QualityCostAllocationRead };

export const COQ_CATEGORY_OPTIONS = [
  { label: "Prevention", value: "prevention" },
  { label: "Appraisal", value: "appraisal" },
  { label: "Internal Failure", value: "internal_failure" },
  { label: "External Failure", value: "external_failure" },
] as const;

export interface CostEventTypeOption {
  label: string;
  value: string;
  color: string;
  is_quality: boolean;
}

// ---------------------------------------------------------------------------
// Package Types hook (now Cost Event Types)
// ---------------------------------------------------------------------------

/**
 * Hook to fetch cost event types from the API.
 * Returns normalized options suitable for Select/Segmented components.
 */
export const useCostEventTypes = () => {
  return useQuery<CostEventTypeOption[]>({
    queryKey: queryKeys.costEventTypes.list,
    queryFn: async () => {
      const res = await CostEventTypesService.getCostEventTypes(1, 10000);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const items = Array.isArray(res) ? res : (res as any)?.items || [];
      return items.map(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (ct: any) => ({
          label: ct.name,
          value: ct.cost_event_type_id,
          color: ct.color || "blue",
          is_quality: ct.is_quality || false,
        }),
      );
    },
    staleTime: 5 * 60 * 1000, // 5 minutes -- cost event types change rarely
  });
};

// ---------------------------------------------------------------------------
// List hook
// ---------------------------------------------------------------------------

interface CostEventListParams {
  project_id: string;
  wbs_element_id?: string;
  coq_category?: string;
  cost_event_type_id?: string;
  quality_only?: boolean;
  status?: string;
  page?: number;
  perPage?: number;
  asOf?: string;
  queryOptions?: Omit<
    UseQueryOptions<PaginatedResponse<CostEventRead>>,
    "queryKey" | "queryFn"
  >;
}

/**
 * Hook to fetch cost events for a project with pagination.
 */
export const useCostEvents = (params: CostEventListParams) => {
  const { asOf: tmAsOf } = useTimeMachineParams();

  return useQuery<PaginatedResponse<CostEventRead>>({
    queryKey: queryKeys.costEvents.list(params.project_id, {
      wbs_element_id: params.wbs_element_id,
      coq_category: params.coq_category,
      cost_event_type_id: params.cost_event_type_id,
      quality_only: params.quality_only,
      status: params.status,
      page: params.page,
      perPage: params.perPage,
      asOf: params.asOf || tmAsOf,
    }),
    queryFn: async () => {
      const {
        project_id,
        wbs_element_id,
        coq_category,
        cost_event_type_id,
        status,
        page = 1,
        perPage = 20,
      } = params;

      const result = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/cost-events",
        query: {
          project_id,
          wbs_element_id: wbs_element_id || undefined,
          page,
          per_page: perPage,
          coq_category: coq_category || undefined,
          cost_event_type_id: cost_event_type_id || undefined,
          status: status || undefined,
          as_of: params.asOf || tmAsOf || undefined,
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
      return result as unknown as PaginatedResponse<CostEventRead>;
    },
    enabled: !!params.project_id,
    ...params.queryOptions,
  });
};

// ---------------------------------------------------------------------------
// Detail hook
// ---------------------------------------------------------------------------

export const useCostEvent = (
  costEventId: string,
  asOf?: string,
) => {
  const { asOf: tmAsOf } = useTimeMachineParams();

  return useQuery<CostEventRead>({
    queryKey: queryKeys.costEvents.detail(costEventId, {
      asOf: asOf || tmAsOf,
    }),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/cost-events/{cost_event_id}",
        path: { cost_event_id: costEventId },
        query: { as_of: asOf || tmAsOf || undefined },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!costEventId,
  });
};

// ---------------------------------------------------------------------------
// History hook
// ---------------------------------------------------------------------------

export const useCostEventHistory = (costEventId: string) => {
  return useQuery<CostEventRead[]>({
    queryKey: queryKeys.costEvents.history(costEventId),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/cost-events/{cost_event_id}/history",
        path: { cost_event_id: costEventId },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!costEventId,
  });
};

// ---------------------------------------------------------------------------
// Summary hook
// ---------------------------------------------------------------------------

export const useCostEventSummary = (projectId: string) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<CostEventSummary>({
    queryKey: queryKeys.costEvents.summary(projectId, { asOf }),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/cost-events/project/{project_id}/summary",
        path: { project_id: projectId },
        query: {
          as_of: asOf || undefined,
        },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!projectId,
  });
};

// ---------------------------------------------------------------------------
// Allocations hook
// ---------------------------------------------------------------------------

export const useCostEventAllocations = (costEventId: string) => {
  return useQuery<QualityCostAllocationRead[]>({
    queryKey: queryKeys.costEvents.allocations(costEventId),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/cost-events/{cost_event_id}/allocations",
        path: { cost_event_id: costEventId },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!costEventId,
  });
};

// ---------------------------------------------------------------------------
// COQ Metrics hook
// ---------------------------------------------------------------------------

export const useCOQMetrics = (projectId: string) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<COQMetrics>({
    queryKey: queryKeys.costEvents.coqMetrics(projectId, { asOf }),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/cost-events/project/{project_id}/coq-metrics",
        path: { project_id: projectId },
        query: {
          as_of: asOf || undefined,
        },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!projectId,
  });
};

// ---------------------------------------------------------------------------
// COQ Trend hook
// ---------------------------------------------------------------------------

export const useCOQTrend = (
  projectId: string,
  granularity: "week" | "month" = "month",
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<COQTrendResponse>({
    queryKey: queryKeys.costEvents.coqTrend(projectId, granularity, { asOf }),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/cost-events/project/{project_id}/coq-trend",
        path: { project_id: projectId },
        query: {
          granularity,
          as_of: asOf || undefined,
        },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!projectId,
  });
};

// ---------------------------------------------------------------------------
// Create mutation
// ---------------------------------------------------------------------------

export const useCreateCostEvent = (
  mutationOptions?: Omit<
    UseMutationOptions<
      CostEventRead,
      Error,
      CostEventCreate
    >,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CostEventCreate) => {
      return __request(OpenAPI, {
        method: "POST",
        url: "/api/v1/cost-events",
        body: data,
        mediaType: "application/json",
        errors: { 422: "Validation Error" },
      });
    },
    onSuccess: (...args) => {
      const created = args[0] as CostEventRead;
      queryClient.invalidateQueries({
        queryKey: queryKeys.costEvents.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.costEvents.summary(created.project_id),
      });

      toast.success("Cost event created successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      toast.error(`Error creating cost event: ${(args[0] as Error).message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};

// ---------------------------------------------------------------------------
// Update mutation
// ---------------------------------------------------------------------------

export const useUpdateCostEvent = (
  mutationOptions?: Omit<
    UseMutationOptions<
      CostEventRead,
      Error,
      { id: string; data: CostEventUpdate },
      { previousEvent?: CostEventRead }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation<
    CostEventRead,
    Error,
    { id: string; data: CostEventUpdate },
    { previousEvent?: CostEventRead }
  >({
    mutationFn: ({ id, data }) => {
      return __request(OpenAPI, {
        method: "PUT",
        url: "/api/v1/cost-events/{cost_event_id}",
        path: { cost_event_id: id },
        body: data,
        mediaType: "application/json",
        errors: { 422: "Validation Error" },
      });
    },
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.costEvents.detail(id, { asOf }),
      });
      await queryClient.cancelQueries({
        queryKey: queryKeys.costEvents.lists(),
      });

      const previousEvent = queryClient.getQueryData<CostEventRead>(
        queryKeys.costEvents.detail(id, { asOf }),
      );

      if (previousEvent) {
        queryClient.setQueryData(
          queryKeys.costEvents.detail(id, { asOf }),
          (old: CostEventRead) => ({ ...old, ...data }),
        );
      }

      return { previousEvent };
    },
    onSuccess: (...args) => {
      const updated = args[0] as CostEventRead;
      queryClient.invalidateQueries({
        queryKey: queryKeys.costEvents.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.costEvents.summary(updated.project_id),
      });

      toast.success("Cost event updated successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      const error = args[0] as Error;
      const variables = args[1] as { id: string };
      const context = args[2] as { previousEvent?: CostEventRead } | undefined;
      if (context?.previousEvent) {
        queryClient.setQueryData(
          queryKeys.costEvents.detail(variables.id, { asOf }),
          context.previousEvent,
        );
      }
      toast.error(`Error updating cost event: ${error.message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};

// ---------------------------------------------------------------------------
// Delete mutation
// ---------------------------------------------------------------------------

export const useDeleteCostEvent = (
  mutationOptions?: Omit<
    UseMutationOptions<
      void,
      Error,
      { id: string; projectId: string }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id }: { id: string; projectId: string }) => {
      return __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/cost-events/{cost_event_id}",
        path: { cost_event_id: id },
        query: { control_date: asOf || undefined },
        errors: { 422: "Validation Error" },
      });
    },
    onSuccess: (...args) => {
      const variables = args[1] as { projectId: string };

      queryClient.invalidateQueries({
        queryKey: queryKeys.costEvents.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.costEvents.summary(variables.projectId),
      });

      toast.success("Cost event deleted successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      toast.error(`Error deleting cost event: ${(args[0] as Error).message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};

// ---------------------------------------------------------------------------
// Upsert allocations mutation
// ---------------------------------------------------------------------------

export const useUpsertAllocations = (
  costEventId: string,
  mutationOptions?: Omit<
    UseMutationOptions<
      QualityCostAllocationRead[],
      Error,
      QualityCostAllocation[]
    >,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (allocations: QualityCostAllocation[]) => {
      return __request(OpenAPI, {
        method: "PUT",
        url: "/api/v1/cost-events/{cost_event_id}/allocations",
        path: { cost_event_id: costEventId },
        body: allocations,
        mediaType: "application/json",
        errors: { 422: "Validation Error" },
      });
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.costEvents.allocations(costEventId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.costEvents.all,
      });

      toast.success("Allocations updated successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      toast.error(`Error updating allocations: ${(args[0] as Error).message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};
