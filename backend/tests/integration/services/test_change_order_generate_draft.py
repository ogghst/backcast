"""Integration tests for ChangeOrderService.generate_draft method.

Tests AI-powered change order draft generation with database integration.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.change_order_parser import ChangeOrderRequirementParser
from app.core.enums import ChangeOrderStatus
from app.models.domain.project import Project
from app.services.change_order_service import ChangeOrderService


@pytest.mark.asyncio
async def test_generate_draft_success(
    db_session: AsyncSession,
    test_project: Project,
    test_user: dict[str, str],
):
    """Test successful change order draft generation with AI."""
    service = ChangeOrderService(db_session)

    # Mock AI response
    mock_response = {
        "title": "Add Safety Sensors",
        "description": "Install additional safety sensors on assembly line",
        "reason": "Updated safety regulations require additional sensors",
        "budget_impact": 25000.0,
        "schedule_impact_days": 5,
        "risk_level": "Low",
        "affected_entities": ["WBE-001", "CE-002"],
        "recommendation": "Approve",
        "confidence_score": 0.85,
    }

    mock_completion = MagicMock()
    mock_message = MagicMock()
    mock_message.content = json.dumps(mock_response)
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_completion.choices = [mock_choice]

    with (
        patch(
            "app.ai.change_order_parser.LLMClientFactory.create_client",
        ) as mock_create_client,
        patch(
            "app.ai.change_order_parser.AIConfigService.list_providers",
            new_callable=AsyncMock,
        ),
        patch(
            "app.ai.change_order_parser.AIConfigService.list_models",
            new_callable=AsyncMock,
        ),
    ):
        # Setup mocks
        from app.models.domain.ai import AIModel, AIProvider

        mock_provider = MagicMock(spec=AIProvider)
        mock_provider.id = uuid4()
        mock_model = MagicMock(spec=AIModel)
        mock_model.model_id = uuid4()

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_create_client.return_value = mock_client

        # Mock config service methods
        with patch.object(
            ChangeOrderRequirementParser,
            "_config_service",
        ) as mock_config_service:
            mock_config_service.list_providers = AsyncMock(return_value=[mock_provider])
            mock_config_service.list_models = AsyncMock(return_value=[mock_model])

            draft = await service.generate_draft(
                project_id=test_project.project_id,
                title="Add Safety Sensors",
                description="Install additional safety sensors on assembly line",
                reason="Updated safety regulations require additional sensors",
                actor_id=UUID(test_user["user_id"]),
            )

            # Verify draft was created
            assert draft is not None
            assert draft.code.startswith("CO-")
            assert draft.title == "Add Safety Sensors"
            assert draft.status == ChangeOrderStatus.DRAFT
            assert draft.impact_level == "LOW"
            assert draft.branch == "main"
            assert draft.branch_name.startswith("BR-")

            # Verify AI analysis was stored
            assert draft.impact_analysis_results is not None
            assert "ai_analysis" in draft.impact_analysis_results
            ai_analysis = draft.impact_analysis_results["ai_analysis"]
            assert ai_analysis["confidence_score"] == 0.85
            assert ai_analysis["risk_assessment"] == "Low"
            assert ai_analysis["recommendation"] == "Approve"
            assert ai_analysis["estimated_budget_impact"] == 25000.0
            assert ai_analysis["estimated_schedule_impact_days"] == 5


@pytest.mark.asyncio
async def test_generate_draft_ai_fallback(
    db_session: AsyncSession,
    test_project: Project,
    test_user: dict[str, str],
):
    """Test draft generation falls back to manual data when AI fails."""
    service = ChangeOrderService(db_session)

    with (
        patch(
            "app.ai.change_order_parser.LLMClientFactory.create_client",
            side_effect=Exception("AI service unavailable"),
        ),
        patch(
            "app.ai.change_order_parser.AIConfigService.list_providers",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        draft = await service.generate_draft(
            project_id=test_project.project_id,
            title="Manual Change",
            description="Manual description",
            reason="Manual reason",
            actor_id=UUID(test_user["user_id"]),
        )

        # Verify draft was created with manual data
        assert draft is not None
        assert draft.title == "Manual Change"
        assert draft.description == "Manual description"
        assert draft.status == ChangeOrderStatus.DRAFT
        assert draft.impact_level == "MEDIUM"  # Default

        # Verify AI analysis reflects fallback
        assert draft.impact_analysis_results is not None
        assert "ai_analysis" in draft.impact_analysis_results
        ai_analysis = draft.impact_analysis_results["ai_analysis"]
        assert ai_analysis["confidence_score"] == 0.0


@pytest.mark.asyncio
async def test_generate_draft_project_not_found(
    db_session: AsyncSession,
    test_user: dict[str, str],
):
    """Test draft generation fails when project doesn't exist."""
    service = ChangeOrderService(db_session)

    with pytest.raises(ValueError, match="Project .* not found"):
        await service.generate_draft(
            project_id=uuid4(),
            title="Test",
            description="Test",
            reason="Test",
            actor_id=UUID(test_user["user_id"]),
        )


@pytest.mark.asyncio
async def test_generate_draft_branch_creation(
    db_session: AsyncSession,
    test_project: Project,
    test_user: dict[str, str],
):
    """Test that generate_draft creates the correct branch structure."""
    service = ChangeOrderService(db_session)

    mock_response = {
        "title": "Test Change",
        "description": "Test description",
        "reason": "Test reason",
        "budget_impact": 10000.0,
        "schedule_impact_days": 3,
        "risk_level": "Medium",
        "affected_entities": [],
        "recommendation": "Review required",
        "confidence_score": 0.7,
    }

    mock_completion = MagicMock()
    mock_message = MagicMock()
    mock_message.content = json.dumps(mock_response)
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_completion.choices = [mock_choice]

    with patch(
        "app.ai.change_order_parser.LLMClientFactory.create_client",
    ) as mock_create_client:
        from app.models.domain.ai import AIModel, AIProvider

        mock_provider = MagicMock(spec=AIProvider)
        mock_provider.id = uuid4()
        mock_model = MagicMock(spec=AIModel)
        mock_model.model_id = uuid4()

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_create_client.return_value = mock_client

        with patch.object(
            ChangeOrderRequirementParser,
            "_config_service",
        ) as mock_config_service:
            mock_config_service.list_providers = AsyncMock(return_value=[mock_provider])
            mock_config_service.list_models = AsyncMock(return_value=[mock_model])

            draft = await service.generate_draft(
                project_id=test_project.project_id,
                title="Test Change",
                description="Test description",
                reason="Test reason",
                actor_id=UUID(test_user["user_id"]),
            )

            # Verify branch naming
            assert draft.code.startswith("CO-")
            assert draft.branch_name == f"BR-{draft.code}"
            assert draft.branch == "main"

            # Verify the change order was created on main branch
            # but has a branch_name for the change order branch
            assert draft.branch == "main"
