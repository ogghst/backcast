/**
 * Work Package API hooks - TanStack Query integration.
 *
 * Work Packages are PMI-style budget holders sitting under Control Accounts.
 * They are branchable (support change orders) and versionable.
 * Each Work Package groups Cost Elements (EOCs) and tracks budget vs actuals.
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
import type {
  WorkPackageRead,
  WorkPackageCreate,
  WorkPackageUpdate,
} from "@/api/generated";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface WorkPackageListParams {
  control_account_id?: string;
  status?: string;
  page?: number;
  perPage?: number;
  asOf?: string;
  queryOptions?: Omit<
    UseQueryOptions<PaginatedResponse<WorkPackageRead>>,
    "queryKey" | "queryFn"
  >;
}

// ---------------------------------------------------------------------------
// List hook
// ---------------------------------------------------------------------------

/**
 * Hook to fetch work packages with optional filtering by control account.
 */
export const useWorkPackages = (params: WorkPackageListParams = {}) => {
  const { asOf: tmAsOf } = useTimeMachineParams();

  return useQuery<PaginatedResponse<WorkPackageRead>>({
    queryKey: queryKeys.workPackages.list(params.control_account_id, {
      status: params.status,
      page: params.page,
      perPage: params.perPage,
      asOf: params.asOf || tmAsOf,
    }),
    queryFn: async () => {
      const {
        control_account_id,
        status,
        page = 1,
        perPage = 20,
      } = params;

      const result = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/work-packages",
        query: {
          control_account_id: control_account_id || undefined,
          status: status || undefined,
          page,
          per_page: perPage,
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
      return result as unknown as PaginatedResponse<WorkPackageRead>;
    },
    ...params.queryOptions,
  });
};

// ---------------------------------------------------------------------------
// Detail hook
// ---------------------------------------------------------------------------

export const useWorkPackage = (
  workPackageId: string,
  asOf?: string,
) => {
  const { asOf: tmAsOf } = useTimeMachineParams();

  return useQuery<WorkPackageRead>({
    queryKey: queryKeys.workPackages.detail(workPackageId, {
      asOf: asOf || tmAsOf,
    }),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/work-packages/{work_package_id}",
        path: { work_package_id: workPackageId },
        query: { as_of: asOf || tmAsOf || undefined },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!workPackageId,
  });
};

// ---------------------------------------------------------------------------
// History hook
// ---------------------------------------------------------------------------

export const useWorkPackageHistory = (workPackageId: string) => {
  return useQuery<WorkPackageRead[]>({
    queryKey: queryKeys.workPackages.history(workPackageId),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/work-packages/{work_package_id}/history",
        path: { work_package_id: workPackageId },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!workPackageId,
  });
};

// ---------------------------------------------------------------------------
// Budget Status hook
// ---------------------------------------------------------------------------

export const useWorkPackageBudgetStatus = (workPackageId: string) => {
  return useQuery<Record<string, unknown>>({
    queryKey: queryKeys.workPackages.budgetStatus(workPackageId),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/work-packages/{work_package_id}/budget-status",
        path: { work_package_id: workPackageId },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!workPackageId,
  });
};

// ---------------------------------------------------------------------------
// Create mutation
// ---------------------------------------------------------------------------

export const useCreateWorkPackage = (
  mutationOptions?: Omit<
    UseMutationOptions<WorkPackageRead, Error, WorkPackageCreate>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: WorkPackageCreate) => {
      return __request(OpenAPI, {
        method: "POST",
        url: "/api/v1/work-packages",
        body: data,
        mediaType: "application/json",
        errors: { 422: "Validation Error" },
      });
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workPackages.all,
      });
      toast.success("Work package created successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      toast.error(`Error creating work package: ${(args[0] as Error).message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};

// ---------------------------------------------------------------------------
// Update mutation (with optimistic update)
// ---------------------------------------------------------------------------

export const useUpdateWorkPackage = (
  mutationOptions?: Omit<
    UseMutationOptions<
      WorkPackageRead,
      Error,
      { id: string; data: WorkPackageUpdate },
      { previous?: WorkPackageRead }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation<
    WorkPackageRead,
    Error,
    { id: string; data: WorkPackageUpdate },
    { previous?: WorkPackageRead }
  >({
    mutationFn: ({ id, data }) => {
      return __request(OpenAPI, {
        method: "PUT",
        url: "/api/v1/work-packages/{work_package_id}",
        path: { work_package_id: id },
        body: data,
        mediaType: "application/json",
        errors: { 422: "Validation Error" },
      });
    },
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.workPackages.detail(id, { asOf }),
      });
      await queryClient.cancelQueries({
        queryKey: queryKeys.workPackages.lists(),
      });

      const previous = queryClient.getQueryData<WorkPackageRead>(
        queryKeys.workPackages.detail(id, { asOf }),
      );

      if (previous) {
        queryClient.setQueryData(
          queryKeys.workPackages.detail(id, { asOf }),
          (old: WorkPackageRead) => ({ ...old, ...data }),
        );
      }

      return { previous };
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workPackages.all,
      });
      toast.success("Work package updated successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      const error = args[0] as Error;
      const variables = args[1] as { id: string };
      const context = args[2] as { previous?: WorkPackageRead } | undefined;
      if (context?.previous) {
        queryClient.setQueryData(
          queryKeys.workPackages.detail(variables.id, { asOf }),
          context.previous,
        );
      }
      toast.error(`Error updating work package: ${error.message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};

// ---------------------------------------------------------------------------
// Delete mutation
// ---------------------------------------------------------------------------

export const useDeleteWorkPackage = (
  mutationOptions?: Omit<
    UseMutationOptions<void, Error, string>,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => {
      return __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/work-packages/{work_package_id}",
        path: { work_package_id: id },
        query: { control_date: asOf || undefined },
        errors: { 422: "Validation Error" },
      });
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workPackages.all,
      });
      toast.success("Work package deleted successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      toast.error(`Error deleting work package: ${(args[0] as Error).message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};
