"""Domain model for agent run schedules.

A schedule is a cron-driven template that a separate scheduler process polls.
When due, the scheduler calls the trigger API endpoint, which creates a FRESH
conversation session from the template fields and launches the run via
``asyncio.create_task`` in the backend process.

Non-versioned entity (SimpleEntityBase) — schedules are configuration, not
audit-tracked domain data.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import SimpleEntityBase


class AIAgentSchedule(SimpleEntityBase):
    """Cron-driven schedule for an agent execution template.

    Each fire creates a fresh conversation session (``assistant_config_id``,
    ``prompt``, ``project_id``, ``branch_id``, ``context``) and launches a
    background run.  ``next_run_at`` is the scheduler's source of truth for
    due-schedule polling; the scheduler rewrites it after every fire.
    """

    __tablename__ = "ai_agent_schedules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_config_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        ForeignKey("ai_assistant_configs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    execution_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="standard", server_default="standard"
    )
    cron_expr: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="UTC", server_default="UTC"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    project_id: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True, index=True)
    branch_id: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    owner_user_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_execution_id: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<AIAgentSchedule(id={self.id}, name={self.name}, "
            f"cron={self.cron_expr}, is_active={self.is_active})>"
        )
