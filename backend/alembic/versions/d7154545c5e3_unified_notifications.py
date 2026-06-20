"""unified notifications

Revision ID: d7154545c5e3
Revises: 19f52d1c0418
Create Date: 2026-06-19 21:30:48.873915

Adds the three tables backing the unified notification system
(``telegram_accounts``, ``user_notification_preferences``,
``notification_deliveries``) and extends ``notifications`` with actor,
severity, project, and idempotency columns plus a partial unique index for
per-user dedup.

NOTE: autogenerate also emitted a spurious drop/recreate of
``schedule_dependencies`` (pre-existing DB/model index drift unrelated to this
change). Those operations were removed to keep the migration surgical.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7154545c5e3"
down_revision: Union[str, Sequence[str], None] = "19f52d1c0418"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- New table: telegram_accounts (per-user Telegram linkage) ---
    op.create_table(
        "telegram_accounts",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=False),
        sa.Column("telegram_user_id", sa.String(length=64), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("link_token", sa.String(length=64), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("telegram_accounts", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_telegram_accounts_link_token"),
            ["link_token"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_telegram_accounts_user_id"),
            ["user_id"],
            unique=True,
        )

    # --- New table: user_notification_preferences ---
    op.create_table(
        "user_notification_preferences",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "event_type",
            "channel",
            name="uq_notif_pref_user_type_channel",
        ),
    )
    with op.batch_alter_table(
        "user_notification_preferences", schema=None
    ) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_user_notification_preferences_user_id"),
            ["user_id"],
            unique=False,
        )

    # --- New table: notification_deliveries ---
    op.create_table(
        "notification_deliveries",
        sa.Column("notification_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("notification_deliveries", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_notification_deliveries_notification_id"),
            ["notification_id"],
            unique=False,
        )

    # --- Extend notifications with actor/severity/project/idempotency ---
    # Widen event_type from VARCHAR(50) to VARCHAR(64) to hold dotted codes
    # (e.g. 'agent.approval_req'). Not auto-detected because compare_type=False.
    op.alter_column(
        "notifications",
        "event_type",
        existing_type=sa.String(length=50),
        type_=sa.String(length=64),
        existing_nullable=False,
    )

    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("actor_type", sa.String(length=16), nullable=True)
        )
        batch_op.add_column(sa.Column("actor_id", sa.UUID(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "severity",
                sa.String(length=16),
                nullable=False,
                server_default="info",
            )
        )
        batch_op.add_column(sa.Column("project_id", sa.UUID(), nullable=True))
        batch_op.add_column(
            sa.Column("idempotency_key", sa.String(length=128), nullable=True)
        )
        batch_op.create_index(
            batch_op.f("ix_notifications_idempotency_key"),
            ["idempotency_key"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_notifications_project_id"),
            ["project_id"],
            unique=False,
        )
        batch_op.create_index(
            "ux_notifications_idempotency",
            ["user_id", "idempotency_key"],
            unique=True,
            postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        )


def downgrade() -> None:
    """Downgrade schema (removes unified-notification additions)."""
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.drop_index(
            "ux_notifications_idempotency",
            postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        )
        batch_op.drop_index(batch_op.f("ix_notifications_project_id"))
        batch_op.drop_index(batch_op.f("ix_notifications_idempotency_key"))
        batch_op.drop_column("idempotency_key")
        batch_op.drop_column("project_id")
        batch_op.drop_column("severity")
        batch_op.drop_column("actor_id")
        batch_op.drop_column("actor_type")

    # Narrow event_type back to VARCHAR(50).
    op.alter_column(
        "notifications",
        "event_type",
        existing_type=sa.String(length=64),
        type_=sa.String(length=50),
        existing_nullable=False,
    )

    with op.batch_alter_table("notification_deliveries", schema=None) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_notification_deliveries_notification_id")
        )
    op.drop_table("notification_deliveries")

    with op.batch_alter_table(
        "user_notification_preferences", schema=None
    ) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_user_notification_preferences_user_id")
        )
    op.drop_table("user_notification_preferences")

    with op.batch_alter_table("telegram_accounts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_telegram_accounts_user_id"))
        batch_op.drop_index(batch_op.f("ix_telegram_accounts_link_token"))
    op.drop_table("telegram_accounts")
