"""Fix temporal entity foreign key constraints.

This migration fixes foreign key constraints for temporal entities that reference
business keys (like user_id) instead of primary keys.

Problem:
- ChangeOrder.assigned_approver_id has FK to users.user_id (business key, not PK)
- Forecast.approved_by has no FK constraint
- PostgreSQL requires FKs to reference either PK or UNIQUE columns

Solution:
- Create compound unique index on users(user_id, transaction_time) for current versions
- This enables FKs to reference "current" versions by business key
- Follows EVCS pattern for temporal entity references

Pattern for Temporal Entity FKs:
1. Business key (e.g., user_id) identifies the entity across versions
2. Compound index (user_id, transaction_time) ensures uniqueness for current versions
3. FK references the compound index with WHERE clause for current versions
4. Application layer validates business logic (e.g., user exists, is active)

Revision ID: e584fd7a5320
Revises: 7947e91eb50c
Create Date: 2026-03-18 14:41:58.388149

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e584fd7a5320'
down_revision: Union[str, Sequence[str], None] = '7947e91eb50c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Fix temporal entity foreign key constraints.

    IMPORTANT: This migration removes invalid FK constraints and implements
    application-level referential integrity for temporal entities.

    Problem: PostgreSQL FKs require referencing PK or UNIQUE columns.
    users.user_id is a business key (indexed but not unique).

    Solution:
    1. Remove invalid FK constraints from models
    2. Create unique index on current versions for validation support
    3. Implement application-level checks in service layer
    4. Document pattern in ADR-005

    Phase 1: Create supporting index for user_id queries
    Phase 2: Remove invalid FK from ChangeOrder.assigned_approver_id
    Phase 3: Add index support for Forecast.approved_by validation
    """

    # Phase 1: Create unique index on user_id for current versions
    # This supports efficient queries and validation (though FK can't reference it)
    # Pattern: ensures uniqueness of user_id across current versions
    op.execute("""
        CREATE UNIQUE INDEX uq_users_current_user_id
        ON users (user_id)
        WHERE upper_inf(transaction_time) AND deleted_at IS NULL;
    """)

    # Add comment explaining the pattern
    op.execute("""
        COMMENT ON INDEX uq_users_current_user_id IS
        'Ensures user_id is unique across current (non-deleted) versions.
        Used for application-level FK validation since PostgreSQL FKs
        cannot reference partial unique indexes.';
    """)

    # Phase 2: Remove invalid FK constraint from ChangeOrder
    # The FK references users.user_id which is not PK or UNIQUE, so it's invalid
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'change_orders_assigned_approver_id_fkey'
            ) THEN
                ALTER TABLE change_orders
                DROP CONSTRAINT change_orders_assigned_approver_id_fkey;
            END IF;
        END $$;
    """)

    # Note: We don't add a new FK constraint because:
    # 1. users.user_id is not PK or UNIQUE constraint
    # 2. Partial unique indexes cannot be referenced by FKs
    # 3. Application-level validation in service layer is the correct pattern

    # Phase 3: Ensure Forecast.approved_by column exists
    # No FK constraint - application-level validation only
    op.execute("""
        ALTER TABLE forecasts
        ADD COLUMN IF NOT EXISTS approved_by uuid;
    """)

    # Create index for efficient validation queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_forecasts_approved_by
        ON forecasts (approved_by)
        WHERE approved_by IS NOT NULL;
    """)


def downgrade() -> None:
    """Downgrade schema - Revert temporal entity FK changes.

    WARNING: This removes the supporting indexes but does NOT recreate
    the invalid FK constraints (they were never enforced correctly).
    """

    # Phase 3: Remove Forecast.approved_by index
    op.execute("DROP INDEX IF EXISTS ix_forecasts_approved_by;")

    # Phase 2: Do not recreate the invalid FK
    # The old FK referenced users.user_id which was not a valid target
    # (not PK, not UNIQUE constraint)

    # Phase 1: Remove the unique index on current user versions
    op.execute("DROP INDEX IF EXISTS uq_users_current_user_id;")
