import { createResourceHooks } from "@/hooks/useCrud";
import { useQuery } from "@tanstack/react-query";
import {
  WbEsService,
  type WBERead,
  type WBECreate,
  type WBEUpdate,
} from "@/api/generated";

interface WBEListParams {
  pagination?: { current?: number; pageSize?: number };
  projectId?: string;
  parentWbeId?: string | null;
  branch?: string;
}

/**
 * Helper to unwrap paginated response from API.
 * WBE API returns:
 * - Array when using hierarchical filters (projectId/parentWbeId)
 * - Paginated object {items, total, page, per_page} when using general listing
 */
const unwrapWBEResponse = <T>(res: T[] | { items: T[] }): T[] => {
  return Array.isArray(res) ? res : (res as { items: T[] }).items;
};

// Direct usage of WbEsService with named methods (no adapter needed)
export const {
  useList: useWBEs,
  useDetail: useWBE,
  useCreate: useCreateWBE,
  useUpdate: useUpdateWBE,
  useDelete: useDeleteWBE,
} = createResourceHooks<WBERead, WBECreate, WBEUpdate>("wbes", {
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

    // Unwrap paginated response if needed (backend returns {items, total...} or items[])
    return unwrapWBEResponse(response);
  },
  detail: WbEsService.getWbe,
  create: WbEsService.createWbe,
  update: WbEsService.updateWbe,
  delete: WbEsService.deleteWbe,
});

// Breadcrumb hook
export const useWBEBreadcrumb = (wbeId: string | undefined) => {
  return useQuery({
    queryKey: ["wbes", wbeId, "breadcrumb"],
    queryFn: () => WbEsService.getWbeBreadcrumb(wbeId!),
    enabled: !!wbeId,
  });
};
