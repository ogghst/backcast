"""Add CO workflow config tables and config_snapshot column.

Revision ID: 20260505_co_workflow_config
Revises: 02a4e8ce7dbb
Create Date: 2026-05-05

Creates:
- co_workflow_config: Parent config table (global + per-project)
- co_impact_level_config: Impact level thresholds
- co_approval_rule_config: Approval authority mapping (5-role)
- co_sla_rule_config: SLA deadlines per impact level
- co_config_audit_log: Config change audit trail

Adds:
- config_snapshot JSONB column on change_orders (nullable)

Seeds:
- Global default config with current hardcoded values
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260505_co_workflow_config"
down_revision: Union[str, Sequence[str], None] = "02a4e8ce7dbb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create CO workflow config tables and seed global defaults."""
    # Create co_workflow_config (parent table)
    op.create_table(
        "co_workflow_config",
        sa.Column("id", postgresql.UUID(), nullable=False),
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
        sa.Column("config_id", postgresql.UUID(), nullable=False),
        sa.Column("project_id", postgresql.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by", postgresql.UUID(), nullable=False),
        sa.Column("updated_by", postgresql.UUID(), nullable=True),
        sa.Column("impact_weights", postgresql.JSONB(), nullable=False),
        sa.Column("score_boundaries", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("config_id"),
        sa.UniqueConstraint("project_id"),
    )
    op.create_index(
        "ix_co_workflow_config_config_id", "co_workflow_config", ["config_id"]
    )
    op.create_index(
        "ix_co_workflow_config_project_id", "co_workflow_config", ["project_id"]
    )

    # Create co_impact_level_config
    op.create_table(
        "co_impact_level_config",
        sa.Column("id", postgresql.UUID(), nullable=False),
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
        sa.Column("config_id", postgresql.UUID(), nullable=False),
        sa.Column("level_name", sa.String(20), nullable=False),
        sa.Column("level_order", sa.Integer(), nullable=False),
        sa.Column(
            "threshold_amount", sa.Numeric(precision=15, scale=2), nullable=False
        ),
        sa.Column(
            "score_threshold_min", sa.Numeric(precision=10, scale=2), nullable=False
        ),
        sa.Column(
            "score_threshold_max", sa.Numeric(precision=10, scale=2), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["config_id"], ["co_workflow_config.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_co_impact_level_config_config_id",
        "co_impact_level_config",
        ["config_id"],
    )

    # Create co_approval_rule_config
    op.create_table(
        "co_approval_rule_config",
        sa.Column("id", postgresql.UUID(), nullable=False),
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
        sa.Column("config_id", postgresql.UUID(), nullable=False),
        sa.Column("impact_level_name", sa.String(20), nullable=False),
        sa.Column("required_authority_level", sa.String(20), nullable=False),
        sa.Column("approver_role", sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["config_id"], ["co_workflow_config.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_co_approval_rule_config_config_id",
        "co_approval_rule_config",
        ["config_id"],
    )

    # Create co_sla_rule_config
    op.create_table(
        "co_sla_rule_config",
        sa.Column("id", postgresql.UUID(), nullable=False),
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
        sa.Column("config_id", postgresql.UUID(), nullable=False),
        sa.Column("impact_level_name", sa.String(20), nullable=False),
        sa.Column("business_days", sa.Integer(), nullable=False),
        sa.Column(
            "escalation_trigger_pct", sa.Numeric(precision=5, scale=2), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["config_id"], ["co_workflow_config.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_co_sla_rule_config_config_id", "co_sla_rule_config", ["config_id"]
    )

    # Create co_config_audit_log
    op.create_table(
        "co_config_audit_log",
        sa.Column("id", postgresql.UUID(), nullable=False),
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
        sa.Column("config_id", postgresql.UUID(), nullable=False),
        sa.Column("changed_by", postgresql.UUID(), nullable=False),
        sa.Column("old_values", postgresql.JSONB(), nullable=True),
        sa.Column("new_values", postgresql.JSONB(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["config_id"], ["co_workflow_config.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_co_config_audit_log_config_id", "co_config_audit_log", ["config_id"]
    )

    # Add config_snapshot column to change_orders
    op.add_column(
        "change_orders",
        sa.Column(
            "config_snapshot",
            postgresql.JSONB(),
            nullable=True,
            comment="Workflow config snapshot at submission time",
        ),
    )

    # Seed global default config using separate execute calls (asyncpg limitation)
    op.execute("""
        INSERT INTO co_workflow_config (id, config_id, project_id, is_active, version, created_by, impact_weights, score_boundaries)
        VALUES (
            gen_random_uuid(),
            gen_random_uuid(),
            NULL,
            true,
            1,
            gen_random_uuid(),
            '{"budget": 0.4, "schedule": 0.3, "revenue": 0.2, "evm": 0.1}'::jsonb,
            '{"LOW": 10, "MEDIUM": 30, "HIGH": 50, "CRITICAL": 999}'::jsonb
        )
    """)

    op.execute("""
        INSERT INTO co_impact_level_config (id, config_id, level_name, level_order, threshold_amount, score_threshold_min, score_threshold_max, is_active)
        SELECT
            gen_random_uuid(),
            cw.id,
            level_name,
            level_order,
            threshold_amount,
            score_min,
            score_max,
            true
        FROM co_workflow_config cw,
        (VALUES
            ('LOW'::varchar, 1, 10000.00, 0.00, 9.99),
            ('MEDIUM'::varchar, 2, 50000.00, 10.00, 29.99),
            ('HIGH'::varchar, 3, 100000.00, 30.00, 49.99),
            ('CRITICAL'::varchar, 4, 999999999.00, 50.00, 999.00)
        ) AS levels(level_name, level_order, threshold_amount, score_min, score_max)
        WHERE cw.project_id IS NULL
    """)

    op.execute("""
        INSERT INTO co_approval_rule_config (id, config_id, impact_level_name, required_authority_level, approver_role)
        SELECT
            gen_random_uuid(),
            cw.id,
            impact_level,
            authority,
            role
        FROM co_workflow_config cw,
        (VALUES
            ('LOW'::varchar, 'LOW'::varchar, 'viewer'::varchar),
            ('MEDIUM'::varchar, 'MEDIUM'::varchar, 'editor_pm'::varchar),
            ('HIGH'::varchar, 'HIGH'::varchar, 'dept_head'::varchar),
            ('HIGH'::varchar, 'HIGH'::varchar, 'director'::varchar),
            ('CRITICAL'::varchar, 'CRITICAL'::varchar, 'admin'::varchar)
        ) AS rules(impact_level, authority, role)
        WHERE cw.project_id IS NULL
    """)

    op.execute("""
        INSERT INTO co_sla_rule_config (id, config_id, impact_level_name, business_days, escalation_trigger_pct)
        SELECT
            gen_random_uuid(),
            cw.id,
            impact_level,
            days,
            NULL
        FROM co_workflow_config cw,
        (VALUES
            ('LOW'::varchar, 2),
            ('MEDIUM'::varchar, 5),
            ('HIGH'::varchar, 10),
            ('CRITICAL'::varchar, 15)
        ) AS sla(impact_level, days)
        WHERE cw.project_id IS NULL
    """)


def downgrade() -> None:
    """Remove CO workflow config tables and config_snapshot column."""
    op.drop_column("change_orders", "config_snapshot")
    op.drop_table("co_config_audit_log")
    op.drop_table("co_sla_rule_config")
    op.drop_table("co_approval_rule_config")
    op.drop_table("co_impact_level_config")
    op.drop_table("co_workflow_config")
