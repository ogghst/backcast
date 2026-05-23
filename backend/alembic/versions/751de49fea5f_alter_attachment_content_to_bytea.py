"""alter_attachment_content_to_bytea

Revision ID: 751de49fea5f
Revises: b958ab350c70
Create Date: 2026-05-23 09:39:31.242232

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '751de49fea5f'
down_revision: Union[str, Sequence[str], None] = 'b958ab350c70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change attachment content column from TEXT to BYTEA for efficient binary storage."""
    op.execute(
        "ALTER TABLE cost_registration_attachments "
        "ALTER COLUMN content TYPE BYTEA USING content::bytea"
    )


def downgrade() -> None:
    """Revert BYTEA back to TEXT."""
    op.execute(
        "ALTER TABLE cost_registration_attachments "
        "ALTER COLUMN content TYPE TEXT USING content::text"
    )
