"""add max_supervisor_iterations to ai_assistant_configs

Revision ID: cf2b0f1ece1f
Revises: bc147fc0eb64
Create Date: 2026-06-11 23:58:07.096874

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf2b0f1ece1f'
down_revision: Union[str, Sequence[str], None] = 'bc147fc0eb64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('ai_assistant_configs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('max_supervisor_iterations', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('ai_assistant_configs', schema=None) as batch_op:
        batch_op.drop_column('max_supervisor_iterations')
