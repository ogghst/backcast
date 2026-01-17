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
import { toast } from "sonner";
import {
  CostRegistrationsService,
  type CostRegistrationRead,
  type CostRegistrationCreate,
  type CostRegistrationUpdate,
} from "@/api/generated";
import type { PaginatedResponse } from "@/types/api";

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
  return useQuery<PaginatedResponse<CostRegistrationRead>>({
    queryKey: ["cost_registrations", params],
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
        cost_element_id,
        search || null,
        null, // filters string - can be enhanced later
        sortField || null,
        serverSortOrder,
        undefined, // as_of - time travel not needed for current view
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
  return useQuery({
    queryKey: ["budget_status", costElementId],
    queryFn: async () => {
      return await CostRegistrationsService.getBudgetStatus(costElementId);
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
    queryKey: ["cost_registration_history", costRegistrationId],
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
 */
export const useCreateCostRegistration = (
  mutationOptions?: Omit<
    UseMutationOptions<CostRegistrationRead, Error, CostRegistrationCreate>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CostRegistrationCreate) => {
      return CostRegistrationsService.createCostRegistration(data);
    },
    onSuccess: (...args) => {
      // Invalidate related queries
      const costElementId = args[0].cost_element_id;
      queryClient.invalidateQueries({
        queryKey: ["cost_registrations"],
      });
      queryClient.invalidateQueries({
        queryKey: ["budget_status", costElementId],
      });
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
 */
export const useUpdateCostRegistration = (
  mutationOptions?: Omit<
    UseMutationOptions<
      CostRegistrationRead,
      Error,
      { id: string; data: CostRegistrationUpdate }
    >,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: CostRegistrationUpdate;
    }) => {
      return CostRegistrationsService.updateCostRegistration(id, data);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: ["cost_registrations"],
      });
      queryClient.invalidateQueries({
        queryKey: ["budget_status"],
      });
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
 */
export const useDeleteCostRegistration = (
  mutationOptions?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => {
      return CostRegistrationsService.deleteCostRegistration(id);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: ["cost_registrations"],
      });
      queryClient.invalidateQueries({
        queryKey: ["budget_status"],
      });
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
