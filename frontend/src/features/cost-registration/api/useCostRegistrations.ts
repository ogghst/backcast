/**
 * Cost Registration API hooks - TanStack Query integration.
 *
 * Cost registrations track actual expenditures against cost elements.
 * They are versionable but NOT branchable (costs are global facts).
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
  CostRegistrationsService,
  ProjectBudgetSettingsService,
  type CostRegistrationRead,
  type CostRegistrationCreate,
  type CostRegistrationUpdate,
} from "@/api/generated";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";

/**
 * Cost Registration API parameters for filtering, pagination, and sorting.
 *
 * Filtering hierarchy: cost_element_id > wbe_id > project_id.
 * At least one of cost_element_id, wbe_id, or project_id should be provided
 * for scoped queries.
 */
interface CostRegistrationListParams {
  cost_element_id?: string;
  wbe_id?: string;
  project_id?: string;
  pagination?: { current?: number; pageSize?: number };
  filters?: Record<string, (string | number | boolean)[] | null>;
  search?: string;
  sortField?: string;
  sortOrder?: string;
  queryOptions?: Omit<
    UseQueryOptions<PaginatedResponse<CostRegistrationRead>>,
    "queryKey" | "queryFn"
  >;
}

/**
 * Hook to fetch cost registrations with pagination.
 *
 * Supports filtering by cost_element_id, wbe_id, or project_id.
 * Filtering hierarchy: cost_element_id > wbe_id > project_id.
 *
 * @param params - Query parameters including at least one filter id, pagination, filters, search, sort
 * @returns TanStack Query result with paginated cost registrations
 */
export const useCostRegistrations = (params?: CostRegistrationListParams) => {
  const { asOf } = useTimeMachineParams();
  const filterId =
    params?.cost_element_id || params?.wbe_id || params?.project_id || "";

  return useQuery<PaginatedResponse<CostRegistrationRead>>({
    queryKey: queryKeys.costRegistrations.list(filterId, { ...params, asOf }),
    queryFn: async () => {
      const {
        cost_element_id,
        wbe_id,
        project_id,
        pagination,
        // filters,
        search,
        sortField,
        sortOrder,
      } = params || {};

      if (!cost_element_id && !wbe_id && !project_id) {
        throw new Error(
          "At least one of cost_element_id, wbe_id, or project_id is required",
        );
      }

      const page = pagination?.current || 1;
      const perPage = pagination?.pageSize || 20;
      const serverSortOrder = sortOrder === "descend" ? "desc" : "asc";

      // Use __request to pass wbe_id and project_id which are not yet
      // in the generated client.
      const result = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/cost-registrations",
        query: {
          page,
          per_page: perPage,
          branch: "main",
          mode: "merged",
          cost_element_id: cost_element_id || undefined,
          wbe_id: wbe_id || undefined,
          project_id: project_id || undefined,
          search: search || undefined,
          filters: undefined,
          sort_field: sortField || undefined,
          sort_order: serverSortOrder,
          as_of: asOf || undefined,
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
      return result as unknown as PaginatedResponse<CostRegistrationRead>;
    },
    enabled:
      !!params?.cost_element_id ||
      !!params?.wbe_id ||
      !!params?.project_id,
    ...params?.queryOptions,
  });
};

/**
 * Hook to get budget status for a cost element.
 *
 * @param costElementId - The cost element ID to get budget status for
 * @returns TanStack Query result with budget status (budget, used, remaining, percentage)
 */
export const useBudgetStatus = (costElementId: string) => {
  const { asOf } = useTimeMachineParams();
  return useQuery({
    queryKey: queryKeys.costRegistrations.budgetStatus(costElementId, { asOf }),
    queryFn: async () => {
      // Pass as_of parameter for time-travel queries
      // FIX: Use undefined instead of null so the request function doesn't filter it out
      return await CostRegistrationsService.getBudgetStatus(
        costElementId,
        asOf || undefined,
      );
    },
    enabled: !!costElementId,
  });
};

/**
 * Hook to get project-level budget status (aggregated across all cost elements).
 *
 * @param projectId - The project ID to get budget status for
 * @returns TanStack Query result with project budget status (project_budget, total_spend, remaining, percentage)
 */
export const useProjectBudgetStatus = (projectId: string) => {
  return useQuery({
    queryKey: ["project-budget-status", projectId] as const,
    queryFn: async () => {
      // Call the new project-budget-status endpoint
      return await __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/cost-registrations/project-budget-status/${projectId}`,
        query: {
          branch: "main",
        },
        errors: { 404: "Project not found", 422: "Validation Error" },
      });
    },
    enabled: !!projectId,
  });
};

export const useWBEBudgetStatus = (wbeId: string) => {
  return useQuery({
    queryKey: ["wbe-budget-status", wbeId] as const,
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/cost-registrations/wbe-budget-status/${wbeId}`,
        query: {
          branch: "main",
        },
        errors: { 404: "WBE not found", 422: "Validation Error" },
      });
    },
    enabled: !!wbeId,
  });
};

