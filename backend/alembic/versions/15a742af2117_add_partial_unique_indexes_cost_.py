"""add_partial_unique_indexes_cost_elements_wbes

Revision ID: 15a742af2117
Revises: 6c93c299c703
Create Date: 2026-04-01 07:20:19.343741

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15a742af2117'
down_revision: Union[str, Sequence[str], None] = '6c93c299c703'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add partial unique indexes to prevent duplicate current versions.

    Ensures at most one current version (upper(valid_time) IS NULL) per
    (root_id, branch) combination on cost_elements and wbes tables.
    """
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cost_elements_cost_element_id_branch_current
        ON cost_elements (cost_element_id, branch)
        WHERE upper(valid_time) IS NULL AND deleted_at IS NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_wbes_wbe_id_branch_current
        ON wbes (wbe_id, branch)
        WHERE upper(valid_time) IS NULL AND deleted_at IS NULL
        """
    )


def downgrade() -> None:
    """Remove partial unique indexes."""
    op.execute("DROP INDEX IF EXISTS uq_cost_elements_cost_element_id_branch_current")
    op.execute("DROP INDEX IF EXISTS uq_wbes_wbe_id_branch_current")
