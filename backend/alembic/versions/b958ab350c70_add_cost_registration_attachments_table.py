"""add_cost_registration_attachments_table

Revision ID: b958ab350c70
Revises: 9770cd03bd49
Create Date: 2026-05-23 07:21:41.924861

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b958ab350c70'
down_revision: Union[str, Sequence[str], None] = '9770cd03bd49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cost_registration_attachments table for file attachments on cost registrations."""
    op.create_table(
        'cost_registration_attachments',
        sa.Column('cost_registration_id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('content', sa.LargeBinary(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_cost_registration_attachments_cost_registration_id'),
        'cost_registration_attachments',
        ['cost_registration_id'],
        unique=False,
    )


def downgrade() -> None:
    """Remove cost_registration_attachments table."""
    op.drop_index(
        op.f('ix_cost_registration_attachments_cost_registration_id'),
        table_name='cost_registration_attachments',
    )
    op.drop_table('cost_registration_attachments')
