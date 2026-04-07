import { useQuery, UseQueryResult } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { DashboardData, DashboardDataAPI } from "../types";
import { transformDashboardData } from "../types";
import { queryKeys } from "@/api/queryKeys";

export function useDashboardData(): UseQueryResult<DashboardData, Error> {
  return useQuery<DashboardData>({
    queryKey: queryKeys.dashboard.recentActivity,
    queryFn: async () => {
      const response = await apiClient.get<DashboardDataAPI>("/api/v1/dashboard/recent-activity");
      return transformDashboardData(response.data);
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: 1,
  });
}
