"""Service for agent run schedules.

Thin data-access layer mirroring the no-repository pattern. All DB access is
direct via AsyncSession. Schedules are owner-scoped configuration rows.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.ai_agent_schedule import AIAgentSchedule
from app.models.schemas.ai_agent_schedule import (
    AgentScheduleCreate,
    AgentScheduleUpdate,
    compute_next_run,
)


class AgentScheduleService:
    """CRUD + activation for AIAgentSchedule rows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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
