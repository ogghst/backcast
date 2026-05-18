# Analysis: AI Chat Reliability Fixes (RBAC Cache, Tab Rendering, Temporal Propagation)

**Created:** 2026-05-14
**Request:** Fix four issues discovered during E2E test `20260514_0007-ai-cost-progress` that caused 0 of 2 planned actions to execute. The root causes span RBAC permissions cache expiry, project-scoped AI Chat tab rendering failure, temporal context not reaching global chat, and hardcoded EUR currency.

---

## Clarified Requirements

### Functional Requirements

1. **RBAC cache must never silently zero-out the AI toolset.** When the permissions cache expires (TTL = 1 hour), `_get_cached_permissions()` returns `None`, which `filter_tools_by_role()` converts to an empty permission set, silently removing all 78 permission-gated tools. The system must either refresh the cache on demand, fail loudly, or use a stale-while-revalidate strategy.

2. **Project-scoped AI Chat tab must render its content panel.** Clicking "AI Chat" in the project page tab navigation marks the tab as `[active]` but the content panel stays on Overview. Users must be able to access AI chat within a project context.

3. **Temporal line date must propagate to the AI agent when set.** When a user sets the Time Machine to a specific date (e.g., May 20, 2026) on the project page, the AI chat must receive that `as_of` value. Currently, navigating to the global `/chat` route loses the Time Machine project context.

4. **Currency display should respect the project's configured currency** (deferred -- see P3 below).

### Non-Functional Requirements

- Zero silent failures: any RBAC cache miss that degrades the AI toolset must be logged at ERROR level at minimum.
- Backward compatible: existing API contracts and WebSocket message formats must not change.
- No new database tables or migrations for items 1-3.
- Test coverage for the RBAC cache-refresh path.

### Constraints

- The RBAC cache is an in-memory dictionary on a singleton `UnifiedRBACService`. It is refreshed at startup and after RBAC admin write operations. There is no periodic refresh.
- The `filter_tools_by_role()` function is synchronous and called during WebSocket message handling. It cannot directly `await` an async cache refresh.
- The Time Machine store is Zustand-based with per-project settings keyed by `currentProjectId`. When `currentProjectId` is null (global routes), temporal settings are inaccessible.

---

## Context Discovery

### Product Scope

- The AI chat feature is a primary user interface for interacting with the EVCS system. Users delegate project management operations (create cost registrations, set progress, manage change orders) to AI agents.
- Silent tool filtering directly violates user trust: the AI agent reports "Done" with zero actions executed, giving no indication of failure.

### Architecture Context

- **Bounded contexts involved:** AI Agent (`app/ai/`), RBAC (`app/core/rbac_unified.py`), Frontend Chat (`src/features/ai/chat/`)
- **RBAC singleton pattern:** `UnifiedRBACService` is instantiated once via `get_unified_rbac_service()`. Its `_permissions_cache` dict is shared across all requests. Cache TTL is 1 hour (`_PERMISSIONS_CACHE_TTL = timedelta(hours=1)`).
- **Tool filtering pipeline:** `filter_tools_by_execution_mode()` -> `filter_tools_by_role()` -> `compile_subagents()`. The RBAC filter runs twice: once for the assistant's default role, once for the user's actual role.
- **PageNavigation component:** Uses Ant Design `Tabs` with route-based navigation. The `activeKey` is derived from `location.pathname === item.path` (exact match). The project page uses `<Outlet />` for child routes, which means the tab bar and the content area are separate React subtrees -- the `Tabs` component does not render tab panels; it only highlights the active tab and calls `navigate()`.

### Codebase Analysis

**Backend:**

- `backend/app/core/rbac_unified.py:130-141` -- `_get_cached_permissions()` returns `None` on cache miss or TTL expiry. No fallback, no error signal.
- `backend/app/ai/tools/__init__.py:91-92` -- `perms = unified_service._get_cached_permissions(role)` then `role_permissions = set(perms) if perms else set()`. The `else set()` is the silent degradation point.
- `backend/app/ai/subagent_compiler.py:152` -- `subagent_tools = [t for t in available_tools if t.name in filtered_tool_names]`. When `available_tools` has only 2 items, every specialist gets 0-1 tools.
- `backend/app/main.py:108` -- Cache is refreshed once at startup. No periodic refresh or on-demand refresh mechanism.
- `backend/app/services/rbac_admin_service.py:182` -- Cache is refreshed after admin write operations. But between writes, the cache expires silently.

**Frontend:**

