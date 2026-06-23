"""Pydantic schemas for agent run schedules.

Provides schemas for:
- AgentScheduleCreate: Create a cron-driven agent schedule
- AgentScheduleUpdate: Patch an existing schedule
- AgentScheduleRead: Read a schedule
- AgentScheduleTriggerResponse: Trigger endpoint response
- compute_next_run: Helper that resolves a cron expr to its next fire time (UTC)
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, Self
from uuid import UUID
from zoneinfo import ZoneInfo

from croniter import croniter
from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    # Imported lazily at runtime (see _parse_schedule_context) to avoid a
    # circular import: app.models.schemas.ai pulls in the full AI subsystem,
    # which deep-imports back into this schema module via the route layer.
    from app.models.schemas.ai import SessionContext


def _parse_schedule_context(context: dict[str, Any] | None) -> "SessionContext":
    """Parse a raw context dict into a validated SessionContext.

    Reuses SessionContext.validate_context_fields, so an invalid shape
    (e.g. ``{type:"wbe", id:<x>}`` with no project_id) raises ValueError,
    which FastAPI surfaces as 422.

    SessionContext is imported lazily inside the function to avoid a circular
    import (app.models.schemas.ai pulls in the full AI subsystem, which
    deep-imports back into this schema module via the route layer).
    """
    from app.models.schemas.ai import SessionContext

    return SessionContext(**(context or {}))


class AgentScheduleCreate(BaseModel):
    """Schema for creating an agent schedule."""

    name: str = Field(..., min_length=1, max_length=255)
    prompt: str = Field(..., min_length=1)
    assistant_config_id: UUID
    execution_mode: Literal["safe", "standard", "expert"] = "standard"
    cron_expr: str = Field(..., min_length=1)
    timezone: str = "UTC"
    is_active: bool = True
    project_id: UUID | None = None
    branch_id: UUID | None = None
    context: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _derive_project_id_from_context(self) -> Self:
        """Derive project_id from a populated context (mirrors chat scope).

        When context is set, it is the source of truth for the run's scope:
        the parsed SessionContext determines project_id, overriding any value
        supplied alongside it. Invalid context shapes raise here (surfaces
        as a 422).
        """
        if self.context is not None:
            parsed = _parse_schedule_context(self.context)
            if parsed.type == "general":
                self.project_id = None
            elif parsed.type == "project":
                self.project_id = UUID(str(parsed.id))
            else:
                # wbe / cost_element / work_package all carry project_id
                self.project_id = UUID(str(parsed.project_id))
        return self


class AgentScheduleUpdate(BaseModel):
    """Schema for patching an agent schedule (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    prompt: str | None = Field(None, min_length=1)
    assistant_config_id: UUID | None = None
    execution_mode: Literal["safe", "standard", "expert"] | None = None
    cron_expr: str | None = Field(None, min_length=1)
    timezone: str | None = None
    is_active: bool | None = None
    project_id: UUID | None = None
    branch_id: UUID | None = None
    context: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _derive_project_id_from_context(self) -> Self:
        """When a new context is supplied on a patch, derive project_id.

        Leaving context unset (None) preserves the existing scope — do NOT
        touch project_id in that case.
        """
        if self.context is not None:
            parsed = _parse_schedule_context(self.context)
            if parsed.type == "general":
                self.project_id = None
            elif parsed.type == "project":
                self.project_id = UUID(str(parsed.id))
            else:
                self.project_id = UUID(str(parsed.project_id))
        return self


class AgentScheduleRead(BaseModel):
    """Schema for reading an agent schedule."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    prompt: str
    assistant_config_id: UUID
    execution_mode: str
    cron_expr: str
    timezone: str
    is_active: bool
    project_id: UUID | None
    branch_id: UUID | None
    context: dict[str, Any] | None
    owner_user_id: UUID
    last_run_at: datetime | None
    last_execution_id: UUID | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentScheduleTriggerResponse(BaseModel):
    """Response from the schedule trigger endpoint."""

    execution_id: str
    session_id: str


def compute_next_run(cron_expr: str, timezone: str = "UTC") -> datetime:
    """Compute the next fire time for a cron expression in the given tz.

    Validates the cron expression; raises ValueError on invalid input
    (callers should let this surface as a 422).
    """
    try:
        tz = ZoneInfo(timezone)
    except Exception as exc:
        raise ValueError(f"Invalid timezone: {timezone}") from exc
    # croniter raises KeyError/ValueError on invalid expressions, but may raise
    # other types (e.g. AttributeError) for non-string input — normalize all to
    # ValueError so the API surfaces a clean 422 instead of a 500.
    try:
        cron = croniter(cron_expr, datetime.now(tz))  # validates
    except Exception as exc:
        raise ValueError(f"Invalid cron expression: {cron_expr!r}") from exc
    nxt = cron.get_next(datetime)
    return nxt.astimezone(UTC)
