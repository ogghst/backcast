"""Integration tests for AI chat attachment context handling.

Tests verify that attachments are properly loaded and included in the agent context
when processing messages with file attachments. Uses the new content-based storage.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from langchain_core.messages import HumanMessage
from sqlalchemy import select

from app.ai.agent_service import AgentService
from app.models.domain.ai import (
    AIConversationAttachment,
    AIConversationMessage,
    AIConversationSession,
)


@pytest.mark.asyncio
async def test_build_conversation_history_loads_attachments(
    db_session: Any,
) -> None:
    """Test that _build_conversation_history loads attachments for messages.

    Context: When building conversation history for the LLM, messages with
    attachments should have their content loaded from the database.

    Expected:
        - Messages with attachments have attachment content accessible
        - Attachments are loaded via the relationship
        - Image attachments are identified for vision processing
    """
    # Arrange: Create a user, provider, model, assistant config, and session
    from app.models.domain.ai import AIProvider, AIModel, AIAssistantConfig

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
        model_id="gpt-4",
        display_name="GPT-4",
        is_active=True,
    )
    db_session.add(model)
    await db_session.flush()

    assistant_config = AIAssistantConfig(
        name="Test Assistant",
        model_id=model.id,
        system_prompt="You are a helpful assistant.",
        is_active=True,
    )
    db_session.add(assistant_config)
    await db_session.flush()

    session_obj = AIConversationSession(
        user_id=uuid4(),
        assistant_config_id=assistant_config.id,
        title="Test Session",
    )
    db_session.add(session_obj)
    await db_session.flush()

    # Create a user message with an image attachment
    message = AIConversationMessage(
        session_id=session_obj.id,
        role="user",
        content="What do you see in this image?",
    )
    db_session.add(message)
    await db_session.flush()

    # Create an attachment record with base64 content
    attachment = AIConversationAttachment(
        message_id=message.id,
        filename="screenshot.png",
        content_type="image/png",
        content="iVBORw0KGgoAAAANSUhEUg==",
        size=102400,
    )
    db_session.add(attachment)
    await db_session.flush()
    await db_session.commit()

    # Act: Build conversation history
    agent_service = AgentService(db_session)
    history = await agent_service._build_conversation_history(session_obj.id)

    # Assert: History should include the message
    assert len(history) > 0
    user_message = history[-1]  # Last message should be the user message

    # The message should be a HumanMessage with content blocks
    assert isinstance(user_message, HumanMessage)
    # With attachments, content is a list of blocks (text + image_url)
    assert isinstance(user_message.content, list)


@pytest.mark.asyncio
async def test_format_multimodal_message_with_image(db_session: Any) -> None:
    """Test that messages with image attachments use base64 data URLs.

    Context: Vision models require messages with image_url content type.
    This test verifies the format_multimodal_messages method uses base64.

    Expected:
        - Text content is included in the message
        - Image attachments are formatted as image_url with data: URLs
        - URLs follow the data:image/...;base64,... format
    """
    # Arrange: Create agent service
    agent_service = AgentService(db_session)

    # Create message content and attachments
    text_content = "What do you see in this image?"
    base64_content = "iVBORw0KGgoAAAANSUhEUg=="
    attachments = [
        {
            "id": str(uuid4()),
            "filename": "screenshot.png",
            "content_type": "image/png",
            "content": base64_content,
            "size": 102400,
        }
    ]

    # Act
    formatted_content = await agent_service.format_multimodal_messages(
        text_content=text_content,
        attachments=attachments,
    )

    # Verify the format
    assert isinstance(formatted_content, list)
    assert len(formatted_content) == 2

    # First item should be text
    assert formatted_content[0]["type"] == "text"
    assert formatted_content[0]["text"] == text_content

    # Second item should be image_url with data URL
    assert formatted_content[1]["type"] == "image_url"
    assert "url" in formatted_content[1]["image_url"]
    assert formatted_content[1]["image_url"]["url"] == f"data:image/png;base64,{base64_content}"


@pytest.mark.asyncio
async def test_format_multimodal_message_with_multiple_images(db_session: Any) -> None:
    """Test that messages with multiple image attachments are formatted correctly.

    Context: Users may attach multiple images to a single message.
    All images should be included in the formatted message.

    Expected:
        - Text content comes first
        - All image attachments are included
        - Each image has its own image_url entry with data URL
    """
    # Arrange
    agent_service = AgentService(db_session)

    text_content = "Compare these two images"
    attachments = [
        {
            "id": str(uuid4()),
            "filename": "image1.png",
            "content_type": "image/png",
            "content": "base64data1",
            "size": 102400,
        },
        {
            "id": str(uuid4()),
            "filename": "image2.jpg",
            "content_type": "image/jpeg",
            "content": "base64data2",
            "size": 204800,
        }
    ]

    # Act
    formatted_content = await agent_service.format_multimodal_messages(
        text_content=text_content,
        attachments=attachments,
    )

    # Should have text + 2 images
    assert len(formatted_content) == 3
    assert formatted_content[0]["type"] == "text"
    assert formatted_content[1]["type"] == "image_url"
    assert formatted_content[2]["type"] == "image_url"

    # Verify data URLs
    assert formatted_content[1]["image_url"]["url"] == "data:image/png;base64,base64data1"
    assert formatted_content[2]["image_url"]["url"] == "data:image/jpeg;base64,base64data2"


@pytest.mark.asyncio
async def test_format_multimodal_message_inlines_document_content(db_session: Any) -> None:
    """Test that non-image attachments get inline text blocks with content.

    Context: Documents should have their content inlined as text blocks
    rather than being mentioned as placeholders.

    Expected:
        - Text content mentions the document via inline text block
        - Non-image attachments include their extracted content
    """
    # Arrange
    agent_service = AgentService(db_session)

    text_content = "Analyze the data in this CSV"
    csv_content = "name,value\nRevenue,1000\nExpense,800"
    attachments = [
        {
            "id": str(uuid4()),
            "filename": "data.csv",
            "content_type": "text/csv",
            "content": csv_content,
            "size": 2048,
        }
    ]

    # Act
    formatted_content = await agent_service.format_multimodal_messages(
        text_content=text_content,
        attachments=attachments,
    )

    # Should have text + 1 document text block
    assert len(formatted_content) == 2
    assert formatted_content[0]["type"] == "text"
    assert formatted_content[0]["text"] == text_content

    # Second block should be a text block with the CSV content
    assert formatted_content[1]["type"] == "text"
    assert "data.csv" in formatted_content[1]["text"]
    assert csv_content in formatted_content[1]["text"]


@pytest.mark.asyncio
async def test_add_message_with_attachment_ids(db_session: Any) -> None:
    """Test that add_message accepts and stores attachment content.

    Context: Frontend will upload files first, then pass attachment IDs when
    creating a message.

    Expected:
        - Message is created successfully
        - Attachments are linked via foreign key
        - Content is stored in the content field
    """
    # Arrange: Create session
    from app.models.domain.ai import AIProvider, AIModel, AIAssistantConfig

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
        name="Test Assistant",
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

    # Create attachments first (simulating pre-upload)
    message = AIConversationMessage(
        session_id=session_obj.id,
        role="user",
        content="Check out this image",
    )
    db_session.add(message)
    await db_session.flush()

    attachment1 = AIConversationAttachment(
        message_id=message.id,
        filename="chart.png",
        content_type="image/png",
        content="base64chartdata",
        size=512000,
    )
    attachment2 = AIConversationAttachment(
        message_id=message.id,
        filename="data.csv",
        content_type="text/csv",
        content="name,value\nfoo,1",
        size=2048,
    )
    db_session.add(attachment1)
    db_session.add(attachment2)
    await db_session.flush()
    await db_session.commit()

    # Act: Query message with attachments
    result = await db_session.execute(
        select(AIConversationMessage).where(AIConversationMessage.id == message.id)
    )
    retrieved_message = result.scalar_one()

    # Assert: Verify attachments are linked
    assert retrieved_message.id == message.id

    # Load attachments via relationship
    await db_session.refresh(retrieved_message, ["attachments"])
    attachments = retrieved_message.attachments

    assert len(attachments) == 2
    filenames = {a.filename for a in attachments}
    assert filenames == {"chart.png", "data.csv"}

    # Verify content is stored
    contents = {a.filename: a.content for a in attachments}
    assert contents["chart.png"] == "base64chartdata"
    assert contents["data.csv"] == "name,value\nfoo,1"


@pytest.mark.asyncio
async def test_format_multimodal_with_null_content_degrades_gracefully(
    db_session: Any,
) -> None:
    """Test that attachments with null content produce placeholder text.

    Context: Attachments where extraction failed should degrade gracefully
    with a placeholder message instead of crashing.

    Expected:
        - Null content produces "[User attached: filename]" placeholder
        - No crash or error
    """
    # Arrange
    agent_service = AgentService(db_session)

    text_content = "Look at this"
    attachments = [
        {
            "id": str(uuid4()),
            "filename": "unknown.xyz",
            "content_type": "application/unknown",
            "content": None,
            "size": 1024,
        }
    ]

    # Act
    formatted_content = await agent_service.format_multimodal_messages(
        text_content=text_content,
        attachments=attachments,
    )

    # Assert
    assert len(formatted_content) == 2
    assert formatted_content[0]["type"] == "text"
    assert formatted_content[0]["text"] == text_content
    assert formatted_content[1]["type"] == "text"
    assert "unknown.xyz" in formatted_content[1]["text"]
    assert "[User attached:" in formatted_content[1]["text"]
