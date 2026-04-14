"""add project budget settings table

Revision ID: 49226017fda2
Revises: 6f04c31c3ff0
Create Date: 2026-04-14 19:54:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "49226017fda2"
down_revision: str | Sequence[str] | None = "6f04c31c3ff0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "project_budget_settings",
        sa.Column(
            "project_budget_settings_id",
            postgresql.UUID(),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(),
            nullable=False,
        ),
        sa.Column(
            "warning_threshold_percent",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="80.0",
        ),
        sa.Column(
            "allow_project_admin_override",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "valid_time",
            postgresql.TSTZRANGE(),
            server_default=sa.text("tstzrange(now(), NULL, '[]')"),
            nullable=False,
        ),
        sa.Column(
            "transaction_time",
            postgresql.TSTZRANGE(),
            server_default=sa.text("tstzrange(now(), NULL, '[]')"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(), nullable=False),
        sa.Column("deleted_by", postgresql.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_budget_settings")),
    )

    # Create indexes
    op.create_index(
        op.f("ix_project_budget_settings_project_budget_settings_id"),
        "project_budget_settings",
        ["project_budget_settings_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_project_budget_settings_project_id"),
        "project_budget_settings",
        ["project_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_project_budget_settings_created_by"),
        "project_budget_settings",
        ["created_by"],
        unique=False,
    )

    # Note: Foreign key to projects.project_id omitted because that column
    # doesn't have a unique constraint. Referential integrity enforced at application level.


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_project_budget_settings_created_by"),
        table_name="project_budget_settings",
    )
    op.drop_index(
        op.f("ix_project_budget_settings_project_id"),
        table_name="project_budget_settings",
    )
    op.drop_index(
        op.f("ix_project_budget_settings_project_budget_settings_id"),
        table_name="project_budget_settings",
    )
    op.drop_table("project_budget_settings")
