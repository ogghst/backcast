"""Unit tests for ChangeOrderRequirementParser.

Tests AI-powered requirement parsing for change order draft generation.
"""

import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from app.ai.change_order_parser import ChangeOrderRequirementParser
from app.models.domain.ai import AIModel, AIProvider


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_provider():
    """Create a mock AI provider."""
    provider = MagicMock(spec=AIProvider)
    provider.id = uuid4()
    provider.provider_type = "openai"
    provider.base_url = "https://api.openai.com/v1"
    return provider


@pytest.fixture
def mock_model():
    """Create a mock AI model."""
    model = MagicMock(spec=AIModel)
    model.model_id = uuid4()
    model.name = "gpt-4"
    return model


@pytest.fixture
def parser(mock_session):
    """Create a ChangeOrderRequirementParser instance."""
    return ChangeOrderRequirementParser(mock_session)


@pytest.mark.asyncio
async def test_parse_requirements_success(parser, mock_provider, mock_model):
    """Test successful requirement parsing with AI."""
    project_id = uuid4()

    # Mock LLM response
    mock_response = {
        "title": "Upgrade Controller System",
        "description": "Replace legacy PLC controllers with modern system",
        "reason": "Legacy system end-of-life, need modern features",
        "budget_impact": 50000.0,
        "schedule_impact_days": 10,
        "risk_level": "Medium",
        "affected_entities": ["WBE-001", "CE-002"],
        "recommendation": "Approve with conditions",
        "confidence_score": 0.85,
    }

    # Mock chat completion
    mock_completion = MagicMock(spec=ChatCompletion)
    mock_message = MagicMock(spec=ChatCompletionMessage)
    mock_message.content = json.dumps(mock_response)
    mock_choice = MagicMock(spec=Choice)
    mock_choice.message = mock_message
    mock_completion.choices = [mock_choice]

    with patch(
        "app.ai.change_order_parser.LLMClientFactory.create_client",
    ) as mock_create_client, patch(
        "app.ai.change_order_parser.AIConfigService.list_providers",
        new_callable=AsyncMock,
        return_value=[mock_provider],
    ), patch(
        "app.ai.change_order_parser.AIConfigService.list_provider_configs",
        new_callable=AsyncMock,
        return_value=[],
    ), patch(
        "app.ai.change_order_parser.AIConfigService.list_models",
        new_callable=AsyncMock,
        return_value=[mock_model],
    ):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_create_client.return_value = mock_client

        result = await parser.parse_requirements(
            project_id=project_id,
            title="Upgrade Controller System",
            description="Replace legacy PLC controllers with modern system",
            reason="Legacy system end-of-life",
        )

        # Verify parsing results
        assert result["title"] == "Upgrade Controller System"
        assert result["description"] == "Replace legacy PLC controllers with modern system"
        assert result["reason"] == "Legacy system end-of-life, need modern features"
        assert result["budget_impact"] == Decimal("50000")
        assert result["schedule_impact_days"] == 10
        assert result["risk_level"] == "Medium"
        assert result["affected_entities"] == ["WBE-001", "CE-002"]
        assert result["recommendation"] == "Approve with conditions"
        assert result["confidence_score"] == 0.85


@pytest.mark.asyncio
async def test_parse_requirements_invalid_json(parser, mock_provider, mock_model):
    """Test requirement parsing with invalid JSON response."""
    project_id = uuid4()

    # Mock chat completion with invalid JSON
    mock_completion = MagicMock(spec=ChatCompletion)
    mock_message = MagicMock(spec=ChatCompletionMessage)
    mock_message.content = "This is not valid JSON"
    mock_choice = MagicMock(spec=Choice)
    mock_choice.message = mock_message
    mock_completion.choices = [mock_choice]

    with patch(
        "app.ai.change_order_parser.LLMClientFactory.create_client",
    ) as mock_create_client, patch(
        "app.ai.change_order_parser.AIConfigService.list_providers",
        new_callable=AsyncMock,
        return_value=[mock_provider],
    ), patch(
        "app.ai.change_order_parser.AIConfigService.list_provider_configs",
        new_callable=AsyncMock,
        return_value=[],
    ), patch(
        "app.ai.change_order_parser.AIConfigService.list_models",
        new_callable=AsyncMock,
        return_value=[mock_model],
    ):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_create_client.return_value = mock_client

        with pytest.raises(ValueError, match="Invalid JSON response"):
            await parser.parse_requirements(
                project_id=project_id,
                title="Test",
                description="Test",
                reason="Test",
            )


