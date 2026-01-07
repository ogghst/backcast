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

// Direct usage of WbEsService with named methods (no adapter needed)
export const {
  useList: useWBEs,
  useDetail: useWBE,
  useCreate: useCreateWBE,
  useUpdate: useUpdateWBE,
  useDelete: useDeleteWBE,
} = createResourceHooks<WBERead, WBECreate, WBEUpdate>("wbes", {
  list: async (params?: WBEListParams) => {
    const { pagination, ...filters } = params || {};
    const current = pagination?.current || 1;
    const pageSize = pagination?.pageSize || 100;
    const skip = (current - 1) * pageSize;

    return WbEsService.getWbes(
      skip,
      pageSize,
      filters.projectId,
      filters.parentWbeId,
      filters.branch,
    );
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
