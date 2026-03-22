"""Tests for system prompt temporal context."""

import pytest
from datetime import datetime
from app.ai.agent_service import AgentService
from sqlalchemy.ext.asyncio import AsyncSession


class TestSystemPromptTemporalContext:
    """Test system prompt temporal context functionality."""

    @pytest.mark.asyncio
    async def test_system_prompt_includes_temporal_context_when_branch_not_main(
        self, db_session: AsyncSession
    ):
        """Test that system prompt includes temporal context when branch is not 'main'."""
        # Arrange
        service = AgentService(db_session)
        branch_name = "BR-001"

        # Act
        prompt = service._build_system_prompt(
            base_prompt="You are a helpful assistant.",
            as_of=None,
            branch_name=branch_name,
            branch_mode="merged",
        )

        # Assert
        assert "[TEMPORAL CONTEXT]" in prompt
        assert "BR-001" in prompt

    @pytest.mark.asyncio
    async def test_system_prompt_includes_temporal_context_when_as_of_set(
        self, db_session: AsyncSession
    ):
        """Test that system prompt includes temporal context when as_of is set."""
        # Arrange
        service = AgentService(db_session)
        as_of = datetime(2024, 1, 1, 12, 0, 0)

        # Act
        prompt = service._build_system_prompt(
            base_prompt="You are a helpful assistant.",
            as_of=as_of,
            branch_name="main",
            branch_mode="merged",
        )

        # Assert
        assert "[TEMPORAL CONTEXT]" in prompt
        assert "January" in prompt or "2024" in prompt

    @pytest.mark.asyncio
    async def test_system_prompt_excludes_temporal_context_for_defaults(
        self, db_session: AsyncSession
    ):
        """Test that system prompt excludes temporal context for default values."""
        # Arrange
        service = AgentService(db_session)

        # Act
        prompt = service._build_system_prompt(
            base_prompt="You are a helpful assistant.",
            as_of=None,
            branch_name="main",
            branch_mode="merged",
        )

        # Assert
        assert "[TEMPORAL CONTEXT]" not in prompt
