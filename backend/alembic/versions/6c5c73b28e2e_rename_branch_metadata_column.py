"""rename_branch_metadata_column

Revision ID: 6c5c73b28e2e
Revises: 498e23573534
Create Date: 2026-01-29 22:51:58.253822

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6c5c73b28e2e'
down_revision: Union[str, Sequence[str], None] = '498e23573534'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename metadata column to branch_metadata_info
    op.alter_column('branches', 'metadata', new_column_name='branch_metadata_info')


def downgrade() -> None:
    # Rename back to metadata
    op.alter_column('branches', 'branch_metadata_info', new_column_name='metadata')
