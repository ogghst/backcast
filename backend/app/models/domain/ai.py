"""AI domain models for LLM integration.

All entities use SimpleEntityBase pattern (non-versioned).
Provides:
- AIProvider: Provider definitions (OpenAI, Azure, Ollama)
- AIProviderConfig: Key-value config for providers
- AIModel: Available models per provider
- AIAssistantConfig: Assistant configuration with tool permissions
- AIConversationSession: User conversation sessions
- AIConversationMessage: Individual messages
- AIConversationAttachment: File attachments for messages
- AIAgentExecution: Agent execution tracking with status lifecycle
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.base import SimpleEntityBase

if TYPE_CHECKING:
    pass


class AIProvider(SimpleEntityBase):
    """AI Provider definition (OpenAI, Azure, Ollama).

    Non-versioned entity for provider configuration.
    """

    __tablename__ = "ai_providers"

    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    configs: Mapped[list["AIProviderConfig"]] = relationship(
        "AIProviderConfig",
        back_populates="provider",
        cascade="all, delete-orphan",
        foreign_keys="[AIProviderConfig.provider_id]",
    )
    models: Mapped[list["AIModel"]] = relationship(
        "AIModel",
        back_populates="provider",
        cascade="all, delete-orphan",
        foreign_keys="[AIModel.provider_id]",
    )

    def __repr__(self) -> str:
        return (
            f"<AIProvider(id={self.id}, type={self.provider_type}, name={self.name})>"
        )


class AIProviderConfig(SimpleEntityBase):
    """Key-value configuration for AI providers.

    Stores API keys, deployment names, etc.
    Sensitive values are encrypted.
    """

    __tablename__ = "ai_provider_configs"

    provider_id: Mapped[str] = mapped_column(
        PG_UUID,
        ForeignKey("ai_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    provider: Mapped["AIProvider"] = relationship(
        "AIProvider", back_populates="configs", foreign_keys=[provider_id]
    )

    def __repr__(self) -> str:
        return f"<AIProviderConfig(id={self.id}, provider_id={self.provider_id}, key={self.key})>"


class AIModel(SimpleEntityBase):
    """Available models per provider.

    Maps provider to available model IDs.
    """

    __tablename__ = "ai_models"

    provider_id: Mapped[str] = mapped_column(
        PG_UUID,
        ForeignKey("ai_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    provider: Mapped["AIProvider"] = relationship(
        "AIProvider", back_populates="models", foreign_keys=[provider_id]
    )
    assistant_configs: Mapped[list["AIAssistantConfig"]] = relationship(
        "AIAssistantConfig",
        back_populates="model",
        foreign_keys="[AIAssistantConfig.model_id]",
    )

    def __repr__(self) -> str:
        return f"<AIModel(id={self.id}, model_id={self.model_id}, display_name={self.display_name})>"


class AIAssistantConfig(SimpleEntityBase):
    """Assistant configuration with tool permissions.

    Defines which tools an assistant can use.
    """

    __tablename__ = "ai_assistant_configs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_id: Mapped[str] = mapped_column(
        PG_UUID,
        ForeignKey("ai_models.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float(3), nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # LangGraph recursion limit (maximum steps in agent execution loop)
    recursion_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allowed_tools: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    model: Mapped["AIModel"] = relationship(
        "AIModel", back_populates="assistant_configs", foreign_keys=[model_id]
    )
    sessions: Mapped[list["AIConversationSession"]] = relationship(
        "AIConversationSession",
        back_populates="assistant_config",
        cascade="all, delete-orphan",
        foreign_keys="[AIConversationSession.assistant_config_id]",
    )

    def __repr__(self) -> str:
        return f"<AIAssistantConfig(id={self.id}, name={self.name})>"


class AIConversationSession(SimpleEntityBase):
    """User conversation session.

    Groups messages for a conversation with optional project and branch context.
    """

    __tablename__ = "ai_conversation_sessions"

    user_id: Mapped[str] = mapped_column(PG_UUID, nullable=False, index=True)
    assistant_config_id: Mapped[str] = mapped_column(
        PG_UUID,
        ForeignKey("ai_assistant_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_id: Mapped[str | None] = mapped_column(
        PG_UUID, nullable=True, index=True, comment="Optional project context"
    )
    branch_id: Mapped[str | None] = mapped_column(
        PG_UUID, nullable=True, index=True, comment="Optional branch or change order context"
    )
    active_execution_id: Mapped[str | None] = mapped_column(
        PG_UUID,
        nullable=True,
        comment="Reference to the currently running or last agent execution",
    )

    # Relationships
    assistant_config: Mapped["AIAssistantConfig"] = relationship(
        "AIAssistantConfig",
        back_populates="sessions",
        foreign_keys=[assistant_config_id],
    )
    messages: Mapped[list["AIConversationMessage"]] = relationship(
        "AIConversationMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        foreign_keys="[AIConversationMessage.session_id]",
    )
    executions: Mapped[list["AIAgentExecution"]] = relationship(
        "AIAgentExecution",
        back_populates="session",
        cascade="all, delete-orphan",
        foreign_keys="[AIAgentExecution.session_id]",
    )

    def __repr__(self) -> str:
        ctx_parts = [f"user_id={self.user_id}"]
        if self.project_id:
            ctx_parts.append(f"project_id={self.project_id}")
        if self.branch_id:
            ctx_parts.append(f"branch_id={self.branch_id}")
        ctx = ", ".join(ctx_parts)
        return f"<AIConversationSession(id={self.id}, {ctx})>"


class AIConversationMessage(SimpleEntityBase):
    """Individual conversation message.

    Stores role (user/assistant/tool) and content.
    """

    __tablename__ = "ai_conversation_messages"

    session_id: Mapped[str] = mapped_column(
        PG_UUID,
        ForeignKey("ai_conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    tool_results: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    message_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB(), nullable=True)

    # Relationships
    session: Mapped["AIConversationSession"] = relationship(
        "AIConversationSession", back_populates="messages", foreign_keys=[session_id]
    )
    attachments: Mapped[list["AIConversationAttachment"]] = relationship(
        "AIConversationAttachment",
        back_populates="message",
        cascade="all, delete-orphan",
        foreign_keys="[AIConversationAttachment.message_id]",
    )

    def __repr__(self) -> str:
        return f"<AIConversationMessage(id={self.id}, role={self.role})>"


class AIConversationAttachment(SimpleEntityBase):
    """File attachment for a conversation message.

    Stores metadata and inline content for files uploaded by users
    (images, PDFs, CSVs, etc.). File content is stored directly in the
    database as extracted text or base64-encoded image data.
    """
    __tablename__ = "ai_conversation_attachments"

    message_id: Mapped[str] = mapped_column(
        PG_UUID,
        ForeignKey("ai_conversation_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    message: Mapped["AIConversationMessage"] = relationship(
        "AIConversationMessage",
        back_populates="attachments",
        foreign_keys=[message_id],
    )

    def __repr__(self) -> str:
        return (
            f"<AIConversationAttachment(id={self.id}, message_id={self.message_id}, "
            f"filename={self.filename})>"
        )


class AIAgentExecution(SimpleEntityBase):
    """Agent execution tracking with status lifecycle.

    Tracks individual agent executions independent of WebSocket
    connections. Supports status transitions: pending -> running ->
    completed | error | awaiting_approval.
    """

    __tablename__ = "ai_agent_executions"

    session_id: Mapped[str] = mapped_column(
        PG_UUID,
        ForeignKey("ai_conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running"
    )
    started_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[str | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="standard"
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    tool_calls_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Relationships
    session: Mapped["AIConversationSession"] = relationship(
        "AIConversationSession", back_populates="executions", foreign_keys=[session_id]
    )

    def __repr__(self) -> str:
        return (
            f"<AIAgentExecution(id={self.id}, status={self.status}, "
            f"session_id={self.session_id})>"
        )
