"""add_package_types_table

Revision ID: 99e3a2d414dd
Revises: 751de49fea5f
Create Date: 2026-05-24 01:29:48.127174

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '99e3a2d414dd'
down_revision: Union[str, Sequence[str], None] = '751de49fea5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add package_types table for configurable work package categories."""
    op.create_table(
        'package_types',
        sa.Column('package_type_id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('color', sa.String(length=30), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column(
            'valid_time',
            postgresql.TSTZRANGE(),
            server_default=sa.text("tstzrange(now(), NULL, '[]')"),
            nullable=False,
        ),
        sa.Column(
            'transaction_time',
            postgresql.TSTZRANGE(),
            server_default=sa.text("tstzrange(now(), NULL, '[]')"),
            nullable=False,
        ),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('deleted_by', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_package_types_code'), 'package_types', ['code'], unique=False
    )
    op.create_index(
        op.f('ix_package_types_created_by'),
        'package_types',
        ['created_by'],
        unique=False,
    )
    op.create_index(
        op.f('ix_package_types_package_type_id'),
        'package_types',
        ['package_type_id'],
        unique=False,
    )


def downgrade() -> None:
    """Remove package_types table."""
    op.drop_index(
        op.f('ix_package_types_package_type_id'), table_name='package_types'
    )
    op.drop_index(op.f('ix_package_types_created_by'), table_name='package_types')
    op.drop_index(op.f('ix_package_types_code'), table_name='package_types')
    op.drop_table('package_types')
