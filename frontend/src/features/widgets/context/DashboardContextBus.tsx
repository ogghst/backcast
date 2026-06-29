import React, { createContext, useMemo, useState } from "react";
import { useTimeMachine } from "@/contexts/TimeMachineContext";
import type { BranchMode } from "@/stores/useTimeMachineStore";
import type { PortfolioFilterValue } from "@/stores/usePortfolioFilterStore";

/** Dashboard scope: a single project, or the cross-project portfolio. */
export type DashboardScope = "project" | "portfolio";

/**
 * Dashboard context value providing entity selection and time-machine state.
 *
 * Consumes (does not duplicate) TimeMachineContext for branch/viewDate.
 * Adds entity-level context (projectId, wbsElementId, costElementId) for widgets.
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

  /** Dashboard scope — drives whether widgets are project- or portfolio-oriented. */
  scope: DashboardScope;
  /** Project identifier from URL params (empty string for portfolio scope). */
  projectId: string;
  /** Currently selected WBE identifier */
  wbsElementId: string | undefined;
  /** Currently selected cost element identifier */
  costElementId: string | undefined;
  /** Update the selected WBE */
  setWbeId: (id: string | undefined) => void;
  /** Update the selected cost element */
  setCostElementId: (id: string | undefined) => void;
  /** Portfolio filter values; present only on portfolio-scope dashboards. */
  portfolioFilter?: PortfolioFilterValue;
}

// eslint-disable-next-line react-refresh/only-export-components
export const DashboardContext = createContext<DashboardContextValue | null>(
  null,
);

interface DashboardContextBusProps {
  /** Project identifier (URL param). Required when scope is "project"; omitted for portfolio scope. */
  projectId?: string;
  /** Dashboard scope. "project" (default) requires projectId; "portfolio" is cross-project. */
  scope?: DashboardScope;
  /** Portfolio filter values (controlDate/status/rag). The portfolio host reads these from usePortfolioFilterStore and passes them through; undefined for project scope. */
  portfolioFilter?: PortfolioFilterValue;
  children: React.ReactNode;
}

/**
 * Provider that composes TimeMachineContext with entity-level selection state.
 *
 * Must be rendered inside `TimeMachineProvider` (which wraps the entire app).
 *
 * @example
 * ```tsx
 * // Project dashboard (default scope).
 * <DashboardContextBus projectId={projectId}>
 *   <DashboardGrid />
 * </DashboardContextBus>
 *
 * // Portfolio dashboard.
 * <DashboardContextBus scope="portfolio" portfolioFilter={filter}>
 *   <DashboardGrid />
 * </DashboardContextBus>
 * ```
 */
export function DashboardContextBus({
  projectId,
  scope = "project",
  portfolioFilter,
  children,
}: DashboardContextBusProps) {
  if (scope === "project" && !projectId) {
    throw new Error(
      "DashboardContextBus: projectId is required when scope is 'project'",
    );
  }

  const { asOf, branch, mode, isHistorical, invalidateQueries } =
    useTimeMachine();

  const [wbsElementId, setWbeId] = useState<string | undefined>(undefined);
  const [costElementId, setCostElementId] = useState<string | undefined>(
    undefined,
  );

  const effectiveProjectId = projectId ?? "";

  const value = useMemo<DashboardContextValue>(
    () => ({
      asOf,
      branch,
      mode,
      isHistorical,
      invalidateQueries,
      scope,
      projectId: effectiveProjectId,
      wbsElementId,
      costElementId,
      setWbeId,
      setCostElementId,
      portfolioFilter,
    }),
    [
      asOf,
      branch,
      mode,
      isHistorical,
      invalidateQueries,
      scope,
      effectiveProjectId,
      wbsElementId,
      costElementId,
      portfolioFilter,
    ],
  );

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  );
}
