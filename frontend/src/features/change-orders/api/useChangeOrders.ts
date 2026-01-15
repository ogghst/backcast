import {
  useQuery,
  useMutation,
  useQueryClient,
  UseMutationOptions,
  UseQueryOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import {
  ChangeOrdersService,
  type ChangeOrderPublic,
  type ChangeOrderCreate,
  type ChangeOrderUpdate,
  type MergeRequest,
} from "@/api/generated";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import type { PaginatedResponse } from "@/types/api";

export interface ChangeOrderListParams {
  pagination?: {
    current?: number;
    pageSize?: number;
  };
  projectId: string; // Required - change orders are scoped to projects
  branch?: string;
}

const getPaginationParams = (params?: ChangeOrderListParams) => {
  const current = params?.pagination?.current || 1;
  const pageSize = params?.pagination?.pageSize || 20;

  return {
    page: current,
    per_page: pageSize,
  };
};

/**
 * Custom hook for fetching change orders for a project.
 * Change orders are always scoped to a specific project.
 */
export const useChangeOrders = (params: ChangeOrderListParams) => {
  const { asOf } = useTimeMachineParams();

  return useQuery({
    queryKey: ["change-orders", params, { asOf }],
    queryFn: async () => {
      const serverParams = getPaginationParams(params);

      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/change-orders",
        query: {
          project_id: params.projectId,
          ...serverParams,
          branch: params.branch || "main",
          as_of: asOf || undefined,
        },
      }) as Promise<PaginatedResponse<ChangeOrderPublic>>;
    },
    enabled: !!params.projectId,
  });
};

/**
 * Custom create hook for change orders with Time Machine integration.
 * Automatically creates a co-{code} branch when the change order is created.
 *
 * Change orders can be created at any control date, including in the past.
 * Uses Time Machine's asOf as control_date for historical creation.
 */
export const useCreateChangeOrder = (
  mutationOptions?: Omit<
    UseMutationOptions<ChangeOrderPublic, Error, ChangeOrderCreate>,
    "mutationFn"
  >
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ChangeOrderCreate) => {
      // Only include control_date if asOf is set (not null/undefined)
      // Remove effective_date if not set
      const payload: Record<string, string | number | boolean | null | undefined> = { ...data };
      if (asOf) {
        payload.control_date = asOf;
      } else {
        delete payload.control_date;
      }
      if (!payload.effective_date) {
        delete payload.effective_date;
      }
      return ChangeOrdersService.createChangeOrder(payload as ChangeOrderCreate);
    },
    onSuccess: (data, ...args) => {
      // Invalidate change orders queries for this project
      queryClient.invalidateQueries({
        queryKey: ["change-orders", { projectId: data.project_id }],
      });
      // Invalidate branches query for this project to show the new CO branch
      queryClient.invalidateQueries({
        queryKey: ["projects", data.project_id, "branches"],
      });
      toast.success(`Change Order ${data.code} created with branch co-${data.code}`);
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating change order: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};

/**
 * Custom update hook for change orders with Time Machine integration.
 * Creates a new version on the current active branch.
 */
export const useUpdateChangeOrder = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ChangeOrderPublic,
      Error,
      { id: string; data: ChangeOrderUpdate }
    >,
    "mutationFn"
  >
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ChangeOrderUpdate }) => {
      // Remove control_date if not set
      const payload: Record<string, string | number | boolean | null | undefined> = { ...data };
      if (asOf) {
        payload.control_date = asOf;
      } else {
        delete payload.control_date;
      }
      return ChangeOrdersService.updateChangeOrder(id, payload as ChangeOrderUpdate);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ["change-orders"] });
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
 * Custom delete hook for change orders with Time Machine integration.
 * Soft deletes the current version.
 */
export const useDeleteChangeOrder = (
  mutationOptions?: Omit<
    UseMutationOptions<void, Error, string>,
    "mutationFn"
  >
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => {
      return __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/change-orders/{change_order_id}",
        path: {
          change_order_id: id,
        },
        query: asOf ? { control_date: asOf } : undefined,
      }) as Promise<void>;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ["change-orders"] });
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
 * Custom hook for fetching a single change order by ID.
 */
