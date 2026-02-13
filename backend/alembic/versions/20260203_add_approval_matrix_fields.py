"""Add approval matrix and SLA tracking fields to change_orders.

Revision ID: 20260203_add_approval_matrix_fields
Revises: 20260203_add_revenue_allocation_to_wbes
Create Date: 2026-02-03

This migration adds fields for the approval matrix and SLA tracking system:
- impact_level: Financial impact classification (LOW/MEDIUM/HIGH/CRITICAL)
- assigned_approver_id: User responsible for approval
- sla_assigned_at: When SLA timer started
- sla_due_date: SLA deadline
- sla_status: Current SLA tracking status

Part of E06-U09 to E06-U13 implementation.
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = '0206_appr_matrix'
down_revision = '0206_rev_alloc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add approval matrix and SLA tracking fields to change_orders table."""
    # Add new columns
    op.add_column(
        'change_orders',
        sa.Column('impact_level', sa.String(20), nullable=True)
    )
    op.add_column(
        'change_orders',
        sa.Column('assigned_approver_id', postgresql.UUID(), nullable=True)
    )
    op.add_column(
        'change_orders',
        sa.Column('sla_assigned_at', sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        'change_orders',
        sa.Column('sla_due_date', sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        'change_orders',
        sa.Column('sla_status', sa.String(20), nullable=True)
    )

    # Create foreign key constraint for assigned_approver_id
    # Note: users table uses 'id' as primary key, not 'user_id'
    op.create_foreign_key(
        'fk_change_orders_assigned_approver',
        'change_orders', 'users',
        ['assigned_approver_id'], ['id'],
        ondelete='SET NULL'
    )

    # Create index for sla_due_date to support SLA monitoring queries
    op.create_index(
        'ix_change_orders_sla_due_date',
        'change_orders',
        ['sla_due_date']
    )

    # Create index for impact_level to support filtering by impact
    op.create_index(
        'ix_change_orders_impact_level',
        'change_orders',
        ['impact_level']
    )


def downgrade() -> None:
    """Remove approval matrix and SLA tracking fields from change_orders table."""
    # Drop indexes
    op.drop_index('ix_change_orders_impact_level', table_name='change_orders')
    op.drop_index('ix_change_orders_sla_due_date', table_name='change_orders')

    # Drop foreign key constraint
    op.drop_constraint('fk_change_orders_assigned_approver', 'change_orders', type_='foreignkey')

    # Drop columns
    op.drop_column('change_orders', 'sla_status')
    op.drop_column('change_orders', 'sla_due_date')
    op.drop_column('change_orders', 'sla_assigned_at')
    op.drop_column('change_orders', 'assigned_approver_id')
    op.drop_column('change_orders', 'impact_level')
