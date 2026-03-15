"""create_ai_tables

Revision ID: c65f1ef54182
Revises: 20260228_rm_wbe_budget
Create Date: 2026-03-05

AI Integration Tables:
- ai_providers: Provider definitions (OpenAI, Azure, Ollama)
- ai_provider_configs: Key-value config (API keys, deployment names)
- ai_models: Available models per provider
- ai_assistant_configs: Assistant configuration with tool permissions
- ai_conversation_sessions: User conversation sessions
- ai_conversation_messages: Individual messages
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c65f1ef54182"
down_revision: str | Sequence[str] | None = "20260228_rm_wbe_budget"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create AI integration tables."""
    # ai_providers - Provider definitions
    op.create_table(
        "ai_providers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_providers_type", "ai_providers", ["provider_type"], unique=False
    )
    op.create_index(
        "ix_ai_providers_active", "ai_providers", ["is_active"], unique=False
    )

    # ai_provider_configs - Key-value config for providers
    op.create_table(
        "ai_provider_configs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("is_encrypted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["ai_providers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_provider_configs_provider",
        "ai_provider_configs",
        ["provider_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_ai_provider_configs_provider_key",
        "ai_provider_configs",
        ["provider_id", "key"],
    )

    # ai_models - Available models per provider
    op.create_table(
        "ai_models",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider_id", sa.UUID(), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["ai_providers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_models_provider", "ai_models", ["provider_id"], unique=False)
    op.create_unique_constraint(
        "uq_ai_models_provider_model", "ai_models", ["provider_id", "model_id"]
    )

    # ai_assistant_configs - Assistant configuration
    op.create_table(
        "ai_assistant_configs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("model_id", sa.UUID(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("temperature", sa.Numeric(3, 2), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("allowed_tools", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["ai_models.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_assistant_configs_model",
        "ai_assistant_configs",
        ["model_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_assistant_configs_active",
        "ai_assistant_configs",
        ["is_active"],
        unique=False,
    )

    # ai_conversation_sessions - User conversation sessions
    op.create_table(
        "ai_conversation_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("assistant_config_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["assistant_config_id"],
            ["ai_assistant_configs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_conversation_sessions_user",
        "ai_conversation_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_conversation_sessions_assistant",
        "ai_conversation_sessions",
        ["assistant_config_id"],
        unique=False,
    )

    # ai_conversation_messages - Individual messages
    op.create_table(
        "ai_conversation_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=True),
        sa.Column("tool_results", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["ai_conversation_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_conversation_messages_session",
        "ai_conversation_messages",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove AI integration tables."""
    op.drop_index("ix_ai_conversation_messages_session", "ai_conversation_messages")
    op.drop_table("ai_conversation_messages")

    op.drop_index("ix_ai_conversation_sessions_assistant", "ai_conversation_sessions")
    op.drop_index("ix_ai_conversation_sessions_user", "ai_conversation_sessions")
    op.drop_table("ai_conversation_sessions")

    op.drop_index("ix_ai_assistant_configs_active", "ai_assistant_configs")
    op.drop_index("ix_ai_assistant_configs_model", "ai_assistant_configs")
    op.drop_table("ai_assistant_configs")

    op.drop_unique_constraint("ai_models", "uq_ai_models_provider_model")
    op.drop_index("ix_ai_models_provider", "ai_models")
    op.drop_table("ai_models")

    op.drop_unique_constraint(
        "ai_provider_configs", "uq_ai_provider_configs_provider_key"
    )
    op.drop_index("ix_ai_provider_configs_provider", "ai_provider_configs")
    op.drop_table("ai_provider_configs")

    op.drop_index("ix_ai_providers_active", "ai_providers")
    op.drop_index("ix_ai_providers_type", "ai_providers")
    op.drop_table("ai_providers")
