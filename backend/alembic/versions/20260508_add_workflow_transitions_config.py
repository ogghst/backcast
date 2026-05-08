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
                "Draft": ["Submitted for Approval"],
                "Submitted for Approval": ["Under Review", "Approved", "Rejected"],
                "Under Review": ["Approved", "Rejected"],
                "Rejected": ["Draft", "Submitted for Approval"],
                "Approved": ["Implemented"],
                "Implemented": []
            },
            "lock_transitions": [["Draft", "Submitted for Approval"]],
            "unlock_transitions": [["Under Review", "Rejected"]],
            "editable_statuses": ["Draft", "Rejected"]
        }'::jsonb
        WHERE project_id IS NULL;
    """)


def downgrade() -> None:
    op.drop_column("co_workflow_config", "workflow_transitions")
