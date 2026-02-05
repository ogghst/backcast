import { useMutation, useQuery, useQueryClient, UseQueryOptions } from "@tanstack/react-query";
import { toast } from "sonner";
import { request as __request } from "@/api/generated/core/request";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import type { ChangeOrderPublic, ChangeOrderApproval, ApprovalInfoPublic } from "@/api/generated";
import { queryKeys } from "@/api/queryKeys";

/**
 * Custom hook for fetching approval information for a change order.
 *
 * Context: Used to determine if the current user can approve a change order
 * and to display approval authority information.
 *
 * @param id - Change Order ID
 * @param queryOptions - Optional React Query options
 * @returns Approval information including impact level, assigned approver, and user authority
 */
export const useApprovalInfo = (
  id: string | undefined,
  queryOptions?: Omit<UseQueryOptions<ApprovalInfoPublic, Error>, "queryKey">
) => {
  return useQuery({
    queryKey: queryKeys.changeOrders.detail(id || "", { approvalInfo: true }),
    queryFn: async () => {
      if (!id) throw new Error("Change Order ID is required");

      return __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/change-orders/${id}/approval-info`,
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
    ...mutationOptions,
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
    ...mutationOptions,
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
    ...mutationOptions,
  });
};
