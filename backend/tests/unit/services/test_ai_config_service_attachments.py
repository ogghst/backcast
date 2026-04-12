"""Tests for AI config service attachment handling."""
import pytest
from uuid import uuid4, UUID
from sqlalchemy import select
from app.models.domain.ai import AIConversationAttachment
from app.services.ai_config_service import AIConfigService


@pytest.mark.asyncio
async def test_add_message_with_attachments(db_session, ai_assistant_config_factory):
    """Test that add_message saves attachments with content to the database."""
    service = AIConfigService(db_session)

    # Create session
    session = await service.create_session(
        user_id=uuid4(),
        assistant_config_id=ai_assistant_config_factory.id,
    )

    attachments = [
        {
            "file_id": str(uuid4()),
            "filename": "test.txt",
            "content_type": "text/plain",
            "file_size": 1024,
            "content": "Hello, this is a text file.",
        }
    ]

    # Act
    message = await service.add_message(
        session_id=session.id,
        role="user",
        content="Hello with attachment",
        attachments=attachments,
    )

    # Assert - query attachments directly to avoid lazy loading issues
    result = await db_session.execute(
        select(AIConversationAttachment).where(
            AIConversationAttachment.message_id == str(message.id)
        )
    )
    attachment_list = result.scalars().all()

    assert len(attachment_list) == 1
    assert attachment_list[0].filename == "test.txt"
    assert attachment_list[0].content_type == "text/plain"
    assert attachment_list[0].content == "Hello, this is a text file."
    assert attachment_list[0].size == 1024


@pytest.mark.asyncio
async def test_add_message_with_multiple_attachments(db_session, ai_assistant_config_factory):
    """Test that multiple attachments with mixed content types are saved correctly."""
    service = AIConfigService(db_session)

    session = await service.create_session(
        user_id=uuid4(),
        assistant_config_id=ai_assistant_config_factory.id,
    )

    attachments = [
        {
            "file_id": str(uuid4()),
            "filename": "document1.pdf",
            "content_type": "application/pdf",
            "file_size": 2048,
            "content": "Extracted PDF text content here.",
        },
        {
            "file_id": str(uuid4()),
            "filename": "image.png",
            "content_type": "image/png",
            "file_size": 51200,
            "content": "iVBORw0KGgoAAAANSUhEUg==",
        },
    ]

    message = await service.add_message(
        session_id=session.id,
        role="user",
        content="Here are my files",
        attachments=attachments,
    )

    # Query attachments directly
    result = await db_session.execute(
        select(AIConversationAttachment).where(
            AIConversationAttachment.message_id == str(message.id)
        )
    )
    attachment_list = result.scalars().all()

    assert len(attachment_list) == 2
    filenames = {a.filename for a in attachment_list}
    assert filenames == {"document1.pdf", "image.png"}


@pytest.mark.asyncio
async def test_add_message_without_attachments(db_session, ai_assistant_config_factory):
    """Test that messages without attachments still work (backward compatibility)."""
    service = AIConfigService(db_session)

    session = await service.create_session(
        user_id=uuid4(),
        assistant_config_id=ai_assistant_config_factory.id,
    )

    # Call without attachments parameter
    message = await service.add_message(
        session_id=session.id,
        role="user",
        content="Hello without attachment",
    )

    # Query attachments directly - should be none
    result = await db_session.execute(
        select(AIConversationAttachment).where(
            AIConversationAttachment.message_id == str(message.id)
        )
    )
    attachment_list = result.scalars().all()

    assert len(attachment_list) == 0
