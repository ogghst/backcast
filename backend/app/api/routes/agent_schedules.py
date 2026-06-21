"""API routes for agent run schedules.

CRUD is owner-scoped (a user manages their own schedules; cross-owner access
returns 404 to avoid leaking existence). The trigger endpoint launches a run
via ``asyncio.create_task`` in the backend process — it is the entry point the
separate scheduler process hits when a schedule becomes due. An overlap guard
serializes concurrent triggers per-schedule via a transaction-scoped advisory
lock and refuses (409) if a run for that schedule is already active.
"""

import asyncio
import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_service import AgentService
from app.ai.event_types import ExecutionStatus
from app.ai.tools.types import ExecutionMode
from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.core.rbac_unified import get_unified_rbac_service
from app.db.session import async_session_maker, get_db
from app.models.domain.ai import AIAgentExecution
from app.models.domain.ai_agent_schedule import AIAgentSchedule
from app.models.schemas.ai_agent_schedule import (
    AgentScheduleCreate,
    AgentScheduleRead,
    AgentScheduleTriggerResponse,
    AgentScheduleUpdate,
)
from app.services.agent_schedule_service import AgentScheduleService
from app.services.ai_config_service import AIConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/agent-schedules", tags=["Agent Schedules"])

# Strong references to fire-and-forget execution tasks. asyncio only keeps a
# weak reference to tasks, so a task created in a request handler and never
# awaited can be garbage-collected mid-run once the handler returns. We hold
# each task here and drop it when it completes. (The minutes-long agent run
# outlives the HTTP trigger request by design.)
_background_tasks: set[asyncio.Task[None]] = set()


# ---------------------------------------------------------------------------
# DI helpers (mirrored locally from ai_chat.py — do not import across routes)
# ---------------------------------------------------------------------------


def get_agent_schedule_service(
    session: AsyncSession = Depends(get_db),
) -> AgentScheduleService:
    """Build an AgentScheduleService bound to the request session."""
    return AgentScheduleService(session)


def get_ai_config_service(session: AsyncSession = Depends(get_db)) -> AIConfigService:
    """Build an AIConfigService bound to the request session."""
    return AIConfigService(session)


# ---------------------------------------------------------------------------
# Owner-scope helper
# ---------------------------------------------------------------------------


async def _load_owned_schedule(
    service: AgentScheduleService, schedule_id: UUID, current_user: UserIdentity
) -> AIAgentSchedule:
    """Load a schedule, 404-ing if missing OR not owned by the caller.

    Returns 404 (not 403) for foreign-owned schedules to avoid leaking
    existence across owners.
    """
    schedule = await service.get_schedule(schedule_id)
    if schedule is None or str(schedule.owner_user_id) != str(current_user.user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found")
    return schedule


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[AgentScheduleRead],
    operation_id="list_agent_schedules",
    dependencies=[Depends(RoleChecker(required_permission="agent-schedule-manage"))],
)
async def list_agent_schedules(
    is_active: bool | None = Query(None),
    assistant_config_id: UUID | None = Query(None),
    owner_user_id: UUID | None = Query(None),
    service: AgentScheduleService = Depends(get_agent_schedule_service),
    current_user: UserIdentity = Depends(get_current_user),
) -> list[AIAgentSchedule]:
    """List schedules. Owner-scoped: callers see their own schedules.

    An explicit ``owner_user_id`` query param lets an admin list another
    owner's schedules (RBAC still gates the call).
    """
    effective_owner = (
        owner_user_id if owner_user_id is not None else current_user.user_id
    )
    return await service.list_schedules(
        owner_user_id=effective_owner,
        is_active=is_active,
        assistant_config_id=assistant_config_id,
    )


