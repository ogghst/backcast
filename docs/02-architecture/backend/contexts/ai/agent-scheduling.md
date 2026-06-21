# Agent Scheduling System

**Status:** IMPLEMENTED. Users define cron-scheduled agent runs; an **in-process
scheduler task** (a lifespan background task in the API server) fires them.

> **History:** this shipped as a *separate* scheduler process (a docker service
> that fired runs by HTTP-POSTing a trigger endpoint as the owner). A single-node
> architecture review concluded that was over-engineered — separation isolated
> only the ~180-line scheduling tick (not execution, which always ran in the
> backend anyway), while paying concrete footguns (a `SCHEDULER_API_BASE_URL`
> silent-no-fire, an ORM model-registration crash, a second DB pool, JWT-as-owner
> impersonation, duplicated env). It was **relocated in-process**: same tick logic,
> but it calls the shared launcher directly. See `memory/33-agent-scheduling-system.md`.

**Owner subsystem:** AI execution (`backend/app/ai/`), scheduling
(`backend/app/scheduler/`), the shared launcher
(`backend/app/services/agent_schedule_service.py::trigger_schedule_run`), API
(`backend/app/api/routes/agent_schedules.py`), frontend admin
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

## The load-bearing constraint (why runs execute in the backend process)

`ExecutionLifecycle`, `AgentRunnerManager`, and every `AgentEventBus`
(`backend/app/ai/execution/`) are **module-level, in-memory, single-process singletons**.
An agent run **must execute in the API server process** to have a live event bus. If it ran
elsewhere:

- WebSocket clients couldn't watch the run stream live,
- the **Stop button** couldn't reach it (it sets an in-memory `asyncio.Event`),
- the Agents History "running" badge would desync, and
- completion notifications (`_notify_agent_owner`) would fire where the in-app WS
  connection registry (`user_connection_manager`) is empty, so the bell wouldn't push live.

**Resolution — the scheduler runs *in* the API server process.** It is an asyncio
background task started in the FastAPI lifespan (alongside the Telegram poller and the
orphan-execution reaper). It polls the shared DB every `SCHEDULER_POLL_INTERVAL_SECONDS`,
and when a schedule is due it calls `trigger_schedule_run(schedule_id)` **directly** (a
typed, in-process call — no HTTP, no JWT). `trigger_schedule_run` creates a fresh session
+ a RUNNING execution row and launches `start_execution(...)` as a fire-and-forget
`asyncio.create_task` *in this same process*, so the WS bus, Stop button, Agents History
badge, and live notification delivery all work.

This is the simplest configuration that satisfies the constraint: one process owns both
scheduling and execution, so there is no cross-process URL, no second connection pool, and
no impersonation token to misconfigure.

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

### Shared launcher — `trigger_schedule_run` (`agent_schedule_service.py`)
The single overlap-guarded launch path, called by **both** the in-process scheduler tick and
the HTTP `/trigger` handler (the "Run now" button). Raises `ScheduleOverlapError` /
`ScheduleNotFoundError` (the HTTP handler maps them to 409/404; the tick treats them as
"handled"). Flow:

1. Transaction-scoped advisory lock: `SELECT pg_advisory_xact_lock(hashtext('aas:'||id))`.
2. **Overlap check**: any `AIAgentExecution` with this `schedule_id` in
   `pending`/`running`/`awaiting_approval`? → rollback + raise `ScheduleOverlapError`.
3. Load the schedule (template fields) inside the locked txn; raise
   `ScheduleNotFoundError` if gone.
4. Create a **fresh** `AIConversationSession` from the schedule template.
5. **Create the `RUNNING` `AIAgentExecution` row** (pre-generated id, `schedule_id`,
   `run_in_background=True`) **inside the locked transaction**, then commit. Because the row
   is committed before the lock releases, a concurrent caller's overlap check sees it →
   `ScheduleOverlapError` (the guard is airtight; there is no gap).
6. Fire-and-forget `asyncio.create_task(_run_schedule_execution(...))` calling
   `start_execution(..., execution_id=<pre-gen>, schedule_id=<id>, run_in_background=True)`.
   `_preflight_execution` detects the pre-created row and skips re-insertion. The task is
   held in a module-level set (`_background_tasks`) so asyncio doesn't GC it mid-run after
   the launcher returns.

The run inherits `_notify_agent_owner` → the owner gets completion/failure in the bell +
Telegram (delivered from the backend process, so the WS push works).

### HTTP handler — `POST /api/v1/ai/agent-schedules/{id}/trigger`
Authorized for the schedule **owner or an admin** (no `RoleChecker` — triggering an existing
schedule is authorized by its existence, created under `agent-schedule-manage`; this also
means a later permission revocation does not silently halt already-scheduled runs). It does
the owner-or-admin check, then delegates to `trigger_schedule_run` and maps
`ScheduleOverlapError`→409 / `ScheduleNotFoundError`→404.

### Scheduler — in-process lifespan task (`backend/app/scheduler/`)
Hand-rolled asyncio loop (no APScheduler/Celery/Redis — single-server, code/DB-sharing),
started/stopped by the FastAPI lifespan in `backend/app/main.py` (`_scheduler_task` +
`_scheduler_stop`, mirroring the Telegram poller). It uses the API server's **shared** DB
engine (no separate pool) and no HTTP client.
- **`run_scheduler_loop(stop)`** (`main.py`): `while not stop: await tick(...); await
  wait_for(stop.wait(), timeout=POLL)`. Each tick is wrapped in `try/except` so a failure
  (e.g. a transient DB outage) never aborts the loop — it logs `[scheduler] tick failed` and
  retries next interval.
