"""Integration tests for agent vision integration.

Tests verify that the agent properly handles image attachments in the chat flow,
including formatting multimodal messages with base64 data URLs and passing them
to the LLM.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.ai.agent_service import AgentService
from app.models.domain.ai import (
    AIConversationAttachment,
    AIConversationMessage,
    AIConversationSession,
    AIProvider,
    AIModel,
    AIAssistantConfig,
)


@pytest.mark.asyncio
async def test_agent_formats_multimodal_messages_for_vision(
    db_session: Any,
) -> None:
    """Test that agent formats multimodal messages when user has image attachments.

    Context: When a user sends a message with image attachments, the agent
    should use format_multimodal_messages to create the proper content structure
    for vision models using base64 data URLs.

    Expected:
        - User message with attachments triggers format_multimodal_messages
        - Formatted content includes both text and image_url blocks
        - Image uses data:image/...;base64,... data URL format
    """
    # Arrange: Create provider, model, assistant config, and session
    provider = AIProvider(
        provider_type="openai",
        name="Test Provider",
        base_url="https://api.openai.com/v1",
        is_active=True,
    )
    db_session.add(provider)
    await db_session.flush()

    model = AIModel(
        provider_id=provider.id,
        model_id="gpt-4-vision-preview",
        display_name="GPT-4 Vision",
        is_active=True,
    )
    db_session.add(model)
    await db_session.flush()

    assistant_config = AIAssistantConfig(
        name="Vision Assistant",
        model_id=model.id,
        system_prompt="You are a helpful assistant with vision capabilities.",
        is_active=True,
    )
    db_session.add(assistant_config)
    await db_session.flush()

    session_obj = AIConversationSession(
        user_id=uuid4(),
        assistant_config_id=assistant_config.id,
        title="Vision Test Session",
    )
    db_session.add(session_obj)
    await db_session.flush()

    # Create user message
    message = AIConversationMessage(
        session_id=session_obj.id,
        role="user",
        content="What do you see in this image?",
    )
    db_session.add(message)
    await db_session.flush()

    # Create attachment record with base64 content
    base64_content = "iVBORw0KGgoAAAANSUhEUg=="
    attachment = AIConversationAttachment(
        message_id=message.id,
        filename="chart.png",
        content_type="image/png",
        content=base64_content,
        size=102400,
    )
    db_session.add(attachment)
    await db_session.flush()
    await db_session.commit()

    # Act: Format multimodal message using the agent service
    agent_service = AgentService(db_session)

    # Get the message with attachments eagerly loaded
    result = await db_session.execute(
        select(AIConversationMessage)
        .where(AIConversationMessage.id == message.id)
        .options(selectinload(AIConversationMessage.attachments))
    )
    msg = result.scalar_one()

    # Build attachment dicts as agent service does
    attachment_dicts = [
        {
            "file_id": str(a.id),
            "filename": a.filename,
            "content_type": a.content_type,
            "content": a.content,
            "file_size": a.size,
        }
        for a in msg.attachments
    ]

    # Format the multimodal message
    formatted_content = await agent_service.format_multimodal_messages(
        text_content=msg.content,
        attachments=attachment_dicts,
    )

    # Assert: Verify the format
    assert isinstance(formatted_content, list)
    assert len(formatted_content) == 2

    # First item is text
    assert formatted_content[0]["type"] == "text"
    assert "What do you see" in formatted_content[0]["text"]

    # Second item is image_url with data URL
    assert formatted_content[1]["type"] == "image_url"
    assert "url" in formatted_content[1]["image_url"]
    data_url = formatted_content[1]["image_url"]["url"]
    assert data_url.startswith("data:image/png;base64,")
    assert base64_content in data_url


@pytest.mark.asyncio
async def test_agent_handles_mixed_attachments(
    db_session: Any,
) -> None:
    """Test that agent handles messages with both images and documents.

    Context: Users may attach both images (for vision) and documents (for reference).
    Images should be formatted as image_url data URLs, documents as inline text blocks.

    Expected:
        - Image attachments get image_url data URL formatting
        - Document attachments get inline text content blocks
        - All attachment types are handled correctly
    """
    # Arrange: Create session and message
    provider = AIProvider(
        provider_type="openai",
        name="Test Provider",
        is_active=True,
    )
    db_session.add(provider)
    await db_session.flush()

    model = AIModel(
        provider_id=provider.id,
        model_id="gpt-4",
        display_name="GPT-4",
        is_active=True,
    )
    db_session.add(model)
    await db_session.flush()

    assistant_config = AIAssistantConfig(
        name="Assistant",
        model_id=model.id,
        is_active=True,
    )
    db_session.add(assistant_config)
    await db_session.flush()

    session_obj = AIConversationSession(
        user_id=uuid4(),
        assistant_config_id=assistant_config.id,
    )
    db_session.add(session_obj)
    await db_session.flush()

    # Act: Format with mixed attachments
    agent_service = AgentService(db_session)

    csv_content = "name,value\nRevenue,1000"
    formatted_content = await agent_service.format_multimodal_messages(
        text_content="Analyze the image and the data",
        attachments=[
            {
                "id": str(uuid4()),
                "filename": "screenshot.png",
                "content_type": "image/png",
                "content": "base64imagedata",
                "size": 102400,
            },
            {
                "id": str(uuid4()),
                "filename": "data.csv",
                "content_type": "text/csv",
                "content": csv_content,
                "size": 2048,
            }
        ],
    )

    # Assert: text + image + document text block
    assert len(formatted_content) == 3

    # First block is text
    assert formatted_content[0]["type"] == "text"

    # Second block is image_url with data URL
    assert formatted_content[1]["type"] == "image_url"
    assert formatted_content[1]["image_url"]["url"].startswith("data:image/png;base64,")

    # Third block is inline text with CSV content
    assert formatted_content[2]["type"] == "text"
    assert "data.csv" in formatted_content[2]["text"]
    assert csv_content in formatted_content[2]["text"]


@pytest.mark.asyncio
async def test_agent_handles_no_attachments(
    db_session: Any,
) -> None:
    """Test that agent handles messages without attachments gracefully.

    Context: Most messages don't have attachments. The agent should work normally.

    Expected:
        - Messages without attachments work as before
        - No special formatting is applied
        - Backward compatibility is maintained
    """
    # Arrange
    agent_service = AgentService(db_session)

    # Act: Format message with no attachments
    formatted_content = await agent_service.format_multimodal_messages(
        text_content="What is the capital of France?",
        attachments=None,
    )

    # Assert: Should just have text content
    assert len(formatted_content) == 1
    assert formatted_content[0]["type"] == "text"
    assert "capital of France" in formatted_content[0]["text"]


@pytest.mark.asyncio
async def test_agent_handles_empty_attachments_list(
    db_session: Any,
) -> None:
    """Test that agent handles empty attachments list.

    Context: Frontend may pass an empty list for messages with no attachments.

    Expected:
        - Empty list is treated same as None
        - Only text content is returned
    """
    # Arrange
    agent_service = AgentService(db_session)

    # Act
    formatted_content = await agent_service.format_multimodal_messages(
        text_content="Hello",
        attachments=[],
    )

    # Assert
    assert len(formatted_content) == 1
    assert formatted_content[0]["type"] == "text"
    assert formatted_content[0]["text"] == "Hello"