/**
 * Hook to get project budget settings including warning threshold.
 *
 * @param projectId - The project ID to get budget settings for
 * @returns TanStack Query result with project budget settings (warning_threshold_percent, etc.)
 */
export const useProjectBudgetSettings = (projectId: string) => {
  return useQuery({
    queryKey: ["project-budget-settings", projectId] as const,
    queryFn: async () => {
      return await ProjectBudgetSettingsService.getProjectBudgetSettings(projectId);
    },
    enabled: !!projectId,
  });
};

/**
 * Hook to get cost registration history.
 *
 * @param costRegistrationId - The cost registration ID to get history for
 * @returns TanStack Query result with version history
 */
export const useCostRegistrationHistory = (costRegistrationId: string) => {
  return useQuery({
    queryKey: queryKeys.costRegistrations.history(costRegistrationId),
    queryFn: async () => {
      return await CostRegistrationsService.getCostRegistrationHistory(
        costRegistrationId,
      );
    },
    enabled: !!costRegistrationId,
  });
};

type CostEntityType = "cost_element" | "wbe" | "project";

/** Set the entity filter param corresponding to the entity type. */
const applyEntityFilter = (
  query: Record<string, string | undefined>,
  entityType: CostEntityType,
  entityId: string,
) => {
  const key = entityType === "cost_element" ? "cost_element_id" : entityType === "wbe" ? "wbe_id" : "project_id";
  query[key] = entityId;
};

/**
 * Hook to fetch aggregated cost data grouped by period.
 *
 * Supports aggregation at cost_element, wbe, or project level.
 */
