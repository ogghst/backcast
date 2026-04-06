"""add dashboard_layouts table

Revision ID: 20260405_add_dashboard_layouts
Revises: 15a742af2117
Create Date: 2026-04-05

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260405_add_dashboard_layouts'
down_revision: str | Sequence[str] | None = '15a742af2117'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create dashboard_layouts table for storing user dashboard configurations."""
    op.create_table(
        "dashboard_layouts",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
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
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "is_template",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_default",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "widgets",
            pg.JSONB(),
            server_default="[]",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dashboard_layouts")),
    )
    op.create_index(
        op.f("ix_dashboard_layouts_user_id"),
        "dashboard_layouts",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_dashboard_layouts_project_id"),
        "dashboard_layouts",
        ["project_id"],
    )
    op.create_index(
        op.f("ix_dashboard_layouts_is_template"),
        "dashboard_layouts",
        ["is_template"],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_dashboard_layouts_default_per_user_project
        ON dashboard_layouts (user_id, project_id)
        WHERE is_default = true AND project_id IS NOT NULL
        """
    )


def downgrade() -> None:
    """Drop dashboard_layouts table and associated indexes."""
    op.execute("DROP INDEX IF EXISTS uq_dashboard_layouts_default_per_user_project")
    op.drop_index(op.f("ix_dashboard_layouts_is_template"), table_name="dashboard_layouts")
    op.drop_index(op.f("ix_dashboard_layouts_project_id"), table_name="dashboard_layouts")
    op.drop_index(op.f("ix_dashboard_layouts_user_id"), table_name="dashboard_layouts")
    op.drop_table("dashboard_layouts")
