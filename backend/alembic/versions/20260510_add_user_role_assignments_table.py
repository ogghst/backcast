"""add user_role_assignments table

Revision ID: 20260510_unified_rbac
Revises: 20260509_fix_notification_fk
Create Date: 2026-05-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260510_unified_rbac"
down_revision: str | Sequence[str] | None = "20260509_fix_notification_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user_role_assignments table for unified RBAC."""
    op.create_table(
        "user_role_assignments",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(),
            nullable=False,
        ),
        sa.Column(
            "scope_type",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "scope_id",
            postgresql.UUID(),
            nullable=True,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=True,
        ),
        sa.Column(
            "granted_by",
            postgresql.UUID(),
            nullable=True,
        ),
        sa.Column(
            "granted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "expires_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "scope_type",
            "scope_id",
            name="uq_user_role_assignment_scope",
        ),
        # No FK to users.user_id — it's a business key with duplicates across
        # EVCS versions, so PostgreSQL cannot enforce a UNIQUE constraint.
        # Referential integrity is handled at the application layer.
        # (See migration e584fd7a5320 for the established pattern.)
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["rbac_roles.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_user_role_assignments_user_id",
        "user_role_assignments",
        ["user_id"],
    )
    op.create_index(
        "ix_user_role_assignments_role_id",
        "user_role_assignments",
        ["role_id"],
    )
    op.create_index(
        "ix_user_role_assignments_scope_type",
        "user_role_assignments",
        ["scope_type"],
    )
    op.create_index(
        "ix_user_role_assignments_scope_id",
        "user_role_assignments",
        ["scope_id"],
    )


def downgrade() -> None:
    """Remove user_role_assignments table."""
    op.drop_index("ix_user_role_assignments_scope_id", table_name="user_role_assignments")
    op.drop_index("ix_user_role_assignments_scope_type", table_name="user_role_assignments")
    op.drop_index("ix_user_role_assignments_role_id", table_name="user_role_assignments")
    op.drop_index("ix_user_role_assignments_user_id", table_name="user_role_assignments")
    op.drop_table("user_role_assignments")
