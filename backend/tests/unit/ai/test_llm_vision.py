"""Unit tests for LLM client vision support.

Tests verify that the LLM client can handle multi-modal messages with image_url content.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import AsyncOpenAI

from app.ai.llm_client import stream_with_error_handling


class MockAsyncIterator:
    """Mock async iterator for testing."""

    def __init__(self, items: list) -> None:
        self.items = items
        self.index = 0

    def __aiter__(self) -> "MockAsyncIterator":
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


@pytest.mark.asyncio
async def test_llm_client_supports_multimodal_messages() -> None:
    """Test that LLM client can handle messages with image_url content.

    Context: Vision models require messages with mixed content types (text and image_url).
    The stream_with_error_handling function should properly format these for the OpenAI API.

    Expected:
        - Messages with content list are accepted
        - Image_url content blocks are properly formatted
        - Text and image content are both included in API call
    """
    # Arrange: Create a mock OpenAI client
    mock_client = MagicMock(spec=AsyncOpenAI)

    # Mock the streaming response with proper async iterator
    mock_chunks = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="The image shows"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content=" a chart"))]),
    ]

    mock_response = MockAsyncIterator(mock_chunks)
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Create multimodal message with text and image
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What do you see?"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "http://localhost:8020/api/v1/ai/chat/images/abc123.png"
                    },
                },
            ],
        }
    ]

    # Act: Stream with multimodal message
    chunks = []
    try:
        async for chunk in stream_with_error_handling(
            client=mock_client,
            model="gpt-4-vision-preview",
            messages=messages,
        ):
            if chunk.choices and chunk.choices[0].delta.content:
                chunks.append(chunk.choices[0].delta.content)
    except Exception as e:
        pytest.fail(f"stream_with_error_handling raised exception: {e}")

    # Assert: Client was called with multimodal message
    mock_client.chat.completions.create.assert_called_once()
    call_args = mock_client.chat.completions.create.call_args

    # Verify messages parameter was passed correctly
    assert "messages" in call_args.kwargs
    sent_messages = call_args.kwargs["messages"]
    assert len(sent_messages) == 1

    # Verify message structure
    user_message = sent_messages[0]
    assert user_message["role"] == "user"
    assert isinstance(user_message["content"], list)
    assert len(user_message["content"]) == 2

    # Verify text content block
    text_block = user_message["content"][0]
    assert text_block["type"] == "text"
    assert "What do you see?" in text_block["text"]

    # Verify image_url content block
    image_block = user_message["content"][1]
    assert image_block["type"] == "image_url"
    assert "url" in image_block["image_url"]
    assert "abc123.png" in image_block["image_url"]["url"]

    # Verify response was streamed
    assert len(chunks) > 0
    assert "chart" in "".join(chunks)


@pytest.mark.asyncio
async def test_llm_client_supports_multiple_images() -> None:
    """Test that LLM client can handle messages with multiple image attachments.

    Context: Users may attach multiple images to a single message.

    Expected:
        - All image_url blocks are included
        - Images are in the correct order
    """
    # Arrange
    mock_client = MagicMock(spec=AsyncOpenAI)
    mock_chunks = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="Comparing"))]),
    ]
    mock_response = MockAsyncIterator(mock_chunks)
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Create message with multiple images
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Compare these:"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "http://localhost:8020/api/v1/ai/chat/images/img1.png"
                    },
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "http://localhost:8020/api/v1/ai/chat/images/img2.jpg"
                    },
                },
            ],
        }
    ]

    # Act
    async for _ in stream_with_error_handling(
        client=mock_client,
        model="gpt-4-vision-preview",
        messages=messages,
    ):
        break  # Just need to verify the call was made

    # Assert
    call_args = mock_client.chat.completions.create.call_args
    sent_messages = call_args.kwargs["messages"]
    user_message = sent_messages[0]
    content = user_message["content"]

    # Should have text + 2 images
    assert len(content) == 3
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[2]["type"] == "image_url"


@pytest.mark.asyncio
async def test_llm_client_backward_compatible_with_string_content() -> None:
    """Test that LLM client still works with simple string content.

    Context: Existing code uses string content for messages.
    We need backward compatibility.

    Expected:
        - String content messages still work
        - No breaking changes to existing functionality
    """
    # Arrange
    mock_client = MagicMock(spec=AsyncOpenAI)
    mock_chunks = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello!"))]),
    ]
    mock_response = MockAsyncIterator(mock_chunks)
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Create message with simple string content (old style)
    messages = [{"role": "user", "content": "What is the capital of France?"}]

    # Act
    chunks = []
    async for chunk in stream_with_error_handling(
        client=mock_client,
        model="gpt-4",
        messages=messages,
    ):
        if chunk.choices and chunk.choices[0].delta.content:
            chunks.append(chunk.choices[0].delta.content)

    # Assert
    assert "Hello!" in "".join(chunks)
    mock_client.chat.completions.create.assert_called_once()
