"""add_document_repository_tables

Revision ID: ce3a584f24f5
Revises: f16b5bcdbf1c
Create Date: 2026-05-25 17:49:29.140609

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ce3a584f24f5'
down_revision: Union[str, Sequence[str], None] = 'f16b5bcdbf1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create document repository tables and indexes."""
    # pg_trgm extension required for trigram GIN indexes
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    # --- document_folders ---
    op.create_table(
        'document_folders',
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('path', sa.String(length=1024), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_document_folders_project_id'),
        'document_folders',
        ['project_id'],
    )

    # --- documents ---
    op.create_table(
        'documents',
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('folder_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('extension', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'tags',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column('current_version_id', sa.UUID(), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False),
        sa.Column('locked_by', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_documents_project_id'),
        'documents',
        ['project_id'],
    )
    op.create_index(
        op.f('ix_documents_folder_id'),
        'documents',
        ['folder_id'],
    )
    # GIN trigram index for document name search
    op.execute(
        'CREATE INDEX ix_documents_name_trgm ON documents '
        "USING gin (name gin_trgm_ops)"
    )
    # GIN index for JSONB tags
    op.execute(
        'CREATE INDEX ix_documents_tags_gin ON documents '
        'USING gin (tags)'
    )

    # --- document_versions ---
    op.create_table(
        'document_versions',
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('storage_key', sa.String(length=512), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('checksum_sha256', sa.String(length=64), nullable=False),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('thumbnail_key', sa.String(length=512), nullable=True),
        sa.Column('uploaded_by', sa.UUID(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_document_versions_document_id'),
        'document_versions',
        ['document_id'],
    )
    # Composite index for document + version lookups
    op.create_index(
        'ix_document_versions_document_id_version_number',
        'document_versions',
        ['document_id', 'version_number'],
    )
    # GIN trigram index for full-text search on extracted_text
    op.execute(
        'CREATE INDEX ix_document_versions_extracted_text_trgm '
        'ON document_versions USING gin (extracted_text gin_trgm_ops)'
    )

    # --- document_entity_links ---
    op.create_table(
        'document_entity_links',
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_document_entity_links_document_id'),
        'document_entity_links',
        ['document_id'],
    )
    # Composite index for entity lookups
    op.create_index(
        'ix_document_entity_links_entity_type_entity_id',
        'document_entity_links',
        ['entity_type', 'entity_id'],
    )
    # Unique constraint: one link per (document, entity_type, entity_id)
    op.create_unique_constraint(
        'uq_document_entity_links_document_entity',
        'document_entity_links',
        ['document_id', 'entity_type', 'entity_id'],
    )


def downgrade() -> None:
    """Drop document repository tables and indexes."""
    op.drop_constraint(
        'uq_document_entity_links_document_entity',
        'document_entity_links',
        type_='unique',
    )
    op.drop_index(
        'ix_document_entity_links_entity_type_entity_id',
        table_name='document_entity_links',
    )
    op.drop_index(
        op.f('ix_document_entity_links_document_id'),
        table_name='document_entity_links',
    )
    op.drop_table('document_entity_links')

    op.execute(
        'DROP INDEX IF EXISTS ix_document_versions_extracted_text_trgm'
    )
    op.drop_index(
        'ix_document_versions_document_id_version_number',
        table_name='document_versions',
    )
    op.drop_index(
        op.f('ix_document_versions_document_id'),
        table_name='document_versions',
    )
    op.drop_table('document_versions')

    op.execute('DROP INDEX IF EXISTS ix_documents_tags_gin')
    op.execute('DROP INDEX IF EXISTS ix_documents_name_trgm')
    op.drop_index(op.f('ix_documents_folder_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_project_id'), table_name='documents')
    op.drop_table('documents')

    op.drop_index(
        op.f('ix_document_folders_project_id'),
        table_name='document_folders',
    )
    op.drop_table('document_folders')