@pytest.mark.asyncio
async def test_validate_risk_level(parser):
    """Test risk level validation and normalization."""
    # Test valid risk levels
    assert parser._validate_risk_level("low") == "Low"
    assert parser._validate_risk_level("MEDIUM") == "Medium"
    assert parser._validate_risk_level("High") == "High"

    # Test invalid risk level defaults to Medium
    assert parser._validate_risk_level("Critical") == "Medium"
    assert parser._validate_risk_level("") == "Medium"


@pytest.mark.asyncio
async def test_parse_requirements_no_provider(parser):
    """Test requirement parsing when no AI provider is configured."""
    with patch(
        "app.ai.change_order_parser.AIConfigService.list_providers",
        new_callable=AsyncMock,
        return_value=[],
    ):
        with pytest.raises(ValueError, match="No AI provider configured"):
            await parser.parse_requirements(
                project_id=uuid4(),
                title="Test",
                description="Test",
                reason="Test",
            )


@pytest.mark.asyncio
async def test_parse_requirements_no_model(parser, mock_provider):
    """Test requirement parsing when no AI model is configured."""
    with patch(
        "app.ai.change_order_parser.AIConfigService.list_providers",
        new_callable=AsyncMock,
        return_value=[mock_provider],
    ), patch(
        "app.ai.change_order_parser.AIConfigService.list_provider_configs",
        new_callable=AsyncMock,
        return_value=[],
    ), patch(
        "app.ai.change_order_parser.AIConfigService.list_models",
        new_callable=AsyncMock,
        return_value=[],
    ):
        with pytest.raises(ValueError, match="No AI model configured"):
            await parser.parse_requirements(
                project_id=uuid4(),
                title="Test",
                description="Test",
                reason="Test",
            )


@pytest.mark.asyncio
async def test_analyze_with_impact_only(parser, mock_provider, mock_model):
    """Test analyze_with_impact without existing change order."""
    project_id = uuid4()

    mock_response = {
        "title": "Test Change",
        "description": "Test description",
        "reason": "Test reason",
        "budget_impact": 10000.0,
        "schedule_impact_days": 5,
        "risk_level": "Low",
        "affected_entities": [],
        "recommendation": "Approve",
        "confidence_score": 0.9,
    }

    mock_completion = MagicMock(spec=ChatCompletion)
    mock_message = MagicMock(spec=ChatCompletionMessage)
    mock_message.content = json.dumps(mock_response)
    mock_choice = MagicMock(spec=Choice)
    mock_choice.message = mock_message
    mock_completion.choices = [mock_choice]

    with patch(
        "app.ai.change_order_parser.LLMClientFactory.create_client",
    ) as mock_create_client, patch(
        "app.ai.change_order_parser.AIConfigService.list_providers",
        new_callable=AsyncMock,
        return_value=[mock_provider],
    ), patch(
        "app.ai.change_order_parser.AIConfigService.list_provider_configs",
        new_callable=AsyncMock,
        return_value=[],
    ), patch(
        "app.ai.change_order_parser.AIConfigService.list_models",
        new_callable=AsyncMock,
        return_value=[mock_model],
    ):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_create_client.return_value = mock_client

        result = await parser.analyze_with_impact(
            project_id=project_id,
            title="Test Change",
            description="Test description",
            reason="Test reason",
        )

        assert result["title"] == "Test Change"
        # When no change_order_id is provided, actual_impact_available is not set
        # because we skip the impact analysis entirely
        assert "analysis_summary" in result
