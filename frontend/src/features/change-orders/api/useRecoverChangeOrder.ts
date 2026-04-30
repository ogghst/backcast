import { useMutation, useQueryClient, UseMutationOptions } from "@tanstack/react-query";
import { toast } from "sonner";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import type { ChangeOrderPublic } from "@/api/generated";
import { queryKeys } from "@/api/queryKeys";

/**
 * Request payload for recovering a stuck change order workflow.
 */
export interface ChangeOrderRecoveryRequest {
  /** Manual impact level assignment (LOW/MEDIUM/HIGH/CRITICAL) */
  impact_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  /** User to assign as approver (use User.id, not User.user_id) */
  assigned_approver_id: string;
  /** Skip impact analysis and use manual values (default: true) */
  skip_impact_analysis?: boolean;
  /** Explanation for recovery (10-500 chars, required for audit) */
  recovery_reason: string;
}

/**
 * Custom hook for recovering a stuck change order workflow.
 *
 * Context: Admin-only endpoint to recover stuck change orders when
 * impact analysis fails or workflow gets stuck in intermediate states.
 * Allows manual override of impact level and approver assignment.
 *
 * Requires change-order-recover permission (admin only).
 *
 * Automatically invalidates queries and shows toast notifications.
 */
export const useRecoverChangeOrder = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ChangeOrderPublic,
      Error,
      { id: string; recoveryData: ChangeOrderRecoveryRequest }
    >,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      recoveryData,
    }: {
      id: string;
      recoveryData: ChangeOrderRecoveryRequest;
    }) => {
      return __request(OpenAPI, {
        method: "POST",
        url: `/api/v1/change-orders/${id}/recover`,
        body: recoveryData,
      }) as Promise<ChangeOrderPublic>;
    },
    onSuccess: (data, ...args) => {
      // Invalidate change orders queries
      queryClient.invalidateQueries({ queryKey: queryKeys.changeOrders.all });
      queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrders.detail(data.change_order_id, {}),
      });
      // Invalidate branches query for this project
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.branches(data.project_id.toString()),
      });

      toast.success(
        `Change Order ${data.code} workflow recovered successfully. Status: ${data.status}`,
      );
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error recovering change order: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};