@router.post(
    "",
    response_model=AgentScheduleRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_agent_schedule",
    dependencies=[Depends(RoleChecker(required_permission="agent-schedule-manage"))],
)
async def create_agent_schedule(
    body: AgentScheduleCreate,
    service: AgentScheduleService = Depends(get_agent_schedule_service),
    current_user: UserIdentity = Depends(get_current_user),
) -> AIAgentSchedule:
    """Create a schedule. Invalid cron/timezone → 422."""
    try:
        return await service.create_schedule(body, current_user.user_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e


@router.get(
    "/{schedule_id}",
    response_model=AgentScheduleRead,
    operation_id="get_agent_schedule",
    dependencies=[Depends(RoleChecker(required_permission="agent-schedule-manage"))],
)
async def get_agent_schedule(
    schedule_id: UUID,
    service: AgentScheduleService = Depends(get_agent_schedule_service),
    current_user: UserIdentity = Depends(get_current_user),
) -> AIAgentSchedule:
    """Get a single schedule (owner-scoped)."""
    return await _load_owned_schedule(service, schedule_id, current_user)


@router.put(
    "/{schedule_id}",
    response_model=AgentScheduleRead,
    operation_id="update_agent_schedule",
    dependencies=[Depends(RoleChecker(required_permission="agent-schedule-manage"))],
)
async def update_agent_schedule(
    schedule_id: UUID,
    body: AgentScheduleUpdate,
    service: AgentScheduleService = Depends(get_agent_schedule_service),
    current_user: UserIdentity = Depends(get_current_user),
) -> AIAgentSchedule:
    """Patch a schedule (owner-scoped). Invalid cron/timezone → 422."""
    await _load_owned_schedule(service, schedule_id, current_user)
    try:
        updated = await service.update_schedule(schedule_id, body)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e
    if updated is None:  # pragma: no cover — _load_owned_schedule already 404s
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found")
    return updated


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_agent_schedule",
    dependencies=[Depends(RoleChecker(required_permission="agent-schedule-manage"))],
)
async def delete_agent_schedule(
    schedule_id: UUID,
    service: AgentScheduleService = Depends(get_agent_schedule_service),
    current_user: UserIdentity = Depends(get_current_user),
) -> Response:
    """Delete a schedule (owner-scoped)."""
    await _load_owned_schedule(service, schedule_id, current_user)
    await service.delete_schedule(schedule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{schedule_id}/toggle",
    response_model=AgentScheduleRead,
    operation_id="toggle_agent_schedule",
    dependencies=[Depends(RoleChecker(required_permission="agent-schedule-manage"))],
)
async def toggle_agent_schedule(
    schedule_id: UUID,
    service: AgentScheduleService = Depends(get_agent_schedule_service),
    current_user: UserIdentity = Depends(get_current_user),
) -> AIAgentSchedule:
    """Flip is_active; clear next_run_at when deactivated (owner-scoped)."""
    await _load_owned_schedule(service, schedule_id, current_user)
    toggled = await service.toggle_active(schedule_id)
    if toggled is None:  # pragma: no cover — _load_owned_schedule already 404s
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found")
    return toggled


# ---------------------------------------------------------------------------
# Trigger endpoint (overlap-guarded launcher)
# ---------------------------------------------------------------------------


