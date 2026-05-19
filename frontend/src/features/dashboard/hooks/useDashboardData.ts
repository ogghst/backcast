import { useQuery, UseQueryResult } from "@tanstack/react-query";
import { useMemo } from "react";
import { apiClient } from "@/api/client";
import type { DashboardData, DashboardDataAPI } from "../types";
import { transformDashboardData } from "../types";
import { queryKeys } from "@/api/queryKeys";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";

export function useDashboardData(): UseQueryResult<DashboardData, Error> {
  const { asOf, branch } = useTimeMachineParams();

  const queryParams = useMemo(
    () => ({
      asOf: asOf || undefined,
      branch,
    }),
    [asOf, branch],
  );

  return useQuery<DashboardData>({
    queryKey: queryKeys.dashboard.recentActivity(queryParams),
    queryFn: async () => {
      const response = await apiClient.get<DashboardDataAPI>(
        "/api/v1/dashboard/recent-activity",
        {
          params: {
            as_of: asOf || undefined,
            branch,
          },
        },
      );
      return transformDashboardData(response.data);
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: 1,
  });
}
