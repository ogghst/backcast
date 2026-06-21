"""API routes for agent run schedules.

CRUD is owner-scoped (a user manages their own schedules; cross-owner access
returns 404 to avoid leaking existence). The ``/trigger`` endpoint ("Run now")
delegates to :func:`trigger_schedule_run` — the same overlap-guarded launcher
the in-process scheduler tick calls. Overlap is refused with 409 if a run for
that schedule is already active.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.core.rbac_unified import get_unified_rbac_service
from app.db.session import get_db
from app.models.domain.ai_agent_schedule import AIAgentSchedule
from app.models.schemas.ai_agent_schedule import (
    AgentScheduleCreate,
    AgentScheduleRead,
    AgentScheduleTriggerResponse,
    AgentScheduleUpdate,
)
from app.services.agent_schedule_service import (
    AgentScheduleService,
    ScheduleNotFoundError,
    ScheduleOverlapError,
    trigger_schedule_run,
)

router = APIRouter(prefix="/ai/agent-schedules", tags=["Agent Schedules"])


# ---------------------------------------------------------------------------
# DI helpers
# ---------------------------------------------------------------------------


def get_agent_schedule_service(
    session: AsyncSession = Depends(get_db),
) -> AgentScheduleService:
    """Build an AgentScheduleService bound to the request session."""
    return AgentScheduleService(session)


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
# Trigger endpoint ("Run now") — delegates to the shared launcher
# ---------------------------------------------------------------------------


@router.post(
    "/{schedule_id}/trigger",
    response_model=AgentScheduleTriggerResponse,
    operation_id="trigger_agent_schedule",
)
async def trigger_agent_schedule(
    schedule_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    service: AgentScheduleService = Depends(get_agent_schedule_service),
) -> AgentScheduleTriggerResponse:
    """Launch a run for a schedule ("Run now"). Owner or admin.

    Delegates to ``trigger_schedule_run`` — the same overlap-guarded launcher
    the in-process scheduler tick uses — so manual and scheduled runs traverse
    identical code. Authorization is by the schedule's existence (created under
    ``agent-schedule-manage``); a later permission revocation does not silently
    halt already-scheduled runs.
    """
    # owner-or-admin: a foreign, non-admin caller gets 404 (no existence leak)
    sched = await service.get_schedule(schedule_id)
    if sched is None or str(sched.owner_user_id) != str(current_user.user_id):
        roles = await get_unified_rbac_service().get_user_roles(
            current_user.user_id, "global", None
        )
        if sched is None or "admin" not in roles:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found")

    try:
        return await trigger_schedule_run(schedule_id)
    except ScheduleOverlapError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An execution for this schedule is already running",
        ) from None
    except ScheduleNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found") from None
