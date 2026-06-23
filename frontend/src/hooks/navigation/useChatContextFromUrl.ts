/**
 * URL-based AI Chat Context Parser
 *
 * Parses the AI chat context from URL **search params** (the `ctx` query param,
 * plus `p`/`session`/`exec` riders). This is the successor to `useAIChatContext`
 * (route-param based) for the unified `/chat?ctx=…` route.
 *
 * URL contract:
 *   ?ctx=<type>[:<id>] &p=<projectRootId> &session=<sessionId> &exec=<executionId>
 *
 *   - general      → ctx=general (or omitted)
 *   - project      → ctx=project:<projectId> (p optional; falls back to id)
 *   - wbe          → ctx=wbe:<wbsElementId>          (p required)
 *   - cost_element → ctx=cost_element:<id>           (p required)
 *   - work_package → ctx=work_package:<id>           (p required)
 *
 * `name` is intentionally left undefined — a later phase resolves the friendly
 * name lazily so URLs/bookmarks stay clean.
 */

import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import type { SessionContext } from "@/features/ai/types";

const KNOWN_CONTEXT_TYPES = new Set<SessionContext["type"]>([
  "general",
  "project",
  "wbe",
  "cost_element",
  "work_package",
]);

/**
 * Pure parser for the `ctx`/`p` query-param pair. Exported separately so it is
 * unit-testable without a router.
 *
 * @param ctx - raw value of the `ctx` param (may be null/empty)
 * @param p   - raw value of the `p` (project root id) param (may be null)
 */
export function parseChatContext(
  ctx: string | null,
  p: string | null,
): SessionContext {
  // Missing/empty ctx → general
  if (!ctx) {
    return { type: "general" };
  }

  // Split on the FIRST `:` — left = type, right = id
  const colonIndex = ctx.indexOf(":");
  if (colonIndex === -1) {
    // No colon: must be a bare known type (e.g. "general")
    const type = ctx as SessionContext["type"];
    if (KNOWN_CONTEXT_TYPES.has(type)) {
      return { type };
    }
    return { type: "general" };
  }

  const left = ctx.slice(0, colonIndex);
  const right = ctx.slice(colonIndex + 1);

  const type = left as SessionContext["type"];
  if (!KNOWN_CONTEXT_TYPES.has(type)) {
    return { type: "general" };
  }

  // project_id: `p` param if present; for `project` ONLY, fall back to the id
  // portion (project root_id can differ from the id passed — matches the old
  // ProjectChat.tsx which passed projectId={project?.project_id}).
  let project_id: string | undefined;
  if (p) {
    project_id = p;
  } else if (type === "project" && right) {
    project_id = right;
  }

  return {
    type,
    id: right || undefined,
    ...(project_id !== undefined ? { project_id } : {}),
  };
}

/**
 * Serialize a `SessionContext` into the `?ctx=` URL fragment.
 *
 * Mirrors the inverse of `parseChatContext`:
 *   - `general`         → `"general"`
 *   - any typed context → `"${type}:${id ?? ""}"`
 * and appends `&p=${project_id}` whenever the context is NOT a bare project
 * (project self-references its own id, so `p` is redundant there) but a
 * `project_id` is present. Returns the full `ctx=…&p=…` query string fragment
 * WITHOUT the leading `?`.
 *
 * Lives here (the URL-contract module) because it is the pure inverse of
 * `parseChatContext` above. Pure/type-only deps so importing it adds no
 * runtime/bundle cost.
 */
export function serializeCtx(ctx: SessionContext): string {
  let qs: string;
  if (ctx.type === "general") {
    qs = "ctx=general";
  } else {
    qs = `ctx=${ctx.type}:${ctx.id ?? ""}`;
  }

  if (ctx.type !== "project" && ctx.project_id) {
    qs += `&p=${ctx.project_id}`;
  }

  return qs;
}

interface UseChatContextFromUrlResult {
  context: SessionContext;
  sessionId?: string;
  executionId?: string;
}

/**
 * Hook that reads chat context + session/execution riders from URL search
 * params. Wrap usage in a router context (the `/chat` route already is).
 */
export function useChatContextFromUrl(): UseChatContextFromUrlResult {
  const [searchParams] = useSearchParams();
  const ctx = searchParams.get("ctx");
  const p = searchParams.get("p");
  const session = searchParams.get("session");
  const exec = searchParams.get("exec");

  return useMemo(
    () => ({
      context: parseChatContext(ctx, p),
      ...(session ? { sessionId: session } : {}),
      ...(exec ? { executionId: exec } : {}),
    }),
    [ctx, p, session, exec],
  );
}
