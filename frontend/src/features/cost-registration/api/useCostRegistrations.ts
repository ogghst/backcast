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
  type CostRegistrationRead,
  type CostRegistrationCreate,
  type CostRegistrationUpdate,
} from "@/api/generated";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";

/**
 * Cost Registration API parameters for filtering, pagination, and sorting.
 */
interface CostRegistrationListParams {
  cost_element_id?: string;
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
 * Hook to fetch cost registrations for a cost element with pagination.
 *
 * @param params - Query parameters including cost_element_id (required), pagination, filters, search, sort
 * @returns TanStack Query result with paginated cost registrations
 */
export const useCostRegistrations = (params?: CostRegistrationListParams) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<PaginatedResponse<CostRegistrationRead>>({
    queryKey: queryKeys.costRegistrations.list(
      params?.cost_element_id || "",
      { ...params, asOf },
    ),
    queryFn: async () => {
      const {
        cost_element_id,
        pagination,
        // filters,
        search,
        sortField,
        sortOrder,
      } = params || {};

      if (!cost_element_id) {
        throw new Error("cost_element_id is required");
      }

      const page = pagination?.current || 1;
      const perPage = pagination?.pageSize || 20;

      const serverSortOrder = sortOrder === "descend" ? "desc" : "asc";

      const result = await CostRegistrationsService.getCostRegistrations(
        page,
        perPage,
        "main", // branch - default value
        "merged", // mode - default value
        cost_element_id, // costElementId - correct position
        search || null,
        null, // filters string - can be enhanced later
        sortField || null,
        serverSortOrder,
        asOf || undefined, // as_of - pass time machine context for time-travel queries
      );

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
    enabled: !!params?.cost_element_id, // Only run if cost_element_id is provided
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
      // Check for budget exceeded error
      if (error instanceof Error && error.message.includes("Budget exceeded")) {
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
