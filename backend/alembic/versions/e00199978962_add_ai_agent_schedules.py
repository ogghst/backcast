"""add ai_agent_schedules

Revision ID: e00199978962
Revises: d7154545c5e3
Create Date: 2026-06-21 04:23:59.418492

Adds the ``ai_agent_schedules`` table backing the cron-driven agent
scheduling system and extends ``ai_agent_executions`` with a ``schedule_id``
column so the overlap guard can detect an already-running scheduled run.

Includes a partial index on ``ai_agent_schedules.is_active`` (WHERE true) —
the ORM cannot express partial WHERE, so it is declared only here.

NOTE: autogenerate also emitted a spurious drop of ``schedule_dependencies``
(pre-existing DB/model index drift unrelated to this change — same drift
already noted on d7154545c5e3). Those operations were removed to keep the
migration surgical.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e00199978962"
down_revision: Union[str, Sequence[str], None] = "d7154545c5e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- New table: ai_agent_schedules (cron-driven agent run templates) ---
    op.create_table(
        "ai_agent_schedules",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("assistant_config_id", sa.UUID(), nullable=False),
        sa.Column(
            "execution_mode",
            sa.String(length=20),
            server_default="standard",
            nullable=False,
        ),
        sa.Column("cron_expr", sa.String(length=120), nullable=False),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default="UTC",
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("branch_id", sa.UUID(), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_execution_id", sa.UUID(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assistant_config_id"],
            ["ai_assistant_configs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ai_agent_schedules", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_ai_agent_schedules_assistant_config_id"),
            ["assistant_config_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_ai_agent_schedules_next_run_at"),
            ["next_run_at"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_ai_agent_schedules_owner_user_id"),
            ["owner_user_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_ai_agent_schedules_project_id"),
            ["project_id"],
            unique=False,
        )
        # Partial index — only active schedules. The ORM cannot express the
        # WHERE clause, so it lives only in this migration. The scheduler's
        # due-schedule query is ``is_active=true AND next_run_at <= now()``,
        # which this index serves directly.
        batch_op.create_index(
            "ix_ai_agent_schedules_is_active",
            ["is_active"],
            unique=False,
            postgresql_where=sa.text("is_active"),
        )

    # --- Extend ai_agent_executions with schedule_id (overlap-guard key) ---
    with op.batch_alter_table("ai_agent_executions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "schedule_id",
                sa.UUID(),
                nullable=True,
                comment="Originating ai_agent_schedules.id, if this run was scheduled",
            )
        )
        batch_op.create_index(
            batch_op.f("ix_ai_agent_executions_schedule_id"),
            ["schedule_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema (removes ai_agent_schedules + schedule_id)."""
    with op.batch_alter_table("ai_agent_executions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ai_agent_executions_schedule_id"))
        batch_op.drop_column("schedule_id")

    with op.batch_alter_table("ai_agent_schedules", schema=None) as batch_op:
        batch_op.drop_index("ix_ai_agent_schedules_is_active")
        batch_op.drop_index(batch_op.f("ix_ai_agent_schedules_project_id"))
        batch_op.drop_index(batch_op.f("ix_ai_agent_schedules_owner_user_id"))
        batch_op.drop_index(batch_op.f("ix_ai_agent_schedules_next_run_at"))
        batch_op.drop_index(batch_op.f("ix_ai_agent_schedules_assistant_config_id"))

    op.drop_table("ai_agent_schedules")
