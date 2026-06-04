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
    Idempotent: skip if column is already TEXT.
    """
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'mcp_servers' AND column_name = 'config'"
        )
    )
    data_type = result.scalar()
    if data_type and data_type.lower() != "text":
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
