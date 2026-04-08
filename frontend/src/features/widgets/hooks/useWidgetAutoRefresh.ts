import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

/**
 * Manages automatic data refresh for a widget based on a configurable interval.
 * Pauses refetching when the widget is not visible.
 */
export function useWidgetAutoRefresh(
  queryKey: readonly unknown[],
  refreshInterval: number | undefined,
  isVisible: boolean,
): { isStale: boolean; lastRefreshed: Date | null } {
  const queryClient = useQueryClient();
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (!refreshInterval || !isVisible) return;

    intervalRef.current = setInterval(() => {
      queryClient.refetchQueries({ queryKey, stale: true }).then(() => {
        const state = queryClient.getQueryState(queryKey);
        if (state?.dataUpdatedAt) {
          setLastRefreshed(new Date(state.dataUpdatedAt));
        }
      });
    }, refreshInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [queryClient, queryKey, refreshInterval, isVisible]);

  // Compute staleness from query state (derived data, not impure call during render)
  const dataUpdatedAt = queryClient.getQueryState(queryKey)?.dataUpdatedAt;
  const isStale = useMemo(() => {
    if (!refreshInterval || !dataUpdatedAt) return false;
    return dataUpdatedAt + refreshInterval < Date.now();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshInterval, dataUpdatedAt, lastRefreshed]);

  return { isStale, lastRefreshed };
}
