import {
  useMutation,
  useQueryClient,
  UseMutationOptions,
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

// Extended types for Branch support
export type CreateWithBranch = CostElementCreate & { branch?: string };
export type UpdateWithBranch = CostElementUpdate & { branch?: string };

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
  queryOptions?: unknown;
  wbe_id?: string; // Add wbe_id for direct filtering support if needed
}

// Custom useCostElements list hook with Time Machine integration
export const useCostElements = (params?: CostElementListParams) => {
  const { asOf } = useTimeMachineParams();

  return useQuery({
    queryKey: ["cost_elements", params, { asOf }],
    queryFn: async () => {
      const {
        branch = "main",
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

      const wbeId = filters?.wbe_id?.[0] as string | undefined;
      const typeId = filters?.cost_element_type_id?.[0] as string | undefined;
      const serverSortOrder = sortOrder === "descend" ? "desc" : "asc";

      // Manual request to support as_of query param
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
  >
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateWithBranch) => {
      const { branch, ...rest } = data;
      // Inject control_date
      const payload: CostElementCreate = {
        ...rest,
        control_date: asOf || null,
      };
      return CostElementsService.createCostElement(payload, branch || "main");
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ["cost_elements"] });
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
export const useUpdateCostElement = (
  mutationOptions?: Omit<
    UseMutationOptions<
      CostElementRead,
      Error,
      { id: string; data: UpdateWithBranch }
    >,
    "mutationFn"
  >
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateWithBranch }) => {
      const { branch, ...rest } = data;
      // Inject control_date
      const payload: CostElementUpdate = {
        ...rest,
        control_date: asOf || null,
      };
      return CostElementsService.updateCostElement(
        id,
        payload,
        branch || "main"
      );
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ["cost_elements"] });
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
export const useDeleteCostElement = (
  mutationOptions?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">
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
      queryClient.invalidateQueries({ queryKey: ["cost_elements"] });
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
