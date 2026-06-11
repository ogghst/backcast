"""remove_mcp_specialist

Revision ID: 7e61a160474b
Revises: 0001_baseline
Create Date: 2026-06-03 00:02:15.926181

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e61a160474b"
down_revision: str | Sequence[str] | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove mcp_specialist specialist and clean up delegation config references."""
    # 1. Remove "mcp_specialist" from allowed_specialists arrays in main agents
    op.execute("""
        UPDATE ai_assistant_configs
        SET delegation_config = jsonb_set(
            delegation_config,
            '{allowed_specialists}',
            (
                SELECT jsonb_agg(elem)
                FROM jsonb_array_elements_text(
                    delegation_config->'allowed_specialists'
                ) AS elem
                WHERE elem != 'mcp_specialist'
            )
        )
        WHERE agent_type = 'main'
          AND delegation_config->'allowed_specialists' IS NOT NULL
          AND EXISTS (
              SELECT 1
              FROM jsonb_array_elements_text(
                  delegation_config->'allowed_specialists'
              ) AS elem
              WHERE elem = 'mcp_specialist'
          );
    """)

    # 2. Delete the mcp_specialist specialist row
    op.execute("""
        DELETE FROM ai_assistant_configs
        WHERE name = 'mcp_specialist'
          AND agent_type = 'specialist';
    """)


def downgrade() -> None:
    """Re-add mcp_specialist to allowed_specialists for the Senior Project Manager."""
    op.execute("""
        UPDATE ai_assistant_configs
        SET delegation_config = jsonb_set(
            delegation_config,
            '{allowed_specialists}',
            (
                SELECT jsonb_agg(elem)
                FROM (
                    SELECT jsonb_array_elements_text(
                        delegation_config->'allowed_specialists'
                    ) AS elem
                    UNION ALL
                    SELECT 'mcp_specialist'::jsonb
                ) sub
            )
        )
        WHERE agent_type = 'main'
          AND name = 'Senior Project Manager'
          AND delegation_config->'allowed_specialists' IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM jsonb_array_elements_text(
                  delegation_config->'allowed_specialists'
              ) AS elem
              WHERE elem = 'mcp_specialist'
          );
    """)
