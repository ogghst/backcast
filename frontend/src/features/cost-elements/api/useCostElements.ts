/**
 * Cost Element API hooks - EOC (Element of Cost) line items under WorkPackage.
 *
 * Cost Elements are versionable but NOT branchable.
 * They represent individual cost line items (by type) within a Work Package.
 */

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
 * Cost Element API parameters for filtering, pagination, and sorting.
 */
interface CostElementListParams {
  pagination?: { current?: number; pageSize?: number };
  filters?: Record<string, (string | number | boolean)[] | null>;
  search?: string;
  sortField?: string;
  sortOrder?: string;
  queryOptions?: Omit<
    UseQueryOptions<PaginatedResponse<CostElementRead>>,
    "queryKey" | "queryFn"
  >;
  work_package_id?: string;
}

// Custom useCostElements list hook with Time Machine integration
export const useCostElements = (params?: CostElementListParams) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<PaginatedResponse<CostElementRead>>({
    queryKey: queryKeys.costElements.list(params?.work_package_id, {
      ...params,
      asOf,
    }),
    queryFn: async () => {
      const {
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
          if (key === "work_package_id" || key === "cost_element_type_id") return;

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

      const workPackageId = params?.work_package_id || filters?.work_package_id?.[0] as string | undefined;
      const typeId = filters?.cost_element_type_id?.[0] as string | undefined;
      const serverSortOrder = sortOrder === "descend" ? "desc" : "asc";

      const res = await CostElementsService.getCostElements(
        page,
        perPage,
        workPackageId,
        typeId,
        search,
        filterString,
        sortField,
        serverSortOrder,
        asOf || undefined,
      );

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
    mutationFn: async (data: CreateWithBranch) => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { branch: _branch, ...rest } = data;
      const payload: CostElementCreate = {
        ...rest,
        control_date: asOf || null,
      };
      // CostElementsService no longer has createCostElement; use raw request
      const res = await __request(OpenAPI, {
        method: "POST",
        url: "/api/v1/cost-elements",
        body: payload,
        mediaType: "application/json",
      });
      return res as CostElementRead;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.costElements.lists(),
      });
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
      const payload: CostElementUpdate = {
        ...rest,
        control_date: asOf || null,
      };
      return CostElementsService.updateCostElement(id, payload);
    },
    onMutate: async ({ id, data }) => {
      const branch = data.branch || tmBranch;

      await queryClient.cancelQueries({
        queryKey: queryKeys.costElements.detail(id, { branch, asOf }),
      });
      await queryClient.cancelQueries({
        queryKey: queryKeys.costElements.lists(),
      });

      const previousElement = queryClient.getQueryData<CostElementRead>(
        queryKeys.costElements.detail(id, { branch, asOf }),
      );

      if (previousElement) {
        queryClient.setQueryData(
          queryKeys.costElements.detail(id, { branch, asOf }),
          (old: CostElementRead) => ({
            ...old,
            ...data,
          }),
        );
      }

      return { previousElement: previousElement as CostElementRead | undefined };
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.costElements.all });
      toast.success("Updated successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, variables, context) => {
      const ctx = context as { previousElement?: CostElementRead } | undefined;
      if (ctx?.previousElement) {
        const branch = variables.data.branch || tmBranch;
        queryClient.setQueryData(
          queryKeys.costElements.detail(variables.id, { branch, asOf }),
          ctx.previousElement,
        );
      }
      toast.error(`Error updating: ${error.message}`);
      mutationOptions?.onError?.(error, variables, ctx as { previousElement?: CostElementRead }, undefined as unknown as never);
    },
  });
};

/**
 * Custom delete hook with Time Machine integration.
 */
export const useDeleteCostElement = (
  mutationOptions?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (compositeId: string) => {
      const [id, branch] = compositeId.split(":::");

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
 */
export const useCostElement = (
  costElementId: string,
  branch?: string,
  options?: Omit<UseQueryOptions<CostElementRead>, "queryKey" | "queryFn">,
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<CostElementRead>({
    queryKey: queryKeys.costElements.detail(costElementId, { branch, asOf }),
    queryFn: async () => {
      return await CostElementsService.getCostElement(
        costElementId,
        asOf || undefined,
      );
    },
    enabled: !!costElementId && (options?.enabled ?? true),
    ...options,
  });
};
