"""Tests for system prompt builder - temporal context removal.

Tests verify that temporal context is NOT added to the system prompt,
following the maximum security approach where temporal parameters are
hidden from the LLM and enforced only at the tool level via ToolContext.
"""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_service import AgentService


@pytest.mark.asyncio
class TestBuildSystemPromptNoTemporalContext:
    """Test _build_system_prompt removes temporal context (maximum security)."""

    async def test_build_system_prompt_no_temporal_with_default_values(
        self, db_session: AsyncSession
    ) -> None:
        """Verify system prompt has NO temporal context with default values.

        Given: base_prompt and default temporal params (main branch, current time)
        When: _build_system_prompt() is called
        Then: returns base_prompt WITHOUT temporal context section
        """
        service = AgentService(db_session)

        base_prompt = "You are a helpful assistant for project management."
        as_of = None
        branch_name = "main"
        branch_mode = "merged"

        result = service._build_system_prompt(
            base_prompt=base_prompt,
            as_of=as_of,
            branch_name=branch_name,
            branch_mode=branch_mode,
        )

        # Should return base prompt unchanged (no temporal context added)
        assert result == base_prompt
        assert "[TEMPORAL CONTEXT]" not in result
        assert "Branch:" not in result
        assert "As of:" not in result
        assert "Mode:" not in result

    async def test_build_system_prompt_no_temporal_with_feature_branch(
        self, db_session: AsyncSession
    ) -> None:
        """Verify system prompt has NO temporal context even with feature branch.

        Given: base_prompt with feature branch context
        When: _build_system_prompt() is called with branch_name="feature-1"
        Then: returns base_prompt WITHOUT temporal context section
              (temporal context enforced at tool level only, not in prompt)
        """
        service = AgentService(db_session)

        base_prompt = "You are a helpful assistant for project management."
        as_of = None
        branch_name = "feature-1"
        branch_mode = "merged"

        result = service._build_system_prompt(
            base_prompt=base_prompt,
            as_of=as_of,
            branch_name=branch_name,
            branch_mode=branch_mode,
        )

        # Should return base prompt unchanged (maximum security: no temporal info in prompt)
        assert result == base_prompt
        assert "[TEMPORAL CONTEXT]" not in result
        assert "feature-1" not in result
        assert "Branch:" not in result

    async def test_build_system_prompt_no_temporal_with_historical_date(
        self, db_session: AsyncSession
    ) -> None:
        """Verify system prompt has NO temporal context even with historical date.

        Given: base_prompt with historical as_of date
        When: _build_system_prompt() is called with as_of=datetime(2025, 1, 1)
        Then: returns base_prompt WITHOUT temporal context section
        """
        service = AgentService(db_session)

        base_prompt = "You are a helpful assistant for project management."
        as_of = datetime(2025, 1, 1)
        branch_name = "main"
        branch_mode = "merged"

        result = service._build_system_prompt(
            base_prompt=base_prompt,
            as_of=as_of,
            branch_name=branch_name,
            branch_mode=branch_mode,
        )

        # Should return base prompt unchanged (maximum security)
        assert result == base_prompt
        assert "[TEMPORAL CONTEXT]" not in result
        assert "2025" not in result
        assert "January" not in result
        assert "As of:" not in result

    async def test_build_system_prompt_no_temporal_with_all_params(
        self, db_session: AsyncSession
    ) -> None:
        """Verify system prompt has NO temporal context with all params set.

        Given: base_prompt with all temporal params set
        When: _build_system_prompt() is called with as_of, branch, and mode
        Then: returns base_prompt WITHOUT temporal context section
              (temporal enforcement happens at tool level only)
        """
        service = AgentService(db_session)

        base_prompt = "You are a helpful assistant for project management."
        as_of = datetime(2025, 12, 15)
        branch_name = "change-order-1"
        branch_mode = "isolated"

        result = service._build_system_prompt(
            base_prompt=base_prompt,
            as_of=as_of,
            branch_name=branch_name,
            branch_mode=branch_mode,
        )

        # Should return base prompt unchanged (maximum security)
        assert result == base_prompt
        assert "[TEMPORAL CONTEXT]" not in result
        assert "change-order-1" not in result
        assert "December" not in result
        assert "isolated" not in result

    async def test_build_system_prompt_preserves_original_content(
        self, db_session: AsyncSession
    ) -> None:
        """Verify system prompt preserves original base prompt content.

        Given: base_prompt with multiline content
        When: _build_system_prompt() is called
        Then: returns base_prompt unchanged, preserving all content
        """
        service = AgentService(db_session)

        base_prompt = """You are a helpful assistant for project management.

You help users with:
- Project budget tracking
- Earned value management
- Change order management

Always provide accurate and helpful responses."""
        as_of = datetime(2025, 6, 30)
        branch_name = "feature-budget"
        branch_mode = "isolated"

        result = service._build_system_prompt(
            base_prompt=base_prompt,
            as_of=as_of,
            branch_name=branch_name,
            branch_mode=branch_mode,
        )

        # Should return base prompt unchanged, preserving all content
        assert result == base_prompt
        assert "Earned value management" in result
        assert "Change order management" in result
        assert "[TEMPORAL CONTEXT]" not in result