- `frontend/src/components/navigation/PageNavigation.tsx` -- The `Tabs` component does NOT render tab panels. It is purely a navigation bar. The `<Outlet />` in `ProjectLayout` renders child routes. This is correct behavior -- the tab bar is navigation-only. The E2E test report that "tabpanel stays on Overview" means the route navigation is not triggering when clicking "AI Chat" tab.
- `frontend/src/pages/projects/ProjectChat.tsx` -- Sets Time Machine `currentProjectId` on mount. Passes `contextOverride` to `ChatInterface`. This component is correctly wired for the project-scoped route `/projects/:projectId/chat`.
- `frontend/src/routes/index.tsx:167-169` -- The `chat` child route maps to `<ProjectChat />`. Route is correctly registered.
- `frontend/src/stores/useTimeMachineStore.ts:112-114` -- `getSelectedTime()` returns `null` when `currentProjectId` is null (global routes). This is by design -- the Time Machine is project-scoped.
- `frontend/src/features/ai/chat/api/useStreamingChat.ts:816-844` -- The streaming hook reads `getSelectedTime()`, `getSelectedBranch()`, `getViewMode()` from the Time Machine store and passes them as `as_of`, `branch_name`, `branch_mode` in the WebSocket message. This plumbing is correct.

---

## Solution Options

### Option 1: Stale-While-Revalidate with Error Logging (Recommended)

**Architecture & Design:**

For the RBAC cache, implement a "stale-while-revalidate" pattern: when `_get_cached_permissions()` detects an expired entry, return the stale data immediately and trigger an async background refresh. Additionally, add an ERROR-level log when returning stale data and a WARNING when the cache is completely empty (no stale data available).

For the tab rendering bug, the root cause is likely in the E2E test's interaction with Ant Design Tabs rather than a code bug. The `PageNavigation` component uses `navigate()` on tab change, which should work. The E2E report says clicking "AI Chat" shows `[active]` but content doesn't change -- this suggests the click event is being intercepted or the navigation is not completing. Needs browser-level investigation.

For temporal propagation, the correct fix is to ensure users use the project-scoped chat route (which properly sets Time Machine context) rather than making the global chat route aware of project-specific temporal state. Fixing the tab rendering (BUG 1) makes the global chat workaround unnecessary for project-scoped AI operations.

**Implementation:**

Backend changes:
- Modify `_get_cached_permissions()` to return expired data with a flag, or refactor `filter_tools_by_role()` to handle the None case explicitly.
- Add a synchronous `_refresh_permissions_cache_sync()` method (or restructure to call async refresh from sync context via `asyncio.get_event_loop()`).
- Add ERROR-level logging when cache miss would result in 0 tools.
- Add unit test for the cache-expiry-then-filter scenario.

Frontend changes:
- Investigate the PageNavigation + project chat tab interaction in a real browser session.
- If the tab click is working correctly but the E2E test Playwright snapshot is misleading, update the E2E test approach.
- If there is a genuine rendering bug, fix the navigation or route matching.

**Trade-offs:**

| Aspect          | Assessment                                                              |
| --------------- | ----------------------------------------------------------------------- |
| Pros            | Minimal code change; preserves existing cache architecture; no new infrastructure; stale data is still correct (permissions change rarely) |
| Cons            | Stale permissions could theoretically allow a recently-revoked permission to persist for one more request; requires careful async handling |
| Complexity      | Low-Med (RBAC cache change is ~20 lines; tab investigation is exploratory) |
| Maintainability | Good (adds logging and graceful degradation to existing pattern)        |
| Performance     | No degradation; stale data returned synchronously, refresh is async     |

---

### Option 2: On-Demand Synchronous Cache Refresh

**Architecture & Design:**

Convert `filter_tools_by_role()` to an async function and call `await refresh_permissions_cache()` on cache miss before proceeding with the filter. This guarantees fresh data on every cache miss.

**Implementation:**

Backend changes:
- Make `filter_tools_by_role()` async.
- On cache miss, call `await unified_service.refresh_permissions_cache()` synchronously.
- Requires a database session to be available in the filter context.
- Update all callers of `filter_tools_by_role()` to await the result.

Frontend changes:
- Same as Option 1 for tab rendering and temporal propagation.

**Trade-offs:**

| Aspect          | Assessment                                                              |
| --------------- | ----------------------------------------------------------------------- |
| Pros            | Always fresh permissions; simple to reason about; no stale data risk    |
| Cons            | Adds a database query to every chat request after cache expiry; changes the sync-to-async contract of filter_tools_by_role, affecting all callers |
| Complexity      | Med (requires cascading async changes through the call chain)           |
| Maintainability | Fair (async propagation increases coupling to database layer)           |
| Performance     | One additional DB query per cache miss (rare after startup warm-up)     |

---

