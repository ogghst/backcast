"""Add cost_element_types table

Revision ID: a1b2c3d4e5f6
Revises: f159e127bad9
Create Date: 2026-01-06 19:25:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "4af275505a7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create cost_element_types table."""
    # Create cost_element_types table
    # NOTE: No FK constraint on department_id because in a bitemporal system,
    # department_id is a root ID that appears in multiple rows (versions).
    # FK constraints require UNIQUE, which root IDs cannot have.
    # Referential integrity is enforced at the application level.
    op.execute(
        """
        CREATE TABLE cost_element_types (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cost_element_type_id UUID NOT NULL,
            department_id UUID NOT NULL,
            code VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            
            -- Versioning columns (from VersionableMixin)
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID
        );
        """
    )

    # Create indexes
    op.execute(
        "CREATE INDEX ix_cost_element_types_cost_element_type_id "
        "ON cost_element_types(cost_element_type_id);"
    )
    op.execute(
        "CREATE INDEX ix_cost_element_types_department_id "
        "ON cost_element_types(department_id);"
    )
    op.execute("CREATE INDEX ix_cost_element_types_code ON cost_element_types(code);")

    # Create temporal indexes
    op.execute(
        "CREATE INDEX ix_cost_element_types_valid_time "
        "ON cost_element_types USING GIST (valid_time);"
    )
    op.execute(
        "CREATE INDEX ix_cost_element_types_transaction_time "
        "ON cost_element_types USING GIST (transaction_time);"
    )

    # NOTE: EXCLUDE constraint for version overlap is not added here
    # to match existing entity patterns (departments, projects, wbes).
    # Version overlap prevention is handled at the application level via Commands.


def downgrade() -> None:
    """Drop cost_element_types table."""
    op.execute("DROP TABLE IF EXISTS cost_element_types CASCADE;")
