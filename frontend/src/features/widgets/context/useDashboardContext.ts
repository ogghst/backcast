import { useContext } from "react";
import { DashboardContext } from "./DashboardContextBus";
import type { DashboardContextValue } from "./DashboardContextBus";

export type { DashboardContextValue };

/**
 * Hook to access the dashboard context.
 *
 * @throws Error if used outside DashboardContextBus
 *
 * @example
 * ```tsx
 * function MyWidget() {
 *   const { projectId, branch, wbeId } = useDashboardContext();
 *   // ...
 * }
 * ```
 */
export function useDashboardContext(): DashboardContextValue {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error(
      "useDashboardContext must be used within DashboardContextBus",
    );
  }
  return context;
}
