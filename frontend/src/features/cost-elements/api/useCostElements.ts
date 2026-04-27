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
  CostElementsService,
  type CostElementRead,
  type CostElementCreate,
  type CostElementUpdate,
} from "@/api/generated";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";

// Extended types for Branch support
export type CreateWithBranch = CostElementCreate & { branch?: string };
export type UpdateWithBranch = CostElementUpdate & { branch?: string };

/**
 * Map frontend branch mode to API branch mode for EVM endpoints.
 * Frontend uses "merged"/"isolated", EVM API uses "merge"/"strict".
 *
 * @param mode - Frontend mode ("merged" | "isolated")
 * @returns API branch mode ("merge" | "strict")
 */
function mapBranchModeForEvm(mode: "merged" | "isolated"): "merge" | "strict" {
  return mode === "merged" ? "merge" : "strict";
}

/**
 * Cost Element API parameters for filtering, pagination, and sorting.
 */
interface CostElementListParams {
  branch?: string;
  pagination?: { current?: number; pageSize?: number };
  filters?: Record<string, (string | number | boolean)[] | null>;
  search?: string;
  sortField?: string;
  sortOrder?: string;
  queryOptions?: Omit<
    UseQueryOptions<PaginatedResponse<CostElementRead>>,
    "queryKey" | "queryFn"
  >;
  wbe_id?: string; // Add wbe_id for direct filtering support if needed
}

// Custom useCostElements list hook with Time Machine integration
export const useCostElements = (params?: CostElementListParams) => {
  const { mode, branch: tmBranch, asOf } = useTimeMachineParams();

  return useQuery<PaginatedResponse<CostElementRead>>({
    queryKey: queryKeys.costElements.list({
      ...params,
      mode,
      branch: tmBranch,
      asOf, // FIX: Include asOf in query key for proper cache isolation
    }),
    queryFn: async () => {
      const {
        branch = tmBranch || "main",
        pagination,
        filters,
        search,
        sortField,
        sortOrder,
      } = params || {};
      const page = pagination?.current || 1;
      const perPage = pagination?.pageSize || 20;

      let filterString: string | undefined;
      if (filters) {
        const filterParts: string[] = [];
        Object.entries(filters).forEach(([key, value]) => {
          if (key === "wbe_id" || key === "cost_element_type_id") return;

          if (
            value &&
            (Array.isArray(value) ? value.length > 0 : value !== undefined)
          ) {
            const values = Array.isArray(value) ? value : [value];
            filterParts.push(`${key}:${values.join(",")}`);
          }
        });
        filterString =
          filterParts.length > 0 ? filterParts.join(";") : undefined;
      }

      const wbeId = params?.wbe_id || filters?.wbe_id?.[0] as string | undefined;
      const typeId = filters?.cost_element_type_id?.[0] as string | undefined;
      const serverSortOrder = sortOrder === "descend" ? "desc" : "asc";

      // Manual request to support as_of and mode query params
      const res = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/cost-elements",
        query: {
          page,
          per_page: perPage,
          branch,
          wbe_id: wbeId,
          cost_element_type_id: typeId,
          search,
          filters: filterString,
          sort_field: sortField,
          sort_order: serverSortOrder,
          mode: mode,
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
      return res as unknown as PaginatedResponse<CostElementRead>;
    },
    ...params?.queryOptions,
  });
};

/**
 * Custom create hook with Time Machine integration.
 * Automatically injects control_date from TimeMachine context.
 */

export const useCreateCostElement = (
  mutationOptions?: Omit<
    UseMutationOptions<CostElementRead, Error, CreateWithBranch>,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateWithBranch) => {
      const { branch, ...rest } = data;
      // Inject control_date
      const payload: CostElementCreate = {
        ...rest,
        branch: branch || "main",
        control_date: asOf || null,
      };
      return CostElementsService.createCostElement(payload);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.costElements.lists(),
      });
      // Invalidate EVM analysis (forecast comparison queries)
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });
      toast.success("Created successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Custom update hook with Time Machine integration.
 * Automatically injects control_date from TimeMachine context.
 */
export const useUpdateCostElement = (
  mutationOptions?: Omit<
    UseMutationOptions<
      CostElementRead,
      Error,
      { id: string; data: UpdateWithBranch },
      { previousElement?: CostElementRead }
    >,
    "mutationFn"
  >,
) => {
  const { asOf, branch: tmBranch } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation<
    CostElementRead,
    Error,
    { id: string; data: UpdateWithBranch },
    { previousElement?: CostElementRead }
  >({
    mutationFn: ({ id, data }: { id: string; data: UpdateWithBranch }) => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { branch: _branch, ...rest } = data;
      // Inject control_date
      const payload: CostElementUpdate = {
        ...rest,
        control_date: asOf || null,
        // branch field might not exist on Update model, sticking to rest.
        // If update doesn't support moving branch, we don't send it.
      };
      return CostElementsService.updateCostElement(id, payload);
    },
    onMutate: async ({ id, data }) => {
      const branch = data.branch || tmBranch;

      // Cancel any outgoing refetches (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({
        queryKey: queryKeys.costElements.detail(id, { branch, asOf }),
      });
      await queryClient.cancelQueries({
        queryKey: queryKeys.costElements.lists(),
      });

      // Snapshot the previous value
      const previousElement = queryClient.getQueryData(
        queryKeys.costElements.detail(id, { branch, asOf }),
      );

      // Optimistically update to the new value
      if (previousElement) {
        queryClient.setQueryData(
          queryKeys.costElements.detail(id, { branch, asOf }),
          (old: CostElementRead) => ({
            ...old,
            ...data,
          }),
        );
      }

      return { previousElement };
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.costElements.all });
      // Invalidate EVM analysis
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });
      toast.success("Updated successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, variables, context: unknown) => {
      // Rollback
      if (context?.previousElement) {
        const branch = variables.data.branch || tmBranch;
        queryClient.setQueryData(
          queryKeys.costElements.detail(variables.id, { branch, asOf }),
          context.previousElement,
        );
      }
      toast.error(`Error updating: ${error.message}`);
      mutationOptions?.onError?.(error, variables, context, undefined);
    },
  });
};

