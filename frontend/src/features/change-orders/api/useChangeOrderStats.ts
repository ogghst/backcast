/**
 * Custom hook for fetching Change Order statistics for a project.
 *
 * Provides aggregated analytics including:
 * - Summary KPIs (total count, cost exposure, pending/approved values)
 * - Distribution by status and impact level
 * - Cumulative cost trend over time
 * - Approval workload by approver
 * - Aging items (stuck/overdue change orders)
 */
import { useQuery, UseQueryOptions } from "@tanstack/react-query";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { queryKeys } from "@/api/queryKeys";

/**
 * Response type for change order statistics.
 * Matches backend ChangeOrderStatsResponse schema.
 */
export interface ChangeOrderStatsResponse {
  total_count: number;
  total_cost_exposure: number;
  pending_value: number;
  approved_value: number;
  by_status: ChangeOrderStatusStats[];
  by_impact_level: ChangeOrderImpactStats[];
  cost_trend: ChangeOrderTrendPoint[];
  avg_approval_time_days: number | null;
  approval_workload: ApprovalWorkloadItem[];
  aging_items: AgingChangeOrder[];
  aging_threshold_days: number;
}

export interface ChangeOrderStatusStats {
  status: string;
  count: number;
  total_value: number | null;
}

export interface ChangeOrderImpactStats {
  impact_level: string;
  count: number;
  total_value: number | null;
}

export interface ChangeOrderTrendPoint {
  date: string;
  cumulative_value: number;
  count: number;
}

export interface ApprovalWorkloadItem {
  approver_id: string;
  approver_name: string;
  pending_count: number;
  overdue_count: number;
  avg_days_waiting: number;
}

export interface AgingChangeOrder {
  change_order_id: string;
  code: string;
  title: string;
  status: string;
  days_in_status: number;
  impact_level: string | null;
  sla_status: string | null;
}

export interface UseChangeOrderStatsParams {
  projectId: string;
  branch?: string;
  agingThresholdDays?: number;
}

/**
 * Custom hook for fetching change order statistics.
 *
 * @param params - Query parameters
 * @param params.projectId - Project ID (required)
 * @param params.branch - Branch name (default: "main")
 * @param params.agingThresholdDays - Days threshold for aging detection (default: 7)
 * @param queryOptions - Additional query options
 */
export const useChangeOrderStats = (
  params: UseChangeOrderStatsParams,
  queryOptions?: Omit<
    UseQueryOptions<ChangeOrderStatsResponse, Error>,
    "queryKey" | "queryFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const { projectId, branch = "main", agingThresholdDays = 7 } = params;

  return useQuery({
    queryKey: queryKeys.changeOrders.stats(projectId, {
      branch,
      asOf,
      agingThresholdDays,
    }),
    queryFn: async () => {
      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/change-orders/stats",
        query: {
          project_id: projectId,
          branch,
          as_of: asOf || undefined,
          aging_threshold_days: agingThresholdDays,
        },
      }) as Promise<ChangeOrderStatsResponse>;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes - analytics can be slightly stale
    refetchOnWindowFocus: true,
    ...queryOptions,
  });
};
