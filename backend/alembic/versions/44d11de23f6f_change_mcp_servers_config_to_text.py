"""change_mcp_servers_config_to_text

Revision ID: 44d11de23f6f
Revises: 0174adcb05ff
Create Date: 2026-06-03 15:26:55.183396

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '44d11de23f6f'
down_revision: Union[str, Sequence[str], None] = '0174adcb05ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change mcp_servers.config from JSONB to TEXT.

    Existing data is truncated — reseed will populate with encrypted blobs.
    """
    op.execute("TRUNCATE TABLE mcp_servers")
    op.alter_column(
        "mcp_servers",
        "config",
        existing_type=JSONB,
        type_=sa.Text,
        existing_nullable=False,
    )


def downgrade() -> None:
    """Revert mcp_servers.config back to JSONB."""
    op.execute("TRUNCATE TABLE mcp_servers")
    op.alter_column(
        "mcp_servers",
        "config",
        existing_type=sa.Text,
        type_=JSONB,
        existing_nullable=False,
    )