/**
 * Custom delete hook with Time Machine integration.
 * Automatically injects control_date from TimeMachine context as a query parameter.
 */
export const useDeleteCostElement = (
  mutationOptions?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (compositeId: string) => {
      // compositeId format: "uuid:::branch"
      const [id, branch] = compositeId.split(":::");

      // Manual request to support control_date query param
      return __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/cost-elements/{cost_element_id}",
        path: {
          cost_element_id: id,
        },
        query: {
          branch: branch || "main",
          control_date: asOf || undefined,
        },
      }) as Promise<void>;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.costElements.lists(),
      });
      // Invalidate EVM analysis (forecast comparison queries)
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });
      toast.success("Deleted successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Hook to get a single cost element by ID.
 * @param costElementId - The cost element ID to fetch
 * @param branch - Branch to query (default: from TimeMachine context)
 * @param options - Additional options for useQuery
 * @returns TanStack Query result with cost element data
 */
export const useCostElement = (
  costElementId: string,
  branch?: string,
  options?: Omit<UseQueryOptions<CostElementRead>, "queryKey" | "queryFn">,
) => {
  const { mode, branch: tmBranch, asOf } = useTimeMachineParams();
  const effectiveBranch = branch || tmBranch || "main";

  return useQuery<CostElementRead>({
    queryKey: queryKeys.costElements.detail(costElementId, { branch: effectiveBranch, asOf }),
    queryFn: async () => {
      return await CostElementsService.getCostElement(
        costElementId,
        effectiveBranch,
        mode,
        asOf || undefined,
      );
    },
    enabled: !!costElementId && (options?.enabled ?? true),
    ...options,
  });
};

/**
 * Hook to get breadcrumb trail for a cost element.
 * Returns project, WBE, and cost element information for navigation.
 *
 * @param costElementId - The cost element ID to fetch breadcrumb for
 * @returns TanStack Query result with breadcrumb data
 */
export const useCostElementBreadcrumb = (costElementId: string) => {
  return useQuery({
    queryKey: queryKeys.costElements.breadcrumb(costElementId),
    queryFn: async () => {
      return await CostElementsService.getCostElementBreadcrumb(costElementId);
    },
    enabled: !!costElementId,
  });
};

/**
 * Hook to get the forecast for a specific cost element.
 * Uses the new 1:1 relationship endpoint (GET /cost-elements/{id}/forecast).
 *
 * @param costElementId - The cost element ID to fetch forecast for
 * @param branch - Branch to query (default: from TimeMachine context)
 * @returns TanStack Query result with forecast data
 */
export const useCostElementForecast = (
  costElementId: string,
  branch?: string,
) => {
  const { mode, branch: tmBranch, asOf } = useTimeMachineParams();

  return useQuery({
    queryKey: queryKeys.forecasts.byCostElement(
      costElementId,
      branch || tmBranch,
      { mode, asOf },
    ),
    queryFn: async () => {
      return await CostElementsService.getCostElementForecast(
        costElementId,
        branch || tmBranch || "main",
        mode,
        asOf || undefined,
      );
    },
    enabled: !!costElementId,
  });
};

/**
 * Hook to update the forecast for a cost element.
 * Uses the new 1:1 relationship endpoint (PUT /cost-elements/{id}/forecast).
 *
 * Automatically injects control_date from TimeMachine context.
 */
export const useUpdateCostElementForecast = (
  mutationOptions?: Omit<
    UseMutationOptions<
      Record<string, unknown>,
      Error,
      { costElementId: string; data: Record<string, unknown>; branch?: string }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      costElementId,
      data,
      branch,
    }: {
      costElementId: string;
      data: Record<string, unknown>;
      branch?: string;
    }) => {
      // Include branch and control_date in request body (as per API conventions for write operations)
      const payload = {
        ...data,
        branch: branch || "main",
        control_date: asOf || null,
      };
      return CostElementsService.updateCostElementForecast(
        costElementId,
        payload,
      );
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forecasts.byCostElement(args[0].costElementId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });
      toast.success("Forecast updated successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating forecast: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Hook to delete the forecast for a cost element.
 * Uses the new 1:1 relationship endpoint (DELETE /cost-elements/{id}/forecast).
 *
 * Automatically injects control_date from TimeMachine context.
 */
export const useDeleteCostElementForecast = (
  mutationOptions?: Omit<
    UseMutationOptions<void, Error, { costElementId: string; branch?: string }>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      costElementId,
      branch,
    }: {
      costElementId: string;
      branch?: string;
    }) => {
      return CostElementsService.deleteCostElementForecast(
        costElementId,
        branch || "main",
      );
    },
    onSuccess: (_data, variables, _context) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forecasts.byCostElement(variables.costElementId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });
      toast.success("Forecast deleted successfully");
      mutationOptions?.onSuccess?.(_data, variables, _context, undefined);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting forecast: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Hook to get EVM (Earned Value Management) metrics for a cost element.
 * Uses the new EVM metrics endpoint (GET /cost-elements/{id}/evm).
 *
 * @param costElementId - The cost element ID to fetch EVM metrics for
 * @param branch - Branch to query (default: from TimeMachine context)
 * @returns TanStack Query result with EVM metrics data
 */
