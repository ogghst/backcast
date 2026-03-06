"""LLM Client Factory for OpenAI-compatible endpoints.

Support for OpenAI, Azure OpenAI, and Ollama endpoints.
"""

import logging
from typing import Any

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

        Args:
            provider: AI provider configuration
            config: AI config service for getting decrypted config values

        Returns:
            Configured AsyncOpenAI client
        """
        config_values = await config.list_provider_configs(provider.id, decrypt=True)

        client_kwargs: dict[str, Any] = {
            "api_key": "",
            "timeout": 30.0,
            "max_retries": 2,
        }

        # Extract config values
        api_key = None
        base_url = None
        for cfg in config_values:
            if cfg.key == "api_key":
                api_key = cfg.value
            elif cfg.key == "base_url":
                base_url = cfg.value
            elif cfg.key == "timeout" and cfg.value is not None:
                client_kwargs["timeout"] = float(cfg.value)
            elif cfg.key == "max_retries" and cfg.value is not None:
                client_kwargs["max_retries"] = int(cfg.value)

        # Set API key
        if api_key:
            client_kwargs["api_key"] = api_key

        # Set base URL for provider
        if base_url:
            client_kwargs["base_url"] = base_url
        elif provider.base_url:
            client_kwargs["base_url"] = provider.base_url

        # Handle provider type specific configurations
        if provider.provider_type == "azure":
            # Azure OpenAI requires api_version
            client_kwargs["api_version"] = "2024-02-15-preview"
            # Extract Azure-specific config
            azure_deployment = next(
                (cfg.value for cfg in config_values if cfg.key == "azure_deployment"),
                None
            )
            if azure_deployment:
                client_kwargs["azure_deployment"] = azure_deployment
        elif provider.provider_type == "ollama":
            # Ollama uses base_url (required)
            if not base_url and not provider.base_url:
                raise ValueError("Ollama provider requires base_url")

        return AsyncOpenAI(**client_kwargs)

