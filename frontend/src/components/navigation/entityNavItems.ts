/**
 * Pure builders for entity-detail navigation items.
 *
 * Single source of truth for the entity-detail nav arrays. The sidebar's
 * entity section consumes these (the in-page `PageNavigation` tab strip was
 * removed in Phase 3 of the nav redesign — the sidebar is the single home).
 *
 * Also the canonical home of the `NavigationItem` type, re-exported from
 * `@/components/navigation`.
 *
 * These are PURE functions — no React, no hooks. Each mirrors the exact
 * keys/labels/paths of its source layout (param names preserved).
 */

import type React from "react";

/** A single navigation entry (key/label/path, optional icon). */
export interface NavigationItem {
  key: string;
  label: string;
  path: string;
  icon?: React.ReactNode;
}

/**
 * Project detail nav. Mirrors `ProjectLayout` (Explorer tab intentionally
 * omitted — it's disabled in the route).
 */
export function projectNavItems(projectId: string): NavigationItem[] {
  return [
    { key: "dashboard", label: "Dashboard", path: `/projects/${projectId}/dashboard` },
    { key: "overview", label: "Overview", path: `/projects/${projectId}` },
    { key: "structure", label: "Structure", path: `/projects/${projectId}/structure` },
    { key: "schedule", label: "Schedule", path: `/projects/${projectId}/schedule` },
    { key: "change-orders", label: "Change Orders", path: `/projects/${projectId}/change-orders` },
    { key: "members", label: "Members", path: `/projects/${projectId}/members` },
    { key: "evm-analysis", label: "EVM Analysis", path: `/projects/${projectId}/evm-analysis` },
    { key: "coq-analysis", label: "COQ Analysis", path: `/projects/${projectId}/coq-analysis` },
    { key: "cost-events", label: "Cost Events", path: `/projects/${projectId}/cost-events` },
    { key: "documents", label: "Documents", path: `/projects/${projectId}/documents` },
    { key: "admin", label: "Admin", path: `/projects/${projectId}/admin` },
  ];
}

/**
 * WBS Element detail nav. Mirrors `WBSElementLayout`.
 */
export function wbeNavItems(
  projectId: string,
  wbsElementId: string,
): NavigationItem[] {
  const base = `/projects/${projectId}/wbs-elements/${wbsElementId}`;
  return [
    { key: "overview", label: "Overview", path: base },
    { key: "evm-analysis", label: "EVM Analysis", path: `${base}/evm-analysis` },
    { key: "cost-history", label: "Cost History", path: `${base}/cost-history` },
    { key: "documents", label: "Documents", path: `${base}/documents` },
  ];
}

/**
 * Cost Element detail nav. Mirrors `CostElementLayout`.
 */
export function costElementNavItems(id: string): NavigationItem[] {
  const base = `/cost-elements/${id}`;
  return [
    { key: "overview", label: "Overview", path: base },
    { key: "cost-registrations", label: "Cost Registrations", path: `${base}/cost-registrations` },
    { key: "cost-history", label: "Cost History", path: `${base}/cost-history` },
    { key: "documents", label: "Documents", path: `${base}/documents` },
  ];
}

/**
 * Control Account detail nav. Mirrors `ControlAccountLayout`.
 *
 * NOTE: `ControlAccountLayout` declares evm-analysis / cost-history / documents
 * tabs that are NOT registered as route children today (only the index Overview
 * route exists). The items are reproduced verbatim so the sidebar matches the
 * existing tab strip; the routes themselves are out of scope for this phase.
 */
export function controlAccountNavItems(
  projectId: string,
  controlAccountId: string,
): NavigationItem[] {
  const base = `/projects/${projectId}/control-accounts/${controlAccountId}`;
  return [
    { key: "overview", label: "Overview", path: base },
    { key: "evm-analysis", label: "EVM Analysis", path: `${base}/evm-analysis` },
    { key: "cost-history", label: "Cost History", path: `${base}/cost-history` },
    { key: "documents", label: "Documents", path: `${base}/documents` },
  ];
}

/**
 * Work Package detail nav. Mirrors `WorkPackageLayout`. Works for both the
 * nested (`/projects/:projectId/work-packages/:id`) and standalone
 * (`/work-packages/:id`) routes — `projectId` is optional exactly as the layout
 * treats it.
 */
export function workPackageNavItems(
  id: string,
  projectId?: string,
): NavigationItem[] {
  const base = projectId
    ? `/projects/${projectId}/work-packages/${id}`
    : `/work-packages/${id}`;
  return [
    { key: "overview", label: "Overview", path: base },
    { key: "cost-registrations", label: "Cost Registrations", path: `${base}/cost-registrations` },
    { key: "cost-history", label: "Cost History", path: `${base}/cost-history` },
    { key: "evm-analysis", label: "EVM Analysis", path: `${base}/evm-analysis` },
    { key: "documents", label: "Documents", path: `${base}/documents` },
  ];
}
