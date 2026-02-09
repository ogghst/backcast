import { useMemo } from "react";
import { useAuthStore } from "@/stores/useAuthStore";
import { usePermission } from "@/hooks/usePermission";
import { useApprovalInfo } from "./useApprovals";
import type { ChangeOrderPublic } from "@/api/generated";

/**
 * Result of the useCanApprove hook.
 */
export interface UseCanApproveResult {
  /** Whether the current user can approve this change order */
  canApprove: boolean;
  /** The current user's authority level (LOW/MEDIUM/HIGH/CRITICAL) */
  authorityLevel: string | null;
  /** Whether the approval info is still loading */
  isLoading: boolean;
  /** The reason the user cannot approve (if canApprove is false) */
  reason?: string;
}

/**
 * useCanApprove - Hook to check if the current user can approve a change order.
 *
 * Context: Used by WorkflowButtons and other components to control approval action visibility.
 * Combines approval info from the API with user permissions to determine authority.
 *
 * Features:
 * - Fetches approval info from backend (impact level, assigned approver, user authority)
 * - Checks if user has change-order-approve permission
 * - Combines with user authority level to determine approval rights
 * - Provides clear reason when approval is not allowed
 *
 * @param changeOrder - The change order to check approval authority for
 * @returns Object with canApprove flag, authority level, loading state, and optional reason
 *
 * @example
 * ```tsx
 * const { canApprove, authorityLevel, isLoading, reason } = useCanApprove(changeOrder);
 *
 * if (isLoading) return <Spin />;
 * if (!canApprove) return <Tooltip title={reason}><Button disabled>Approve</Button></Tooltip>;
 * return <Button onClick={handleApprove}>Approve (Level: {authorityLevel})</Button>;
 * ```
 */
export function useCanApprove(changeOrder: ChangeOrderPublic | undefined): UseCanApproveResult {
  const { can } = usePermission();
  const user = useAuthStore((state) => state.user);

  // Fetch approval info from backend
  const { data: approvalInfo, isLoading } = useApprovalInfo(
    changeOrder?.change_order_id,
    {
      enabled: !!changeOrder && changeOrder.status !== "Draft",
    }
  );

  // Check if user has the approve permission
  const hasApprovePermission = can("change-order-approve");

  // Determine if user can approve
  const result = useMemo((): UseCanApproveResult => {
    if (!changeOrder) {
      return {
        canApprove: false,
        authorityLevel: null,
        isLoading: false,
        reason: "Change order not found",
      };
    }

    // Draft status cannot be approved (must be submitted first)
    if (changeOrder.status === "Draft") {
      return {
        canApprove: false,
        authorityLevel: approvalInfo?.user_authority_level || null,
        isLoading,
        reason: "Change order must be submitted for approval first",
      };
    }

    // Rejected or Implemented status cannot be approved
    if (changeOrder.status === "Rejected" || changeOrder.status === "Implemented") {
      return {
        canApprove: false,
        authorityLevel: approvalInfo?.user_authority_level || null,
        isLoading,
        reason: `Cannot approve a ${changeOrder.status} change order`,
      };
    }

    // Already approved
    if (changeOrder.status === "Approved") {
      return {
        canApprove: false,
        authorityLevel: approvalInfo?.user_authority_level || null,
        isLoading,
        reason: "Change order is already approved",
      };
    }

    // User doesn't have approve permission
    if (!hasApprovePermission) {
      return {
        canApprove: false,
        authorityLevel: approvalInfo?.user_authority_level || null,
        isLoading,
        reason: "You do not have permission to approve change orders",
      };
    }

    // Still loading approval info
    if (isLoading || !approvalInfo) {
      return {
        canApprove: false,
        authorityLevel: null,
        isLoading: true,
        reason: "Loading approval information...",
      };
    }

    // Backend has determined user cannot approve
    if (!approvalInfo.user_can_approve) {
      // Check if user is the assigned approver
      const isAssignedApprover =
        approvalInfo.assigned_approver &&
        user &&
        approvalInfo.assigned_approver.user_id === user.user_id;

      if (!isAssignedApprover) {
        return {
          canApprove: false,
          authorityLevel: approvalInfo.user_authority_level || null,
          isLoading: false,
          reason: `You are not the assigned approver. Assigned: ${approvalInfo.assigned_approver?.full_name || "Unknown"}`,
        };
      }

      // Check if user has sufficient authority level
      const authorityLevels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
      const userLevelIndex = authorityLevels.indexOf(approvalInfo.user_authority_level || "");
      const requiredLevelIndex = authorityLevels.indexOf(approvalInfo.impact_level || "");

      if (userLevelIndex < requiredLevelIndex) {
        return {
          canApprove: false,
          authorityLevel: approvalInfo.user_authority_level || null,
          isLoading: false,
          reason: `Insufficient authority. Your level: ${approvalInfo.user_authority_level}, Required: ${approvalInfo.impact_level}`,
        };
      }

      return {
        canApprove: false,
        authorityLevel: approvalInfo.user_authority_level || null,
        isLoading: false,
        reason: "You are not authorized to approve this change order",
      };
    }

    // User can approve
    return {
      canApprove: true,
      authorityLevel: approvalInfo.user_authority_level || null,
      isLoading: false,
    };
  }, [changeOrder, approvalInfo, isLoading, hasApprovePermission, user]);

  return result;
}
