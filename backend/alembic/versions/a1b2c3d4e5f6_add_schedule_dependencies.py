"""add_schedule_dependencies

Revision ID: a1b2c3d4e5f6
Revises: 44d11de23f6f
Create Date: 2026-06-03 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '44d11de23f6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Pre-defined ENUM with create_type=False so SQLAlchemy does not
# auto-create the type during create_table (it may already exist).
_dependency_type = PG_ENUM(
    'FS', 'SS', 'FF', 'SF',
    name='dependency_type',
    create_type=False,
    metadata=sa.MetaData(),
)


def upgrade() -> None:
    """Create schedule_dependencies table with dependency_type ENUM."""
    # Create ENUM idempotently — safe if already created by create_all/reseed.
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE dependency_type AS ENUM ('FS','SS','FF','SF'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    )

    op.create_table(
        'schedule_dependencies',
        sa.Column(
            'id',
            PG_UUID,
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column('schedule_dependency_id', PG_UUID, nullable=False),
        sa.Column('predecessor_id', PG_UUID, nullable=False),
        sa.Column('successor_id', PG_UUID, nullable=False),
        sa.Column(
            'dependency_type',
            _dependency_type,
            nullable=False,
            server_default='FS',
        ),
        sa.Column(
            'lag_days', sa.Integer, nullable=False, server_default='0'
        ),
        sa.Column(
            'branch', sa.String(100), nullable=False, server_default='main'
        ),
        sa.Column('project_id', PG_UUID, nullable=False),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
        ),
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
        ),
    )

    op.create_index(
        'ix_schedule_dependencies_schedule_dep',
        'schedule_dependencies',
        ['schedule_dependency_id'],
    )
    op.create_index(
        'ix_schedule_dependencies_predecessor_id',
        'schedule_dependencies',
        ['predecessor_id'],
    )
    op.create_index(
        'ix_schedule_dependencies_successor_id',
        'schedule_dependencies',
        ['successor_id'],
    )
    op.create_index(
        'ix_schedule_dependencies_project_id',
        'schedule_dependencies',
        ['project_id'],
    )
    op.create_index(
        'ix_schedule_dependencies_predecessor_branch',
        'schedule_dependencies',
        ['predecessor_id', 'branch'],
    )
    op.create_index(
        'ix_schedule_dependencies_successor_branch',
        'schedule_dependencies',
        ['successor_id', 'branch'],
    )
    op.create_index(
        'ix_schedule_dependencies_project_branch',
        'schedule_dependencies',
        ['project_id', 'branch'],
    )
    op.create_unique_constraint(
        'uq_schedule_dependency_link',
        'schedule_dependencies',
        ['predecessor_id', 'successor_id', 'dependency_type', 'branch'],
    )


def downgrade() -> None:
    """Drop schedule_dependencies table and dependency_type ENUM."""
    op.drop_constraint(
        'uq_schedule_dependency_link',
        'schedule_dependencies',
        type_='unique',
    )
    op.drop_table('schedule_dependencies')

    op.execute("DROP TYPE IF EXISTS dependency_type")
