"""Merge session context and temporal FK fixes

Revision ID: 1fd0ec9f01a4
Revises: 20260320_phase3e_session_context, e584fd7a5320
Create Date: 2026-03-20 23:15:01.433797

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '1fd0ec9f01a4'
down_revision: str | Sequence[str] | None = ('20260320_phase3e_session_context', 'e584fd7a5320')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
