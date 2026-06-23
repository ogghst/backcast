"""Service for agent run schedules.

Thin data-access layer mirroring the no-repository pattern. All DB access is
direct via AsyncSession. Schedules are owner-scoped configuration rows.

Also owns the overlap-guarded launcher (:func:`trigger_schedule_run`) shared by
the HTTP ``/trigger`` handler and the in-process scheduler tick.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_service import AgentService
from app.ai.event_types import ExecutionStatus
from app.ai.tools.types import ExecutionMode
from app.core.rbac_unified import get_unified_rbac_service, rbac_session
from app.db.session import async_session_maker
from app.models.domain.ai import AIAgentExecution
from app.models.domain.ai_agent_schedule import AIAgentSchedule
from app.models.domain.wbs_element import WBSElement
from app.models.schemas.ai_agent_schedule import (
    AgentScheduleCreate,
    AgentScheduleTriggerResponse,
    AgentScheduleUpdate,
    compute_next_run,
)
from app.services.ai_config_service import AIConfigService

logger = logging.getLogger(__name__)


class AgentScheduleService:
    """CRUD + activation for AIAgentSchedule rows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _authorize_scope(
        self,
        *,
        owner_user_id: UUID,
        project_id: UUID | None,
        context: dict[str, Any] | None,
    ) -> None:
        """Authorize the run's context scope (global / project / WBE).

        Global scope (project_id is None) is always allowed. Project scope
        requires the owner to have access to that project via unified RBAC.
        WBE scope additionally requires a current, non-deleted WBS Element
        owned by that project.

        Raises ValueError (surfaces as a 422 from the routes) on denial.
        """
        if project_id is None:
            return  # global scope — nothing to check

        async with rbac_session(self.session):
            accessible = await get_unified_rbac_service().get_accessible_projects(
                owner_user_id
            )
        if project_id not in accessible:
            msg = f"No access to project {project_id}"
            raise ValueError(msg)

        if context is not None and context.get("type") == "wbe":
            wbe_id = context.get("id")
            if wbe_id is None:
                msg = "WBE context requires 'id'"
                raise ValueError(msg)
            exists = (
                await self.session.execute(
                    select(WBSElement.wbs_element_id)
                    .where(WBSElement.wbs_element_id == UUID(str(wbe_id)))
                    .where(WBSElement.project_id == project_id)
                    .where(sa_func.upper(WBSElement.valid_time).is_(None))
                    .where(WBSElement.deleted_at.is_(None))
                    .limit(1)
                )
            ).first()
            if exists is None:
                msg = f"WBS element {wbe_id} not found in project {project_id}"
                raise ValueError(msg)

    async def list_schedules(
        self,
        *,
        owner_user_id: UUID | None = None,
        is_active: bool | None = None,
        assistant_config_id: UUID | None = None,
    ) -> list[AIAgentSchedule]:
        """List schedules with optional filters, newest first."""
        stmt = select(AIAgentSchedule)
        if owner_user_id is not None:
            stmt = stmt.where(AIAgentSchedule.owner_user_id == owner_user_id)
        if is_active is not None:
            stmt = stmt.where(AIAgentSchedule.is_active == is_active)
        if assistant_config_id is not None:
            stmt = stmt.where(
                AIAgentSchedule.assistant_config_id == assistant_config_id
            )
        stmt = stmt.order_by(AIAgentSchedule.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_schedule(self, schedule_id: UUID) -> AIAgentSchedule | None:
        """Get a single schedule by ID."""
        stmt = select(AIAgentSchedule).where(AIAgentSchedule.id == str(schedule_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_schedule(
        self, data: AgentScheduleCreate, owner_user_id: UUID
    ) -> AIAgentSchedule:
        """Create a new schedule. Computes next_run_at from the cron expr.

        Raises ValueError if the cron expression or timezone is invalid.
        """
        next_run_at = compute_next_run(data.cron_expr, data.timezone)
        await self._authorize_scope(
            owner_user_id=owner_user_id,
            project_id=data.project_id,
            context=data.context,
        )
        schedule = AIAgentSchedule(
            name=data.name,
            prompt=data.prompt,
            assistant_config_id=data.assistant_config_id,
            execution_mode=data.execution_mode,
            cron_expr=data.cron_expr,
            timezone=data.timezone,
            is_active=data.is_active,
            project_id=data.project_id if data.project_id else None,
            branch_id=data.branch_id if data.branch_id else None,
            context=data.context,
            owner_user_id=owner_user_id,
            next_run_at=next_run_at if data.is_active else None,
        )
        self.session.add(schedule)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(schedule)
        return schedule

    async def update_schedule(
        self, schedule_id: UUID, data: AgentScheduleUpdate
    ) -> AIAgentSchedule | None:
        """Patch a schedule. Recomputes next_run_at if cron/tz changed.

        Returns None if the schedule does not exist.
        Raises ValueError if a changed cron/tz is invalid.
        """
        schedule = await self.get_schedule(schedule_id)
        if schedule is None:
            return None

        cron_changed = data.cron_expr is not None
        tz_changed = data.timezone is not None
        active_changed = data.is_active is not None

        if data.name is not None:
            schedule.name = data.name
        if data.prompt is not None:
            schedule.prompt = data.prompt
        if data.assistant_config_id is not None:
            schedule.assistant_config_id = data.assistant_config_id
        if data.execution_mode is not None:
            schedule.execution_mode = data.execution_mode
        if data.cron_expr is not None:
            schedule.cron_expr = data.cron_expr
        if data.timezone is not None:
            schedule.timezone = data.timezone
        if data.is_active is not None:
            schedule.is_active = data.is_active
        if data.project_id is not None:
            schedule.project_id = data.project_id
        if data.branch_id is not None:
            schedule.branch_id = data.branch_id
        if data.context is not None:
            schedule.context = data.context
            # The schema validator derives project_id from the parsed context;
            # apply that derived value too (covers the general-scope case where
            # the derived project_id is None — the guard above would skip None).
            schedule.project_id = data.project_id
            await self._authorize_scope(
                owner_user_id=schedule.owner_user_id,
                project_id=schedule.project_id,
                context=schedule.context,
            )

        # Recompute next_run_at when the schedule cadence or active state moves.
        if cron_changed or tz_changed or active_changed:
            effective_active = schedule.is_active
            if effective_active:
                schedule.next_run_at = compute_next_run(
                    schedule.cron_expr, schedule.timezone
                )
            else:
                schedule.next_run_at = None

        await self.session.commit()
        await self.session.refresh(schedule)
        return schedule

    async def delete_schedule(self, schedule_id: UUID) -> bool:
        """Delete a schedule. Returns True if a row was deleted."""
        schedule = await self.get_schedule(schedule_id)
        if schedule is None:
            return False
        await self.session.delete(schedule)
        await self.session.commit()
        return True

    async def toggle_active(self, schedule_id: UUID) -> AIAgentSchedule | None:
        """Flip is_active; clear next_run_at when deactivated.

        Returns None if the schedule does not exist.
        """
        schedule = await self.get_schedule(schedule_id)
        if schedule is None:
            return None
        schedule.is_active = not schedule.is_active
        if schedule.is_active:
            schedule.next_run_at = compute_next_run(
                schedule.cron_expr, schedule.timezone
            )
        else:
            schedule.next_run_at = None
        await self.session.commit()
        await self.session.refresh(schedule)
        return schedule

    async def set_last_run(self, schedule_id: UUID, execution_id: str) -> None:
        """Best-effort update of last_run_at / last_execution_id.

        Swallows errors so a failed last-run update never masks the run's
        own outcome (called from the fire-and-forget launcher's finally block).
        """
        schedule = await self.get_schedule(schedule_id)
        if schedule is None:
            return
        schedule.last_run_at = datetime.now(UTC)
        schedule.last_execution_id = UUID(execution_id)
        await self.session.commit()


# ---------------------------------------------------------------------------
# Overlap-guarded launcher (shared by the HTTP "Run now" handler + scheduler)
# ---------------------------------------------------------------------------


class ScheduleOverlapError(Exception):
    """An execution for this schedule is already active."""


class ScheduleNotFoundError(Exception):
    """The schedule does not exist."""


# Strong refs to fire-and-forget execution tasks. asyncio only keeps a weak
# reference to tasks, so a task created in a handler/tick and never awaited can
# be garbage-collected mid-run once the caller returns. We hold each task here
# and drop it when it completes. (The minutes-long agent run outlives the
# caller by design.)
_background_tasks: set[asyncio.Task[None]] = set()


async def trigger_schedule_run(schedule_id: UUID) -> AgentScheduleTriggerResponse:
    """Overlap-guarded launcher for a schedule run.

    Shared by the HTTP ``/trigger`` handler (the "Run now" button) and the
    in-process scheduler tick. Creates a fresh conversation session + a RUNNING
    ``AIAgentExecution`` row inside a transaction-scoped advisory lock (so a
    concurrent caller's overlap check sees the RUNNING row before the lock
    releases), then launches the agent run fire-and-forget via
    ``asyncio.create_task`` in THIS process — the in-memory
    ExecutionLifecycle/event-bus singletons live here.

    Raises:
        ScheduleNotFoundError: the schedule row is gone.
        ScheduleOverlapError: an execution for this schedule is already active.
    """
    execution_id = str(uuid.uuid4())

    async with async_session_maker() as db:
        # 1. transaction-scoped advisory lock keyed by schedule.
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
            raise ScheduleOverlapError(str(schedule_id))

        # 3. load the schedule (template fields) inside the locked txn.
        sched_row = (
            await db.execute(
                select(AIAgentSchedule).where(AIAgentSchedule.id == schedule_id)
            )
        ).scalar_one_or_none()
        if sched_row is None:
            await db.rollback()
            raise ScheduleNotFoundError(str(schedule_id))

        # 4. fresh session from the schedule template.
        sched_config = AIConfigService(db)
        session = await sched_config.create_session(
            user_id=sched_row.owner_user_id,
            assistant_config_id=sched_row.assistant_config_id,
            project_id=sched_row.project_id,
            branch_id=sched_row.branch_id,
            context=sched_row.context,
        )

        # 5. Create the RUNNING execution row INSIDE the locked txn so the
        #    overlap check is airtight: when the lock releases the RUNNING row
        #    is already visible to a concurrent caller. _preflight_execution
        #    (called by the background run) detects the pre-created row and
        #    skips re-insert.
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
        await db.commit()  # releases advisory lock; session + RUNNING row persist
        session_id = str(session.id)

        # capture template fields BEFORE the session closes (ORM objects detach)
        owner_id = sched_row.owner_user_id
        sched_prompt = sched_row.prompt
        sched_exec_mode = sched_row.execution_mode
        sched_project_id = sched_row.project_id
        sched_branch_id = sched_row.branch_id
        sched_assistant_config_id = sched_row.assistant_config_id
        sched_id_uuid = sched_row.id

    # 6. fire-and-forget launch. Held in _background_tasks so asyncio doesn't
    #    GC the minutes-long task after this function returns.
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
