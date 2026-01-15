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
  APPROVE: { label: "Approve", status: "Under Review" },
  REJECT: { label: "Reject", status: "Rejected" },
  MERGE: { label: "Merge to Main", status: "Implemented" },
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
      queryClient.invalidateQueries({ queryKey: ["change-orders"] });
      queryClient.invalidateQueries({ queryKey: ["branches"] });
      options?.onSuccess?.(data);
    },
    onError: options?.onError,
  });

  // Merge mutation
  const mergeMutation = useMergeChangeOrder({
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["change-orders"] });
      queryClient.invalidateQueries({ queryKey: ["branches"] });
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
   * Approve the Change Order (Submitted for Approval → Under Review)
   */
  const approve = useCallback(
    async (comment?: string) => {
      const data: ChangeOrderUpdate = {
        status: WORKFLOW_ACTIONS.APPROVE.status,
        comment,
      };
      return updateMutation.mutateAsync({ id: changeOrderId, data });
    },
    [changeOrderId, updateMutation]
  );

  /**
   * Reject the Change Order (any status → Rejected)
   */
  const reject = useCallback(
    async (comment?: string) => {
      const data: ChangeOrderUpdate = {
        status: WORKFLOW_ACTIONS.REJECT.status,
        comment,
      };
      return updateMutation.mutateAsync({ id: changeOrderId, data });
    },
    [changeOrderId, updateMutation]
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

  return {
    submit,
    approve,
    reject,
    merge,
    isLoading: updateMutation.isPending || mergeMutation.isPending,
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
