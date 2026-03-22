"""add_project_members_table

Revision ID: 021bb7eeaa21
Revises: 1fd0ec9f01a4
Create Date: 2026-03-21 15:17:43.379428

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "021bb7eeaa21"
# Depends on unique constraints migration
down_revision: str | Sequence[str] | None = "42751fa7cef1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "project_members",
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
            "user_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "assigned_by",
            sa.UUID(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name=op.f("fk_project_members_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.project_id"],
            name=op.f("fk_project_members_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by"],
            ["users.user_id"],
            name=op.f("fk_project_members_assigned_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_members")),
        sa.UniqueConstraint(
            "user_id",
            "project_id",
            name="uq_project_members_user_project",
        ),
    )
    # Create indexes for common queries
    op.create_index(
        op.f("ix_project_members_user_id"),
        "project_members",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_members_project_id"),
        "project_members",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_members_role"),
        "project_members",
        ["role"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_project_members_role"), table_name="project_members")
    op.drop_index(op.f("ix_project_members_project_id"), table_name="project_members")
    op.drop_index(op.f("ix_project_members_user_id"), table_name="project_members")
    op.drop_table("project_members")
