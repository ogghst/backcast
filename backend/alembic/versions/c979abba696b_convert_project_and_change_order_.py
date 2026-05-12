"""Convert project and change order statuses to lowercase

Revision ID: c979abba696b
Revises: 20260511b_proj_member_migr
Create Date: 2026-05-12 08:13:11.326372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c979abba696b'
down_revision: Union[str, Sequence[str], None] = '20260511b_proj_member_migr'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - convert project and change order statuses to lowercase."""
    # Update projects table - convert status values to lowercase
    op.execute(
        "UPDATE projects SET status = 'draft' WHERE status = 'Draft'"
    )
    op.execute(
        "UPDATE projects SET status = 'active' WHERE status = 'Active'"
    )
    op.execute(
        "UPDATE projects SET status = 'on_hold' WHERE status = 'On Hold'"
    )
    op.execute(
        "UPDATE projects SET status = 'completed' WHERE status = 'Completed'"
    )
    op.execute(
        "UPDATE projects SET status = 'cancelled' WHERE status = 'Cancelled'"
    )

    # Update change_orders table - convert status values to lowercase
    op.execute(
        "UPDATE change_orders SET status = 'draft' WHERE status = 'Draft'"
    )
    op.execute(
        "UPDATE change_orders SET status = 'submitted_for_approval' WHERE status = 'Submitted for Approval'"
    )
    op.execute(
        "UPDATE change_orders SET status = 'under_review' WHERE status = 'Under Review'"
    )
    op.execute(
        "UPDATE change_orders SET status = 'approved' WHERE status = 'Approved'"
    )
    op.execute(
        "UPDATE change_orders SET status = 'implemented' WHERE status = 'Implemented'"
    )
    op.execute(
        "UPDATE change_orders SET status = 'rejected' WHERE status = 'Rejected'"
    )


def downgrade() -> None:
    """Downgrade schema - convert status values back to capitalized."""
    # Revert projects table
    op.execute(
        "UPDATE projects SET status = 'Draft' WHERE status = 'draft'"
    )
    op.execute(
        "UPDATE projects SET status = 'Active' WHERE status = 'active'"
    )
    op.execute(
        "UPDATE projects SET status = 'On Hold' WHERE status = 'on_hold'"
    )
    op.execute(
        "UPDATE projects SET status = 'Completed' WHERE status = 'completed'"
    )
    op.execute(
        "UPDATE projects SET status = 'Cancelled' WHERE status = 'cancelled'"
    )

    # Revert change_orders table
    op.execute(
        "UPDATE change_orders SET status = 'Draft' WHERE status = 'draft'"
    )
    op.execute(
        "UPDATE change_orders SET status = 'Submitted for Approval' WHERE status = 'submitted_for_approval'"
    )
    op.execute(
        "UPDATE change_orders SET status = 'Under Review' WHERE status = 'under_review'"
    )
    op.execute(
        "UPDATE change_orders SET status = 'Approved' WHERE status = 'approved'"
    )
    op.execute(
        "UPDATE change_orders SET status = 'Implemented' WHERE status = 'implemented'"
    )
    op.execute(
        "UPDATE change_orders SET status = 'Rejected' WHERE status = 'rejected'"
    )
