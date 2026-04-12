"""Unit tests for AI conversation attachments."""

from typing import Any

import pytest
from sqlalchemy import select
from uuid import uuid4, UUID

from app.models.domain.ai import AIConversationAttachment, AIConversationMessage, AIConversationSession, AIAssistantConfig, AIModel, AIProvider


@pytest.mark.asyncio
async def test_attachment_model_has_message_foreign_key(db_session: Any) -> None:
    """Test that AIConversationAttachment has a foreign key to AIConversationMessage.

    Context: Verifies the relationship between attachments and messages.
    Expected: Attachment model has message_id field that references messages table.
    """
    # Arrange: Create a user, provider, model, assistant config, session, and message
    # Create provider
    provider = AIProvider(
        provider_type="openai",
        name="Test Provider",
        base_url="https://api.openai.com/v1",
        is_active=True,
    )
    db_session.add(provider)
    await db_session.flush()

    # Create model
    model = AIModel(
        provider_id=provider.id,
        model_id="gpt-4",
        display_name="GPT-4",
        is_active=True,
    )
    db_session.add(model)
    await db_session.flush()

    # Create assistant config
    assistant_config = AIAssistantConfig(
        name="Test Assistant",
        model_id=model.id,
        system_prompt="You are a helpful assistant.",
        is_active=True,
    )
    db_session.add(assistant_config)
    await db_session.flush()

    # Create session
    session_obj = AIConversationSession(
        user_id=uuid4(),
        assistant_config_id=assistant_config.id,
        title="Test Session",
    )
    db_session.add(session_obj)
    await db_session.flush()

    # Create message
    message = AIConversationMessage(
        session_id=session_obj.id,
        role="user",
        content="Test message with attachment",
    )
    db_session.add(message)
    await db_session.flush()

    # Act: Create attachment with content field
    attachment = AIConversationAttachment(
        message_id=message.id,
        filename="test_image.png",
        content_type="image/png",
        content="iVBORw0KGgoAAAANSUhEUg==",
        size=1024,
    )
    db_session.add(attachment)
    await db_session.flush()

    # Assert: Verify attachment was created with message_id
    assert attachment.id is not None
    assert attachment.message_id == message.id
    assert attachment.filename == "test_image.png"
    assert attachment.content_type == "image/png"
    assert attachment.content == "iVBORw0KGgoAAAANSUhEUg=="
    assert attachment.size == 1024
    assert attachment.created_at is not None

    await db_session.commit()


@pytest.mark.asyncio
async def test_attachment_content_stored_correctly(db_session: Any) -> None:
    """Test that attachment content (extracted text or base64) is stored correctly.

    Context: Ensures file content is preserved for LLM consumption.
    Expected: Content field stores extracted text or base64 data.
    """
    # Arrange
    # Create minimal chain: provider -> model -> assistant -> session -> message
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

    message = AIConversationMessage(
        session_id=session_obj.id,
        role="user",
        content="Message with PDF attachment",
    )
    db_session.add(message)
    await db_session.flush()

    # Act: Create attachment with extracted text content
    extracted_text = "Quarterly Report 2026\nRevenue: $1.2M\nExpenses: $800K"
    attachment = AIConversationAttachment(
        message_id=message.id,
        filename="report.pdf",
        content_type="application/pdf",
        content=extracted_text,
        size=2048576,  # 2MB
    )
    db_session.add(attachment)
    await db_session.flush()

    # Assert: Verify content field is stored and retrievable
    retrieved = await db_session.execute(
        select(AIConversationAttachment).where(AIConversationAttachment.id == attachment.id)
    )
    attachment_obj = retrieved.scalar_one()

    assert attachment_obj.filename == "report.pdf"
    assert attachment_obj.content_type == "application/pdf"
    assert attachment_obj.content == extracted_text
    assert attachment_obj.size == 2048576
    assert attachment_obj.created_at is not None

    await db_session.commit()


@pytest.mark.asyncio
async def test_attachment_can_be_queried_by_message_id(db_session: Any) -> None:
    """Test that attachments can be queried by their message_id.

    Context: Frontend needs to fetch all attachments for a message.
    Expected: Query by message_id returns all attachments for that message.
    """
    # Arrange
    # Create minimal chain
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

    message = AIConversationMessage(
        session_id=session_obj.id,
        role="user",
        content="Message with multiple attachments",
    )
    db_session.add(message)
    await db_session.flush()

    # Create multiple attachments for the same message
    attachment1 = AIConversationAttachment(
        message_id=message.id,
        filename="image1.png",
        content_type="image/png",
        content="base64imagedata1",
        size=1024,
    )
    attachment2 = AIConversationAttachment(
        message_id=message.id,
        filename="image2.jpg",
        content_type="image/jpeg",
        content="base64imagedata2",
        size=2048,
    )
    db_session.add(attachment1)
    db_session.add(attachment2)
    await db_session.flush()

    # Act: Query attachments by message_id
    result = await db_session.execute(
        select(AIConversationAttachment).where(
            AIConversationAttachment.message_id == message.id
        )
    )
    attachments = result.scalars().all()

    # Assert: Should return both attachments
    assert len(attachments) == 2
    filenames = {a.filename for a in attachments}
    assert filenames == {"image1.png", "image2.jpg"}

    await db_session.commit()


@pytest.mark.asyncio
async def test_attachment_content_can_be_null(db_session: Any) -> None:
    """Test that attachment content field allows null values.

    Context: Attachments with unsupported types or failed extraction
    may have null content. The system should handle this gracefully.

    Expected: Attachment can be created with content=None.
    """
    # Arrange
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

    message = AIConversationMessage(
        session_id=session_obj.id,
        role="user",
        content="Message with unsupported attachment",
    )
    db_session.add(message)
    await db_session.flush()

    # Act: Create attachment with null content
    attachment = AIConversationAttachment(
        message_id=message.id,
        filename="archive.zip",
        content_type="application/zip",
        content=None,
        size=5120,
    )
    db_session.add(attachment)
    await db_session.flush()

    # Assert
    assert attachment.content is None
    assert attachment.filename == "archive.zip"

    await db_session.commit()