export const useChangeOrder = (
  id: string | undefined,
  queryOptions?: Omit<UseQueryOptions<ChangeOrderPublic, Error>, "queryKey">
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery({
    queryKey: ["change-orders", "detail", id, { asOf }],
    queryFn: async () => {
      if (!id) throw new Error("Change Order ID is required");

      return __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/change-orders/${id}`,
        query: asOf ? { as_of: asOf } : undefined,
      }) as Promise<ChangeOrderPublic>;
    },
    enabled: !!id,
    ...queryOptions,
  });
};

/**
 * Custom hook for fetching change order history.
 */
export const useChangeOrderHistory = (
  id: string | undefined,
  enabled = true
) => {
  return useQuery({
    queryKey: ["change-orders", "history", id],
    queryFn: async () => {
      if (!id) throw new Error("Change Order ID is required");
      return ChangeOrdersService.getChangeOrderHistory(id);
    },
    enabled: !!id && enabled,
  });
};

/**
 * Merge conflict type - represents a single field conflict during merge.
 */
export interface MergeConflict {
  entity_type: string;
  entity_id: string;
  field: string;
  source_branch: string;
  target_branch: string;
  source_value: string | null;
  target_value: string | null;
}

/**
 * Custom hook for checking merge conflicts between branches.
 * Returns an empty array if no conflicts exist.
 */
export const useCheckMergeConflicts = (
  changeOrderId: string | undefined,
  sourceBranch: string,
  targetBranch: string = "main",
  options?: Omit<UseQueryOptions<MergeConflict[], Error>, "queryKey">
) => {
  return useQuery({
    queryKey: ["change-orders", "merge-conflicts", changeOrderId, sourceBranch, targetBranch],
    queryFn: async () => {
      if (!changeOrderId) throw new Error("Change Order ID is required");
      if (!sourceBranch) throw new Error("Source branch is required");
      const result = await ChangeOrdersService.getMergeConflicts(
        changeOrderId,
        sourceBranch,
        targetBranch
      );
      return result as unknown as MergeConflict[];
    },
    enabled: !!changeOrderId && !!sourceBranch,
    ...options,
  });
};

/**
 * Custom merge hook for change orders with MergeRequest support.
 * Automatically checks for conflicts before merging (if enabled).
 * Shows toast notifications for success/error.
 */
export const useMergeChangeOrder = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ChangeOrderPublic,
      Error,
      { id: string; mergeRequest: MergeRequest }
    >,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, mergeRequest }: { id: string; mergeRequest: MergeRequest }) => {
      return ChangeOrdersService.mergeChangeOrder(id, mergeRequest);
    },
    onSuccess: (data, ...args) => {
      // Invalidate change orders queries
      queryClient.invalidateQueries({ queryKey: ["change-orders"] });
      // Invalidate branches queries
      queryClient.invalidateQueries({ queryKey: ["branches"] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });

      const targetBranch = args[0]?.mergeRequest?.target_branch || "main";
      toast.success(
        `Change Order merged successfully to ${targetBranch}. Status: ${data.status}`
      );
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error: Error & { status?: number; detail?: { conflicts?: MergeConflict[] } }, ...args) => {
      // Handle 409 Conflict error with conflict details
      if (error?.status === 409 && error?.detail?.conflicts) {
        const conflicts = error.detail.conflicts as MergeConflict[];
        const conflictCount = conflicts.length;
        const conflictSummary = conflicts
          .slice(0, 3)
          .map((c) => `${c.entity_type}.${c.field}`)
          .join(", ");
        const moreText = conflictCount > 3 ? ` and ${conflictCount - 3} more` : "";

        toast.error(
          `Merge blocked: ${conflictCount} conflict${conflictCount > 1 ? "s" : ""} detected. ${conflictSummary}${moreText}.`
        );
      } else {
        toast.error(`Error merging change order: ${error.message}`);
      }
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};
