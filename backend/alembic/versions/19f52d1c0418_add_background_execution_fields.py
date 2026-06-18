"""add background execution fields

Revision ID: 19f52d1c0418
Revises: d7e588f29806
Create Date: 2026-06-18 09:10:30.470530

Adds two columns to ``ai_agent_executions`` for the Background Agent
Execution + Agents History feature:

- ``run_in_background`` (Boolean, NOT NULL, server_default 'false'):
  when True the execution survives a transport disconnect (the
  transport-agnostic ExecutionLifecycle skips the grace-stop on
  last-observer detach).  Defaults to False so the default WS flow and
  pre-existing rows are unaffected.
- ``name`` (String(255), nullable): prompt-derived display name for the
  Agents History page (the user's message truncated to 120 chars by the
  service).  Nullable so pre-existing rows remain valid.

Surgical: only these two columns are added.  (Autogenerate also reported
unrelated drift on the ``schedule_dependencies`` table, which is out of
scope for this change and intentionally NOT included.)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '19f52d1c0418'
down_revision: Union[str, Sequence[str], None] = 'd7e588f29806'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add run_in_background and name to ai_agent_executions."""
    with op.batch_alter_table('ai_agent_executions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'run_in_background',
                sa.Boolean(),
                server_default='false',
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column('name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Drop run_in_background and name from ai_agent_executions."""
    with op.batch_alter_table('ai_agent_executions', schema=None) as batch_op:
        batch_op.drop_column('name')
        batch_op.drop_column('run_in_background')
