"""grant set_project_context to assistant configs

Revision ID: d7e588f29806
Revises: 2db3a62769df
Create Date: 2026-06-17 10:00:00.000000

Data-only migration: grants ``set_project_context`` (the RBAC-gated tool
that establishes/switches the session's project scope in general chat) to
assistant configs.

- Main agents (agent_type='main'): append ``"set_project_context"`` to
  ``delegation_config.direct_tools`` so the supervisor can call it directly
  when the user references a project in a no-project chat. (The supervisor
  loader at ``app/ai/supervisor_orchestrator.py`` sources its direct tools
  from this field.)
- Specialists (agent_type='specialist'): append ``"set_project_context"`` to
  ``allowed_tools`` where the whitelist is explicit (NOT ``["*"]``) and does
  not already include it.

Autogenerate does NOT detect this (no schema change) -- the SQL is hand
written. Both columns are JSONB; we use the containment operator ``@>``
to guard idempotency and the ``||`` concat to append.

The live DB lags the seed (per project memory), so a seed-only change would
not reach existing deployments -- this migration is required.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7e588f29806"
down_revision: Union[str, Sequence[str], None] = "2db3a62769df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Grant ``set_project_context`` to main + specialist configs (idempotent)."""
    # Main agents: append "set_project_context" to delegation_config.direct_tools
    # where it has a direct_tools array that does not already contain it.
    op.execute(
        """
        UPDATE ai_assistant_configs
        SET delegation_config = jsonb_set(
            delegation_config,
            '{direct_tools}',
            delegation_config->'direct_tools' || '"set_project_context"'::jsonb
        )
        WHERE agent_type = 'main'
          AND delegation_config ? 'direct_tools'
          AND NOT (delegation_config->'direct_tools' @> '"set_project_context"'::jsonb)
        """
    )

    # Specialists: append "set_project_context" to allowed_tools where the
    # whitelist is explicit (not a wildcard ["*"]) and does not already include it.
    op.execute(
        """
        UPDATE ai_assistant_configs
        SET allowed_tools = allowed_tools || '"set_project_context"'::jsonb
        WHERE agent_type = 'specialist'
          AND allowed_tools IS NOT NULL
          AND NOT (allowed_tools @> '["set_project_context"]'::jsonb)
          AND NOT (allowed_tools @> '["*"]'::jsonb)
        """
    )


def downgrade() -> None:
    """Remove ``set_project_context`` from direct_tools and allowed_tools (idempotent)."""
    # Main agents: strip "set_project_context" from delegation_config.direct_tools.
    op.execute(
        """
        UPDATE ai_assistant_configs
        SET delegation_config = jsonb_set(
            delegation_config,
            '{direct_tools}',
            (
                SELECT jsonb_agg(elem)
                FROM jsonb_array_elements(delegation_config->'direct_tools') AS el(elem)
                WHERE elem <> to_jsonb('set_project_context'::text)
            )
        )
        WHERE agent_type = 'main'
          AND delegation_config ? 'direct_tools'
          AND delegation_config->'direct_tools' @> '"set_project_context"'::jsonb
        """
    )

    # Specialists: strip "set_project_context" from allowed_tools.
    op.execute(
        """
        UPDATE ai_assistant_configs
        SET allowed_tools = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(allowed_tools) AS el(elem)
            WHERE elem <> to_jsonb('set_project_context'::text)
        )
        WHERE agent_type = 'specialist'
          AND allowed_tools IS NOT NULL
          AND allowed_tools @> '["set_project_context"]'::jsonb
        """
    )
