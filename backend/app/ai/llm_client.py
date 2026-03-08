"""LLM Client Factory for OpenAI-compatible endpoints.

Support for OpenAI, Azure OpenAI, and Ollama endpoints.
"""

import logging

from openai import AsyncOpenAI

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
