/**
 * Effective chat context for the sidebar's chat-history scoping.
 *
 * On the `/chat` route the URL `?ctx=` contract is the SOLE source of truth, so
 * this delegates to `useChatContextFromUrl`. On entity-detail routes the
 * effective context is derived from the route params (project / wbe / cost
 * element / work package) so the sidebar history list is scoped to what the
 * user is currently viewing. Otherwise it falls back to `{ type: "general" }`.
 *
 * Route patterns mirror `src/routes/index.tsx` exactly:
 *   - /chat                                       → ?ctx= contract
 *   - /projects/:projectId                        → project
 *   - /projects/:projectId/wbs-elements/:wbsElementId → wbe
 *   - /projects/:projectId/control-accounts/:controlAccountId → (control_account,
 *     which is NOT a supported SessionContext type → general)
 *   - /projects/:projectId/work-packages/:id      → work_package
 *   - /work-packages/:id                          → work_package (standalone)
 *   - /cost-elements/:id                          → cost_element
 */

import { useMemo } from "react";
import { useMatch, useParams } from "react-router-dom";

import type { SessionContext } from "@/features/ai/types";
import {
  useChatContextFromUrl,
  parseChatContext,
} from "@/hooks/navigation/useChatContextFromUrl";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";

/**
 * Resolve the effective `SessionContext` for the sidebar.
 *
 * Precedence:
 *   1. `/chat` route → `?ctx=` contract (sole source on chat).
 *   2. Entity-detail routes → derived from route params (matched by pattern).
 *   3. otherwise → `{ type: "general" }`.
 *
 * `project_id` is resolved from the route param when present, else from
 * `useTimeMachineStore.currentProjectId` (the WBS/cost/work-package routes
 * either nest under a project or need a fallback root).
 *
 * Patterns carry a trailing `/*` splat so the chat context STAYS scoped on
 * entity sub-routes (React Router 6 `useMatch` is exact-match, so the bare
 * patterns returned null on `/projects/p1/dashboard` etc.).
 */
export function useEffectiveChatContext(): SessionContext {
  // 1. The /chat route is authoritative — ?ctx= is the sole source there.
  const onChat = useMatch("/chat");

  // 2. Match each entity-detail route root. useMatch returns null when the
  //    pattern doesn't match the current location, so exactly one (at most) is
  //    non-null. Order from most-specific to least.
  const projectMatch = useMatch("/projects/:projectId/*");
  const wbsMatch = useMatch(
    "/projects/:projectId/wbs-elements/:wbsElementId/*",
  );
  const nestedWpMatch = useMatch(
    "/projects/:projectId/work-packages/:id/*",
  );
  const standaloneWpMatch = useMatch("/work-packages/:id/*");
  const costElementMatch = useMatch("/cost-elements/:id/*");

  const params = useParams<{
    projectId?: string;
    wbsElementId?: string;
    id?: string;
  }>();

  const chatContext = useChatContextFromUrl();
  const tmProjectId = useTimeMachineStore((s) => s.currentProjectId);

  return useMemo<SessionContext>(() => {
    if (onChat) {
      return chatContext.context;
    }

    const fallbackProjectId = params.projectId ?? tmProjectId ?? undefined;

    if (wbsMatch) {
      return {
        type: "wbe",
        id: params.wbsElementId!,
        ...(fallbackProjectId !== undefined
          ? { project_id: fallbackProjectId }
          : {}),
      };
    }

    if (nestedWpMatch || standaloneWpMatch) {
      return {
        type: "work_package",
        id: params.id!,
        ...(fallbackProjectId !== undefined
          ? { project_id: fallbackProjectId }
          : {}),
      };
    }

    if (costElementMatch) {
      return {
        type: "cost_element",
        id: params.id!,
        ...(fallbackProjectId !== undefined
          ? { project_id: fallbackProjectId }
          : {}),
      };
    }

    if (projectMatch) {
      return {
        type: "project",
        id: params.projectId!,
        project_id: params.projectId!,
      };
    }

    return { type: "general" };
  }, [
    onChat,
    projectMatch,
    wbsMatch,
    nestedWpMatch,
    standaloneWpMatch,
    costElementMatch,
    params.projectId,
    params.wbsElementId,
    params.id,
    tmProjectId,
    chatContext.context,
  ]);
}

// Re-export for callers/tests that need the pure parser.
export { parseChatContext };
