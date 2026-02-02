"""refactor_branch_pkg_to_id

Revision ID: 498e23573534
Revises: 20260129_000000
Create Date: 2026-01-29 15:07:37.274118

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '498e23573534'
down_revision: Union[str, Sequence[str], None] = '20260129_000000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add id column with default generation for existing rows
    op.add_column('branches', sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False))
    
    # 2. Drop old composite primary key
    op.drop_constraint('pk_branches', 'branches', type_='primary')
    
    # 3. Create new primary key on id
    op.create_primary_key('pk_branches', 'branches', ['id'])
    
    # 4. Add unique index on (name, project_id) combined (since it was PK before, it must be unique)
    # Actually, VersionableMixin implies uniqueness over time, but for active branch lookups
    # we usually want name+project_id to be unique.
    # The model defines name and project_id as not nullable.
    # We should add an index for performance at least.
    op.create_index(op.f('ix_branches_name_project_id'), 'branches', ['name', 'project_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Drop the index we added
    op.drop_index(op.f('ix_branches_name_project_id'), table_name='branches')
    
    # 2. Drop the new PK
    op.drop_constraint('pk_branches', 'branches', type_='primary')
    
    # 3. Re-create the old composite PK
    op.create_primary_key('pk_branches', 'branches', ['name', 'project_id'])
    
    # 4. Drop the id column
    op.drop_column('branches', 'id')
