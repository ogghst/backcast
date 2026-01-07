"""Add cost_elements table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-06 19:26:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create cost_elements table."""
    # Create cost_elements table
    # NOTE: No FK constraints on wbe_id or cost_element_type_id because in a
    # bitemporal system, these are root IDs that appear in multiple rows (versions).
    # FK constraints require UNIQUE, which root IDs cannot have.
    # Referential integrity is enforced at the application level.
    op.execute(
        """
        CREATE TABLE cost_elements (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cost_element_id UUID NOT NULL,
            wbe_id UUID NOT NULL,
            cost_element_type_id UUID NOT NULL,
            code VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            budget_amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
            description TEXT,
            
            -- Versioning columns (from VersionableMixin)
            valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(now(), NULL, '[]'),
            deleted_at TIMESTAMPTZ,
            created_by UUID NOT NULL,
            deleted_by UUID,
            
            -- Branching columns (from BranchableMixin)
            branch VARCHAR(255) NOT NULL DEFAULT 'main',
            parent_id UUID,
            merge_from_branch VARCHAR(255)
        );
        """
    )

    # Create indexes
    op.execute(
        "CREATE INDEX ix_cost_elements_cost_element_id "
        "ON cost_elements(cost_element_id);"
    )
    op.execute("CREATE INDEX ix_cost_elements_wbe_id ON cost_elements(wbe_id);")
    op.execute(
        "CREATE INDEX ix_cost_elements_cost_element_type_id "
        "ON cost_elements(cost_element_type_id);"
    )
    op.execute("CREATE INDEX ix_cost_elements_code ON cost_elements(code);")
    op.execute("CREATE INDEX ix_cost_elements_branch ON cost_elements(branch);")

    # Create temporal indexes
    op.execute(
        "CREATE INDEX ix_cost_elements_valid_time "
        "ON cost_elements USING GIST (valid_time);"
    )
    op.execute(
        "CREATE INDEX ix_cost_elements_transaction_time "
        "ON cost_elements USING GIST (transaction_time);"
    )

    # NOTE: EXCLUDE constraint for version overlap is not added here
    # to match existing entity patterns (departments, projects, wbes).
    # Version overlap prevention is handled at the application level via Commands.


def downgrade() -> None:
    """Drop cost_elements table."""
    op.execute("DROP TABLE IF EXISTS cost_elements CASCADE;")
