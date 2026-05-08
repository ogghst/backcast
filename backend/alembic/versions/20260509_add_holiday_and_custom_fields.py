"""Add holiday_country_code and custom_fields columns.

Revision ID: 20260509_holiday_custom
Revises: 20260509_notifications
Create Date: 2026-05-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "20260509_holiday_custom"
down_revision: str | None = "20260509_notifications"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "co_workflow_config",
        sa.Column(
            "holiday_country_code",
            sa.String(10),
            nullable=True,
            server_default="IT",
        ),
    )
    op.add_column(
        "co_workflow_config",
        sa.Column("custom_fields", JSONB, nullable=True),
    )
    op.add_column(
        "change_orders",
        sa.Column("custom_field_values", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("change_orders", "custom_field_values")
    op.drop_column("co_workflow_config", "custom_fields")
    op.drop_column("co_workflow_config", "holiday_country_code")
