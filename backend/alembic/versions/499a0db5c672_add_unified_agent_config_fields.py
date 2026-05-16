"""add_unified_agent_config_fields

Revision ID: 499a0db5c672
Revises: fa57821982c7
Create Date: 2026-05-16 19:12:37.742109

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '499a0db5c672'
down_revision: Union[str, Sequence[str], None] = 'fa57821982c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ai_assistant_configs', sa.Column(
        'agent_type', sa.String(length=20), nullable=False,
        server_default='main',
        comment="Agent type: 'main' (user-facing) or 'specialist' (delegated)",
    ))
    op.add_column('ai_assistant_configs', sa.Column(
        'allowed_tools', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
        comment='Tool whitelist for specialist agents. None means all available tools.',
    ))
    op.add_column('ai_assistant_configs', sa.Column(
        'delegation_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
        comment='Delegation config for main agents: {direct_tools: [...], allowed_specialists: [...] or null}',
    ))
    op.add_column('ai_assistant_configs', sa.Column(
        'structured_output_schema', sa.String(length=100), nullable=True,
        comment='Fully qualified Pydantic model class name for structured output (specialist-only)',
    ))
    op.add_column('ai_assistant_configs', sa.Column(
        'is_system', sa.Boolean(), nullable=False,
        server_default=sa.text('false'),
        comment='System agents cannot be deleted, only disabled',
    ))

    # Set defaults for existing seed assistants
    op.execute(
        "UPDATE ai_assistant_configs "
        "SET agent_type = 'main', is_system = true "
        "WHERE agent_type = 'main'"
    )


def downgrade() -> None:
    op.drop_column('ai_assistant_configs', 'is_system')
    op.drop_column('ai_assistant_configs', 'structured_output_schema')
    op.drop_column('ai_assistant_configs', 'delegation_config')
    op.drop_column('ai_assistant_configs', 'allowed_tools')
    op.drop_column('ai_assistant_configs', 'agent_type')
