/**
 * useDashboardData Hook
 *
 * Custom hook for fetching dashboard data using TanStack Query.
 * Provides cached data with 5-minute stale time and proper error handling.
 */

import { useQuery, UseQueryResult } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { DashboardData, DashboardDataAPI } from "../types";
import { queryKeys } from "@/api/queryKeys";

/**
 * Dashboard data hook with TanStack Query integration
 *
 * Features:
 * - 5-minute cache (staleTime)
 * - Automatic background refetch on window focus
 * - Proper error handling via axios interceptors
 * - Type-safe response with backend-to-frontend transformation
 *
 * @returns TanStack Query result with DashboardData
 *
 * @example
 * ```tsx
 * function Dashboard() {
 *   const { data, isLoading, error, refetch } = useDashboardData();
 *
 *   if (isLoading) return <DashboardSkeleton />;
 *   if (error) return <ErrorState onRetry={refetch} />;
 *   if (!data) return null;
 *
 *   return <DashboardContent data={data} />;
 * }
 * ```
 */
export function useDashboardData(): UseQueryResult<DashboardData, Error> {
  return useQuery<DashboardData>({
    queryKey: queryKeys.dashboard.recentActivity,
    queryFn: async () => {
      const response = await apiClient.get<DashboardDataAPI>("/api/v1/dashboard/recent-activity");
      // Transform backend API response to frontend format
      const { transformDashboardData } = await import("../types");
      return transformDashboardData(response.data);
    },
    // Cache data for 5 minutes
    staleTime: 5 * 60 * 1000,
    // Keep data in cache for 10 minutes
    gcTime: 10 * 60 * 1000,
    // Don't refetch on window focus to avoid unnecessary requests
    refetchOnWindowFocus: false,
    // Retry once on failure
    retry: 1,
  });
}