@router.post(
    "/{schedule_id}/trigger",
    response_model=AgentScheduleTriggerResponse,
    operation_id="trigger_agent_schedule",
)
async def trigger_agent_schedule(
    schedule_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
) -> AgentScheduleTriggerResponse:
    """Launch a run for a schedule from a FRESH conversation session.

    Authorization: the schedule's owner, or an admin. No ``RoleChecker`` —
    triggering an existing schedule is authorized by its existence (it was
    created under ``agent-schedule-manage``), so a later permission revocation
    does not silently halt already-scheduled runs.

    Overlap guard: a transaction-scoped advisory lock serializes concurrent
    triggers for the same schedule, and the RUNNING ``AIAgentExecution`` row is
    created INSIDE the locked transaction (before commit) so a concurrent
    trigger's overlap check sees it → 409. The actual run then launches
    fire-and-forget via ``asyncio.create_task`` in the backend process (the
    in-memory lifecycle/event-bus singletons require this).
    """
    execution_id = str(uuid.uuid4())

    async with async_session_maker() as db:
        # 1. transaction-scoped advisory lock keyed by schedule → serializes
        #    concurrent triggers for the same schedule.
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"aas:{schedule_id}"},
        )

        # 2. overlap check: any ACTIVE execution for THIS schedule?
        active = await db.execute(
            select(AIAgentExecution.id).where(
                AIAgentExecution.schedule_id == schedule_id,
                AIAgentExecution.status.in_(
                    [
                        ExecutionStatus.PENDING,
                        ExecutionStatus.RUNNING,
                        ExecutionStatus.AWAITING_APPROVAL,
                    ]
                ),
            )
        )
        if active.first() is not None:
            await db.rollback()  # releases the advisory lock
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "An execution for this schedule is already running",
            )

        # load schedule inside the locked txn (need its template fields)
        sched_row = (
            await db.execute(
                select(AIAgentSchedule).where(AIAgentSchedule.id == str(schedule_id))
            )
        ).scalar_one_or_none()
        if sched_row is None:
            await db.rollback()
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found")
        if str(sched_row.owner_user_id) != str(current_user.user_id):
            # admin bypass: admins may trigger any schedule
            roles = await get_unified_rbac_service().get_user_roles(
                current_user.user_id, "global", None
            )
            if "admin" not in roles:
                await db.rollback()
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found")

        # 3. fresh session from the schedule template. Schedule UUID columns
        # are now Mapped[UUID], so pass them directly to create_session.
        sched_config = AIConfigService(db)
        try:
            session = await sched_config.create_session(
                user_id=sched_row.owner_user_id,
                assistant_config_id=sched_row.assistant_config_id,
                project_id=sched_row.project_id,
                branch_id=sched_row.branch_id,
                context=sched_row.context,
            )
        except ValueError as e:
            await db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

        # Create the RUNNING execution row INSIDE the locked transaction so the
        # overlap check is airtight: when the lock releases the RUNNING row is
        # already visible to a concurrent trigger. _preflight_execution (called
        # by the background run) detects this pre-created row and skips insert.
        db.add(
            AIAgentExecution(
                id=UUID(execution_id),
                session_id=session.id,
                status=ExecutionStatus.RUNNING,
                execution_mode=sched_row.execution_mode,
                run_in_background=True,
                name=(sched_row.prompt or "").strip()[:120] or None,
                schedule_id=sched_row.id,
            )
        )
        await db.commit()  # releases advisory lock; session + RUNNING row persisted
        session_id = str(session.id)

        # capture template fields BEFORE exiting the with-block (ORM objects
        # are detached after close).
        owner_id = sched_row.owner_user_id
        sched_prompt = sched_row.prompt
        sched_exec_mode = sched_row.execution_mode
        sched_project_id = sched_row.project_id
        sched_branch_id = sched_row.branch_id
        sched_assistant_config_id = sched_row.assistant_config_id
        sched_id_uuid = sched_row.id

    # 5. fire-and-forget launch in the BACKEND process. Hold a strong reference
    #    (see _background_tasks) so the task is not GC'd mid-run after this
    #    handler returns. execution_id was generated at the top; its RUNNING row
    #    already persists inside the locked txn above.
    task = asyncio.create_task(
        _run_schedule_execution(
            execution_id=execution_id,
            session_id=session_id,
            schedule_id=sched_id_uuid,
            owner_user_id=owner_id,
            prompt=sched_prompt,
            execution_mode=sched_exec_mode,
            project_id=sched_project_id,
            branch_id=sched_branch_id,
            assistant_config_id=sched_assistant_config_id,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return AgentScheduleTriggerResponse(
        execution_id=execution_id, session_id=session_id
    )


async def _run_schedule_execution(
    *,
    execution_id: str,
    session_id: str,
    schedule_id: UUID,
    owner_user_id: UUID,
    prompt: str,
    execution_mode: str,
    project_id: UUID | None,
    branch_id: UUID | None,
    assistant_config_id: UUID,
) -> None:
    """Fire-and-forget launcher for a scheduled agent run.

    Loads the assistant config, builds an AgentService, and calls
    start_execution with ``run_in_background=True`` and the originating
    ``schedule_id``. Best-effort updates last_run_at/last_execution_id on the
    schedule in a finally block.
    """
    try:
        # Load the assistant config (the schedule FK is RESTRICT, so it exists
        # unless it was deleted after the txn above committed).
        async with async_session_maker() as db:
            cfg_service = AIConfigService(db)
            cfg = await cfg_service.get_assistant_config(assistant_config_id)
        if cfg is None:
            logger.error(
                "[SCHEDULE_TRIGGER] Assistant config %s not found for schedule %s; "
                "aborting execution %s",
                assistant_config_id,
                schedule_id,
                execution_id,
            )
            return

        async with async_session_maker() as db:
            agent_service = AgentService(db)
            await agent_service.start_execution(
                message=prompt,
                assistant_config=cfg,
                session_id=UUID(session_id),
                user_id=owner_user_id,
                project_id=project_id,
                branch_id=branch_id,
                execution_mode=ExecutionMode(execution_mode),
                execution_id=execution_id,
                schedule_id=schedule_id,
                run_in_background=True,
            )
    except Exception:
        logger.error(
            "[SCHEDULE_TRIGGER] Failed execution %s for schedule %s",
            execution_id,
            schedule_id,
            exc_info=True,
        )
    finally:
        # best-effort last_run update
        try:
            async with async_session_maker() as db:
                svc = AgentScheduleService(db)
                await svc.set_last_run(schedule_id, execution_id)
        except Exception:
            logger.error(
                "[SCHEDULE_TRIGGER] Failed to update last_run for schedule %s",
                schedule_id,
                exc_info=True,
            )