export const useAggregatedCosts = (
  entityType: CostEntityType,
  entityId: string,
  period: "daily" | "weekly" | "monthly",
  startDate: string,
  endDate?: string,
) => {
  const { asOf } = useTimeMachineParams();
  return useQuery({
    queryKey: queryKeys.costRegistrations.aggregated(entityType, entityId, { period, startDate, endDate, asOf }),
    queryFn: async () => {
      const query: Record<string, string | undefined> = {
        period,
        start_date: startDate,
        end_date: endDate || undefined,
        as_of: asOf || undefined,
      };
      applyEntityFilter(query, entityType, entityId);

      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/cost-registrations/aggregated",
        query,
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!entityId && !!startDate,
  });
};

/**
 * Hook to fetch cumulative cost data over a date range.
 *
 * Supports cumulative costs at cost_element, wbe, or project level.
 */
export const useCumulativeCosts = (
  entityType: CostEntityType,
  entityId: string,
  startDate: string,
  endDate?: string,
) => {
  const { asOf } = useTimeMachineParams();
  return useQuery({
    queryKey: queryKeys.costRegistrations.cumulative(entityType, entityId, { startDate, endDate, asOf }),
    queryFn: async () => {
      const query: Record<string, string | undefined> = {
        start_date: startDate,
        end_date: endDate || undefined,
        as_of: asOf || undefined,
      };
      applyEntityFilter(query, entityType, entityId);

      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/cost-registrations/cumulative",
        query,
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!entityId && !!startDate,
  });
};

/**
 * Hook to create a new cost registration.
 *
 * Automatically invalidates cost_registrations queries on success.
 * Automatically injects control_date from TimeMachine context.
 */
export const useCreateCostRegistration = (
  mutationOptions?: Omit<
    UseMutationOptions<CostRegistrationRead, Error, CostRegistrationCreate>,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CostRegistrationCreate) => {
      const payload = { ...data, control_date: asOf || null };
      return CostRegistrationsService.createCostRegistration(payload);
    },
    onSuccess: (...args) => {
      // Invalidate related queries
      const costElementId = args[0].cost_element_id;
      // Invalidate list for this cost element
      queryClient.invalidateQueries({
        queryKey: queryKeys.costRegistrations.list(costElementId),
      });
      // Invalidate general list/search?
      queryClient.invalidateQueries({
        queryKey: queryKeys.costRegistrations.all,
      });

      queryClient.invalidateQueries({
        queryKey: queryKeys.costRegistrations.budgetStatus(costElementId),
      });

      // Invalidate forecasts because actual costs affect EVM metrics
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });

      toast.success("Cost registration created successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      // Check for budget exceeded error (422 from backend enforcement)
      const isBudgetExceeded =
        (error as { body?: { type?: string } })?.body?.type === "budget_exceeded" ||
        (error instanceof Error && error.message.includes("Budget exceeded"));
      if (isBudgetExceeded) {
        toast.error("Budget exceeded: Cannot add cost that exceeds budget");
      } else {
        toast.error(`Error creating cost registration: ${error.message}`);
      }
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};

/**
 * Hook to update an existing cost registration.
 *
 * Automatically invalidates cost_registrations queries on success.
 * Automatically injects control_date from TimeMachine context.
 */
export const useUpdateCostRegistration = (
  mutationOptions?: Omit<
    UseMutationOptions<
      CostRegistrationRead,
      Error,
      { id: string; data: CostRegistrationUpdate; costElementId: string }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: CostRegistrationUpdate;
      costElementId: string;
    }) => {
      const payload = { ...data, control_date: asOf || null };
      return CostRegistrationsService.updateCostRegistration(id, payload);
    },
    onSuccess: (...args) => {
      // costElementId helps precise invalidation
      const variables = args[1]; // Mutation variables
      const costElementId = variables.costElementId;

      queryClient.invalidateQueries({
        queryKey: queryKeys.costRegistrations.all,
      });
      if (costElementId) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.costRegistrations.budgetStatus(costElementId),
        });
        queryClient.invalidateQueries({
          queryKey: queryKeys.costRegistrations.list(costElementId),
        });
      }
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });

      toast.success("Cost registration updated successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating cost registration: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};

/**
 * Hook to delete (soft delete) a cost registration.
 *
 * Automatically invalidates cost_registrations queries on success.
 * Automatically injects control_date from TimeMachine context as a query parameter.
 */
export const useDeleteCostRegistration = (
  mutationOptions?: Omit<
    UseMutationOptions<void, Error, { id: string; costElementId: string }>,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id }: { id: string; costElementId: string }) => {
      // Manual request to support control_date query param
      return __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/cost-registrations/{cost_registration_id}",
        path: { cost_registration_id: id },
        query: asOf ? { control_date: asOf } : undefined,
      }) as Promise<void>;
    },
    onSuccess: (...args) => {
      const variables = args[1];
      const costElementId = variables.costElementId;

      queryClient.invalidateQueries({
        queryKey: queryKeys.costRegistrations.all,
      });
      if (costElementId) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.costRegistrations.budgetStatus(costElementId),
        });
        queryClient.invalidateQueries({
          queryKey: queryKeys.costRegistrations.list(costElementId),
        });
      }
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });

      toast.success("Cost registration deleted successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting cost registration: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};
