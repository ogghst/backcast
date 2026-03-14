import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type {
  ChangeOrderPublic,
  ChangeOrderUpdate,
  MergeRequest,
} from "@/api/generated";
import {
  useUpdateChangeOrder,
  useMergeChangeOrder,
} from "../api/useChangeOrders";
import {
  useApproveChangeOrder,
  useRejectChangeOrder,
  useArchiveChangeOrder,
} from "../api/useApprovals";
import { queryKeys } from "@/api/queryKeys";

interface WorkflowActionsOptions {
  /** Callback when transition succeeds */
  onSuccess?: (data: ChangeOrderPublic) => void;
  /** Callback when transition fails */
  onError?: (error: Error) => void;
}

/**
 * Workflow action types with their corresponding status values.
 */
export const WORKFLOW_ACTIONS = {
  SUBMIT: { label: "Submit", status: "Submitted for Approval" },
  REVIEW: { label: "Put Under Review", status: "Under Review" },
  APPROVE: { label: "Approve", status: "Approved" },
  REJECT: { label: "Reject", status: "Rejected" },
  REOPEN: { label: "Reopen", status: "Draft" },
  MERGE: { label: "Merge to Main", status: "Implemented" },
  ARCHIVE: { label: "Archive Branch", status: "Archived" },
} as const;

export type WorkflowActionKey = keyof typeof WORKFLOW_ACTIONS;

/**
 * useWorkflowActions - Hook for workflow transition and merge operations.
 *
 * Provides methods for executing workflow transitions (Submit, Approve, Reject)
 * and merge operations with optional comment support.
 *
 * All methods automatically invalidate queries and show toast notifications.
 */
export function useWorkflowActions(changeOrderId: string, options?: WorkflowActionsOptions) {
  const queryClient = useQueryClient();

  // Update mutation for status transitions
  const updateMutation = useUpdateChangeOrder({
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.changeOrders.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.changeOrders.branches });
      options?.onSuccess?.(data);
    },
    onError: options?.onError,
  });

  // Approval/rejection mutations using dedicated endpoints
  const approveMutation = useApproveChangeOrder({
    onSuccess: (data) => {
      options?.onSuccess?.(data);
    },
    onError: options?.onError,
  });

  const rejectMutation = useRejectChangeOrder({
    onSuccess: (data) => {
      options?.onSuccess?.(data);
    },
    onError: options?.onError,
  });

  // Merge mutation
  const mergeMutation = useMergeChangeOrder({
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.changeOrders.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.changeOrders.branches });
      options?.onSuccess?.(data);
    },
    onError: options?.onError,
  });

  // Archive mutation
  const archiveMutation = useArchiveChangeOrder({
    onSuccess: (data) => {
      options?.onSuccess?.(data);
    },
    onError: options?.onError,
  });

  /**
   * Submit the Change Order for review (Draft → Submitted for Approval)
   */
  const submit = useCallback(
    async (comment?: string) => {
      const data: ChangeOrderUpdate = {
        status: WORKFLOW_ACTIONS.SUBMIT.status,
        comment,
      };
      return updateMutation.mutateAsync({ id: changeOrderId, data });
    },
    [changeOrderId, updateMutation]
  );

  /**
   * Put the Change Order under review (Submitted for Approval → Under Review)
   */
  const review = useCallback(
    async (comment?: string) => {
      const data: ChangeOrderUpdate = {
        status: WORKFLOW_ACTIONS.REVIEW.status,
        comment,
      };
      return updateMutation.mutateAsync({ id: changeOrderId, data });
    },
    [changeOrderId, updateMutation]
  );

  /**
   * Approve the Change Order using dedicated approval endpoint
   */
  const approve = useCallback(
    async (comment?: string) => {
      const approval = { comments: comment || null };
      return approveMutation.mutateAsync({ id: changeOrderId, approval });
    },
    [changeOrderId, approveMutation]
  );

  /**
   * Reject the Change Order using dedicated rejection endpoint
   */
  const reject = useCallback(
    async (comment?: string) => {
      const approval = { comments: comment || null };
      return rejectMutation.mutateAsync({ id: changeOrderId, approval });
    },
    [changeOrderId, rejectMutation]
  );

  /**
   * Merge the Change Order branch to main (Approved → Implemented)
   *
   * @param mergeRequest - Merge options including target branch and comment
   */
  const merge = useCallback(
    async (mergeRequest?: Partial<MergeRequest>) => {
      const request: MergeRequest = {
        target_branch: mergeRequest?.target_branch || "main",
        comment: mergeRequest?.comment,
      };
      return mergeMutation.mutateAsync({
        id: changeOrderId,
        mergeRequest: request,
      });
    },
    [changeOrderId, mergeMutation]
  );

  /**
   * Archive the Change Order branch (Implemented/Rejected → Archived)
   *
   * Soft-deletes the branch, making it invisible in active lists but
   * still accessible via time-travel queries.
   */
  const archive = useCallback(
    async () => {
      return archiveMutation.mutateAsync({ id: changeOrderId });
    },
    [changeOrderId, archiveMutation]
  );

  /**
   * Reopen the Change Order (Rejected → Draft)
   *
   * Returns a rejected change order to Draft status for further editing.
   */
  const reopen = useCallback(
    async (comment?: string) => {
      const data: ChangeOrderUpdate = {
        status: WORKFLOW_ACTIONS.REOPEN.status,
        comment,
      };
      return updateMutation.mutateAsync({ id: changeOrderId, data });
    },
    [changeOrderId, updateMutation]
  );

  return {
    submit,
    review,
    approve,
    reject,
    reopen,
    merge,
    archive,
    isLoading: updateMutation.isPending || approveMutation.isPending || rejectMutation.isPending || mergeMutation.isPending || archiveMutation.isPending,
    mutation: updateMutation,
  };
}

/**
 * Helper to check if a workflow action is available based on available_transitions.
 */
export function isActionAvailable(
  action: WorkflowActionKey,
  availableTransitions: string[] | null | undefined
): boolean {
  if (!availableTransitions) return false;  
  const targetStatus = WORKFLOW_ACTIONS[action].status;
  return availableTransitions.includes(targetStatus);
}
