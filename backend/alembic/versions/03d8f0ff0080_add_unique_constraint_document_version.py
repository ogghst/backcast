"""add_unique_constraint_document_version

Revision ID: 03d8f0ff0080
Revises: 29016c1d5e78
Create Date: 2026-05-25 19:40:46.643559

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '03d8f0ff0080'
down_revision: Union[str, Sequence[str], None] = '29016c1d5e78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique constraint on (document_id, version_number)."""
    op.create_unique_constraint(
        'uq_document_versions_document_id_version_number',
        'document_versions',
        ['document_id', 'version_number'],
    )


def downgrade() -> None:
    """Remove unique constraint on (document_id, version_number)."""
    op.drop_constraint(
        'uq_document_versions_document_id_version_number',
        'document_versions',
        type_='unique',
    )
