"""fix notification user_id to reference root user_id instead of PK

Revision ID: 20260509_fix_notification_fk
Revises: 286db0b842be
Create Date: 2026-05-09

This migration fixes the notification.user_id column to reference the root
user_id instead of the primary key. For versioned entities, foreign key
constraints at the database level are problematic because:

1. The root user_id is not the primary key
2. There's only a partial unique index on current versions
3. PostgreSQL FK constraints require a unique constraint on the referenced column

The solution is to:
1. Update notification records to use root user_id values
2. Remove the FK constraint (application-level validation instead)
3. Keep the index for query performance

The User model is versioned with bitemporal tracking:
- users.id: Primary key, changes with each version
- users.user_id: Root entity identifier, stable across all versions

Notifications should reference the root user_id to maintain referential
integrity across user versions, validated at the application layer.

Changes:
1. Drop FK constraint (not suitable for versioned entities)
2. Update existing notification records: Map user_id from PK to root ID
3. Keep index on notifications.user_id for query performance
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260509_fix_notification_fk"
down_revision: str | Sequence[str] | None = "286db0b842be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Steps:
    1. Drop FK constraint (not suitable for versioned entities)
    2. Update existing notification records: Map user_id from PK to root ID
    3. Keep index on notifications.user_id for query performance
    """
    # Step 1: Drop foreign key constraint using IF EXISTS to avoid
    # transaction abort when the constraint has already been dropped
    op.execute("""
        ALTER TABLE notifications
        DROP CONSTRAINT IF EXISTS fk_notifications_user_id
    """)

    # Step 2: Update existing notification records
    # Map from PK values to root ID values
    op.execute("""
        UPDATE notifications n
        SET user_id = u.user_id
        FROM users u
        WHERE n.user_id = u.id
    """)

    # Step 3: Ensure index exists (should already exist from table creation)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_notifications_user_id
        ON notifications (user_id)
    """)


def downgrade() -> None:
    """Downgrade schema.

    WARNING: This is a destructive operation. The data migration from
    root user_id back to PK values is lossy and should not be run in
    production. Use a database backup instead.
    """
    # Update notification records back to PK values (best effort)
    # This is lossy since multiple users may share the same root user_id
    op.execute("""
        UPDATE notifications n
        SET user_id = u.id
        FROM users u
        WHERE n.user_id = u.user_id
    """)

    # Recreate the FK constraint (for rollback only)
    op.create_foreign_key(
        "fk_notifications_user_id",
        "notifications",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
