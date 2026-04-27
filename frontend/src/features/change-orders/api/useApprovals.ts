import { useMutation, useQuery, useQueryClient, UseMutationOptions, UseQueryOptions } from "@tanstack/react-query";
import { toast } from "sonner";
import { request as __request } from "@/api/generated/core/request";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import type { ChangeOrderPublic, ChangeOrderApproval, ApprovalInfoPublic } from "@/api/generated";
import { queryKeys } from "@/api/queryKeys";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import type { PaginatedResponse } from "@/types";

/**
 * Parameters for useApprovalInfo hook.
 */
interface UseApprovalInfoParams {
  /** Change Order ID */
  id: string | undefined;
  /** Branch name (optional, defaults to time machine context branch or "main") */
  branch?: string;
}

/**
 * Custom hook for fetching approval information for a change order.
 *
 * Context: Used to determine if the current user can approve a change order
 * and to display approval authority information.
 *
 * @param params - Parameters including id and optional branch (or legacy id string)
 * @param queryOptions - Optional React Query options
 * @returns Approval information including impact level, assigned approver, and user authority
 *
 * @example
 * // Modern usage with params object
 * const { data: approvalInfo } = useApprovalInfo({ id: changeOrderId });
 *
 * // Legacy usage with just id (still supported)
 * const { data: approvalInfo } = useApprovalInfo(changeOrderId);
 */
