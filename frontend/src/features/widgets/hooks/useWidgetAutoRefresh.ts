import { useEffect, useRef, useState } from "react";
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
  const [isStale, setIsStale] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stalenessCheckRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  // Check staleness periodically (every second) instead of during render
  useEffect(() => {
    if (!refreshInterval) return;

    const checkStaleness = () => {
      if (!lastRefreshed) {
        setIsStale(false);
        return;
      }
      const now = Date.now();
      setIsStale(lastRefreshed.getTime() + refreshInterval < now);
    };

    // Check immediately
    checkStaleness();

    // Then check every second
    stalenessCheckRef.current = setInterval(checkStaleness, 1000);

    return () => {
      if (stalenessCheckRef.current) {
        clearInterval(stalenessCheckRef.current);
      }
    };
  }, [refreshInterval, lastRefreshed]);

  return { isStale, lastRefreshed };
}