- **`tick()` (dispatch-then-advance)** (`tick.py`): claim active due rows
  `FOR UPDATE SKIP LOCKED`; deactivate any whose cron is now invalid; **advance STALE rows**
  (older than the grace window) without firing; commit; **dispatch FRESH rows** concurrently
  (bounded by `Semaphore(SCHEDULER_MAX_CONCURRENCY)`, refs held by `asyncio.gather`) by
  calling `trigger_schedule_run`; then **advance `next_run_at` only for rows whose dispatch
  was handled**. A failed dispatch (any unexpected error) leaves `next_run_at` in the past →
  the next tick retries it (until it ages past grace and is then skipped).

### Frontend
Admin page `AgentScheduleManagement` (templated on `MCPServerManagement`) with a cron editor
(`react-js-cron`'s `<Cron>`) + live human-readable preview (`cronstrue`), assistant +
execution-mode selectors, active `Switch`, Run-now, and per-row edit/delete. Route
`/admin/agent-schedules`, nav entry in `UserProfile` (permission-gated). Agents History shows
a `scheduled` tag for executions with a non-null `schedule_id`.

---

## Overlap prevention ("no two runs of the same schedule at once")

Airtight, no Redis, single process:
1. **Single backend process** — the scheduler is an in-process task, so there is exactly one
   scheduler by construction (no multi-instance risk; no single-instance lock needed).
2. **`FOR UPDATE SKIP LOCKED`** claim in the tick.
3. **`trigger_schedule_run` advisory lock + active-status check → `ScheduleOverlapError`** —
   the authoritative guard, shared by the scheduler and Run-now. Crucially, the `RUNNING`
   `AIAgentExecution` row is created **inside the locked transaction** (before commit), so
   when the lock releases the row is already visible and a concurrent caller's overlap check
   sees it. `_preflight_execution` detects the pre-created row and skips re-insertion (so the
   WS/REST invoke paths, which pass a fresh id, are unaffected).

> Caveat: there is a sub-second window between the locked transaction committing and
> `_preflight_execution` inserting the row if a caller bypasses `trigger_schedule_run`. Both
> real callers go through it, so this is not reachable in practice.

---

## Misfire policy — skip missed, with transient-failure retry

A fire is honored only if `next_run_at` is within `SCHEDULER_MISFIRE_GRACE_SECONDS` (default
120 s ≈ 2× poll) of `now`. STALE-due rows (the server was down longer than the grace window)
are advanced to the next future cron fire **without firing** — the missed window is dropped.
A FRESH dispatch that **fails** (any unexpected error from `trigger_schedule_run`) is
**retried**: its `next_run_at` is left in the past so the next tick re-fires it, until it ages
past the grace window (then treated as stale). A dispatch that raises `ScheduleOverlapError`
(a run is already active) or `ScheduleNotFoundError` (schedule deleted) is considered handled
and advances normally.

---

## Configuration (`backend/app/core/config.py` → env)

| setting | default | purpose |
|---|---|---|
| `SCHEDULER_POLL_INTERVAL_SECONDS` | `60` | tick loop cadence |
| `SCHEDULER_MAX_CONCURRENCY` | `5` | concurrent `trigger_schedule_run` calls per tick |
| `SCHEDULER_MISFIRE_GRACE_SECONDS` | `120` | skip-missed grace window |

The scheduler shares the backend's `Settings` / DB engine / `SECRET_KEY`, so there is no
separate env block and no scheduler-specific URL or pool. RBAC: permission
`agent-schedule-manage` is granted to `admin`, `ai-manager`, `manager`
(`backend/app/db/seed_users_rbac.py`; the seeder is idempotent/additive).

---

## Runbook

- **Dev:** the scheduler starts automatically with the backend — `dev-start.sh` (or
  `uv run uvicorn app.main:app --reload`) launches it in the lifespan. Look for
  `[STARTUP] agent_scheduler OK` + `[scheduler] started` in `backend/logs/app.log`. It stops
  with the backend (Ctrl+C); under `--reload`, a file save restarts it.
- **Prod:** there is **no separate scheduler service** — it runs inside the `backend`
  container's lifespan. Nothing extra to deploy/monitor beyond the backend.
- **A schedule that won't fire?** Check: `is_active`? `next_run_at` populated and ≤ now?
  owner still has `agent-schedule-manage`? Is the backend up (the scheduler lives in it) and
  is Postgres reachable? Grep `app.log` for `[scheduler] tick failed`.
- **A schedule stuck "running"?** A previous run is active → `trigger_schedule_run` raises
  `ScheduleOverlapError` until it finishes (or is stopped from Agents History). The startup
  reaper in `main.py` flips orphaned active rows to `ERROR` on a backend restart.
- **DB outage:** the scheduler tick fails gracefully (`[scheduler] tick failed`, caught +
  retried each interval) and resumes automatically once Postgres is back — no manual action.
  DB-dependent *request* endpoints will 500 during the outage (and trip the exception →
  notification alert).
- **HITL (`ask_user`) on scheduled runs** will hang up to `AI_ASK_USER_TIMEOUT_SECONDS` with
  no human to answer — prefer `safe`/`standard` assistants and prompts that don't require
  human input for scheduled runs.
