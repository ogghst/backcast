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
  WbEsService,
  type WBERead,
  type WBECreate,
  type WBEUpdate,
} from "@/api/generated";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import type { PaginatedResponse } from "@/types/api";

// Custom params interface
export interface WBEListParams {
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
  parentWbeId?: string;
  branch?: string;
  search?: string;
  sortField?: string;
  sortOrder?: string;
  queryOptions?: any;
}

// Custom useWBEs list hook with Time Machine integration
export const useWBEs = (params?: WBEListParams) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<PaginatedResponse<WBERead>>({
    queryKey: ["wbes", params, { asOf }],
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

      // Manual request to support as_of query param
      const response = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/wbes",
        query: {
          page: current,
          per_page: pageSize,
          project_id: params?.projectId,
          parent_wbe_id: params?.parentWbeId,
          branch: params?.branch || "main",
          search: params?.search,
          filters: filterString,
          sort_field: sortField as string,
          sort_order: sortOrder,
          as_of: asOf || undefined,
        },
      });

      // Normalize response to always be PaginatedResponse
      if (Array.isArray(response)) {
        // Hierarchical or filtered list request that returned raw array
        return {
          items: response,
          total: response.length,
          page: 1,
          per_page: response.length,
        };
      }

      // It's already a PaginatedResponse
      return response as unknown as PaginatedResponse<WBERead>;
    },
    ...params?.queryOptions,
  });
};

/**
 * Custom create hook with Time Machine integration.
 * Automatically injects control_date from TimeMachine context.
 */
export const useCreateWBE = (
  mutationOptions?: Omit<
    UseMutationOptions<WBERead, Error, WBECreate>,
    "mutationFn"
  >
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: WBECreate) => {
      const payload = { ...data, control_date: asOf || null };
      return WbEsService.createWbe(payload);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ["wbes"] });
      toast.success("Created successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};

/**
 * Custom update hook with Time Machine integration.
 * Automatically injects control_date from TimeMachine context.
 */
export const useUpdateWBE = (
  mutationOptions?: Omit<
    UseMutationOptions<WBERead, Error, { id: string; data: WBEUpdate }>,
    "mutationFn"
  >
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WBEUpdate }) => {
      const payload = { ...data, control_date: asOf || null };
      return WbEsService.updateWbe(id, payload);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ["wbes"] });
      toast.success("Updated successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};

/**
 * Custom delete hook with Time Machine integration.
 * Automatically injects control_date from TimeMachine context as a query parameter.
 */
export const useDeleteWBE = (
  mutationOptions?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => {
      // Manual request to support control_date query param
      return __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/wbes/{wbe_id}",
        path: {
          wbe_id: id,
        },
        query: asOf ? { control_date: asOf } : undefined,
      }) as Promise<void>;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ["wbes"] });
      toast.success("Deleted successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};

/**
 * Custom useWBE hook with time-travel support.
 * Automatically injects as_of parameter from TimeMachine context.
 */
export const useWBE = (
  id: string | undefined,
  queryOptions?: Omit<UseQueryOptions<WBERead, Error>, "queryKey">
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery({
    queryKey: ["wbes", "detail", id, { asOf }],
    queryFn: async () => {
      if (!id) throw new Error("WBE ID is required");

      // Call the API with as_of parameter if available
      return __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/wbes/${id}`,
        query: asOf ? { as_of: asOf } : undefined,
      }) as Promise<WBERead>;
    },
    enabled: !!id,
    ...queryOptions,
  });
};

// Breadcrumb hook
export const useWBEBreadcrumb = (wbeId: string | undefined) => {
  return useQuery({
    queryKey: ["wbes", wbeId, "breadcrumb"],
    queryFn: () => WbEsService.getWbeBreadcrumb(wbeId!),
    enabled: !!wbeId,
  });
};
