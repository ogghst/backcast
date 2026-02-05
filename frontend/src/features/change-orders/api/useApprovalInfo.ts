import { useQuery, UseQueryOptions } from "@tanstack/react-query";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { queryKeys } from "@/api/queryKeys";

/**
 * TypeScript interface for ApprovalInfoPublic schema.
 *
 * Matches backend schema in backend/app/models/schemas/change_order.py
 */
export interface ApprovalInfo {
  /** Financial impact level (LOW/MEDIUM/HIGH/CRITICAL) */
  impact_level: string | null;
  /** Financial impact details (budget_delta, revenue_delta) */
  financial_impact: {
    budget_delta: number;
    revenue_delta: number;
  } | null;
  /** Assigned approver details */
  assigned_approver: {
    user_id: string;
    full_name: string;
    email: string;
    role: string;
  } | null;
  /** When the approval SLA started */
  sla_assigned_at: string | null;
  /** SLA deadline for approval */
  sla_due_date: string | null;
  /** Current SLA tracking status (pending/approaching/overdue) */
  sla_status: string | null;
  /** Number of business days remaining until SLA deadline */
  sla_business_days_remaining: number | null;
  /** Whether the current user has authority to approve this change order */
  user_can_approve: boolean;
  /** Current user's authority level (LOW/MEDIUM/HIGH/CRITICAL) */
  user_authority_level: string | null;
}

/**
 * Custom hook for fetching change order approval information.
 *
 * Context: Used in change order detail view to display approval matrix,
 * assigned approver, SLA status, and user's approval authority.
 *
 * @param changeOrderId - Change Order ID to fetch approval info for
 * @param queryOptions - Optional React Query configuration
 * @returns Query result with ApprovalInfo data
 *
 * @example
 * const { data: approvalInfo, isLoading } = useApprovalInfo(changeOrderId);
 */
export const useApprovalInfo = (
  changeOrderId: string | undefined,
  queryOptions?: Omit<UseQueryOptions<ApprovalInfo, Error>, "queryKey">,
) => {
  return useQuery({
    queryKey: queryKeys.changeOrders.approvalInfo(changeOrderId || ""),
    queryFn: async () => {
      if (!changeOrderId) throw new Error("Change Order ID is required");

      return __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/change-orders/${changeOrderId}/approval-info`,
      }) as Promise<ApprovalInfo>;
    },
    enabled: !!changeOrderId,
    ...queryOptions,
  });
};
