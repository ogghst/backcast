import { useQuery, UseQueryOptions } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import type { ApprovalInfoPublic } from "@/api/generated";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";

// Re-export ApprovalInfoPublic as ApprovalInfo for backward compatibility
export type ApprovalInfo = ApprovalInfoPublic;

/**
 * Parameters for useApprovalInfo hook.
 */
interface UseApprovalInfoParams {
  /** Change Order ID to fetch approval info for */
  changeOrderId: string | undefined;
  /** Branch name (optional, defaults to time machine context branch or "main") */
  branch?: string;
}

/**
 * Custom hook for fetching change order approval information.
 *
 * Context: Used in change order detail view to display approval matrix,
 * assigned approver, SLA status, and user's approval authority.
 *
 * @param params - Parameters including changeOrderId and optional branch
 * @param queryOptions - Optional React Query configuration
 * @returns Query result with ApprovalInfo data
 *
 * @example
 * // Use current branch from time machine context
 * const { data: approvalInfo, isLoading } = useApprovalInfo({ changeOrderId });
 *
 * // Use specific branch
 * const { data: approvalInfo, isLoading } = useApprovalInfo({
 *   changeOrderId,
 *   branch: "BR-CO-2026-001"
 * });
 */
export const useApprovalInfo = (
  params: UseApprovalInfoParams | string | undefined,
  queryOptions?: Omit<UseQueryOptions<ApprovalInfoPublic, Error>, "queryKey">,
) => {
  // Support legacy call pattern where first arg is just changeOrderId string
  const changeOrderId = typeof params === "string" ? params : params?.changeOrderId;
  const paramBranch = typeof params === "object" ? params?.branch : undefined;

  // Get branch and asOf from time machine context with fallback
  const { branch: tmBranch, asOf } = useTimeMachineParams();
  const branch = paramBranch || tmBranch || "main";

  return useQuery({
    queryKey: queryKeys.changeOrders.approvalInfo(changeOrderId || "", { asOf }),
    queryFn: async () => {
      if (!changeOrderId) throw new Error("Change Order ID is required");

      return __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/change-orders/${changeOrderId}/approval-info`,
        query: {
          branch: branch,
          as_of: asOf || undefined,
        },
      }) as Promise<ApprovalInfoPublic>;
    },
    enabled: !!changeOrderId,
    ...queryOptions,
  });
};
