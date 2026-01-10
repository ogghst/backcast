import { createResourceHooks } from "@/hooks/useCrud";
import { useQuery, UseQueryOptions } from "@tanstack/react-query";
import {
  WbEsService,
  type WBERead,
  type WBECreate,
  type WBEUpdate,
} from "@/api/generated";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";

interface WBEListParams {
  pagination?: { current?: number; pageSize?: number };
  projectId?: string;
  parentWbeId?: string | null;
  branch?: string;
}

import type { PaginatedResponse } from "@/types/api";

// ... imports

// Create base hooks without time-travel support
const baseHooks = createResourceHooks<
  WBERead,
  WBECreate,
  WBEUpdate,
  PaginatedResponse<WBERead>
>("wbes", {
  list: async (params?: any) => {
    // Convert Ant Design table params to server format
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
      filterString = filterParts.length > 0 ? filterParts.join(";") : undefined;
    }

    // Support both AntD sorter object and flat params from useTableParams
    const sortField = params?.sorter?.field || params?.sortField;
    const sortOrderRaw = params?.sorter?.order || params?.sortOrder;
    const sortOrder = sortOrderRaw === "descend" ? "desc" : "asc";

    const response = await WbEsService.getWbes(
      current,
      pageSize,
      params?.projectId,
      params?.parentWbeId,
      params?.branch || "main",
      params?.search,
      filterString,
      sortField,
      sortOrder
    );

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
  detail: WbEsService.getWbe,
  create: WbEsService.createWbe,
  update: WbEsService.updateWbe,
  delete: WbEsService.deleteWbe,
});

// Export list, create, update, delete as-is
export const useWBEs = baseHooks.useList;
export const useCreateWBE = baseHooks.useCreate;
export const useUpdateWBE = baseHooks.useUpdate;
export const useDeleteWBE = baseHooks.useDelete;

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
      });
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
