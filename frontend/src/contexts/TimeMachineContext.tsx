import React, { createContext, useContext, useMemo, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";

/**
 * Time Machine context value providing as_of and branch parameters
 * for API calls throughout the component tree.
 */
interface TimeMachineContextValue {
  /** ISO timestamp for time-travel, undefined for current time */
  asOf: string | undefined;
  /** Current branch name */
  branch: string;
  /** Whether viewing historical data (not "now") */
  isHistorical: boolean;
  /** Invalidate all queries when time/branch changes */
  invalidateQueries: () => void;
}

const TimeMachineContext = createContext<TimeMachineContextValue | null>(null);

interface TimeMachineProviderProps {
  children: React.ReactNode;
}

/**
 * Provider component that supplies time-travel context to the app.
 *
 * Should wrap the main app content (inside QueryClientProvider).
 *
 * @example
 * ```tsx
 * <QueryClientProvider client={queryClient}>
 *   <TimeMachineProvider>
 *     <App />
 *   </TimeMachineProvider>
 * </QueryClientProvider>
 * ```
 */
export function TimeMachineProvider({ children }: TimeMachineProviderProps) {
  const queryClient = useQueryClient();

  // Subscribe to store state
  // Subscribe to store state changes directly to ensure re-renders
  const selectedTime = useTimeMachineStore((state) => {
    if (!state.currentProjectId) return null;
    return state.projectSettings[state.currentProjectId]?.selectedTime ?? null;
  });

  const selectedBranch = useTimeMachineStore((state) => {
    if (!state.currentProjectId) return "main";
    return (
      state.projectSettings[state.currentProjectId]?.selectedBranch ?? "main"
    );
  });

  // Compute context values
  const asOf = useMemo(
    () => (selectedTime ? selectedTime : undefined),
    [selectedTime]
  );

  const isHistorical = useMemo(() => selectedTime !== null, [selectedTime]);

  // Invalidate queries when time or branch changes
  const invalidateQueries = useCallback(() => {
    // Invalidate all project-related queries
    queryClient.invalidateQueries({ queryKey: ["projects"] });
    queryClient.invalidateQueries({ queryKey: ["wbes"] });
    queryClient.invalidateQueries({ queryKey: ["cost-elements"] });
    queryClient.invalidateQueries({ queryKey: ["cost-element-types"] });
  }, [queryClient]);

  const value = useMemo<TimeMachineContextValue>(
    () => ({
      asOf,
      branch: selectedBranch,
      isHistorical,
      invalidateQueries,
    }),
    [asOf, selectedBranch, isHistorical, invalidateQueries]
  );

  return (
    <TimeMachineContext.Provider value={value}>
      {children}
    </TimeMachineContext.Provider>
  );
}

/**
 * Hook to access time machine context values.
 *
 * @throws Error if used outside TimeMachineProvider
 *
 * @example
 * ```tsx
 * function ProjectDetail({ projectId }: { projectId: string }) {
 *   const { asOf, branch, isHistorical } = useTimeMachine();
 *
 *   const { data } = useQuery({
 *     queryKey: ['project', projectId, { asOf, branch }],
 *     queryFn: () => ProjectsService.getProject(projectId, { asOf, branch }),
 *   });
 *
 *   return (
 *     <div>
 *       {isHistorical && <Badge>Viewing History</Badge>}
 *       <ProjectView project={data} />
 *     </div>
 *   );
 * }
 * ```
 */
export function useTimeMachine(): TimeMachineContextValue {
  const context = useContext(TimeMachineContext);
  if (!context) {
    throw new Error("useTimeMachine must be used within TimeMachineProvider");
  }
  return context;
}

/**
 * Hook that returns API query parameters including as_of and branch.
 * Use this when building query keys or API calls.
 *
 * @example
 * ```tsx
 * const params = useTimeMachineParams();
 * // { asOf: '2026-01-15T00:00:00Z', branch: 'main' } or
 * // { asOf: undefined, branch: 'main' } for current time
 * ```
 */
export function useTimeMachineParams(): { asOf?: string; branch: string } {
  const { asOf, branch } = useTimeMachine();
  return useMemo(() => ({ asOf, branch }), [asOf, branch]);
}
