"""Tests for system prompt builder - temporal context handling.

Tests verify that _build_system_prompt correctly handles temporal context
and project context, following the security approach where temporal parameters
are available in the prompt but enforcement happens at tool level via ToolContext.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_service import AgentService


@pytest.mark.asyncio
class TestBuildSystemPromptNoTemporalContext:
    """Test _build_system_prompt with default temporal params (no context added)."""

    async def test_build_system_prompt_no_temporal_with_default_values(
        self,
    ) -> None:
        """Verify system prompt with default temporal values has no temporal section."""
        service = AgentService(Mock(spec=AsyncSession))

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
        self,
    ) -> None:
        """Verify system prompt has temporal context section for feature branch."""
        service = AgentService(Mock(spec=AsyncSession))

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

        # Non-main branches should add temporal context
        assert "[TEMPORAL CONTEXT]" in result
        assert "feature-1" in result
        assert result.startswith(base_prompt)

    async def test_build_system_prompt_no_temporal_with_historical_date(
        self,
    ) -> None:
        """Verify system prompt has temporal context section for historical date."""
        service = AgentService(Mock(spec=AsyncSession))

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

        # Historical as_of (with main branch) should add temporal context
        assert "[TEMPORAL CONTEXT]" in result
        assert result.startswith(base_prompt)

    async def test_build_system_prompt_no_temporal_with_all_params(
        self,
    ) -> None:
        """Verify system prompt with all temporal params set adds context section."""
        service = AgentService(Mock(spec=AsyncSession))

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

        # Non-main branch takes precedence over as_of
        assert "[TEMPORAL CONTEXT]" in result
        assert "change-order-1" in result
        assert result.startswith(base_prompt)

    async def test_build_system_prompt_preserves_original_content(
        self,
    ) -> None:
        """Verify system prompt preserves original base prompt content."""
        service = AgentService(Mock(spec=AsyncSession))

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

        # Should preserve base prompt content
        assert "Earned value management" in result
        assert "Change order management" in result
        assert result.startswith(base_prompt)
