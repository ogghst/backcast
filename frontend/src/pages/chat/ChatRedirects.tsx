/**
 * Old-URL Chat Redirects (bookmark back-compat)
 *
 * The unified chat experience lives at `/chat?ctx=…`. These components keep
 * the previously-bookmarked entity-scoped chat URLs resolving to the new
 * route. Each reads its route params and issues a `replace` redirect.
 *
 * Routes registered in `routes/index.tsx` (top-level, before the AppLayout
 * catch-all):
 *   /projects/:projectId/chat
 *     → /chat?ctx=project:${projectId}&p=${projectId}
 *   /projects/:projectId/wbs-elements/:wbsElementId/chat
 *     → /chat?ctx=wbe:${wbsElementId}&p=${projectId}
 *   /projects/:projectId/work-packages/:id/chat
 *     → /chat?ctx=work_package:${id}&p=${projectId}
 *   /work-packages/:id/chat
 *     → /chat?ctx=work_package:${id}
 *   /cost-elements/:id/chat
 *     → /chat?ctx=cost_element:${id}
 *
 * Note: there is no `returnTo` from a bookmark — the Back button falls back to
 * `navigate(-1)`, which lands on the browser's prior entry (or `/` if none).
 */

// This module co-locates a small pure helper (`buildChatRedirectTarget`) with
// the redirect components that consume it; the react-refresh rule doesn't
// apply to these router plumbing modules.
/* eslint-disable react-refresh/only-export-components */

import type { FC } from "react";
import { useParams, Navigate } from "react-router-dom";

/**
 * Builds the redirect target for a `ctx`/`projectRootId` pair. Pure helper
 * exported for testability without a router context.
 */
export function buildChatRedirectTarget(
  ctx: string,
  projectRootId?: string,
): string {
  const params = new URLSearchParams({ ctx });
  if (projectRootId) {
    params.set("p", projectRootId);
  }
  return `/chat?${params.toString()}`;
}

export const ProjectChatRedirect: FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const target = buildChatRedirectTarget(
    `project:${projectId}`,
    projectId,
  );
  return <Navigate to={target} replace />;
};

export const WBSElementChatRedirect: FC = () => {
  const { projectId, wbsElementId } = useParams<{
    projectId: string;
    wbsElementId: string;
  }>();
  const target = buildChatRedirectTarget(`wbe:${wbsElementId}`, projectId);
  return <Navigate to={target} replace />;
};

export const WorkPackageChatRedirect: FC = () => {
  const { projectId, id } = useParams<{ projectId: string; id: string }>();
  const target = buildChatRedirectTarget(`work_package:${id}`, projectId);
  return <Navigate to={target} replace />;
};

export const StandaloneWorkPackageChatRedirect: FC = () => {
  const { id } = useParams<{ id: string }>();
  // No project in this route shape — omit the `p` rider.
  const target = buildChatRedirectTarget(`work_package:${id}`);
  return <Navigate to={target} replace />;
};

export const CostElementChatRedirect: FC = () => {
  const { id } = useParams<{ id: string }>();
  // No project in this route shape — omit the `p` rider.
  const target = buildChatRedirectTarget(`cost_element:${id}`);
  return <Navigate to={target} replace />;
};
