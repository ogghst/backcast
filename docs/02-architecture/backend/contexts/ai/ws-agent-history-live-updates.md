# WS Live Updates for Agents History (future iteration — design note)

**Status:** NOT YET IMPLEMENTED. Background agent execution + Agents History shipped (v1) with **REST polling** (`useAgentExecutions` refetches every 5 s; `useRunningExecutionsCount` polls every 5 s for the menu badge). This document captures the analysis and a concrete implementation plan for upgrading to **WebSocket push**, so the work is ready to pick up when that iteration starts (most likely alongside **scheduled agents**).

**Owner subsystem:** AI execution / chat transport (`backend/app/ai/execution/`, `backend/app/api/routes/ai_chat.py`, `frontend/src/features/ai/chat/`).

---

## Why polling was chosen for v1 (and when WS wins)

A history **table** is not latency-sensitive: a status badge flipping within ≤5 s is fine UX, and REST maps cleanly onto the paginated/filtered list (`?status=&limit=&offset=`). Polling is stateless, robust to reconnects/proxies, and was already built.

**WS earns its place when any of these become true:**
1. **Scheduled agents land.** A scheduler starts background runs with no chat tab attached → the Agents History page becomes the *primary* live window into them; push is much more valuable.
2. **Sub-second status flips** are desired (instant running→completed/stopped/error the moment it happens).
3. **Many concurrent viewers** — polling cost scales with open tabs (≈1 list + 1 count query per 5 s per tab); a single per-user fan-out scales better.

The architecture is **already observer-based**, so this is an incremental addition, not a rewrite.

---

## What already exists and is reusable

The prior "decouple execution from WS" work made the lifecycle observer-based and the WS a thin transport — the foundations for live history are in place:

- **`ExecutionLifecycle`** (`backend/app/ai/execution/lifecycle.py`): protocol-agnostic, observer-token `attach`/`detach`, `register`, `request_stop`, `terminate`. A "history observer" is just another observer type (like the chat WS observer today, and the future scheduler observer).
- **Per-execution `AgentEventBus`** (`runner_manager.create_bus/get_bus/remove_bus`): already emits `execution_status`, `complete`, `error`, `agent_complete`, `plan_update`, etc. (`app/ai/event_types.py`). Status changes already flow through the bus.
- **Existing WS transport** (`backend/app/api/routes/ai_chat.py`): authenticates via `?token=<jwt>` query param before `websocket.accept()`, checks `ai-chat` RBAC, and has a per-connection message loop that already supports `{type:"subscribe", execution_id, last_seen_sequence}` with **replay** (`bus.replay(since_sequence)` + `replay_start`/`replay_end` markers). `forward_bus_events` already forwards bus events to a socket and exits on `COMPLETE`/`ERROR`.
- **Status-write sites are centralized** in `agent_service`: `_preflight_execution` (→`running`, sets `session.active_execution_id`), `_postflight_execution` (→`completed`/`error`/`stopped`), `_finalize_stopped_execution` (→`stopped`), `_clear_active_execution`. These are the natural fan-out triggers.
- **REST list/count endpoints** (`GET /api/v1/ai/chat/executions`, `…/running-count`) and the `AIConfigService.list_executions_paginated` / `count_running_executions` service methods — **keep these** for bulk/paginated load.
- **Frontend hooks**: `useAgentExecutions` (list), `useRunningExecutionsCount` (badge), `queryKeys.ai.chat.executions.*`, and `useStreamingChat` (the existing chat WS client — owns `wsRef`, reconnect+subscribe logic, sequence persistence). `AgentsHistory.tsx` is an antd Table fed by TanStack Query.

## The gap

The WS subscribe is **per-execution** (`{execution_id}`). There is **no "subscribe to all of my executions"** fan-out. For a history page covering many executions, you need a user-scoped live channel — that is the one substantive new piece.

---

## Target design — hybrid: REST for bulk, WS for deltas

Keep REST for the **paginated/filtered list** (initial load + page/filter changes — REST is correct for bulk fetch). Add WS **only for status deltas**, patching rows in place. This avoids reconciling pagination over WS: you only ever update rows already in view.

### Backend — a user-scoped executions stream
Two viable shapes (pick one at implementation time):

- **Option A (extend the existing socket):** add a new inbound message `{type:"subscribe_executions"}` to the chat `/stream` endpoint (`ai_chat.py` message_handler, next to the existing `subscribe` branch ~line 812). It registers the socket as a **user-executions observer**. On any status change for any of the user's executions, push a minimal delta event.
- **Option B (dedicated endpoint):** `WS /api/v1/ai/chat/executions/stream?token=<jwt>` — a thinner socket purpose-built for history live updates, reusing the same auth/RBAC preamble as `/stream`. Cleaner separation; small duplication of the accept/auth block.

**Fan-out mechanism (the core addition):** a tiny in-process pub/sub keyed by `user_id`. Concretely, a module-level `UserExecutionBroadcaster` (lives next to `execution_lifecycle`, same single-server/in-memory model) with:
- `subscribe(user_id) -> AsyncIterator[Event]` (or a callback registration),
- `publish(user_id, event)`.

**Where to call `publish` (the status-write sites above):** at the end of `_postflight_execution` / `_finalize_stopped_execution` / `_preflight_execution` in `agent_service.py`, emit a delta `{execution_id, status, completed_at, run_in_background, session_id, name}` for the owning user. These sites already have the row + the session (hence `user_id`). This is a handful of one-line `broadcaster.publish(...)` calls — no new status logic.

> Resolve `user_id` from the execution's session (`execution.session.user_id`) — already loaded at these sites. RBAC is inherently satisfied (the user only receives their own executions).

