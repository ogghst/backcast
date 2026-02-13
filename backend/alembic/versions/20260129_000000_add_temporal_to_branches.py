"""add temporal to branches

Revision ID: 20260129_000000
Revises: 20260118_100000
Create Date: 2026-01-29 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260129_000000"
down_revision: str | None = "f69c57fcc47d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    # Add branch_id
    op.add_column('branches', sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=True)) # Nullable first to populate

    # Populate branch_id
    op.execute("UPDATE branches SET branch_id = gen_random_uuid()")

    # Make branch_id non-nullable
    op.alter_column('branches', 'branch_id', nullable=False)

    # Create index
    op.create_index(op.f('ix_branches_branch_id'), 'branches', ['branch_id'], unique=False)

    # Add valid_time
    op.add_column('branches', sa.Column('valid_time', postgresql.TSTZRANGE(), server_default=sa.text("tstzrange(now(), NULL, '[]')"), nullable=False))

    # Add transaction_time
    op.add_column('branches', sa.Column('transaction_time', postgresql.TSTZRANGE(), server_default=sa.text("tstzrange(now(), NULL, '[]')"), nullable=False))

    # Add deleted_by (required by VersionableMixin)
    op.add_column('branches', sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True))

    # Drop created_at
    op.drop_column('branches', 'created_at')

def downgrade() -> None:
    # Add created_at back
    op.add_column('branches', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

    # Drop temporal columns
    op.drop_column('branches', 'deleted_by')
    op.drop_column('branches', 'transaction_time')
    op.drop_column('branches', 'valid_time')

    # Drop branch_id
    op.drop_index(op.f('ix_branches_branch_id'), table_name='branches')
    op.drop_column('branches', 'branch_id')
