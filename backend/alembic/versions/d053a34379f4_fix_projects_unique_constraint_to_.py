"""fix projects unique constraint to include branch

Revision ID: d053a34379f4
Revises: 0e2fe53fe853
Create Date: 2026-04-24 23:27:02.337392

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd053a34379f4'
down_revision: Union[str, Sequence[str], None] = '0e2fe53fe853'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Fix the unique constraint on projects to allow one current version per branch.
    The old constraint only allowed one current version per project_id across all branches,
    which prevented branching from working correctly.

    Also exclude empty ranges from the constraint to allow Time Machine mode updates.
    """
    # Drop the old partial index that only considered project_id
    op.execute("DROP INDEX IF EXISTS uq_projects_project_id_current;")

    # Create a new partial index that considers both project_id and branch
    # This allows one current version per project_id per branch
    # CRITICAL FIX: Exclude empty ranges using isempty() function
    # Empty ranges have upper(valid_time) IS NULL but are NOT current versions
    op.execute(
        """
        CREATE UNIQUE INDEX uq_projects_project_id_branch_current
        ON projects(project_id, branch)
        WHERE upper(valid_time) IS NULL AND deleted_at IS NULL AND NOT isempty(valid_time);
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the new index that includes branch and excludes empty ranges
    op.execute("DROP INDEX IF EXISTS uq_projects_project_id_branch_current;")

    # Restore the old index that only considered project_id
    op.execute(
        """
        CREATE UNIQUE INDEX uq_projects_project_id_current
        ON projects(project_id)
        WHERE upper(valid_time) IS NULL AND deleted_at IS NULL;
        """
    )
