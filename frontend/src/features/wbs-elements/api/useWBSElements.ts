import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import {
  WbsElementsService,
  type WBSElementRead,
  type WBSElementCreate,
  type WBSElementUpdate,
  BranchMode,
} from "@/api/generated";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";

// Custom params interface
export interface WBSElementListParams {
  pagination?: {
    current?: number;
    pageSize?: number;
  };
  filters?: Record<
    string,
    (string | number | boolean | bigint)[] | null | undefined
  >;
  sorter?: {
    field?: string | string[];
    order?: string;
  };
  projectId?: string;
  parentWbsElementId?: string;
  branch?: string;
  search?: string;
  sortField?: string;
  sortOrder?: string;
  queryOptions?: Partial<UseQueryOptions<PaginatedResponse<WBSElementRead>, Error>>;
}

// Custom useWBSElements list hook with Time Machine integration
export const useWBSElements = (params?: WBSElementListParams) => {
  const { asOf, mode, branch: tmBranch } = useTimeMachineParams();
  const branch = params?.branch || tmBranch;

  return useQuery<PaginatedResponse<WBSElementRead>>({
    queryKey: queryKeys.wbsElements.list(params?.projectId || "", {
      ...params,
      asOf,
      mode,
      branch,
    }),
    queryFn: async () => {
      const current = params?.pagination?.current || 1;
      const pageSize = params?.pagination?.pageSize || 20;

      // Convert Ant Design table filters to server format
      let filterString: string | undefined;
      if (params?.filters) {
        const filterParts: string[] = [];
        Object.entries(params.filters).forEach(([key, value]) => {
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

      // Support both AntD sorter object and flat params from useTableParams
      const sortField = params?.sorter?.field || params?.sortField;
      const sortOrderRaw = params?.sorter?.order || params?.sortOrder;
      const sortOrder = sortOrderRaw === "descend" ? "desc" : "asc";

      // Normalize parentWbsElementId: the string "null" must not be sent as a
      // query parameter (it causes 422 from the backend).  Only forward a
      // real ID; undefined/empty means "root level".
      const parentId =
        params?.parentWbsElementId && params.parentWbsElementId !== "null"
          ? params.parentWbsElementId
          : undefined;

      const response = await WbsElementsService.getWbsElements(
        current,
        pageSize,
        params?.projectId,
        parentId,
        branch || "main",
        mode as BranchMode | undefined,
        params?.search,
        filterString,
        sortField as string,
        sortOrder,
        asOf || undefined,
      );

      // Normalize response to always be PaginatedResponse
      if (Array.isArray(response)) {
        return {
          items: response,
          total: response.length,
          page: 1,
          per_page: response.length,
        };
      }

      // It's already a PaginatedResponse
      return response as unknown as PaginatedResponse<WBSElementRead>;
    },
    ...params?.queryOptions,
  });
};

/**
 * Custom create hook with Time Machine integration.
 * Automatically injects control_date and branch from TimeMachine context.
 */
export const useCreateWBSElement = (
  mutationOptions?: Omit<
    UseMutationOptions<WBSElementRead, Error, WBSElementCreate>,
    "mutationFn"
  >,
) => {
  const { asOf, branch } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: WBSElementCreate) => {
      const payload = { ...data, control_date: asOf || null, branch };
      return WbsElementsService.createWbsElement(payload);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.wbsElements.all });
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
 * Automatically injects control_date and branch from TimeMachine context.
 */
export const useUpdateWBSElement = (
  mutationOptions?: Omit<
    UseMutationOptions<WBSElementRead, Error, { id: string; data: WBSElementUpdate }>,
    "mutationFn"
  >,
) => {
  const { asOf, branch } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WBSElementUpdate }) => {
      const payload = { ...data, control_date: asOf || null, branch };
      return WbsElementsService.updateWbsElement(id, payload);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.wbsElements.all });
      toast.success("Updated successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Custom delete hook with Time Machine integration.
 * Automatically injects control_date from TimeMachine context as a query parameter.
 */
export const useDeleteWBSElement = (
  mutationOptions?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => {
      return __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/wbs-elements/{wbs_element_id}",
        path: {
          wbs_element_id: id,
        },
        query: asOf ? { control_date: asOf } : undefined,
      }) as Promise<void>;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.wbsElements.all });
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
 * Custom useWBSElement hook with time-travel support.
 * Automatically injects as_of parameter from TimeMachine context.
 */
export const useWBSElement = (
  id: string | undefined,
  queryOptions?: Omit<UseQueryOptions<WBSElementRead, Error>, "queryKey">,
) => {
  const { asOf, branch } = useTimeMachineParams();

  return useQuery({
    queryKey: queryKeys.wbsElements.breadcrumb(id!, { branch, asOf }),
    queryFn: async () => {
      if (!id) throw new Error("WBS Element ID is required");

      return __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/wbs-elements/${id}`,
        query: {
          ...(asOf ? { as_of: asOf } : {}),
          ...(branch ? { branch } : {}),
        },
      }) as Promise<WBSElementRead>;
    },
    enabled: !!id,
    ...queryOptions,
  });
};

// Breadcrumb hook
export const useWBSElementBreadcrumb = (wbsElementId: string | undefined) => {
  const { asOf, branch, mode } = useTimeMachineParams();

  return useQuery({
    queryKey: queryKeys.wbsElements.breadcrumb(wbsElementId!, { branch, asOf, mode }),
    queryFn: () => {
      return __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/wbs-elements/${wbsElementId}/breadcrumb`,
        query: {
          ...(asOf ? { as_of: asOf } : {}),
          ...(branch ? { branch } : {}),
          mode,
        },
      });
    },
    enabled: !!wbsElementId,
  });
};
