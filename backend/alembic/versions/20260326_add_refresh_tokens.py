"""Add refresh_tokens table.

Revision ID: 20260326_add_refresh_tokens
Revises: 20260326_fix_temporal_ids
Create Date: 2026-03-26 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260326_add_refresh_tokens'
down_revision: Union[str, Sequence[str], None] = '20260326_fix_temporal_ids'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add refresh_tokens table.

    Note: user_id references users.id (PK), not users.user_id (root entity).
    This is because user_id is not unique in the users table (multiple versions
    per user). In the service layer, we'll join with users to filter by user_id.
    """
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
        sa.Column('user_id', postgresql.UUID(), autoincrement=False, nullable=False, comment='References users.id (version-specific PK)'),
        sa.Column('user_root_id', postgresql.UUID(), autoincrement=False, nullable=False, comment='Root user_id for querying across versions'),
        sa.Column('token_hash', sa.String(length=255), autoincrement=False, nullable=False),
        sa.Column('expires_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
        sa.Column('revoked_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_refresh_tokens_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_refresh_tokens'),
        sa.UniqueConstraint('token_hash', name='uq_refresh_token_hash'),
    )
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_user_root_id'), 'refresh_tokens', ['user_root_id'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_expires_at'), 'refresh_tokens', ['expires_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema - remove refresh_tokens table."""
    op.drop_index(op.f('ix_refresh_tokens_expires_at'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_user_root_id'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')


def downgrade() -> None:
    """Downgrade schema - remove refresh_tokens table."""
    op.drop_index(op.f('ix_refresh_tokens_expires_at'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
