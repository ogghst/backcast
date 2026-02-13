"""fix_change_order_approver_fk

Revision ID: 03b4089c06af
Revises: 20260205_impact_fields
Create Date: 2026-02-07 11:27:40.451115

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '03b4089c06af'
down_revision: str | Sequence[str] | None = '20260205_impact_fields'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Drop existing FK referencing users.id
    op.drop_constraint('fk_change_orders_assigned_approver', 'change_orders', type_='foreignkey')

    # 2. Update existing data to point to user_id (Business Key) instead of id (Version Key)
    # Join on users.id = change_orders.assigned_approver_id (assuming current data is "correct" but points to version)
    # Update assigned_approver_id = users.user_id
    op.execute("""
        UPDATE change_orders
        SET assigned_approver_id = users.user_id
        FROM users
        WHERE change_orders.assigned_approver_id = users.id
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Re-create the FK constraint pointing to users.id
    # Note: This will likely fail if data has been updated to user_id values that don't match any id.
    # We attempt it for completeness but acknowledge data loss/integrity issues on downgrade.
    op.create_foreign_key(
        'fk_change_orders_assigned_approver',
        'change_orders',
        'users',
        ['assigned_approver_id'],
        ['id'],
        ondelete='SET NULL'
    )
