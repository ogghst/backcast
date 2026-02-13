import {
  useQuery,
  UseQueryOptions,
} from "@tanstack/react-query";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import type { ImpactAnalysisResponse } from "@/api/generated";
import { queryKeys } from "@/api/queryKeys";

/**
 * Custom hook for fetching impact analysis for a change order.
 * Compares the main branch with the change order's branch to show
 * financial impact, entity changes, and visualizations.
 *
 * @param changeOrderId - The UUID of the change order to analyze
 * @param branchName - Optional branch name (defaults to the CO's branch)
 * @param mode - Comparison mode: "merged" (default) or "isolated"
 * @param queryOptions - Optional TanStack Query options
 */
export const useImpactAnalysis = (
  changeOrderId: string | undefined,
  branchName?: string,
  mode: "merged" | "isolated" = "merged",
  queryOptions?: Omit<UseQueryOptions<ImpactAnalysisResponse, Error>, "queryKey" | "queryFn">
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery({
    queryKey: queryKeys.changeOrders.impact(changeOrderId, branchName, mode),
    queryFn: async () => {
      if (!changeOrderId) throw new Error("Change Order ID is required");
      if (!branchName) throw new Error("Branch name is required for impact analysis");

      return __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/change-orders/${changeOrderId}/impact`,
        query: {
          branch_name: branchName,
          mode: mode,
          as_of: asOf || undefined,
        },
      }) as Promise<ImpactAnalysisResponse>;
    },
    enabled: !!changeOrderId && !!branchName,
    ...queryOptions,
  });
};
