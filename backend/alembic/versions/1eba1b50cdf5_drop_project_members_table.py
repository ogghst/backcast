"""drop_project_members_table

Revision ID: 1eba1b50cdf5
Revises: 64f26b376a85
Create Date: 2026-05-16 06:24:09.123145

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1eba1b50cdf5'
down_revision: str | Sequence[str] | None = '64f26b376a85'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the deprecated project_members table.

    Verifies data integrity before dropping: every row in project_members
    must have a corresponding UserRoleAssignment (scope_type='project',
    matching user_id and project_id as scope_id). If any orphaned rows
    exist, the migration will fail with a clear error message.
    """
    # Verify data integrity: check for orphaned project_members rows
    # that have no corresponding user_role_assignments entry.
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            SELECT COUNT(*) AS orphan_count
            FROM project_members pm
            WHERE NOT EXISTS (
                SELECT 1
                FROM user_role_assignments ura
                WHERE ura.user_id = pm.user_id
                  AND ura.scope_type = 'project'
                  AND ura.scope_id = pm.project_id
            )
        """)
    )
    orphan_count = result.scalar()

    if orphan_count and orphan_count > 0:
        raise RuntimeError(
            f"Cannot drop project_members: found {orphan_count} rows with no "
            "corresponding UserRoleAssignment (scope_type='project'). "
            "Migrate these rows to user_role_assignments before re-running."
        )

    # Drop the table with CASCADE to remove dependent objects
    # (indexes, constraints, etc.)
    op.drop_table('project_members')


def downgrade() -> None:
    """Re-create the project_members table.

    WARNING: This does NOT restore data. The table will be empty.
    """
    op.create_table(
        'project_members',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('assigned_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.user_id'],
                                ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'project_id',
                            name='uq_project_members_user_project'),
    )
