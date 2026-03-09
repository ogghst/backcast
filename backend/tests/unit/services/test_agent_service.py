"""Tests for AgentService streaming functionality."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_service import AgentService
from app.ai.llm_client import LLMStreamingError
from app.models.domain.ai import AIAssistantConfig
from app.models.schemas.ai import (
    AIModelCreate,
    AIProviderCreate,
)


@pytest.mark.asyncio
async def test_chat_stream_sends_tokens(db_session: AsyncSession) -> None:
    """Test that chat_stream sends tokens via WebSocket."""
    service = AgentService(db_session)

    # Create provider and model in database
    from app.services.ai_config_service import AIConfigService

    config_service = AIConfigService(db_session)

    provider_in = AIProviderCreate(
        provider_type="openai",
        name="Test Provider",
        base_url="https://api.openai.com/v1",
    )
    provider = await config_service.create_provider(provider_in)

    model_in = AIModelCreate(
        model_id="gpt-4",
        display_name="GPT-4",
        provider_id=provider.id,
    )
    model = await config_service.create_model(model_in)

    # Create assistant config
    assistant_config = AIAssistantConfig(
        name="Test Assistant",
        model_id=str(model.id),
        system_prompt="You are a helpful assistant",
        temperature=0.7,
        max_tokens=1000,
        allowed_tools=None,
        is_active=True,
    )
    db_session.add(assistant_config)
    await db_session.flush()
    await db_session.refresh(assistant_config)

    # Mock WebSocket
    mock_websocket = MagicMock(spec=WebSocket)
    mock_websocket.send_json = AsyncMock()

    # Create mock chunks for streaming
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock()]
    chunk1.choices[0].delta.content = "Hello"
    chunk1.choices[0].delta.tool_calls = None
    chunk1.choices[0].finish_reason = None
    chunk1.choices[0].message = None

    chunk2 = MagicMock()
    chunk2.choices = [MagicMock()]
    chunk2.choices[0].delta.content = " world"
    chunk2.choices[0].delta.tool_calls = None
    chunk2.choices[0].finish_reason = "stop"
    chunk2.choices[0].message = None

    # Mock stream_with_error_handling to return our chunks
    async def mock_stream(*args: object, **kwargs: object) -> AsyncIterator[MagicMock]:
        yield chunk1
        yield chunk2

    with patch("app.ai.agent_service.stream_with_error_handling", side_effect=mock_stream):
        await service.chat_stream(
            message="Hello",
            assistant_config=assistant_config,
            session_id=None,
            user_id=uuid4(),
            websocket=mock_websocket,
            db=db_session,
        )

    # Verify tokens were sent
    token_calls = [
        call
        for call in mock_websocket.send_json.call_args_list
        if len(call[0]) > 0 and call[0][0].get("type") == "token"
    ]
    assert len(token_calls) >= 1
    assert token_calls[0][0][0]["content"] in ["Hello", " world"]


@pytest.mark.asyncio
async def test_chat_stream_handles_streaming_error(db_session: AsyncSession) -> None:
    """Test that chat_stream handles streaming errors gracefully."""
    service = AgentService(db_session)

    # Create provider and model in database
    from app.services.ai_config_service import AIConfigService

    config_service = AIConfigService(db_session)

    provider_in = AIProviderCreate(
        provider_type="openai",
        name="Test Provider",
        base_url="https://api.openai.com/v1",
    )
    provider = await config_service.create_provider(provider_in)

    model_in = AIModelCreate(
        model_id="gpt-4",
        display_name="GPT-4",
        provider_id=provider.id,
    )
    model = await config_service.create_model(model_in)

    # Create assistant config
    assistant_config = AIAssistantConfig(
        name="Test Assistant",
        model_id=str(model.id),
        system_prompt="You are a helpful assistant",
        temperature=0.7,
        max_tokens=1000,
        allowed_tools=None,
        is_active=True,
    )
    db_session.add(assistant_config)
    await db_session.flush()
    await db_session.refresh(assistant_config)

    # Mock WebSocket
    mock_websocket = MagicMock(spec=WebSocket)
    mock_websocket.send_json = AsyncMock()

    # Mock streaming error
    async def mock_stream_with_error(*args: object, **kwargs: object) -> AsyncIterator[MagicMock]:
        raise LLMStreamingError("Connection failed")
        yield  # Never reached

    with patch(
        "app.ai.agent_service.stream_with_error_handling",
        side_effect=mock_stream_with_error,
    ):
        await service.chat_stream(
            message="Hello",
            assistant_config=assistant_config,
            session_id=None,
            user_id=uuid4(),
            websocket=mock_websocket,
            db=db_session,
        )

    # Verify error message was sent
    error_calls = [
        call
        for call in mock_websocket.send_json.call_args_list
        if len(call[0]) > 0 and call[0][0].get("type") == "error"
    ]
    assert len(error_calls) >= 1


@pytest.mark.asyncio
async def test_chat_stream_sends_complete_message(db_session: AsyncSession) -> None:
    """Test that chat_stream sends complete message at the end."""
    service = AgentService(db_session)

    # Create provider and model in database
    from app.services.ai_config_service import AIConfigService

    config_service = AIConfigService(db_session)

    provider_in = AIProviderCreate(
        provider_type="openai",
        name="Test Provider",
        base_url="https://api.openai.com/v1",
    )
    provider = await config_service.create_provider(provider_in)

    model_in = AIModelCreate(
        model_id="gpt-4",
        display_name="GPT-4",
        provider_id=provider.id,
    )
    model = await config_service.create_model(model_in)

    # Create assistant config
    assistant_config = AIAssistantConfig(
        name="Test Assistant",
        model_id=str(model.id),
        system_prompt="You are a helpful assistant",
        temperature=0.7,
        max_tokens=1000,
        allowed_tools=None,
        is_active=True,
    )
    db_session.add(assistant_config)
    await db_session.flush()
    await db_session.refresh(assistant_config)

    # Mock WebSocket
    mock_websocket = MagicMock(spec=WebSocket)
    mock_websocket.send_json = AsyncMock()

    # Create mock chunk
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta.content = "Response"
    chunk.choices[0].delta.tool_calls = None
    chunk.choices[0].finish_reason = "stop"
    chunk.choices[0].message = None

    async def mock_stream(*args: object, **kwargs: object) -> AsyncIterator[MagicMock]:
        yield chunk

    with patch("app.ai.agent_service.stream_with_error_handling", side_effect=mock_stream):
        await service.chat_stream(
            message="Hello",
            assistant_config=assistant_config,
            session_id=None,
            user_id=uuid4(),
            websocket=mock_websocket,
            db=db_session,
        )

    # Verify complete message was sent
    complete_calls = [
        call
        for call in mock_websocket.send_json.call_args_list
        if len(call[0]) > 0 and call[0][0].get("type") == "complete"
    ]
    assert len(complete_calls) == 1
    assert "session_id" in complete_calls[0][0][0]
    assert "message_id" in complete_calls[0][0][0]


@pytest.mark.asyncio
async def test_chat_stream_handles_websocket_disconnect(db_session: AsyncSession) -> None:
    """Test that chat_stream handles WebSocket disconnection gracefully."""
    service = AgentService(db_session)

    # Create provider and model in database
    from app.services.ai_config_service import AIConfigService

    config_service = AIConfigService(db_session)

    provider_in = AIProviderCreate(
        provider_type="openai",
        name="Test Provider",
        base_url="https://api.openai.com/v1",
    )
    provider = await config_service.create_provider(provider_in)

    model_in = AIModelCreate(
        model_id="gpt-4",
        display_name="GPT-4",
        provider_id=provider.id,
    )
    model = await config_service.create_model(model_in)

    # Create assistant config
    assistant_config = AIAssistantConfig(
        name="Test Assistant",
        model_id=str(model.id),
        system_prompt="You are a helpful assistant",
        temperature=0.7,
        max_tokens=1000,
        allowed_tools=None,
        is_active=True,
    )
    db_session.add(assistant_config)
    await db_session.flush()
    await db_session.refresh(assistant_config)

    # Mock WebSocket that raises exception on send
    mock_websocket = MagicMock(spec=WebSocket)
    mock_websocket.send_json = AsyncMock(side_effect=RuntimeError("WebSocket closed"))

    # Create mock chunk
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta.content = "Response"
    chunk.choices[0].delta.tool_calls = None
    chunk.choices[0].finish_reason = "stop"
    chunk.choices[0].message = None

    async def mock_stream(*args: object, **kwargs: object) -> AsyncIterator[MagicMock]:
        yield chunk

    with patch("app.ai.agent_service.stream_with_error_handling", side_effect=mock_stream):
        # Should not raise exception even though WebSocket fails
        await service.chat_stream(
            message="Hello",
            assistant_config=assistant_config,
            session_id=None,
            user_id=uuid4(),
            websocket=mock_websocket,
            db=db_session,
        )


@pytest.mark.asyncio
async def test_chat_stream_uses_existing_session(db_session: AsyncSession) -> None:
    """Test that chat_stream uses existing session when session_id is provided."""
    service = AgentService(db_session)

    # Create provider and model in database
    from app.services.ai_config_service import AIConfigService

    config_service = AIConfigService(db_session)

    provider_in = AIProviderCreate(
        provider_type="openai",
        name="Test Provider",
        base_url="https://api.openai.com/v1",
    )
    provider = await config_service.create_provider(provider_in)

    model_in = AIModelCreate(
        model_id="gpt-4",
        display_name="GPT-4",
        provider_id=provider.id,
    )
    model = await config_service.create_model(model_in)

    # Create assistant config
    assistant_config = AIAssistantConfig(
        name="Test Assistant",
        model_id=str(model.id),
        system_prompt="You are a helpful assistant",
        temperature=0.7,
        max_tokens=1000,
        allowed_tools=None,
        is_active=True,
    )
    db_session.add(assistant_config)
    await db_session.flush()
    await db_session.refresh(assistant_config)

    # Create existing session
    from app.models.domain.ai import AIConversationSession

    existing_session = AIConversationSession(
        user_id=str(uuid4()),
        assistant_config_id=str(assistant_config.id),
    )
    db_session.add(existing_session)
    await db_session.flush()
    await db_session.refresh(existing_session)

    # Mock WebSocket
    mock_websocket = MagicMock(spec=WebSocket)
    mock_websocket.send_json = AsyncMock()

    # Create mock chunk
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta.content = "Response"
    chunk.choices[0].delta.tool_calls = None
    chunk.choices[0].finish_reason = "stop"
    chunk.choices[0].message = None

    async def mock_stream(*args: object, **kwargs: object) -> AsyncIterator[MagicMock]:
        yield chunk

    with patch("app.ai.agent_service.stream_with_error_handling", side_effect=mock_stream):
        await service.chat_stream(
            message="Hello",
            assistant_config=assistant_config,
            session_id=existing_session.id,
            user_id=uuid4(),
            websocket=mock_websocket,
            db=db_session,
        )

    # Verify messages were sent
    assert mock_websocket.send_json.call_count > 0
