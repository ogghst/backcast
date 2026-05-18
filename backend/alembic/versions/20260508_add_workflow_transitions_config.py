"""Add workflow_transitions JSONB column to co_workflow_config.

Revision ID: 20260508_workflow_transitions
Revises: 20260505_co_workflow_config
Create Date: 2026-05-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260508_workflow_transitions"
down_revision: str = "20260505_co_workflow_config"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "co_workflow_config",
        sa.Column("workflow_transitions", JSONB, nullable=True),
    )

    op.execute("""
        UPDATE co_workflow_config
        SET workflow_transitions = '{
            "transitions": {
                "draft": ["submitted_for_approval"],
                "submitted_for_approval": ["under_review", "approved", "rejected"],
                "under_review": ["approved", "rejected"],
                "rejected": ["draft", "submitted_for_approval"],
                "approved": ["implemented"],
                "implemented": []
            },
            "lock_transitions": [["draft", "submitted_for_approval"]],
            "unlock_transitions": [["under_review", "rejected"]],
            "editable_statuses": ["draft", "rejected"]
        }'::jsonb
        WHERE project_id IS NULL;
    """)


def downgrade() -> None:
    op.drop_column("co_workflow_config", "workflow_transitions")
