"""AI Configuration Service.

Provides CRUD operations for AI providers, models, and assistant configurations.
Handles API key encryption for sensitive values.
"""

import base64
import logging
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.domain.ai import (
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
        self, include_inactive: bool = False
    ) -> list[AIAssistantConfig]:
        """List all assistant configurations."""
        stmt = select(AIAssistantConfig)
        if not include_inactive:
            stmt = stmt.where(AIAssistantConfig.is_active)
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
        # Verify model exists
        model = await self.get_model(config_in.model_id)
        if not model:
            raise ValueError(f"Model {config_in.model_id} not found")

        config = AIAssistantConfig(
            name=config_in.name,
            description=config_in.description,
            model_id=config_in.model_id,
            system_prompt=config_in.system_prompt,
            temperature=config_in.temperature,
            max_tokens=config_in.max_tokens,
            recursion_limit=config_in.recursion_limit,
            allowed_tools=config_in.allowed_tools,
            default_role=config_in.default_role,
            is_active=config_in.is_active,
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
