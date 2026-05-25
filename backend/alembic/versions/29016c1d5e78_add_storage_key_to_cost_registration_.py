"""add_storage_key_to_cost_registration_attachments

Revision ID: 29016c1d5e78
Revises: ce3a584f24f5
Create Date: 2026-05-25 18:08:48.179544

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29016c1d5e78'
down_revision: Union[str, Sequence[str], None] = 'ce3a584f24f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add storage_key column for S3/RustFS migration."""
    op.add_column(
        "cost_registration_attachments",
        sa.Column("storage_key", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    """Remove storage_key column."""
    op.drop_column("cost_registration_attachments", "storage_key")
