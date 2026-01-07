import { createResourceHooks } from "@/hooks/useCrud";
import {
  WbEsService,
  type WBERead,
  type WBECreate,
  type WBEUpdate,
} from "@/api/generated";
import { useQuery } from "@tanstack/react-query";

interface WBEListParams {
  pagination?: { current?: number; pageSize?: number };
  projectId?: string;
  parentWbeId?: string | null;
  branch?: string;
}

const wbeApi = {
  getUsers: async (params?: WBEListParams) => {
    const { pagination, ...filters } = params || {};
    const current = pagination?.current || 1;
    const pageSize = pagination?.pageSize || 100;
    const skip = (current - 1) * pageSize;

    return WbEsService.getWbes(
      skip,
      pageSize,
      filters.projectId,
      filters.parentWbeId,
      filters.branch
    );
  },
  getUser: (id: string) => WbEsService.getWbe(id),
  createUser: (data: WBECreate) => WbEsService.createWbe(data),
  updateUser: (id: string, data: WBEUpdate) => WbEsService.updateWbe(id, data),
  deleteUser: (id: string) => WbEsService.deleteWbe(id),
};

export const {
  useList: useWBEs,
  useDetail: useWBE,
  useCreate: useCreateWBE,
  useUpdate: useUpdateWBE,
  useDelete: useDeleteWBE,
} = createResourceHooks<WBERead, WBECreate, WBEUpdate>("wbes", wbeApi);

// Breadcrumb hook
export const useWBEBreadcrumb = (wbeId: string | undefined) => {
  return useQuery({
    queryKey: ["wbes", wbeId, "breadcrumb"],
    queryFn: () => WbEsService.getWbeBreadcrumb(wbeId!),
    enabled: !!wbeId,
  });
};

// History hook
export const useWBEHistory = (
  wbeId: string | undefined,
  enabled: boolean = true
) => {
  return useQuery({
    queryKey: ["wbes", wbeId, "history"],
    queryFn: () => WbEsService.getWbeHistory(wbeId!),
    enabled: !!wbeId && enabled,
  });
};
