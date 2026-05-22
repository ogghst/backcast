"""migrate_coq_to_four_categories

Revision ID: 9770cd03bd49
Revises: a0b1c2d3e4f5
Create Date: 2026-05-21 23:12:54.884127

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9770cd03bd49'
down_revision: Union[str, Sequence[str], None] = 'a0b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate COQ categories from 2-category to 4-category model."""
    # 1. Widen column to fit longer category names
    op.alter_column(
        'work_packages', 'coq_category',
        existing_type=sa.String(20),
        type_=sa.String(30),
        existing_nullable=True,
    )

    # 2. Migrate data: old categories to new
    op.execute(
        "UPDATE work_packages SET coq_category = 'internal_failure' "
        "WHERE coq_category = 'nonconformance'"
    )
    op.execute(
        "UPDATE work_packages SET coq_category = 'appraisal' "
        "WHERE coq_category = 'conformance'"
    )


def downgrade() -> None:
    """Revert COQ categories from 4-category back to 2-category model."""
    # 1. Collapse 4-category data back to 2-category
    op.execute(
        "UPDATE work_packages SET coq_category = 'conformance' "
        "WHERE coq_category IN ('prevention', 'appraisal')"
    )
    op.execute(
        "UPDATE work_packages SET coq_category = 'nonconformance' "
        "WHERE coq_category IN ('internal_failure', 'external_failure')"
    )

    # 2. Shrink column back
    op.alter_column(
        'work_packages', 'coq_category',
        existing_type=sa.String(30),
        type_=sa.String(20),
        existing_nullable=True,
    )
