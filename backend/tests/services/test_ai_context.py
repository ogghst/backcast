"""Tests for AI conversation session context functionality.

Tests context creation, filtering, and system prompt injection.
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_service import AgentService
from app.models.domain.user import User
from app.models.schemas.ai import (
    AIAssistantConfigCreate,
    AIModelCreate,
    AIProviderCreate,
)
from app.services.ai_config_service import AIConfigService


@pytest.mark.asyncio
class TestAIConversationContext:
    """Test suite for AI conversation session context functionality."""

    async def test_create_session_with_general_context(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test creating a session with general context."""
        config_service = AIConfigService(db_session)

        # Create provider and model
        provider = await config_service.create_provider(
            AIProviderCreate(
                provider_type="openai", name="Test Provider", is_active=True
            )
        )
        model = await config_service.create_model(
            AIModelCreate(
                provider_id=provider.id,
                model_id="gpt-4",
                display_name="GPT-4",
            )
        )
        assistant_config = await config_service.create_assistant_config(
            AIAssistantConfigCreate(
                name="Test Assistant",
                model_id=model.id,
                system_prompt="You are a helpful assistant.",
            )
        )

        # Create session with general context
        session = await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="General Chat",
            context={"type": "general"},
        )

        assert session is not None
        assert session.context == {"type": "general"}
        assert session.title == "General Chat"

    async def test_create_session_with_project_context(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test creating a session with project context."""
        config_service = AIConfigService(db_session)

        # Create provider and model
        provider = await config_service.create_provider(
            AIProviderCreate(
                provider_type="openai", name="Test Provider", is_active=True
            )
        )
        model = await config_service.create_model(
            AIModelCreate(
                provider_id=provider.id,
                model_id="gpt-4",
                display_name="GPT-4",
            )
        )
        assistant_config = await config_service.create_assistant_config(
            AIAssistantConfigCreate(
                name="Test Assistant",
                model_id=model.id,
                system_prompt="You are a helpful assistant.",
            )
        )

        # Create session with project context
        project_id = uuid4()
        session = await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="Project Chat",
            project_id=project_id,
            context={
                "type": "project",
                "id": str(project_id),
                "name": "Test Project",
            },
        )

        assert session is not None
        assert session.context == {
            "type": "project",
            "id": str(project_id),
            "name": "Test Project",
        }
        assert session.project_id == project_id

    async def test_create_session_with_wbe_context(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test creating a session with WBE context."""
        config_service = AIConfigService(db_session)

        # Create provider and model
        provider = await config_service.create_provider(
            AIProviderCreate(
                provider_type="openai", name="Test Provider", is_active=True
            )
        )
        model = await config_service.create_model(
            AIModelCreate(
                provider_id=provider.id,
                model_id="gpt-4",
                display_name="GPT-4",
            )
        )
        assistant_config = await config_service.create_assistant_config(
            AIAssistantConfigCreate(
                name="Test Assistant",
                model_id=model.id,
                system_prompt="You are a helpful assistant.",
            )
        )

        # Create session with WBE context
        project_id = uuid4()
        wbe_id = uuid4()
        session = await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="WBE Chat",
            project_id=project_id,
            context={
                "type": "wbe",
                "id": str(wbe_id),
                "project_id": str(project_id),
                "name": "Test WBE",
            },
        )

        assert session is not None
        assert session.context == {
            "type": "wbe",
            "id": str(wbe_id),
            "project_id": str(project_id),
            "name": "Test WBE",
        }

    async def test_create_session_with_cost_element_context(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test creating a session with cost element context."""
        config_service = AIConfigService(db_session)

        # Create provider and model
        provider = await config_service.create_provider(
            AIProviderCreate(
                provider_type="openai", name="Test Provider", is_active=True
            )
        )
        model = await config_service.create_model(
            AIModelCreate(
                provider_id=provider.id,
                model_id="gpt-4",
                display_name="GPT-4",
            )
        )
        assistant_config = await config_service.create_assistant_config(
            AIAssistantConfigCreate(
                name="Test Assistant",
                model_id=model.id,
                system_prompt="You are a helpful assistant.",
            )
        )

        # Create session with cost element context
        project_id = uuid4()
        cost_element_id = uuid4()
        session = await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="Cost Element Chat",
            project_id=project_id,
            context={
                "type": "cost_element",
                "id": str(cost_element_id),
                "project_id": str(project_id),
                "name": "Test Cost Element",
            },
        )

        assert session is not None
        assert session.context == {
            "type": "cost_element",
            "id": str(cost_element_id),
            "project_id": str(project_id),
            "name": "Test Cost Element",
        }

    async def test_create_session_defaults_to_general_context(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that sessions without explicit context default to general."""
        config_service = AIConfigService(db_session)

        # Create provider and model
        provider = await config_service.create_provider(
            AIProviderCreate(
                provider_type="openai", name="Test Provider", is_active=True
            )
        )
        model = await config_service.create_model(
            AIModelCreate(
                provider_id=provider.id,
                model_id="gpt-4",
                display_name="GPT-4",
            )
        )
        assistant_config = await config_service.create_assistant_config(
            AIAssistantConfigCreate(
                name="Test Assistant",
                model_id=model.id,
                system_prompt="You are a helpful assistant.",
            )
        )

        # Create session without context
        session = await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="Default Context Chat",
        )

        assert session is not None
        assert session.context == {"type": "general"}

    async def test_list_sessions_filter_by_general_context(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test filtering sessions by general context type."""
        config_service = AIConfigService(db_session)

        # Create provider and model
        provider = await config_service.create_provider(
            AIProviderCreate(
                provider_type="openai", name="Test Provider", is_active=True
            )
        )
        model = await config_service.create_model(
            AIModelCreate(
                provider_id=provider.id,
                model_id="gpt-4",
                display_name="GPT-4",
            )
        )
        assistant_config = await config_service.create_assistant_config(
            AIAssistantConfigCreate(
                name="Test Assistant",
                model_id=model.id,
                system_prompt="You are a helpful assistant.",
            )
        )

        # Create multiple sessions with different contexts
        await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="General Chat 1",
            context={"type": "general"},
        )
        await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="General Chat 2",
            context={"type": "general"},
        )
        await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="Project Chat",
            context={"type": "project", "id": str(uuid4()), "name": "Test Project"},
        )

        # Filter by general context
        general_sessions = await config_service.list_sessions(
            user_id=test_user.user_id,
            context_type="general",
        )

        assert len(general_sessions) == 2
        for session in general_sessions:
            assert session.context["type"] == "general"

    async def test_list_sessions_filter_by_project_context(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test filtering sessions by project context type."""
        config_service = AIConfigService(db_session)

        # Create provider and model
        provider = await config_service.create_provider(
            AIProviderCreate(
                provider_type="openai", name="Test Provider", is_active=True
            )
        )
        model = await config_service.create_model(
            AIModelCreate(
                provider_id=provider.id,
                model_id="gpt-4",
                display_name="GPT-4",
            )
        )
        assistant_config = await config_service.create_assistant_config(
            AIAssistantConfigCreate(
                name="Test Assistant",
                model_id=model.id,
                system_prompt="You are a helpful assistant.",
            )
        )

        # Create multiple sessions with different contexts
        await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="General Chat",
            context={"type": "general"},
        )
        await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="Project Chat 1",
            context={"type": "project", "id": str(uuid4()), "name": "Project 1"},
        )
        await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="Project Chat 2",
            context={"type": "project", "id": str(uuid4()), "name": "Project 2"},
        )

        # Filter by project context
        project_sessions = await config_service.list_sessions(
            user_id=test_user.user_id,
            context_type="project",
        )

        assert len(project_sessions) == 2
        for session in project_sessions:
            assert session.context["type"] == "project"

    async def test_list_sessions_without_filter(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test listing all sessions without context filter."""
        config_service = AIConfigService(db_session)

        # Create provider and model
        provider = await config_service.create_provider(
            AIProviderCreate(
                provider_type="openai", name="Test Provider", is_active=True
            )
        )
        model = await config_service.create_model(
            AIModelCreate(
                provider_id=provider.id,
                model_id="gpt-4",
                display_name="GPT-4",
            )
        )
        assistant_config = await config_service.create_assistant_config(
            AIAssistantConfigCreate(
                name="Test Assistant",
                model_id=model.id,
                system_prompt="You are a helpful assistant.",
            )
        )

        # Create multiple sessions with different contexts
        await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="General Chat",
            context={"type": "general"},
        )
        await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="Project Chat",
            context={"type": "project", "id": str(uuid4()), "name": "Test Project"},
        )

        # List all sessions
        all_sessions = await config_service.list_sessions(
            user_id=test_user.user_id,
        )

        assert len(all_sessions) == 2

    async def test_list_sessions_paginated_with_context_filter(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test paginated session listing with context filter."""
        config_service = AIConfigService(db_session)

        # Create provider and model
        provider = await config_service.create_provider(
            AIProviderCreate(
                provider_type="openai", name="Test Provider", is_active=True
            )
        )
        model = await config_service.create_model(
            AIModelCreate(
                provider_id=provider.id,
                model_id="gpt-4",
                display_name="GPT-4",
            )
        )
        assistant_config = await config_service.create_assistant_config(
            AIAssistantConfigCreate(
                name="Test Assistant",
                model_id=model.id,
                system_prompt="You are a helpful assistant.",
            )
        )

        # Create multiple sessions
        for i in range(5):
            await config_service.create_session(
                user_id=test_user.user_id,
                assistant_config_id=assistant_config.id,
                title=f"General Chat {i}",
                context={"type": "general"},
            )
        await config_service.create_session(
            user_id=test_user.user_id,
            assistant_config_id=assistant_config.id,
            title="Project Chat",
            context={"type": "project", "id": str(uuid4()), "name": "Test Project"},
        )

        # Test pagination with context filter
        sessions_page1, has_more = await config_service.list_sessions_paginated(
            user_id=test_user.user_id,
            skip=0,
            limit=3,
            context_type="general",
        )

        assert len(sessions_page1) == 3
        assert has_more is True
        for session in sessions_page1:
            assert session.context["type"] == "general"

        # Get second page
        sessions_page2, has_more = await config_service.list_sessions_paginated(
            user_id=test_user.user_id,
            skip=3,
            limit=3,
            context_type="general",
        )

        assert len(sessions_page2) == 2
        assert has_more is False


@pytest.mark.asyncio
class TestAIAgentSystemPromptContext:
    """Test suite for AI agent system prompt context injection."""

    async def test_system_prompt_with_general_context(
        self, db_session: AsyncSession
    ) -> None:
        """Test system prompt injection with general context."""
        agent_service = AgentService(db_session)

        base_prompt = "You are a helpful assistant."
        context = {"type": "general"}

        system_prompt = agent_service._build_system_prompt(
            base_prompt=base_prompt,
            context=context,
        )

        assert "general conversation" in system_prompt.lower()
        assert base_prompt in system_prompt

    async def test_system_prompt_with_project_context(
        self, db_session: AsyncSession
    ) -> None:
        """Test system prompt injection with project context."""
        agent_service = AgentService(db_session)

        base_prompt = "You are a helpful assistant."
        project_id = uuid4()
        context = {
            "type": "project",
            "id": str(project_id),
            "name": "Test Project",
        }

        system_prompt = agent_service._build_system_prompt(
            base_prompt=base_prompt,
            project_id=project_id,
            context=context,
        )

        assert "test project" in system_prompt.lower()
        assert str(project_id) in system_prompt
        assert "project-scoped tools" in system_prompt.lower()

    async def test_system_prompt_with_wbe_context(
        self, db_session: AsyncSession
    ) -> None:
        """Test system prompt injection with WBE context."""
        agent_service = AgentService(db_session)

        base_prompt = "You are a helpful assistant."
        project_id = uuid4()
        wbe_id = uuid4()
        context = {
            "type": "wbe",
            "id": str(wbe_id),
            "project_id": str(project_id),
            "name": "Test WBE",
        }

        system_prompt = agent_service._build_system_prompt(
            base_prompt=base_prompt,
            context=context,
        )

        assert "test wbe" in system_prompt.lower()
        assert str(wbe_id) in system_prompt
        assert "wbe" in system_prompt.lower()

    async def test_system_prompt_with_cost_element_context(
        self, db_session: AsyncSession
    ) -> None:
        """Test system prompt injection with cost element context."""
        agent_service = AgentService(db_session)

        base_prompt = "You are a helpful assistant."
        project_id = uuid4()
        cost_element_id = uuid4()
        context = {
            "type": "cost_element",
            "id": str(cost_element_id),
            "project_id": str(project_id),
            "name": "Test Cost Element",
        }

        system_prompt = agent_service._build_system_prompt(
            base_prompt=base_prompt,
            context=context,
        )

        assert "test cost element" in system_prompt.lower()
        assert str(cost_element_id) in system_prompt
        assert "cost element" in system_prompt.lower()

    async def test_system_prompt_without_context(
        self, db_session: AsyncSession
    ) -> None:
        """Test system prompt without context (base prompt only)."""
        agent_service = AgentService(db_session)

        base_prompt = "You are a helpful assistant."

        system_prompt = agent_service._build_system_prompt(
            base_prompt=base_prompt,
        )

        assert system_prompt == base_prompt

    async def test_system_prompt_with_legacy_project_id(
        self, db_session: AsyncSession
    ) -> None:
        """Test system prompt with legacy project_id but no context."""
        agent_service = AgentService(db_session)

        base_prompt = "You are a helpful assistant."
        project_id = uuid4()

        system_prompt = agent_service._build_system_prompt(
            base_prompt=base_prompt,
            project_id=project_id,
        )

        assert "specific project" in system_prompt.lower()
        assert str(project_id) in system_prompt