### Option 3: Fail-Fast with Cache Warmup on Startup + Periodic Refresh

**Architecture & Design:**

Keep the cache as-is but add two safety nets: (1) raise a clear exception when `_get_cached_permissions()` returns None during tool filtering, surfacing the error to the user instead of silently degrading; (2) add a background task that refreshes the permissions cache every 30 minutes, keeping the TTL buffer.

**Implementation:**

Backend changes:
- In `filter_tools_by_role()`, when perms is None, raise `RuntimeError(f"RBAC permissions cache expired for role '{role}' -- cannot filter tools")`.
- Add a FastAPI `lifespan` background task that calls `refresh_permissions_cache()` every 30 minutes.
- The error propagates to the WebSocket handler, which sends an error message to the user ("AI chat temporarily unavailable -- please try again in a moment").
- After the error, the next request triggers the periodic refresh and succeeds.

Frontend changes:
- Same as Option 1 for tab rendering and temporal propagation.

**Trade-offs:**

| Aspect          | Assessment                                                              |
| --------------- | ----------------------------------------------------------------------- |
| Pros            | Simplest implementation; no async conversion; clear error visibility; periodic refresh prevents most cache misses |
| Cons            | User-visible errors between cache expiry and next periodic refresh; adds a long-running background task; does not handle the exact moment of cache expiry gracefully |
| Complexity      | Low (background task + exception handling)                              |
| Maintainability | Good (adds visibility without changing existing contracts)              |
| Performance     | Periodic DB query every 30 minutes (negligible)                         |

---

## Comparison Summary

| Criteria           | Option 1 (Stale-While-Revalidate) | Option 2 (On-Demand Sync Refresh) | Option 3 (Fail-Fast + Periodic) |
| ------------------ | ---------------------------------- | --------------------------------- | ------------------------------- |
| Development Effort | Low-Med (~4h)                      | Med (~6h)                         | Low (~2h)                       |
| UX Quality         | Excellent (no user-visible errors) | Excellent (no user-visible errors)| Fair (occasional error toast)   |
| Flexibility        | Good (handles cache miss gracefully)| Good (always fresh data)          | Fair (depends on periodic task) |
| Best For           | Production reliability             | Accuracy-critical use cases       | Quick fix with visibility       |

---

## Decision

**Selected: Option 2 — On-Demand Synchronous Cache Refresh**

Decisions made on 2026-05-14:

1. **RBAC cache refresh: Synchronous** — On cache miss, `filter_tools_by_role()` will trigger a synchronous refresh of the permissions cache before filtering. This guarantees fresh data and avoids serving stale permissions. The sync-to-async conversion of `filter_tools_by_role()` is the accepted trade-off.

2. **BUG 1 (P1): In scope** — Project-scoped AI Chat tab rendering will be investigated and fixed within this iteration.

3. **P2 (Temporal propagation to global chat): Deferred to TD-068** — The correct fix is making project-scoped chat work (P1). Global chat should remain project-agnostic. Deferred as tech debt with a note that P1 fix may eliminate this issue entirely.

4. **P3 (Configurable currency): Deferred to TD-069** — Known limitation, not a regression. Currency is hardcoded to EUR throughout the frontend. Low priority.

### Iteration Scope

| Item | Priority | Status | In Scope? |
|------|----------|--------|-----------|
| RBAC cache expiry → silent tool filtering | P0 CRITICAL | BUG | Yes |
| Project AI Chat tab doesn't render | P1 HIGH | BUG | Yes |
| Temporal date not propagated to global chat | P2 MEDIUM | CONFIG | No → TD-068 |
| Currency hardcoded to EUR | P3 LOW | CONFIG | No → TD-069 |

---

## References

- E2E Test Report: `e2e/20260514_0007-ai-cost-progress/report.md`
- RBAC cache: `backend/app/core/rbac_unified.py` (lines 54-141)
- Tool filtering: `backend/app/ai/tools/__init__.py` (lines 69-113)
- Subagent compilation: `backend/app/ai/subagent_compiler.py` (lines 100-183)
- PageNavigation: `frontend/src/components/navigation/PageNavigation.tsx`
- ProjectChat: `frontend/src/pages/projects/ProjectChat.tsx`
- TimeMachine store: `frontend/src/stores/useTimeMachineStore.ts`
- Streaming hook temporal params: `frontend/src/features/ai/chat/api/useStreamingChat.ts` (lines 816-844)
- WSChatRequest schema: `backend/app/models/schemas/ai.py` (lines 507-545)
- Route config: `frontend/src/routes/index.tsx` (lines 134-178)
- Startup cache refresh: `backend/app/main.py` (lines 101-109)
