# Agent Scheduling System

**Status:** IMPLEMENTED. Users define cron-scheduled agent runs; a separate always-on
scheduler process fires them by calling the backend API.

**Owner subsystem:** AI execution (`backend/app/ai/`), scheduling (`backend/app/scheduler/`),
API (`backend/app/api/routes/agent_schedules.py`), frontend admin
(`frontend/src/pages/admin/AgentScheduleManagement.tsx`).

---

## Why

Agent runs were only launchable manually from chat. Use cases that need an always-on,
unattended trigger were unsupported: daily project-status checks, report writing, data
syncing with external systems, usage monitoring, user notifications, and cleanup. This adds
a scheduling layer so a user can say *"run assistant X with this prompt every day at 08:00"*
and have it fire even with no browser open, while **never starting a second run for a
schedule that is already in flight**.

---

## The load-bearing constraint (why the scheduler is an API client, not an executor)

`ExecutionLifecycle`, `AgentRunnerManager`, and every `AgentEventBus`
(`backend/app/ai/execution/`) are **module-level, in-memory, single-process singletons**.
A separate OS process that called `AgentService.start_execution(...)` directly would create
the event bus in *its own* process — invisible to the API server — so:

- WebSocket clients couldn't watch the run stream live,
- the **Stop button** couldn't reach it (it sets an in-memory `asyncio.Event`),
- the Agents History "running" badge would desync, and
- completion notifications (`_notify_agent_owner`) would fire in the scheduler process,
  where the in-app WS connection registry (`user_connection_manager`) is empty, so the
  notification bell wouldn't push live.

**Resolution — "scheduler as API client":**

- The **scheduler process** owns *scheduling only*: a 60 s loop that reads due schedules from
  the shared DB, advances `next_run_at`, and **launches each run by calling the backend
  trigger endpoint over HTTP**, authenticated **as the schedule's owner** (it mints a
  short-lived JWT with the shared `SECRET_KEY`).
- The **backend (API server)** owns *execution*: the trigger endpoint creates a fresh
  conversation session and runs `start_execution(...)` as a fire-and-forget
  `asyncio.create_task` in its own process. Because the run lives in the backend, the WS
  bus, Stop button, Agents History badge, **and** live notification delivery all keep working.

This is exactly the requested model — the UI and the background service communicate via the
API and share the database — without breaking the in-memory execution model.

---

## Data model