export const useApprovalInfo = (
  params: UseApprovalInfoParams | string | undefined,
  queryOptions?: Omit<UseQueryOptions<ApprovalInfoPublic, Error>, "queryKey">
) => {
  // Support legacy call pattern where first arg is just id string
  const id = typeof params === "string" ? params : params?.id;
  const paramBranch = typeof params === "object" ? params?.branch : undefined;

  // Get branch from time machine context with fallback
  const { branch: tmBranch } = useTimeMachineParams();
  const branch = paramBranch || tmBranch || "main";

  return useQuery({
    queryKey: queryKeys.changeOrders.detail(id || "", { approvalInfo: true, branch }),
    queryFn: async () => {
      if (!id) throw new Error("Change Order ID is required");

      return __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/change-orders/${id}/approval-info`,
        query: {
          branch,
        },
      }) as Promise<ApprovalInfoPublic>;
    },
    enabled: !!id,
    ...queryOptions,
  });
};

/**
 * Custom hook for submitting a change order for approval.
 *
 * Context: Transitions a Draft change order to "Submitted for Approval" status.
 * Calculates financial impact, assigns approver, sets SLA, and locks the branch.
 *
 * Features:
 * - Invalidates change order queries on success
 * - Shows success/error toast notifications
 * - Accepts optional comment for audit trail
 *
 * @param mutationOptions - Optional mutation callbacks
 * @returns Mutation object for submitting for approval
 */
export const useSubmitForApproval = (
  mutationOptions?: Omit<
    UseMutationOptions<ChangeOrderPublic, Error, { id: string; comment?: string }>,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, comment }: { id: string; comment?: string }) => {
      return __request(OpenAPI, {
        method: "PUT",
        url: `/api/v1/change-orders/${id}/submit-for-approval`,
        query: {
          branch: "main",
          comment: comment || undefined,
        },
      }) as Promise<ChangeOrderPublic>;
    },
    onSuccess: async (data, ...args) => {
      // Invalidate change order queries
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.all,
      });
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.detail(data.change_order_id),
      });
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.listsInProject(data.project_id.toString()),
      });
      // Invalidate branches query to update branch selector with new status
      await queryClient.invalidateQueries({
        queryKey: queryKeys.projects.branches(data.project_id.toString()),
      });

      toast.success(
        `Change Order ${data.code} submitted for approval. Impact: ${data.impact_level || "Unknown"}`,
      );
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error submitting for approval: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Custom hook for approving a change order.
 *
 * Context: Transitions a "Submitted for Approval" or "Under Review" change order to "Approved" status.
 * Validates that the current user has sufficient authority based on impact level.
 *
 * Features:
 * - Invalidates change order queries on success
 * - Shows success/error toast notifications
 * - Accepts optional comments for audit trail
 *
 * @param mutationOptions - Optional mutation callbacks
 * @returns Mutation object for approving change order
 */
export const useApproveChangeOrder = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ChangeOrderPublic,
      Error,
      { id: string; approval: ChangeOrderApproval }
    >,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      approval,
    }: {
      id: string;
      approval: ChangeOrderApproval;
    }) => {
      return __request(OpenAPI, {
        method: "PUT",
        url: `/api/v1/change-orders/${id}/approve`,
        query: {
          branch: "main",
        },
        body: approval,
      }) as Promise<ChangeOrderPublic>;
    },
    onSuccess: async (data, ...args) => {
      // Invalidate change order queries
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.all,
      });
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.detail(data.change_order_id),
      });
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.listsInProject(data.project_id.toString()),
      });
      // Invalidate branches query to update branch selector with new status
      await queryClient.invalidateQueries({
        queryKey: queryKeys.projects.branches(data.project_id.toString()),
      });
      // Invalidate approval info query
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.detail(data.change_order_id, { approvalInfo: true }),
      });

      toast.success(`Change Order ${data.code} approved successfully`);
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error approving change order: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Custom hook for rejecting a change order.
 *
 * Context: Transitions any change order to "Rejected" status.
 * Validates that the current user has sufficient authority based on impact level.
 * Unlocks the branch to allow further modifications.
 *
 * Features:
 * - Invalidates change order queries on success
 * - Shows success/error toast notifications
 * - Accepts optional comments explaining the rejection
 *
 * @param mutationOptions - Optional mutation callbacks
 * @returns Mutation object for rejecting change order
 */
export const useRejectChangeOrder = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ChangeOrderPublic,
      Error,
      { id: string; approval: ChangeOrderApproval }
    >,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      approval,
    }: {
      id: string;
      approval: ChangeOrderApproval;
    }) => {
      return __request(OpenAPI, {
        method: "PUT",
        url: `/api/v1/change-orders/${id}/reject`,
        query: {
          branch: "main",
        },
        body: approval,
      }) as Promise<ChangeOrderPublic>;
    },
    onSuccess: async (data, ...args) => {
      // Invalidate change order queries
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.all,
      });
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.detail(data.change_order_id),
      });
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.listsInProject(data.project_id.toString()),
      });
      // Invalidate branches query to update branch selector with new status
      await queryClient.invalidateQueries({
        queryKey: queryKeys.projects.branches(data.project_id.toString()),
      });
      // Invalidate approval info query
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.detail(data.change_order_id, { approvalInfo: true }),
      });

      toast.success(`Change Order ${data.code} rejected`);
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error rejecting change order: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Parameters for usePendingApprovals hook.
 */
interface UsePendingApprovalsParams {
  /** Page number (1-indexed) */
  page?: number;
  /** Items per page */
  perPage?: number;
  /** Branch name (optional, defaults to time machine context branch or "main") */
  branch?: string;
  /** Branch mode: merged or isolated (optional, defaults to time machine context mode or "merged") */
  mode?: "merged" | "isolated";
}

/**
 * Custom hook for fetching change orders pending approval for the current user.
 *
 * Context: Used to display a list of change orders that await the current user's approval.
 * Filters by assigned_approver_id = current_user.user_id and status in pending states.
 *
 * Features:
 * - Respects time machine context for branch and mode
 * - Paginated results
 * - Automatic refetch when user actions change approval status
 *
 * @param params - Optional pagination, branch, and mode parameters
 * @param queryOptions - Optional React Query options
 * @returns Query result with paginated change orders pending approval
 *
 * @example
 * // Use current time machine context (branch from selector, mode from selector)
 * const { data: pendingApprovals, isLoading } = usePendingApprovals();
 *
 * // Use specific branch with pagination
 * const { data: pendingApprovals, isLoading } = usePendingApprovals({
 *   branch: "BR-CO-2026-001",
 *   page: 1,
 *   perPage: 10
 * });
 *
 * // Use isolated mode to see only pending in current branch
 * const { data: pendingApprovals, isLoading } = usePendingApprovals({
 *   mode: "isolated"
 * });
 */
export const usePendingApprovals = (
  params?: UsePendingApprovalsParams,
  queryOptions?: Omit<UseQueryOptions<PaginatedResponse<ChangeOrderPublic>, Error>, "queryKey">
) => {
  // Get branch and mode from time machine context with fallback
  const { branch: tmBranch, mode: tmMode } = useTimeMachineParams();

  const page = params?.page || 1;
  const perPage = params?.perPage || 20;
  const branch = params?.branch || tmBranch || "main";
  const mode = params?.mode || tmMode || "merged";

  return useQuery({
    queryKey: queryKeys.changeOrders.pendingApprovals({ page, perPage, branch, mode }),
    queryFn: async () => {
      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/change-orders/pending-approvals",
        query: {
          page,
          per_page: perPage,
          branch,
          mode,
        },
      }) as Promise<PaginatedResponse<ChangeOrderPublic>>;
    },
    ...queryOptions,
  });
};

/**
 * Custom hook for archiving a change order branch.
 *
 * Context: Archives (soft-deletes) a change order's branch after it has been
 * Implemented or Rejected. The branch will no longer appear in active lists
 * but remains accessible via time-travel queries.
 *
 * Features:
 * - Invalidates change order queries on success
 * - Invalidates branches query to update branch selector
 * - Shows success/error toast notifications
 *
 * @param mutationOptions - Optional mutation callbacks
 * @returns Mutation object for archiving change order branch
 */
export const useArchiveChangeOrder = (
  mutationOptions?: Omit<
    UseMutationOptions<ChangeOrderPublic, Error, { id: string }>,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id }: { id: string }) => {
      return __request(OpenAPI, {
        method: "POST",
        url: `/api/v1/change-orders/${id}/archive`,
      }) as Promise<ChangeOrderPublic>;
    },
    onSuccess: async (data, ...args) => {
      // Invalidate change order queries
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.all,
      });
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.detail(data.change_order_id),
      });
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.listsInProject(data.project_id.toString()),
      });
      // Invalidate branches query to update branch selector (remove archived branch)
      await queryClient.invalidateQueries({
        queryKey: queryKeys.projects.branches(data.project_id.toString()),
      });

      toast.success(`Branch BR-${data.code} archived successfully`);
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error archiving branch: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};
