/**
 * Phase 9 — canonical required-permission + scope mapping for ALL 25 widgets.
 *
 * This is the drift-detection source of truth. Every widget's
 * `requiredPermission` + `scope` is asserted here against the CORRECTED §6
 * mapping of the global-dashboard-widgets design doc. A future edit that
 * changes either field on any widget (or adds/removes a widget) will break a
 * focused assertion, forcing an explicit, reviewed update to this table.
 *
 * The 4 portfolio widgets are also covered by `portfolioWidgets.test.tsx`
 * (render-focused); this file is the single exhaustive mapping assertion.
 *
 * Design doc: docs/03-project-plan/iterations/2026-06-29-global-dashboard-widgets/
 *   global-dashboard-widgets-design.md §6 (corrected).
 */

import { describe, it, expect } from "vitest";
import type { Permission } from "@/types/auth";
// Importing registerAll triggers every widget's module-level
// registerWidget() side effect, populating the shared registry.
import "@/features/widgets/definitions/registerAll";
import { getWidgetDefinition, getAllWidgetDefinitions } from "../..";
import { widgetTypeId } from "../../types";

/**
 * The full mapping. `scope` is asserted on every row; `requiredPermission`
 * uses `Permission | Permission[]` to match the WidgetDefinition type.
 */
const EXPECTATIONS: Array<{
  typeId: string;
  scope: "project" | "portfolio";
  requiredPermission: Permission | Permission[];
}> = [
  // ── 21 project-scope widgets ────────────────────────────────────────────
  { typeId: "project-header", scope: "project", requiredPermission: "project-read" },
  { typeId: "quick-stats-bar", scope: "project", requiredPermission: "evm-read" },
  { typeId: "evm-summary", scope: "project", requiredPermission: "evm-read" },
  { typeId: "budget-status", scope: "project", requiredPermission: "evm-read" },
  {
    typeId: "budget-settings",
    scope: "project",
    requiredPermission: "project-budget-settings-read",
  },
  {
    typeId: "cost-registrations",
    scope: "project",
    // G15 dual: useCostRegistrations (cost-registration-read) AND
    // useProjectCurrency (project-read). Array form → hasAllPermissions.
    requiredPermission: ["cost-registration-read", "project-read"],
  },
  {
    typeId: "change-order-analytics",
    scope: "project",
    requiredPermission: "change-order-read",
  },
  {
    typeId: "change-orders-list",
    scope: "project",
    requiredPermission: "change-order-read",
  },
  { typeId: "wbe-tree", scope: "project", requiredPermission: ["project-read", "wbs-element-read", "control-account-read", "work-package-read", "cost-element-read", "schedule-baseline-read"] },
  { typeId: "variance-chart", scope: "project", requiredPermission: "evm-read" },
  {
    typeId: "progress-tracker",
    scope: "project",
    requiredPermission: "progress-entry-read",
  },
  { typeId: "health-summary", scope: "project", requiredPermission: "evm-read" },
  {
    typeId: "evm-efficiency-gauges",
    scope: "project",
    requiredPermission: "evm-read",
  },
  { typeId: "evm-trend-chart", scope: "project", requiredPermission: "evm-read" },
  { typeId: "forecast", scope: "project", requiredPermission: "evm-read" },
  { typeId: "mini-gantt", scope: "project", requiredPermission: "cost-element-read" },
  { typeId: "cost-history", scope: "project", requiredPermission: "evm-read" },
  { typeId: "coq-summary", scope: "project", requiredPermission: "cost-event-read" },
  {
    typeId: "coq-trend-chart",
    scope: "project",
    requiredPermission: "cost-event-read",
  },
  {
    typeId: "coq-category-breakdown",
    scope: "project",
    requiredPermission: "cost-event-read",
  },
  {
    typeId: "coq-work-packages",
    scope: "project",
    requiredPermission: "cost-event-read",
  },

  // ── 4 portfolio-scope widgets ───────────────────────────────────────────
  { typeId: "portfolio-kpi", scope: "portfolio", requiredPermission: "portfolio-read" },
  {
    typeId: "portfolio-projects-table",
    scope: "portfolio",
    requiredPermission: "portfolio-read",
  },
  {
    typeId: "portfolio-co-pipeline",
    scope: "portfolio",
    requiredPermission: "change-order-read",
  },
  {
    typeId: "portfolio-distress-list",
    scope: "portfolio",
    requiredPermission: "portfolio-read",
  },
];

describe("widget permission + scope mapping (Phase 9, §6 corrected)", () => {
  it("covers exactly the 25 known widgets (21 project + 4 portfolio)", () => {
    expect(EXPECTATIONS).toHaveLength(25);
    expect(EXPECTATIONS.filter((e) => e.scope === "project")).toHaveLength(21);
    expect(EXPECTATIONS.filter((e) => e.scope === "portfolio")).toHaveLength(4);

    // Registry itself must hold exactly these 25 (catches duplicate/extra
    // registerWidget calls introduced alongside a mapping drift).
    expect(getAllWidgetDefinitions()).toHaveLength(25);
  });

  it("has no duplicate typeIds in the expectation table", () => {
    const ids = EXPECTATIONS.map((e) => e.typeId);
    expect(new Set(ids).size).toBe(ids.length);
  });

  // Per-widget assertions. expect() count = scope + requiredPermission per row
  // (50 assertions) + the one definition-presence check per row (25) = 75,
  // plus the structural assertions above.
  it.each(EXPECTATIONS)(
    "widget $typeId is registered with the corrected scope + requiredPermission",
    ({ typeId, scope, requiredPermission }) => {
      const def = getWidgetDefinition(widgetTypeId(typeId));
      expect(def, `${typeId} must be registered`).toBeDefined();
      expect(def?.scope, `${typeId} scope`).toBe(scope);
      expect(def?.requiredPermission, `${typeId} requiredPermission`).toEqual(
        requiredPermission,
      );
    },
  );
});
