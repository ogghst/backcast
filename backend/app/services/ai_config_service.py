"""AI Configuration Service.

Provides CRUD operations for AI providers, models, and assistant configurations.
Handles API key encryption for sensitive values.
"""

import base64
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.domain.ai import (
    AIAgentExecution,
    AIAssistantConfig,
    AIConversationAttachment,
    AIConversationMessage,
    AIConversationSession,
    AIModel,
    AIProvider,
    AIProviderConfig,
)
from app.models.schemas.ai import (
    AIAssistantConfigCreate,
    AIAssistantConfigUpdate,
    AIModelCreate,
    AIModelUpdate,
    AIProviderConfigCreate,
    AIProviderCreate,
    AIProviderUpdate,
    SessionContext,
)

logger = logging.getLogger(__name__)


def _enforce_main_agent_has_model(
    agent_type: str | None, model_id: str | UUID | None
) -> None:
    """Require ``model_id`` for main agents; specialists may omit it.

    Mirrors ``AIAssistantConfigPublic.validate_main_agent_model`` so the same
    invariant holds at write time, preventing rows that would 500 the list
    endpoint on read. ``model_id`` accepts either ``UUID`` (schema values) or
    ``str`` (the ORM column type); only its presence is checked. Raises
    ``ValueError`` (mapped to an HTTP error by the routes) when a main agent
    has no model_id.
    """
    if agent_type == "main" and model_id is None:
        raise ValueError("model_id is required for main agents")