export const useCostElementEvmMetrics = (
  costElementId: string,
  branch?: string,
) => {
  const { mode, branch: tmBranch, asOf } = useTimeMachineParams();

  return useQuery({
    queryKey: queryKeys.costElements.evmMetrics(costElementId, {
      branch: branch || tmBranch,
      mode,
      asOf,
    }),
    queryFn: async () => {
      return await CostElementsService.getEvmMetrics(
        costElementId,
        asOf || undefined,
        branch || tmBranch || "main",
        mapBranchModeForEvm(mode),
      );
    },
    enabled: !!costElementId,
  });
};

/**
 * Hook to get historical EVM metrics (Time Series) for a cost element.
 * Uses the new EVM history endpoint (GET /cost-elements/{id}/evm-history).
 *
 * @param costElementId - The cost element ID
 * @param granularity - Time interval (day, week, month)
 * @param branch - Branch to query
 * @returns TanStack Query result with time-series data
 */
export const useCostElementEvmHistory = (
  costElementId: string,
  granularity: "day" | "week" | "month" = "week",
  branch?: string,
) => {
  const { mode, branch: tmBranch, asOf } = useTimeMachineParams();

  return useQuery({
    queryKey: queryKeys.evm.timeSeries("cost_element", costElementId, {
      branch: branch || tmBranch,
      mode,
      asOf,
      granularity,
    }),
    queryFn: async () => {
      return await CostElementsService.getEvmHistory(
        costElementId,
        granularity,
        asOf || undefined,
        branch || tmBranch || "main",
        mapBranchModeForEvm(mode),
      );
    },
    enabled: !!costElementId,
  });
};

/**
 * Hook to get full version history for a cost element.
 * Returns all versions of the cost element (including forecast data) in the specified branch,
 * ordered by transaction_time descending (most recent first).
 *
 * @param costElementId - The cost element ID
 * @param branch - Branch to query history from
 * @returns TanStack Query result with array of cost element versions
 */
export const useCostElementHistory = (
  costElementId: string,
  branch?: string,
) => {
  const { branch: tmBranch } = useTimeMachineParams();

  return useQuery<CostElementRead[]>({
    queryKey: queryKeys.costElements.detail(costElementId, {
      branch: branch || tmBranch,
      history: true,
    }),
    queryFn: async () => {
      return await CostElementsService.getHistory(
        costElementId,
        branch || tmBranch || "main",
      );
    },
    enabled: !!costElementId,
  });
};
