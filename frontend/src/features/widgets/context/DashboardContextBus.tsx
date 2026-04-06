import React, { createContext, useMemo, useState } from "react";
import { useTimeMachine } from "@/contexts/TimeMachineContext";
import type { BranchMode } from "@/stores/useTimeMachineStore";

/**
 * Dashboard context value providing entity selection and time-machine state.
 *
 * Consumes (does not duplicate) TimeMachineContext for branch/viewDate.
 * Adds entity-level context (projectId, wbeId, costElementId) for widgets.
 */
export interface DashboardContextValue {
  /** ISO timestamp for time-travel, undefined for current time */
  asOf: string | undefined;
  /** Current branch name */
  branch: string;
  /** Branch mode: "merged" or "isolated" */
  mode: BranchMode;
  /** Whether viewing historical data */
  isHistorical: boolean;
  /** Invalidate all queries when time/branch changes */
  invalidateQueries: () => void;

  /** Project identifier from URL params */
  projectId: string;
  /** Currently selected WBE identifier */
  wbeId: string | undefined;
  /** Currently selected cost element identifier */
  costElementId: string | undefined;
  /** Update the selected WBE */
  setWbeId: (id: string | undefined) => void;
  /** Update the selected cost element */
  setCostElementId: (id: string | undefined) => void;
}

// eslint-disable-next-line react-refresh/only-export-components
export const DashboardContext = createContext<DashboardContextValue | null>(
  null,
);

interface DashboardContextBusProps {
  /** Project identifier, typically from URL params */
  projectId: string;
  children: React.ReactNode;
}

/**
 * Provider that composes TimeMachineContext with entity-level selection state.
 *
 * Must be rendered inside `TimeMachineProvider` (which wraps the entire app).
 *
 * @example
 * ```tsx
 * <DashboardContextBus projectId={projectId}>
 *   <DashboardGrid />
 * </DashboardContextBus>
 * ```
 */
export function DashboardContextBus({
  projectId,
  children,
}: DashboardContextBusProps) {
  const { asOf, branch, mode, isHistorical, invalidateQueries } =
    useTimeMachine();

  const [wbeId, setWbeId] = useState<string | undefined>(undefined);
  const [costElementId, setCostElementId] = useState<string | undefined>(
    undefined,
  );

  const value = useMemo<DashboardContextValue>(
    () => ({
      asOf,
      branch,
      mode,
      isHistorical,
      invalidateQueries,
      projectId,
      wbeId,
      costElementId,
      setWbeId,
      setCostElementId,
    }),
    [
      asOf,
      branch,
      mode,
      isHistorical,
      invalidateQueries,
      projectId,
      wbeId,
      costElementId,
    ],
  );

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  );
}