`ai_agent_schedules` (model `AIAgentSchedule`, `SimpleEntityBase`):
`name`, `prompt`, `assistant_config_id` (FK `ai_assistant_configs`, `RESTRICT`),
`execution_mode` (`safe`/`standard`/`expert`, default `standard`), `cron_expr` (5-field unix
cron, validated by `croniter`), `timezone` (IANA, default `UTC`), `is_active` (partial index
where true), `project_id?`, `branch_id?`, `context?` (JSONB), `owner_user_id` (the real user
— RBAC subject + run owner + notification target), `last_run_at`, `last_execution_id`,
`next_run_at` (cached next fire; the tick's primary query key).

`AIAgentExecution` gained a nullable `schedule_id` (indexed, no FK) so each execution points
back to its schedule — used by the overlap check and the Agents History "scheduled" indicator.

Migration: `e00199978962_add_ai_agent_schedules` (`down_revision d7154545c5e3`).

---

## Components

### Trigger endpoint — `POST /api/v1/ai/agent-schedules/{id}/trigger`
Authorized for the schedule **owner or an admin** (no `RoleChecker` — triggering an existing
schedule is authorized by its existence, created under `agent-schedule-manage`; this also
means a later permission revocation does not silently halt already-scheduled runs). Used by
**both** the scheduler and the UI "Run now" button — the single launch path. Flow:

1. Transaction-scoped advisory lock: `SELECT pg_advisory_xact_lock(hashtext('aas:'||id))`.
2. **Overlap check**: any `AIAgentExecution` with this `schedule_id` in
   `pending`/`running`/`awaiting_approval`? → rollback + **409**.
3. Create a **fresh** `AIConversationSession` from the schedule template.
4. **Create the `RUNNING` `AIAgentExecution` row** (pre-generated id, `schedule_id`,
   `run_in_background=True`) **inside the locked transaction**, then commit. Because the row
   is committed before the lock releases, a concurrent trigger's overlap check sees it → 409
   (the guard is airtight; there is no gap).
5. Fire-and-forget `asyncio.create_task(_run_schedule_execution(...))` calling
   `start_execution(..., execution_id=<pre-gen>, schedule_id=<id>, run_in_background=True)`.
   `_preflight_execution` detects the pre-created row and skips re-insertion. The task is
   held in a module-level set (`_background_tasks`) so asyncio doesn't GC it mid-run after
   the handler returns.

The run inherits `_notify_agent_owner` → the owner gets completion/failure in the bell +
Telegram (delivered from the backend process, so the WS push works).

### Scheduler process — `backend/app/scheduler/` (`python -m app.scheduler`)
Hand-rolled asyncio loop (no APScheduler/Celery/Redis — single-server, code/DB-sharing):
- **Single-instance guard**: on startup it acquires a session-level
  `pg_try_advisory_lock(hashtext('backcast-scheduler'))` held for the process lifetime; if
  another scheduler already holds it, it logs and exits (prevents accidental multi-instance
  dispatch).
- Owns its **own small async engine** (`pool_size = SCHEDULER_DB_POOL_SIZE = 5`) — does not
  reuse the API server's pool, avoiding double 50-connection pools.
- One long-lived `httpx.AsyncClient`; SIGTERM/SIGINT → graceful stop → `engine.dispose()`.
- **`tick()` (dispatch-then-advance)**: claim active due rows
  `FOR UPDATE SKIP LOCKED`; deactivate any whose cron is now invalid; **advance STALE rows**
  (older than the grace window) without firing; commit; **dispatch FRESH rows** concurrently
  (bounded by `Semaphore(SCHEDULER_MAX_CONCURRENCY)`, refs held by `asyncio.gather`); then
  **advance `next_run_at` only for rows whose dispatch was handled**. A failed dispatch
  (backend unreachable / 5xx) leaves `next_run_at` in the past → the next tick retries it
  (until it ages past grace and is then skipped).
- **`api_client.trigger_schedule` → bool**: mints `create_access_token(owner_user_id, 5 min)`
  and POSTs the trigger endpoint. Returns `True` (handled → advance: 2xx, or 409/403/404) or
  `False` (retry: connect error / 5xx). Never raises.

### Frontend
Admin page `AgentScheduleManagement` (templated on `MCPServerManagement`) with a cron editor
(`react-js-cron`'s `<Cron>`) + live human-readable preview (`cronstrue`), assistant +
execution-mode selectors, active `Switch`, Run-now, and per-row edit/delete. Route
`/admin/agent-schedules`, nav entry in `UserProfile` (permission-gated). Agents History shows
a `scheduled` tag for executions with a non-null `schedule_id`.

---

## Overlap prevention ("no two runs of the same schedule at once")

Airtight, no Redis:
1. **Single scheduler process** (startup advisory lock enforces it).
2. **`FOR UPDATE SKIP LOCKED`** claim + **in-process in-flight set**.
3. **Trigger endpoint advisory lock + active-status check → 409** — the authoritative guard,
   shared by scheduler and Run-now. Crucially, the `RUNNING` `AIAgentExecution` row is created
   **inside the locked transaction** (before commit), so when the lock releases the row is
   already visible and a concurrent trigger's overlap check sees it → 409.
   `_preflight_execution` detects the pre-created row and skips re-insertion (so the WS/REST
   invoke paths, which pass a fresh id, are unaffected).

---

## Misfire policy — skip missed, with transient-failure retry

A fire is honored only if `next_run_at` is within `SCHEDULER_MISFIRE_GRACE_SECONDS` (default
120 s ≈ 2× poll) of `now`. STALE-due rows (scheduler was down longer than the grace window)
are advanced to the next future cron fire **without firing** — the missed window is dropped.
A FRESH dispatch that **fails transiently** (backend unreachable / 5xx) is **retried**: its
`next_run_at` is left in the past so the next tick re-fires it, until it ages past the grace
window (then treated as stale). A dispatch that returns 409/403/404 is considered handled and
advances normally.

---

## Configuration (`backend/app/core/config.py` → env)

| setting | default | purpose |
|---|---|---|
| `SCHEDULER_POLL_INTERVAL_SECONDS` | `60` | tick loop cadence |
| `SCHEDULER_MAX_CONCURRENCY` | `5` | concurrent trigger POSTs per tick |
| `SCHEDULER_MISFIRE_GRACE_SECONDS` | `120` | skip-missed grace window |
| `SCHEDULER_API_BASE_URL` | `http://backend:8020` (dev) / `http://backend:8080` (prod) | backend trigger endpoint |
| `SCHEDULER_DB_POOL_SIZE` | `5` | scheduler's own engine pool |

RBAC: permission `agent-schedule-manage` is granted to `admin`, `ai-manager`, `manager`
(`backend/app/db/seed_users_rbac.py`; the seeder is idempotent/additive).

---

## Runbook

- **Dev:** `docker compose -f docker-compose.dev.yml --env-file .env.dev up scheduler` —
  logs `[scheduler] tick`, fires due schedules, advances `next_run_at`, stops cleanly on
  SIGTERM.
- **Prod:** the `scheduler` service is part of `deploy/docker-compose.yml` (reuses
  `backcast_evs_backend:latest`, `RUN_MIGRATIONS=false`, depends on a healthy backend, no
  Traefik labels). `deploy/scripts/redeploy.sh` builds it.
- **A schedule that won't fire?** Check: `is_active`? `next_run_at` populated and ≤ now?
  owner still has `agent-schedule-manage` (else trigger 403)? backend reachable at
  `SCHEDULER_API_BASE_URL`?
- **A schedule stuck "running"?** A previous run is active → triggers return 409 until it
  finishes (or is stopped from Agents History). The startup reaper in `main.py` flips
  orphaned active rows to `ERROR` on a backend restart.
- **HITL (`ask_user`) on scheduled runs** will hang up to `AI_ASK_USER_TIMEOUT_SECONDS` with
  no human to answer — prefer `safe`/`standard` assistants and prompts that don't require
  human input for scheduled runs.