**Event shape** (minimal; the list endpoint already returns the full row, so deltas carry only what changes):
```jsonc
{ "type": "execution_delta", "execution_id": "...", "status": "completed",
  "completed_at": "…", "run_in_background": true, "session_id": "…" }
```
Optionally a `{ "type": "execution_created", ... }` when a new execution starts, so a freshly-started background run can be prepended without waiting for the next poll.

### Frontend — delta applier (drops the 5 s poll)
- New hook `useExecutionDeltas()` that opens the executions WS (reuse the connect/reconnect/sequence patterns from `useStreamingChat`, or share a thin WS client). On mount it sends `{type:"subscribe_executions"}`.
- On `execution_delta`: patch the matching row **in place** via `queryClient.setQueryData(queryKeys.ai.chat.executions.list(status), …)` — but only if that row is present in the cached page (in-view). If the status change moves it out of the active filter (e.g. it became `completed` while the "Running" filter is on), remove it and bump `running-count`.
- On `execution_created`: `queryClient.invalidateQueries(executions.list)` (cheap; one paginated refetch) so the new row appears in the right order — avoids manual prepend/sort.
- `useRunningExecutionsCount`: derive from the same stream (increment/decrement on delta) instead of its own 5 s REST poll, so badge + list stay perfectly in sync.
- Remove `refetchInterval: 5000` from `useAgentExecutions` (the WS replaces it). Keep a slow **fallback** poll (e.g. 30 s) or a window-focus refetch as a safety net against missed events / reconnect gaps.

### Reconnection & missed events
Reuse the sequence model already proven on the chat socket: include a `sequence` on each delta and persist `last_seen_sequence` per user (sessionStorage, like chat does per execution). On reconnect, send `{type:"subscribe_executions", last_seen_sequence}` and have the broadcaster replay missed deltas from a short ring buffer (or just invalidate-on-reconnect — simpler, acceptable for a history view).

---

## Decisions / tradeoffs to make at implementation time

- **Option A vs B** (extend `/stream` vs dedicated `/executions/stream`). B is cleaner; A avoids a second auth block. Recommend **B** (purpose-built, testable in isolation).
- **Patch-in-place vs invalidate-on-delta.** Patch is instant and cheap; invalidate is simpler but refetches. Recommend **patch for status flips, invalidate for new executions**.
- **Fallback poll.** Keep a slow (30 s) or focus-triggered REST refetch to self-heal after a dropped socket — polling already exists, so this is nearly free.
- **Backpressure.** A user with many concurrent executions could see bursts; deltas are tiny and infrequent (status changes only, not tokens), so this is low-risk. The broadcaster should drop/ coalesce if a slow consumer backs up (bound the per-user queue).
- **Multi-tab.** Each tab opens its own socket (like chat). Fine; broadcaster fans out to all subscriber callbacks for the user.

---

## Concrete hook points (from the v1 implementation)

| Concern | Location |
|---|---|
| Observer/lifecycle model to extend | `backend/app/ai/execution/lifecycle.py` (`execution_lifecycle`, `_ExecutionContext`, `attach`/`detach`) |
| New `UserExecutionBroadcaster` | new module next to `lifecycle.py` (same in-memory, single-server pattern) |
| `publish(...)` call sites (status writes) | `backend/app/ai/agent_service.py`: `_preflight_execution` (~2437), `_postflight_execution` (~2531), `_finalize_stopped_execution` (~2476) |
| WS endpoint (Option B) + auth preamble | `backend/app/api/routes/ai_chat.py` (mirror the `/stream` accept/auth/RBAC at ~616–711) |
| Event types | `backend/app/ai/event_types.py` (`AgentEventType`) |
| Existing subscribe/replay to model after | `ai_chat.py` `subscribe` branch (~812) + `forward_bus_events` (~60) + `bus.replay` |
| Frontend delta hook + WS client | new `frontend/src/features/ai/chat/api/useExecutionDeltas.ts` (mirror `useStreamingChat` connect/subscribe/sequence) |
| In-place row patch | `queryClient.setQueryData` against `queryKeys.ai.chat.executions.list(status)` in `frontend/src/api/queryKeys.ts` |
| Page to wire | `frontend/src/pages/AgentsHistory.tsx` |
| Reuse REST for initial load/pagination | `useAgentExecutions` + `AIConfigService.list_executions_paginated` (unchanged) |

## Phasing (non-breaking)
1. **Backend:** add `UserExecutionBroadcaster` + `publish` calls + the `/executions/stream` endpoint (Option B). Ship behind the existing REST endpoints — no frontend change yet.
2. **Frontend:** add `useExecutionDeltas`, patch rows in place, derive the badge from the stream. Keep REST for initial load. Remove the 5 s `refetchInterval`, add the 30 s/focus fallback.
3. **Cleanup:** drop `useRunningExecutionsCount`'s REST poll once the stream drives the badge.

## Open questions
- Do we want `execution_created` push (prepend new runs) or rely on the fallback poll/invalidation to surface them? (Push is nicer for the scheduler case.)
- Should the broadcaster also carry **progress** deltas (plan step changes) for running rows, or only terminal/running flips? (Start with status-only; progress can come later and the chat already streams it.)
- Replay buffer size on reconnect (or accept invalidate-on-reconnect).

## When to start
Trigger this iteration when **scheduled agents** begin (the history page becomes the primary live surface for headless runs), or sooner if sub-second status visibility or high viewer concurrency becomes a requirement. Until then, the 5 s REST poll is sufficient and the code is simpler for it.
