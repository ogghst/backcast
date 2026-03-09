"""Tests for LLM Client Factory and streaming support."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.llm_client import (
    LLMClientFactory,
    LLMStreamingError,
    stream_with_error_handling,
    verify_streaming_capability,
)
from app.models.domain.ai import AIProvider
from app.services.ai_config_service import AIConfigService


class MockAPIError(Exception):
    """Mock API error for testing."""

    pass


class MockConnectionError(Exception):
    """Mock connection error for testing."""

    pass


class MockRateLimitError(Exception):
    """Mock rate limit error for testing."""

    pass


@pytest.mark.asyncio
async def test_create_client_openai(db_session) -> None:
    """Test creating an OpenAI client."""
    provider = AIProvider(
        id="test-provider-id",
        provider_type="openai",
        name="Test OpenAI Provider",
        base_url="https://api.openai.com/v1",
        is_active=True,
    )

    config_service = AIConfigService(db_session)

    # Mock the config values
    with patch.object(
        config_service,
        "list_provider_configs",
        new_callable=AsyncMock,
        return_value=[],
    ):
        client = await LLMClientFactory.create_client(provider, config_service)

        # Verify client was created
        assert client is not None
        assert hasattr(client, "chat")
        assert hasattr(client.chat, "completions")


@pytest.mark.asyncio
async def test_create_client_ollama(db_session) -> None:
    """Test creating an Ollama client."""
    provider = AIProvider(
        id="test-provider-id",
        provider_type="ollama",
        name="Test Ollama Provider",
        base_url="http://localhost:11434",
        is_active=True,
    )

    config_service = AIConfigService(db_session)

    # Mock the config values
    with patch.object(
        config_service,
        "list_provider_configs",
        new_callable=AsyncMock,
        return_value=[],
    ):
        client = await LLMClientFactory.create_client(provider, config_service)

        # Verify client was created
        assert client is not None
        assert hasattr(client, "chat")


@pytest.mark.asyncio
async def test_create_client_ollama_missing_base_url(db_session) -> None:
    """Test that creating an Ollama client without base_url raises ValueError."""
    provider = AIProvider(
        id="test-provider-id",
        provider_type="ollama",
        name="Test Ollama Provider",
        base_url=None,
        is_active=True,
    )

    config_service = AIConfigService(db_session)

    # Mock the config values with no base_url
    with patch.object(
        config_service,
        "list_provider_configs",
        new_callable=AsyncMock,
        return_value=[],
    ):
        with pytest.raises(ValueError, match="Ollama provider requires base_url"):
            await LLMClientFactory.create_client(provider, config_service)


@pytest.mark.asyncio
async def test_verify_streaming_capability_success() -> None:
    """Test successful streaming capability verification."""
    mock_client = MagicMock()

    # Create a mock stream that yields a chunk
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]

    # Mock the async iterator
    async def mock_stream():
        yield mock_chunk

    mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

    result = await verify_streaming_capability(mock_client)

    # Verify streaming is supported
    assert result is True
    mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_verify_streaming_capability_api_error() -> None:
    """Test streaming capability verification with API error."""
    mock_client = MagicMock()

    # Mock API error
    mock_client.chat.completions.create = AsyncMock(
        side_effect=MockAPIError("API Error")
    )

    with pytest.raises(LLMStreamingError, match="Unexpected error during streaming verification"):
        await verify_streaming_capability(mock_client)


@pytest.mark.asyncio
async def test_verify_streaming_capability_connection_error() -> None:
    """Test streaming capability verification with connection error."""
    mock_client = MagicMock()

    # Mock connection error
    mock_client.chat.completions.create = AsyncMock(
        side_effect=MockConnectionError("Connection failed")
    )

    with pytest.raises(LLMStreamingError, match="Unexpected error during streaming verification"):
        await verify_streaming_capability(mock_client)


@pytest.mark.asyncio
async def test_verify_streaming_capability_rate_limit_error() -> None:
    """Test streaming capability verification with rate limit error."""
    mock_client = MagicMock()

    # Mock rate limit error
    mock_client.chat.completions.create = AsyncMock(
        side_effect=MockRateLimitError("Rate limit exceeded")
    )

    with pytest.raises(LLMStreamingError, match="Unexpected error during streaming verification"):
        await verify_streaming_capability(mock_client)


@pytest.mark.asyncio
async def test_stream_with_error_handling_success() -> None:
    """Test successful streaming with error handling."""
    mock_client = MagicMock()

    # Create mock chunks
    mock_chunks = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content=" world"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content=None))]),
    ]

    # Mock the async iterator
    async def mock_stream():
        for chunk in mock_chunks:
            yield chunk

    mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

    # Collect chunks
    chunks = []
    async for chunk in stream_with_error_handling(
        client=mock_client,
        model="gpt-4",
        messages=[{"role": "user", "content": "test"}],
    ):
        chunks.append(chunk)

    # Verify we got all chunks
    assert len(chunks) == 3


@pytest.mark.asyncio
async def test_stream_with_error_handling_connection_error() -> None:
    """Test streaming with connection error."""
    mock_client = MagicMock()

    # Mock connection error on create
    mock_client.chat.completions.create = AsyncMock(
        side_effect=MockConnectionError("Connection failed")
    )

    with pytest.raises(
        LLMStreamingError, match="Unexpected error during streaming"
    ):
        async for _ in stream_with_error_handling(
            client=mock_client,
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}],
        ):
            pass


@pytest.mark.asyncio
async def test_stream_with_error_handling_rate_limit_error() -> None:
    """Test streaming with rate limit error."""
    mock_client = MagicMock()

    # Mock rate limit error on create
    mock_client.chat.completions.create = AsyncMock(
        side_effect=MockRateLimitError("Rate limit exceeded")
    )

    with pytest.raises(LLMStreamingError, match="Unexpected error during streaming"):
        async for _ in stream_with_error_handling(
            client=mock_client,
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}],
        ):
            pass


@pytest.mark.asyncio
async def test_stream_with_error_handling_api_error() -> None:
    """Test streaming with API error."""
    mock_client = MagicMock()

    # Mock API error on create
    mock_client.chat.completions.create = AsyncMock(
        side_effect=MockAPIError("API Error")
    )

    with pytest.raises(LLMStreamingError, match="Unexpected error during streaming"):
        async for _ in stream_with_error_handling(
            client=mock_client,
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}],
        ):
            pass


@pytest.mark.asyncio
async def test_stream_with_error_handling_chunk_iteration_error() -> None:
    """Test streaming with error during chunk iteration."""

    mock_client = MagicMock()

    # Create a mock stream that raises an error during iteration
    async def mock_stream_with_error():
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))])
        raise RuntimeError("Iteration error")

    mock_client.chat.completions.create = AsyncMock(
        return_value=mock_stream_with_error()
    )

    with pytest.raises(LLMStreamingError, match="Unexpected error during streaming"):
        async for _ in stream_with_error_handling(
            client=mock_client,
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}],
        ):
            pass


@pytest.mark.asyncio
async def test_stream_with_error_handling_passes_kwargs() -> None:
    """Test that stream_with_error_handling passes additional kwargs to the API call."""
    mock_client = MagicMock()

    # Create a mock stream
    async def mock_stream():
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))])

    mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

    # Call with additional kwargs
    async for _ in stream_with_error_handling(
        client=mock_client,
        model="gpt-4",
        messages=[{"role": "user", "content": "test"}],
        temperature=0.7,
        max_tokens=1000,
    ):
        pass

    # Verify kwargs were passed
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0.7
    assert call_kwargs["max_tokens"] == 1000
