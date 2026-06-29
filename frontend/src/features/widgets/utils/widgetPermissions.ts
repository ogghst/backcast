import type { WidgetDefinition } from "../types";
import type { Permission } from "@/types/auth";
import type { DashboardScope } from "../context/DashboardContextBus";

/**
 * Widget permission + scope helpers (Phase 5 of global-dashboard-widgets).
 *
 * Two independent gates, per the locked design:
 *
 * 1. **Render gate (permission)** — a widget's `requiredPermission` decides
 *    whether the grid may mount the real widget component for the current
 *    user, or must instead render a locked placeholder. This runs at grid
 *    render time and is independent of dashboard scope.
 *
 * 2. **Palette gate (permission + scope)** — the widget catalog additionally
 *    filters by dashboard `scope` so a portfolio dashboard only offers
 *    portfolio widgets (and a project dashboard only project widgets).
 *    A widget with **no `scope` set is treated as `"project"`** for
 *    filtering, so the 21 legacy project widgets stay on the project palette
 *    and are hidden from the portfolio palette. Phase 9 will later stamp
 *    the scope explicitly.
 *
 * The helpers are pure so they can be unit-tested in isolation and shared
 * between {@link WidgetPalette} and {@link DashboardGrid}.
 */

/**
 * Whether a widget definition is visible on the given dashboard scope.
 *
 * - Unset `scope` defaults to `"project"` (legacy widget behaviour).
 * - `"any"` widgets appear on both project and portfolio dashboards.
 * - `"project"` / `"portfolio"` are strict matches.
 */
export function isWidgetInScope(
  def: Pick<WidgetDefinition, "scope">,
  scope: DashboardScope,
): boolean {
  const ws = def.scope ?? "project";
  return ws === "any" || ws === scope;
}

/**
 * Whether the current user is permitted to view a widget, given the auth
 * store's check functions.
 *
 * - No `requiredPermission` → permitted (any authenticated user).
 * - Array form → user must hold **all** listed permissions
 *   (gated via `hasAllPermissions`, e.g. a widget needing both
 *   `project-read` and `cost-registration-read`).
 * - Single permission → gated via `hasPermission`.
 */
export function isWidgetPermitted(
  def: Pick<WidgetDefinition, "requiredPermission">,
  hasPermission: (p: Permission | string) => boolean,
  hasAllPermissions: (p: (Permission | string)[]) => boolean,
): boolean {
  const req = def.requiredPermission;
  if (!req) return true;
  return Array.isArray(req) ? hasAllPermissions(req) : hasPermission(req);
}
