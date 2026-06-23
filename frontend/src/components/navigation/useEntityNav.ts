/**
 * Route-derived entity-detail navigation for the sidebar.
 *
 * Stateless (no store, no fetch): detects the active entity-detail route via
 * `useMatch`/`useParams` against the exact patterns in `src/routes/index.tsx`
 * and returns the matching `entityNavItems` builder output plus a static label.
 *
 * This is NAV, independent of chat context — it includes all 5 entity types
 * (control accounts are NOT a supported chat context, but they DO have nav).
 *
 * Order from most-specific to least so a nested route can't be shadowed by a
 * shorter prefix. Returns `null` on any non-entity route (including the
 * top-level `/projects` LIST route, which must not trigger the project detail).
 */

import { useMemo } from "react";
import { useMatch, useParams } from "react-router-dom";

import type { NavigationItem } from "@/components/navigation";
import {
  controlAccountNavItems,
  costElementNavItems,
  projectNavItems,
  wbeNavItems,
  workPackageNavItems,
} from "@/components/navigation/entityNavItems";

export interface EntityNav {
  label: string;
  items: NavigationItem[];
}

/**
 * Resolve the active entity-detail nav, or `null` when not on an entity route.
 *
 * Mirrors the route patterns registered in `src/routes/index.tsx` with a
 * trailing splat so entity nav STAYS VISIBLE on sub-routes (dashboard, tabs,
 * cost-history, documents, …). React Router 6 `useMatch` is exact-match
 * (`end: true`), so `/projects/:projectId` returned null on every sub-route
 * (e.g. `/projects/p1/dashboard`) — dropping the sidebar entity nav on every
 * tab except Overview. The splat (`/*`) matches zero-or-more trailing segments,
 * so both the entity root AND its sub-routes resolve.
 *
 *   - /projects/:projectId/*                                   → "Project"
 *   - /projects/:projectId/wbs-elements/:wbsElementId/*        → "WBS Element"
 *   - /projects/:projectId/control-accounts/:controlAccountId/* → "Control Account"
 *   - /projects/:projectId/work-packages/:id/*                 → "Work Package"
 *   - /work-packages/:id/*                                      → "Work Package"
 *   - /cost-elements/:id/*                                      → "Cost Element"
 *
 * The `/projects` LIST route has no id segment, so it does NOT match
 * `/projects/:projectId/*` — it correctly returns null.
 */
export function useEntityNav(): EntityNav | null {
  // useMatch returns null for non-matching patterns; at most one is non-null.
  const wbsMatch = useMatch(
    "/projects/:projectId/wbs-elements/:wbsElementId/*",
  );
  const controlAccountMatch = useMatch(
    "/projects/:projectId/control-accounts/:controlAccountId/*",
  );
  const nestedWpMatch = useMatch("/projects/:projectId/work-packages/:id/*");
  const standaloneWpMatch = useMatch("/work-packages/:id/*");
  const costElementMatch = useMatch("/cost-elements/:id/*");
  // The bare project detail pattern — the `/projects` LIST route has no
  // trailing id segment so it will NOT match `/projects/:projectId/*`.
  const projectMatch = useMatch("/projects/:projectId/*");

  const params = useParams<{
    projectId?: string;
    wbsElementId?: string;
    controlAccountId?: string;
    id?: string;
  }>();

  return useMemo<EntityNav | null>(() => {
    if (wbsMatch && params.projectId && params.wbsElementId) {
      return {
        label: "WBS Element",
        items: wbeNavItems(params.projectId, params.wbsElementId),
      };
    }

    if (controlAccountMatch && params.projectId && params.controlAccountId) {
      return {
        label: "Control Account",
        items: controlAccountNavItems(
          params.projectId,
          params.controlAccountId,
        ),
      };
    }

    if (nestedWpMatch && params.projectId && params.id) {
      return {
        label: "Work Package",
        items: workPackageNavItems(params.id, params.projectId),
      };
    }

    if (standaloneWpMatch && params.id) {
      return {
        label: "Work Package",
        items: workPackageNavItems(params.id, params.projectId),
      };
    }

    if (costElementMatch && params.id) {
      return {
        label: "Cost Element",
        items: costElementNavItems(params.id),
      };
    }

    if (projectMatch && params.projectId) {
      return {
        label: "Project",
        items: projectNavItems(params.projectId),
      };
    }

    return null;
  }, [
    wbsMatch,
    controlAccountMatch,
    nestedWpMatch,
    standaloneWpMatch,
    costElementMatch,
    projectMatch,
    params.projectId,
    params.wbsElementId,
    params.controlAccountId,
    params.id,
  ]);
}
