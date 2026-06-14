"""grant ask_user to all assistant configs

Revision ID: 2db3a62769df
Revises: cf2b0f1ece1f
Create Date: 2026-06-14 09:18:36.607596

Data-only migration: makes ``ask_user`` the primary user-questioning
channel by granting it to every assistant config.

- Main agents (agent_type='main'): append ``"ask_user"`` to
  ``delegation_config.direct_tools`` so the supervisor can call it
  directly. (The supervisor loader at
  ``app/ai/supervisor_orchestrator.py`` sources its direct tools from this
  field.)
- Specialists (agent_type='specialist'): append ``"ask_user"`` to
  ``allowed_tools`` where the whitelist is explicit (NOT ``["*"]``) and
  does not already include it.

Autogenerate does NOT detect this (no schema change) -- the SQL is hand
written. Both columns are JSONB; we use the containment operator ``@>``
to guard idempotency and the ``||`` concat to append.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2db3a62769df'
down_revision: Union[str, Sequence[str], None] = 'cf2b0f1ece1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Grant ``ask_user`` to main + specialist assistant configs (idempotent)."""
    # Main agents: append "ask_user" to delegation_config.direct_tools where it
    # has a direct_tools array that does not already contain it.
    op.execute(
        """
        UPDATE ai_assistant_configs
        SET delegation_config = jsonb_set(
            delegation_config,
            '{direct_tools}',
            delegation_config->'direct_tools' || '"ask_user"'::jsonb
        )
        WHERE agent_type = 'main'
          AND delegation_config ? 'direct_tools'
          AND NOT (delegation_config->'direct_tools' @> '"ask_user"'::jsonb)
        """
    )

    # Specialists: append "ask_user" to allowed_tools where the whitelist is
    # explicit (not a wildcard ["*"]) and does not already include it.
    op.execute(
        """
        UPDATE ai_assistant_configs
        SET allowed_tools = allowed_tools || '"ask_user"'::jsonb
        WHERE agent_type = 'specialist'
          AND allowed_tools IS NOT NULL
          AND NOT (allowed_tools @> '["ask_user"]'::jsonb)
          AND NOT (allowed_tools @> '["*"]'::jsonb)
        """
    )


def downgrade() -> None:
    """Remove ``ask_user`` from direct_tools and allowed_tools (idempotent)."""
    # Main agents: strip "ask_user" from delegation_config.direct_tools.
    op.execute(
        """
        UPDATE ai_assistant_configs
        SET delegation_config = jsonb_set(
            delegation_config,
            '{direct_tools}',
            (
                SELECT jsonb_agg(elem)
                FROM jsonb_array_elements(delegation_config->'direct_tools') AS el(elem)
                WHERE elem <> to_jsonb('ask_user'::text)
            )
        )
        WHERE agent_type = 'main'
          AND delegation_config ? 'direct_tools'
          AND delegation_config->'direct_tools' @> '"ask_user"'::jsonb
        """
    )

    # Specialists: strip "ask_user" from allowed_tools.
    op.execute(
        """
        UPDATE ai_assistant_configs
        SET allowed_tools = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(allowed_tools) AS el(elem)
            WHERE elem <> to_jsonb('ask_user'::text)
        )
        WHERE agent_type = 'specialist'
          AND allowed_tools IS NOT NULL
          AND allowed_tools @> '["ask_user"]'::jsonb
        """
    )
