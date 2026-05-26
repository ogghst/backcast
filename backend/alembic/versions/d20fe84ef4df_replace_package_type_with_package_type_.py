"""replace_package_type_with_package_type_id

Revision ID: d20fe84ef4df
Revises: 03d8f0ff0080
Create Date: 2026-05-26 20:13:32.519458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd20fe84ef4df'
down_revision: Union[str, Sequence[str], None] = '03d8f0ff0080'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace package_type string column with package_type_id UUID reference."""
    # Step 1: Add nullable package_type_id column
    op.add_column(
        "work_packages",
        sa.Column("package_type_id", sa.UUID(), nullable=True),
    )

    # Step 2: Populate from join with package_types (match any version — root ID is stable)
    op.execute(
        """
        UPDATE work_packages wp
        SET package_type_id = pt.package_type_id
        FROM (
            SELECT DISTINCT ON (code) code, package_type_id
            FROM package_types
            ORDER BY code, lower(transaction_time) DESC
        ) pt
        WHERE lower(wp.package_type) = lower(pt.code)
        """
    )

    # Step 3: Alter to NOT NULL
    op.alter_column("work_packages", "package_type_id", nullable=False)

    # Step 4: Create index
    op.create_index(
        op.f("ix_work_packages_package_type_id"),
        "work_packages",
        ["package_type_id"],
    )

    # Step 5: Drop old column
    op.drop_column("work_packages", "package_type")


def downgrade() -> None:
    """Restore package_type string column from package_type_id reference."""
    # Step 1: Re-add package_type column as nullable
    op.add_column(
        "work_packages",
        sa.Column("package_type", sa.String(50), nullable=True),
    )

    # Step 2: Populate from join with package_types
    op.execute(
        """
        UPDATE work_packages wp
        SET package_type = pt.code
        FROM package_types pt
        WHERE wp.package_type_id = pt.package_type_id
          AND upper(pt.valid_time) IS NULL AND pt.deleted_at IS NULL
        """
    )

    # Step 3: Alter to NOT NULL
    op.alter_column("work_packages", "package_type", nullable=False)

    # Step 4: Drop package_type_id index and column
    op.drop_index(op.f("ix_work_packages_package_type_id"), table_name="work_packages")
    op.drop_column("work_packages", "package_type_id")
