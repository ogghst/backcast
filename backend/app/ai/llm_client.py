"""LLM Client Factory for OpenAI-compatible endpoints.

Support for OpenAI, Azure OpenAI, and Ollama endpoints.

Streaming Support:
    The AsyncOpenAI client returned by this factory supports streaming responses
    via the `stream=True` parameter in chat.completions.create(). The client
    returns an async iterator that yields chunks containing delta content.

    Example:
        ```python
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            stream=True
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content)
        ```
"""

import logging
from collections.abc import AsyncIterator
from typing import Any, cast

from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

from app.models.domain.ai import AIProvider
from app.services.ai_config_service import AIConfigService

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """Factory for creating OpenAI-compatible LLM clients."""

    @staticmethod
    async def create_client(
        provider: AIProvider,
        config: AIConfigService,
    ) -> AsyncOpenAI:
        """Create an OpenAI client based on provider config.

        Context: Called by AgentService to initialize the connection to the configured AI provider.

        Args:
            provider: AI provider configuration definition
            config: AI config service for getting decrypted config values (e.g., API key)

        Returns:
            Configured AsyncOpenAI client ready for requests

        Raises:
            ValueError: If Ollama provider is missing the required base_url
        """
        config_values = await config.list_provider_configs(provider.id, decrypt=True)

        api_key = ""
        timeout = 30.0
        max_retries = 2
        base_url: str | None = None

        # Extract config values
        for cfg in config_values:
            if cfg.key == "api_key" and cfg.value is not None:
                api_key = str(cfg.value)
            elif cfg.key == "base_url" and cfg.value is not None:
                base_url = str(cfg.value)
            elif cfg.key == "timeout" and cfg.value is not None:
                timeout = float(cfg.value)
            elif cfg.key == "max_retries" and cfg.value is not None:
                max_retries = int(cfg.value)

        # Set base URL for provider if configured at provider level
        if not base_url and provider.base_url:
            base_url = str(provider.base_url)

        # Handle provider type specific configurations
        if provider.provider_type == "azure":
            # Extract Azure-specific config
            azure_deployment = next(
                (
                    str(cfg.value)
                    for cfg in config_values
                    if cfg.key == "azure_deployment" and cfg.value is not None
                ),
                None,
            )

            # For Azure OpenAI we need additional default query parameters or explicit Azure client.
            # Here we follow the existing pattern of using AsyncOpenAI directly with custom query params.
            default_query = {"api-version": "2024-02-15-preview"}
            if azure_deployment:
                default_query["deployment-id"] = str(azure_deployment)

            return AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
                max_retries=max_retries,
                default_query=default_query,
            )

        elif provider.provider_type == "ollama":
            # Ollama uses base_url (required)
            if not base_url:
                raise ValueError("Ollama provider requires base_url")

        return AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )


class LLMStreamingError(Exception):
    """Exception raised when streaming operations fail.

    Attributes:
        message: Error description
        original_error: The original exception from the OpenAI client
    """

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        """Initialize the streaming error.

        Args:
            message: Human-readable error description
            original_error: The original exception that caused this error
        """
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


async def verify_streaming_capability(client: AsyncOpenAI) -> bool:
    """Verify that an OpenAI client supports streaming operations.

    Context: Use this to validate client configuration before initiating
    streaming operations. This performs a minimal test request to ensure
    the client can handle streaming responses.

    Args:
        client: The AsyncOpenAI client to verify

    Returns:
        True if streaming is supported, False otherwise

    Raises:
        LLMStreamingError: If the streaming capability check fails
    """
    try:
        # Perform a minimal streaming request
        stream = await client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use a common model name for verification
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1,
            stream=True,
        )

        # Cast to AsyncIterator to help mypy understand the return type
        async_stream = cast(AsyncIterator[Any], stream)

        # Try to iterate over at least one chunk
        chunk_count = 0
        async for _ in async_stream:
            chunk_count += 1
            if chunk_count >= 1:
                break

        return chunk_count > 0

    except (APIError, APIConnectionError, RateLimitError) as e:
        error_msg = f"Streaming capability check failed: {str(e)}"
        logger.error(error_msg)
        raise LLMStreamingError(error_msg, original_error=e) from e
    except Exception as e:
        error_msg = f"Unexpected error during streaming verification: {str(e)}"
        logger.error(error_msg)
        raise LLMStreamingError(error_msg, original_error=e) from e


async def stream_with_error_handling(
    client: AsyncOpenAI,
    model: str,
    messages: list[dict[str, Any]],
    **kwargs: Any,
) -> AsyncIterator[Any]:
    """Stream chat completions with comprehensive error handling.

    Context: Wrapper around OpenAI's streaming API that handles common
    failure scenarios including connection drops, timeouts, and API errors.

    Args:
        client: The AsyncOpenAI client to use
        model: Model identifier to use
        messages: List of message dictionaries with 'role' and 'content'
        **kwargs: Additional parameters to pass to the API call

    Yields:
        Streaming chunks from the OpenAI API

    Raises:
        LLMStreamingError: If a streaming error occurs during iteration
    """
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            stream=True,
            **kwargs,
        )

        # Cast to AsyncIterator to help mypy understand the return type
        async_stream = cast(AsyncIterator[Any], stream)

        async for chunk in async_stream:
            try:
                yield chunk
            except Exception as e:
                error_msg = f"Error processing streaming chunk: {str(e)}"
                logger.error(error_msg)
                raise LLMStreamingError(error_msg, original_error=e) from e

    except APIConnectionError as e:
        error_msg = "Connection failed during streaming. Check your network connection."
        logger.error(f"{error_msg} Details: {str(e)}")
        raise LLMStreamingError(error_msg, original_error=e) from e
    except RateLimitError as e:
        error_msg = "Rate limit exceeded during streaming. Please retry later."
        logger.error(f"{error_msg} Details: {str(e)}")
        raise LLMStreamingError(error_msg, original_error=e) from e
    except APIError as e:
        error_msg = f"API error during streaming: {str(e)}"
        logger.error(error_msg)
        raise LLMStreamingError(error_msg, original_error=e) from e
    except Exception as e:
        error_msg = f"Unexpected error during streaming: {str(e)}"
        logger.error(error_msg)
        raise LLMStreamingError(error_msg, original_error=e) from e
