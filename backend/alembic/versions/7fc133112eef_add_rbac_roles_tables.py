"""add_rbac_roles_tables

Revision ID: 7fc133112eef
Revises: 081e1509d5a4
Create Date: 2026-04-23 20:21:56.930436

"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7fc133112eef'
down_revision: Union[str, Sequence[str], None] = '081e1509d5a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables metadata for bulk inserts
rbac_roles = sa.table(
    'rbac_roles',
    sa.column('id', postgresql.UUID()),
    sa.column('name', sa.String(100)),
    sa.column('description', sa.Text()),
    sa.column('is_system', sa.Boolean()),
    sa.column('created_at', sa.DateTime(timezone=True)),
    sa.column('updated_at', sa.DateTime(timezone=True)),
)

rbac_role_permissions = sa.table(
    'rbac_role_permissions',
    sa.column('id', postgresql.UUID()),
    sa.column('role_id', postgresql.UUID()),
    sa.column('permission', sa.String(100)),
    sa.column('created_at', sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    """Create rbac_roles and rbac_role_permissions tables and seed from config."""
    # --- Create tables ---
    op.create_table(
        'rbac_roles',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'is_system', sa.Boolean(), nullable=False, server_default='false',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        'rbac_role_permissions',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column(
            'role_id',
            postgresql.UUID(),
            sa.ForeignKey('rbac_roles.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('permission', sa.String(100), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint('role_id', 'permission', name='uq_role_permission'),
    )

    op.create_index(
        op.f('ix_rbac_role_permissions_role_id'),
        'rbac_role_permissions',
        ['role_id'],
    )

    # --- Seed data from rbac.json ---
    rbac_path = Path(__file__).resolve().parent.parent.parent / 'config' / 'rbac.json'
    if not rbac_path.exists():
        return

    with rbac_path.open() as f:
        rbac_config = json.load(f)

    roles_data = rbac_config.get('roles', {})
    if not roles_data:
        return

    # Use a connection to check for existing data (idempotency)
    conn = op.get_bind()
    existing = conn.execute(sa.text('SELECT name FROM rbac_roles')).fetchall()
    existing_names = {row[0] for row in existing}
    if existing_names:
        return

    now = datetime.now(timezone.utc)
    role_rows = []
    permission_rows = []

    for role_name, role_def in roles_data.items():
        role_id = str(uuid4())
        role_rows.append({
            'id': role_id,
            'name': role_name,
            'description': None,
            'is_system': True,
            'created_at': now,
            'updated_at': now,
        })
        for perm in role_def.get('permissions', []):
            permission_rows.append({
                'id': str(uuid4()),
                'role_id': role_id,
                'permission': perm,
                'created_at': now,
            })

    if role_rows:
        op.bulk_insert(rbac_roles, role_rows)
    if permission_rows:
        op.bulk_insert(rbac_role_permissions, permission_rows)


def downgrade() -> None:
    """Drop rbac_role_permissions and rbac_roles tables."""
    op.drop_index(
        op.f('ix_rbac_role_permissions_role_id'),
        table_name='rbac_role_permissions',
    )
    op.drop_table('rbac_role_permissions')
    op.drop_table('rbac_roles')
