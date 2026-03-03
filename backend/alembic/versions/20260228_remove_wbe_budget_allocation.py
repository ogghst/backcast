"""Remove budget_allocation from WBEs, migrate to cost elements.

This migration removes the budget_allocation column from the wbes table
as part of the single source of truth initiative. Budgets now exist only
in CostElement.budget_amount and are computed on-the-fly for WBEs.

Revision ID: 20260228_rm_wbe_budget
Revises: b7c8d9e0f1a2
Create Date: 2026-02-28

Data Migration Strategy:
1. For each WBE with budget_allocation > 0, create a default "Budget Transfer" cost element
2. Copy budget_allocation value to the cost element's budget_amount
3. Drop the budget_allocation column

Rollback Strategy:
1. Re-add budget_allocation column
2. Sum cost element budgets back to WBEs (for "Budget Transfer" cost elements only)
3. Remove the "Budget Transfer" cost elements
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260228_rm_wbe_budget"
down_revision: str | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Constants for the migration
BUDGET_TRANSFER_COST_ELEMENT_TYPE_CODE = "BUDGET-TRANSFER"
BUDGET_TRANSFER_COST_ELEMENT_TYPE_NAME = "Budget Transfer"
BUDGET_TRANSFER_COST_ELEMENT_CODE = "BUDGET-001"
BUDGET_TRANSFER_COST_ELEMENT_NAME = "Migrated Budget"


def upgrade() -> None:
    """Migrate WBE budgets to cost elements, then remove budget_allocation column."""
    conn = op.get_bind()

    # Step 0: Check if we have the minimum required data (departments and users)
    # If not, just drop the budget_allocation column without data migration
    # This happens in fresh test databases
    result = conn.execute(
        text("""
            SELECT
                (SELECT COUNT(*) FROM departments) as dept_count,
                (SELECT COUNT(*) FROM users) as user_count
        """)
    )
    row = result.fetchone()
    if not row or row[0] == 0 or row[1] == 0:
        # No departments or users - just drop the column
        op.drop_column("wbes", "budget_allocation")
        return

    # Step 1: Ensure a "Budget Transfer" cost element type exists
    # This will be used for all migrated budgets
    # NOTE: cost_element_types is NOT branchable, so no branch column
    # Use CAST to avoid asyncpg parameter type ambiguity
    conn.execute(
        text("""
            INSERT INTO cost_element_types (
                id, cost_element_type_id, code, name, department_id,
                description, created_by, valid_time, transaction_time
            )
            SELECT
                gen_random_uuid(),
                gen_random_uuid(),
                CAST(:code AS VARCHAR(50)),
                CAST(:name AS VARCHAR(255)),
                (SELECT department_id FROM departments LIMIT 1),
                'Cost element type for budgets migrated from WBE budget_allocation field',
                (SELECT user_id FROM users LIMIT 1),
                tstzrange(CURRENT_TIMESTAMP, NULL),
                tstzrange(CURRENT_TIMESTAMP, NULL)
            WHERE NOT EXISTS (
                SELECT 1 FROM cost_element_types WHERE code = CAST(:code AS VARCHAR(50))
            )
        """),
        {
            "code": BUDGET_TRANSFER_COST_ELEMENT_TYPE_CODE,
            "name": BUDGET_TRANSFER_COST_ELEMENT_TYPE_NAME,
        },
    )

    # Get the cost element type ID for budget transfers
    result = conn.execute(
        text("""
            SELECT cost_element_type_id FROM cost_element_types
            WHERE code = :code
            AND upper(valid_time) IS NULL
            AND deleted_at IS NULL
            LIMIT 1
        """),
        {"code": BUDGET_TRANSFER_COST_ELEMENT_TYPE_CODE},
    )
    cost_element_type_row = result.fetchone()
    if not cost_element_type_row:
        # If no cost element type was created (e.g., no departments or users),
        # we cannot proceed with data migration. Just drop the column.
        op.drop_column("wbes", "budget_allocation")
        return

    cost_element_type_id = cost_element_type_row[0]

    # Step 2: Create "Budget Transfer" cost elements for each WBE with budget_allocation > 0
    # This preserves the budget data in the new structure
    conn.execute(
        text("""
            INSERT INTO cost_elements (
                id, cost_element_id, wbe_id, cost_element_type_id,
                code, name, budget_amount, description,
                created_by, branch, valid_time, transaction_time
            )
            SELECT
                gen_random_uuid(),
                gen_random_uuid(),
                w.wbe_id,
                :cost_element_type_id,
                :ce_code,
                :ce_name || ' - ' || w.code,
                w.budget_allocation,
                'Budget migrated from WBE budget_allocation during schema refactoring',
                w.created_by,
                w.branch,
                w.valid_time,
                tstzrange(CURRENT_TIMESTAMP, NULL)
            FROM wbes w
            WHERE w.budget_allocation > 0
            AND upper(w.valid_time) IS NULL
            AND w.deleted_at IS NULL
        """),
        {
            "cost_element_type_id": str(cost_element_type_id),
            "ce_code": BUDGET_TRANSFER_COST_ELEMENT_CODE,
            "ce_name": BUDGET_TRANSFER_COST_ELEMENT_NAME,
        },
    )

    # Step 3: Drop the budget_allocation column from wbes table
    op.drop_column("wbes", "budget_allocation")


def downgrade() -> None:
    """Restore budget_allocation column and migrate data back from cost elements."""
    # Step 1: Re-add the budget_allocation column
    op.add_column(
        "wbes",
        sa.Column(
            "budget_allocation",
            postgresql.NUMERIC(precision=15, scale=2),
            nullable=False,
            server_default="0",
            comment="Budget allocated to this WBE",
        ),
    )

    conn = op.get_bind()

    # Step 2: Restore budgets from "Budget Transfer" cost elements
    conn.execute(
        text("""
            UPDATE wbes w
            SET budget_allocation = COALESCE(
                (
                    SELECT SUM(ce.budget_amount)
                    FROM cost_elements ce
                    JOIN cost_element_types cet ON ce.cost_element_type_id = cet.cost_element_type_id
                    WHERE ce.wbe_id = w.wbe_id
                    AND ce.branch = w.branch
                    AND upper(ce.valid_time) IS NULL
                    AND ce.deleted_at IS NULL
                    AND cet.code = :cet_code
                    AND ce.code = :ce_code
                ),
                0
            )
            WHERE upper(w.valid_time) IS NULL
            AND w.deleted_at IS NULL
        """),
        {
            "cet_code": BUDGET_TRANSFER_COST_ELEMENT_TYPE_CODE,
            "ce_code": BUDGET_TRANSFER_COST_ELEMENT_CODE,
        },
    )

    # Step 3: Remove the "Budget Transfer" cost elements (cleanup)
    conn.execute(
        text("""
            DELETE FROM cost_elements ce
            USING cost_element_types cet
            WHERE ce.cost_element_type_id = cet.cost_element_type_id
            AND cet.code = :cet_code
            AND ce.code = :ce_code
        """),
        {
            "cet_code": BUDGET_TRANSFER_COST_ELEMENT_TYPE_CODE,
            "ce_code": BUDGET_TRANSFER_COST_ELEMENT_CODE,
        },
    )

    # Note: We don't remove the cost element type as it may be used elsewhere
    # and keeping it doesn't cause issues