class AIConfigService:
    """Service for managing AI configuration."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._fernet: Fernet | None = None

    def _get_fernet(self) -> Fernet:
        """Get Fernet instance for encryption."""
        if self._fernet is None:
            secret_key = settings.SECRET_KEY
            # Derive a Fernet key from the secret key
            key = base64.urlsafe_b64encode(secret_key.encode()[:32].ljust(32, b"0"))
            self._fernet = Fernet(key)
        return self._fernet

    def _encrypt_value(self, value: str) -> str:
        """Encrypt a sensitive value."""
        return self._get_fernet().encrypt(value.encode()).decode()

    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a sensitive value."""
        try:
            return self._get_fernet().decrypt(encrypted_value.encode()).decode()
        except InvalidToken as e:
            raise ValueError(
                "Provider API key cannot be decrypted — it was encrypted with a different "
                "SECRET_KEY. Re-enter the API key in the AI Settings page."
            ) from e

    # === Provider Operations ===

    async def list_providers(self, include_inactive: bool = False) -> list[AIProvider]:
        """List all AI providers."""
        stmt = select(AIProvider)
        if not include_inactive:
            stmt = stmt.where(AIProvider.is_active)
        stmt = stmt.order_by(AIProvider.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_provider(self, provider_id: UUID) -> AIProvider | None:
        """Get a specific AI provider."""
        stmt = select(AIProvider).where(AIProvider.id == provider_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_provider(self, provider_in: AIProviderCreate) -> AIProvider:
        """Create a new AI provider."""
        provider = AIProvider(
            provider_type=provider_in.provider_type,
            name=provider_in.name,
            base_url=provider_in.base_url,
            is_active=provider_in.is_active,
        )
        self.session.add(provider)
        await self.session.flush()
        return provider

    async def update_provider(
        self, provider_id: UUID, provider_in: AIProviderUpdate
    ) -> AIProvider:
        """Update an AI provider."""
        provider = await self.session.get(AIProvider, provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")

        update_data = provider_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(provider, key, value)

        await self.session.flush()

        # Fetch a fresh copy to get server-generated values (updated_at)
        # This avoids lazy loading issues when Pydantic serializes the entity
        stmt = select(AIProvider).where(AIProvider.id == provider_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete_provider(self, provider_id: UUID) -> None:
        """Delete an AI provider and all its configs/models."""
        provider = await self.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")
        await self.session.delete(provider)

    # === Provider Config Operations ===

    async def list_provider_configs(
        self, provider_id: UUID, decrypt: bool = False
    ) -> list[AIProviderConfig]:
        """List all configs for a provider."""
        stmt = (
            select(AIProviderConfig)
            .where(AIProviderConfig.provider_id == provider_id)
            .order_by(AIProviderConfig.key)
        )
        result = await self.session.execute(stmt)
        configs = list(result.scalars().all())

        if decrypt:
            decrypted = []
            for config in configs:
                if config.is_encrypted and config.value:
                    # Return a detached copy so we don't mutate the ORM object
                    # in the session identity map (would corrupt subsequent calls).
                    copy = AIProviderConfig(
                        id=config.id,
                        provider_id=config.provider_id,
                        key=config.key,
                        value=self._decrypt_value(config.value),
                        is_encrypted=config.is_encrypted,
                    )
                    decrypted.append(copy)
                else:
                    decrypted.append(config)
            return decrypted

        return configs

    async def set_provider_config(
        self, provider_id: UUID, config_in: AIProviderConfigCreate
    ) -> AIProviderConfig:
        """Set a provider config value."""
        # Check if config already exists
        stmt = select(AIProviderConfig).where(
            AIProviderConfig.provider_id == provider_id,
            AIProviderConfig.key == config_in.key,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        value = config_in.value
        if config_in.is_encrypted and value:
            value = self._encrypt_value(value)

        if existing:
            existing.value = value
            existing.is_encrypted = config_in.is_encrypted
            await self.session.flush()
            # Fetch fresh copy to get server-generated values
            result = await self.session.execute(stmt)
            return result.scalar_one()
        else:
            config = AIProviderConfig(
                provider_id=provider_id,
                key=config_in.key,
                value=value,
                is_encrypted=config_in.is_encrypted,
            )
            self.session.add(config)
            await self.session.flush()
            # Fetch fresh copy to get server-generated values
            result = await self.session.execute(stmt)
            return result.scalar_one()

    async def delete_provider_config(self, provider_id: UUID, key: str) -> None:
        """Delete a provider config."""
        stmt = select(AIProviderConfig).where(
            AIProviderConfig.provider_id == provider_id,
            AIProviderConfig.key == key,
        )
        result = await self.session.execute(stmt)
        config = result.scalar_one_or_none()
        if config:
            await self.session.delete(config)

    async def get_decrypted_config(self, provider_id: UUID) -> dict[str, str]:
        """Get all config values for a provider (decrypted)."""
        configs = await self.list_provider_configs(provider_id, decrypt=True)
        return {c.key: c.value for c in configs if c.value}

    # === Model Operations ===

    async def list_models(
        self, provider_id: UUID | None = None, include_inactive: bool = False
    ) -> list[AIModel]:
        """List AI models, optionally filtered by provider."""
        stmt = select(AIModel)
        if provider_id:
            stmt = stmt.where(AIModel.provider_id == provider_id)
        if not include_inactive:
            stmt = stmt.where(AIModel.is_active)
        stmt = stmt.order_by(AIModel.display_name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_model(self, model_id: UUID) -> AIModel | None:
        """Get a specific AI model."""
        stmt = select(AIModel).where(AIModel.id == model_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_model(self, model_in: AIModelCreate) -> AIModel:
        """Create a new AI model."""
        # provider_id is required
        if model_in.provider_id is None:
            raise ValueError("provider_id is required")
        # Verify provider exists
        provider = await self.get_provider(model_in.provider_id)
        if not provider:
            raise ValueError(f"Provider {model_in.provider_id} not found")

        model = AIModel(
            provider_id=model_in.provider_id,
            model_id=model_in.model_id,
            display_name=model_in.display_name,
            is_active=model_in.is_active,
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def update_model(self, model_id: UUID, model_in: AIModelUpdate) -> AIModel:
        """Update an AI model.

        Supports partial updates - only fields present in the request will be modified.
        """
        model = await self.session.get(AIModel, model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        # Only update fields that were explicitly set in the request
        update_data = model_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(model, key, value)

        await self.session.flush()

        # Fetch fresh copy to get server-generated values (updated_at)
        # This avoids lazy loading issues when Pydantic serializes the entity
        stmt = select(AIModel).where(AIModel.id == model_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete_model(self, model_id: UUID) -> None:
        """Delete an AI model."""
        model = await self.get_model(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")
        await self.session.delete(model)

    # === Assistant Config Operations ===

    async def list_assistant_configs(
        self,
        include_inactive: bool = False,
        agent_type: str | None = None,
    ) -> list[AIAssistantConfig]:
        """List all assistant configurations."""
        stmt = select(AIAssistantConfig)
        if not include_inactive:
            stmt = stmt.where(AIAssistantConfig.is_active)
        if agent_type:
            stmt = stmt.where(AIAssistantConfig.agent_type == agent_type)
        stmt = stmt.order_by(AIAssistantConfig.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_assistant_config(self, config_id: UUID) -> AIAssistantConfig | None:
        """Get a specific assistant configuration."""
        stmt = select(AIAssistantConfig).where(AIAssistantConfig.id == config_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_assistant_config(
        self, config_in: AIAssistantConfigCreate
    ) -> AIAssistantConfig:
        """Create a new assistant configuration."""
        # Verify model exists (specialists may omit model_id)
        if config_in.model_id is not None:
            model = await self.get_model(config_in.model_id)
            if not model:
                raise ValueError(f"Model {config_in.model_id} not found")

        # Enforce the same invariant as the read validator at write time so
        # invalid main-agent rows can never be created (defense-in-depth: the
        # Create schema already rejects this at the API boundary with a 422).
        _enforce_main_agent_has_model(config_in.agent_type, config_in.model_id)

        config = AIAssistantConfig(
            name=config_in.name,
            description=config_in.description,
            model_id=config_in.model_id,
            system_prompt=config_in.system_prompt,
            planner_prompt=config_in.planner_prompt,
            supervisor_prompt=config_in.supervisor_prompt,
            temperature=config_in.temperature,
            max_tokens=config_in.max_tokens,
            recursion_limit=config_in.recursion_limit,
            default_role=config_in.default_role,
            is_active=config_in.is_active,
            agent_type=config_in.agent_type,
            allowed_tools=config_in.allowed_tools,
            delegation_config=config_in.delegation_config.model_dump()
            if config_in.delegation_config
            else None,
            structured_output_schema=config_in.structured_output_schema,
        )
        self.session.add(config)
        await self.session.flush()
        return config

    async def update_assistant_config(
        self, config_id: UUID, config_in: AIAssistantConfigUpdate
    ) -> AIAssistantConfig:
        """Update an assistant configuration."""
        config = await self.session.get(AIAssistantConfig, config_id)
        if not config:
            raise ValueError(f"Assistant config {config_id} not found")

        update_data = config_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(config, key, value)

        # Enforce the same invariant as the read validator on the MERGED result,
        # so a partial update can't leave a main agent without a model_id (e.g.
        # flipping agent_type to "main" or clearing model_id).
        _enforce_main_agent_has_model(config.agent_type, config.model_id)

        await self.session.flush()

        # Fetch fresh copy to get server-generated values
        stmt = select(AIAssistantConfig).where(AIAssistantConfig.id == config_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete_assistant_config(self, config_id: UUID) -> None:
        """Delete an assistant configuration."""
        config = await self.get_assistant_config(config_id)
        if not config:
            raise ValueError(f"Assistant config {config_id} not found")
        await self.session.delete(config)

    # === Conversation Session Operations ===

    async def list_sessions(
        self,
        user_id: UUID,
        limit: int = 50,
        context_type: str | None = None,
        context_id: str | None = None,
    ) -> list[AIConversationSession]:
        """List conversation sessions for a user.

        Args:
            user_id: User ID to filter sessions by
            limit: Maximum number of sessions to return
            context_type: Optional context type filter (general, project, wbe, cost_element)
            context_id: Optional entity ID filter for scoped context

        Returns:
            List of conversation sessions
        """
        stmt = select(AIConversationSession).where(
            AIConversationSession.user_id == user_id
        )
        if context_type:
            stmt = stmt.where(
                AIConversationSession.context["type"].astext == context_type
            )
        if context_id:
            stmt = stmt.where(AIConversationSession.context["id"].astext == context_id)
        stmt = stmt.order_by(AIConversationSession.updated_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_sessions_paginated(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 10,
        context_type: str | None = None,
        context_id: str | None = None,
    ) -> tuple[list[AIConversationSession], bool]:
        """List conversation sessions with pagination.

        Args:
            user_id: User ID to filter sessions by
            skip: Number of sessions to skip (for pagination)
            limit: Maximum number of sessions to return
            context_type: Optional context type filter (general, project, wbe, cost_element)
            context_id: Optional entity ID filter for scoped context

        Returns:
            Tuple of (sessions, has_more) where has_more indicates if more
            sessions exist beyond this page.
        """
        # Fetch requested sessions plus one extra to check for more
        stmt = select(AIConversationSession).where(
            AIConversationSession.user_id == user_id
        )
        if context_type:
            stmt = stmt.where(
                AIConversationSession.context["type"].astext == context_type
            )
        if context_id:
            stmt = stmt.where(AIConversationSession.context["id"].astext == context_id)
        stmt = (
            stmt.order_by(AIConversationSession.updated_at.desc())
            .offset(skip)
            .limit(limit + 1)  # Fetch one extra to check for more
        )
        result = await self.session.execute(stmt)
        sessions = list(result.scalars().all())

        has_more = len(sessions) > limit
        if has_more:
            sessions = sessions[:limit]  # Remove the extra item

        return sessions, has_more

    async def count_sessions(self, user_id: UUID) -> int:
        """Count total sessions for a user.

        Args:
            user_id: User ID to count sessions for

        Returns:
            Total number of sessions for the user
        """
        stmt = select(func.count(AIConversationSession.id)).where(
            AIConversationSession.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_executions_paginated(
        self,
        user_id: UUID,
        status: str | None = None,
        schedule_id: UUID | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Any], int, bool]:
        """List a user's agent executions, newest-first, with pagination.

        Joins ``AIAgentExecution -> AIConversationSession`` filtered by the
        session's owner, optionally filters by execution status, and
        left-joins ``ai_assistant_configs`` for the assistant display name.
        Mirrors the shape of :meth:`list_sessions_paginated`.

        Args:
            user_id: Owner to filter executions by (via the session).
            status: Optional ``AIAgentExecution.status`` filter (e.g.
                ``"running"``, ``"completed"``).
            schedule_id: Optional filter to a specific schedule's runs
                (``AIAgentExecution.schedule_id``). Only set for scheduled runs.
            started_from: Optional inclusive lower bound on ``started_at``.
            started_to: Optional inclusive upper bound on ``started_at``.
            limit: Page size (capped by the caller at 50).
            offset: Page offset.

        Returns:
            Tuple of ``(rows, total, has_more)`` where each ``row`` is a
            SQLAlchemy Row with the execution columns plus ``session_id``,
            the session's ``context`` JSONB, ``project_id``, ``branch_id``,
            and the assistant ``assistant_name`` (NULL if no assistant).
        """
        # Fetch one extra to compute has_more.
        stmt = (
            select(
                AIAgentExecution,
                AIConversationSession.context.label("session_context"),
                AIConversationSession.project_id.label("session_project_id"),
                AIConversationSession.branch_id.label("session_branch_id"),
                AIAssistantConfig.name.label("assistant_name"),
            )
            .join(
                AIConversationSession,
                AIConversationSession.id == AIAgentExecution.session_id,
            )
            .outerjoin(
                AIAssistantConfig,
                AIAssistantConfig.id == AIConversationSession.assistant_config_id,
            )
            .where(AIConversationSession.user_id == user_id)
        )
        if status is not None:
            stmt = stmt.where(AIAgentExecution.status == status)
        if schedule_id is not None:
            stmt = stmt.where(AIAgentExecution.schedule_id == schedule_id)
        if started_from is not None:
            stmt = stmt.where(AIAgentExecution.started_at >= started_from)
        if started_to is not None:
            stmt = stmt.where(AIAgentExecution.started_at <= started_to)
        stmt = (
            stmt.order_by(AIAgentExecution.started_at.desc())
            .offset(offset)
            .limit(limit + 1)
        )
        result = await self.session.execute(stmt)
        rows = list(result.all())

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        # Total count (with the same user + optional status filter).
        count_stmt = (
            select(func.count(AIAgentExecution.id))
            .join(
                AIConversationSession,
                AIConversationSession.id == AIAgentExecution.session_id,
            )
            .where(AIConversationSession.user_id == user_id)
        )
        if status is not None:
            count_stmt = count_stmt.where(AIAgentExecution.status == status)
        if schedule_id is not None:
            count_stmt = count_stmt.where(AIAgentExecution.schedule_id == schedule_id)
        if started_from is not None:
            count_stmt = count_stmt.where(AIAgentExecution.started_at >= started_from)
        if started_to is not None:
            count_stmt = count_stmt.where(AIAgentExecution.started_at <= started_to)
        total = (await self.session.execute(count_stmt)).scalar_one()

        return rows, total, has_more

    async def count_running_executions(self, user_id: UUID) -> int:
        """Count a user's executions in an active state (menu badge).

        Args:
            user_id: Owner to count executions for (via the session).

        Returns:
            Number of the user's executions with status in
            ``("running", "awaiting_approval")``.
        """
        active = ("running", "awaiting_approval")
        stmt = (
            select(func.count(AIAgentExecution.id))
            .join(
                AIConversationSession,
                AIConversationSession.id == AIAgentExecution.session_id,
            )
            .where(AIConversationSession.user_id == user_id)
            .where(AIAgentExecution.status.in_(active))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_session(self, session_id: UUID) -> AIConversationSession | None:
        """Get a specific conversation session."""
        stmt = select(AIConversationSession).where(
            AIConversationSession.id == session_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_session(
        self,
        user_id: UUID,
        assistant_config_id: UUID,
        title: str | None = None,
        project_id: UUID | None = None,
        branch_id: UUID | None = None,
        context: SessionContext | dict[str, Any] | None = None,
    ) -> AIConversationSession:
        """Create a new conversation session with optional context.

        Args:
            user_id: User ID creating the session
            assistant_config_id: Assistant configuration to use
            title: Optional session title
            project_id: Optional project context UUID
            branch_id: Optional branch or change order context UUID
            context: Optional SessionContext object or dict (type, id, project_id, name)

        Returns:
            Created conversation session

        Raises:
            ValueError: If assistant config not found
        """
        # Verify assistant config exists
        config = await self.get_assistant_config(assistant_config_id)
        if not config:
            raise ValueError(f"Assistant config {assistant_config_id} not found")

        # Default to general context if not provided
        if context is None:
            session_context = SessionContext(type="general")
        elif isinstance(context, dict):
            # Convert dict to SessionContext for validation
            session_context = SessionContext(**context)
        else:
            session_context = context

        # Convert SessionContext to dict for JSONB storage
        context_dict = session_context.model_dump(mode="json", exclude_none=True)

        session = AIConversationSession(
            user_id=user_id,
            assistant_config_id=assistant_config_id,
            title=title,
            project_id=project_id,
            branch_id=branch_id,
            context=context_dict,
        )
        self.session.add(session)
        await self.session.flush()
        return session

    async def delete_session(self, session_id: UUID) -> None:
        """Delete a conversation session and all its messages."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        await self.session.delete(session)

    # === Conversation Message Operations ===

    async def list_messages(self, session_id: UUID) -> list[AIConversationMessage]:
        """List all messages in a session."""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(AIConversationMessage)
            .options(selectinload(AIConversationMessage.attachments))
            .where(AIConversationMessage.session_id == session_id)
            .order_by(AIConversationMessage.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        message_metadata: dict[str, Any] | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> AIConversationMessage:
        """Add a message to a session.

        Args:
            session_id: Session ID to add message to
            role: Message role (user/assistant/tool)
            content: Message content
            tool_calls: Optional tool calls made by assistant
            tool_results: Optional tool results
            message_metadata: Optional metadata (e.g., subagent_name)
            attachments: Optional list of attachment dicts with keys:
                - file_id: UUID of the file
                - filename: Original filename
                - content_type: MIME type
                - file_size: Size in bytes
                - content: Extracted text or base64-encoded content

        Returns:
            Created message
        """
        message = AIConversationMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_results=tool_results,
            message_metadata=message_metadata,
        )
        self.session.add(message)
        await self.session.flush()

        # Create attachment records if provided
        if attachments:
            for attachment_data in attachments:
                attachment = AIConversationAttachment(
                    message_id=str(message.id),  # Convert UUID to str
                    filename=attachment_data["filename"],
                    content_type=attachment_data["content_type"],
                    content=attachment_data.get("content"),
                    size=attachment_data["file_size"],
                )
                self.session.add(attachment)

        await self.session.flush()
        return message

    # === Briefing Operations ===

    async def get_session_briefing(self, session_id: UUID) -> dict[str, Any] | None:
        """Get briefing data for a session.

        Args:
            session_id: Session ID to get briefing for

        Returns:
            Briefing data dict or None if no briefing exists
        """
        stmt = select(AIConversationSession).where(
            AIConversationSession.id == session_id
        )
        result = await self.session.execute(stmt)
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return session.briefing_data

    async def save_session_briefing(
        self,
        session_id: UUID,
        briefing_data: dict[str, Any],
        plan_data: dict[str, Any] | None = None,
    ) -> None:
        """Save or update briefing data (and optionally plan data) for a session.

        Args:
            session_id: Session ID to save briefing for
            briefing_data: BriefingDocument dict to save
            plan_data: Optional PlanDocument dict to save alongside briefing

        Raises:
            ValueError: If session not found
        """
        session = await self.session.get(AIConversationSession, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        session.briefing_data = briefing_data
        if plan_data is not None:
            session.plan_data = plan_data
        await self.session.flush()

    async def delete_session_briefing(self, session_id: UUID) -> None:
        """Clear briefing data for a session.

        Args:
            session_id: Session ID to clear briefing for

        Raises:
            ValueError: If session not found
        """
        session = await self.session.get(AIConversationSession, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        session.briefing_data = None
        await self.session.flush()
