"""API routes for AI configuration management.

Provides endpoints for managing AI providers, models, and assistant configurations.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker
from app.db.session import get_db
from app.models.schemas.ai import (
    AIAssistantConfigCreate,
    AIAssistantConfigPublic,
    AIAssistantConfigUpdate,
    AIModelCreate,
    AIModelPublic,
    AIModelUpdate,
    AIProviderConfigCreate,
    AIProviderConfigPublic,
    AIProviderCreate,
    AIProviderPublic,
    AIProviderUpdate,
    AIToolPublic,
)
from app.services.ai_config_service import AIConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/config", tags=["AI Configuration"])


def _invalidate_llm_caches() -> None:
    """Invalidate LLM config and client caches after provider/model changes."""
    from app.ai.agent_service import invalidate_llm_config_cache

    invalidate_llm_config_cache()
    logger.info("LLM caches invalidated due to config change")


def _invalidate_specialist_cache() -> None:
    """Invalidate specialist config cache after assistant config changes."""
    from app.ai.subagents.db_loader import invalidate_cache

    invalidate_cache()
    logger.info("Specialist cache invalidated due to assistant config change")


def get_ai_config_service(session: AsyncSession = Depends(get_db)) -> AIConfigService:
    """Get AI configuration service."""
    return AIConfigService(session)


# === Provider Routes ===


@router.get(
    "/providers",
    response_model=list[AIProviderPublic],
    operation_id="list_ai_providers",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-read"))],
)
async def list_providers(
    include_inactive: bool = False,
    service: AIConfigService = Depends(get_ai_config_service),
) -> list[AIProviderPublic]:
    """List all AI providers."""
    providers = await service.list_providers(include_inactive)
    return [AIProviderPublic.model_validate(p) for p in providers]


@router.post(
    "/providers",
    response_model=AIProviderPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_ai_provider",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-create"))],
)
async def create_provider(
    provider_in: AIProviderCreate,
    service: AIConfigService = Depends(get_ai_config_service),
) -> AIProviderPublic:
    """Create a new AI provider."""
    provider = await service.create_provider(provider_in)
    return AIProviderPublic.model_validate(provider)


@router.put(
    "/providers/{provider_id}",
    response_model=AIProviderPublic,
    operation_id="update_ai_provider",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-update"))],
)
async def update_provider(
    provider_id: UUID,
    provider_in: AIProviderUpdate,
    service: AIConfigService = Depends(get_ai_config_service),
) -> AIProviderPublic:
    """Update an AI provider."""
    try:
        provider = await service.update_provider(provider_id, provider_in)
        _invalidate_llm_caches()
        return AIProviderPublic.model_validate(provider)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/providers/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_ai_provider",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-delete"))],
)
async def delete_provider(
    provider_id: UUID,
    service: AIConfigService = Depends(get_ai_config_service),
) -> None:
    """Delete an AI provider."""
    try:
        await service.delete_provider(provider_id)
        _invalidate_llm_caches()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# === Provider Config Routes ===


@router.get(
    "/providers/{provider_id}/configs",
    response_model=list[AIProviderConfigPublic],
    operation_id="list_provider_configs",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-read"))],
)
async def list_provider_configs(
    provider_id: UUID,
    service: AIConfigService = Depends(get_ai_config_service),
) -> list[AIProviderConfigPublic]:
    """List all configs for a provider."""
    configs = await service.list_provider_configs(provider_id)
    return [AIProviderConfigPublic.model_validate(c) for c in configs]


@router.post(
    "/providers/{provider_id}/configs",
    response_model=AIProviderConfigPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="set_provider_config",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-create"))],
)
async def set_provider_config(
    provider_id: UUID,
    config_in: AIProviderConfigCreate,
    service: AIConfigService = Depends(get_ai_config_service),
) -> AIProviderConfigPublic:
    """Set a provider config value."""
    config = await service.set_provider_config(provider_id, config_in)
    _invalidate_llm_caches()
    return AIProviderConfigPublic.model_validate(config)


@router.delete(
    "/providers/{provider_id}/configs/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_provider_config",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-delete"))],
)
async def delete_provider_config(
    provider_id: UUID,
    key: str,
    service: AIConfigService = Depends(get_ai_config_service),
) -> None:
    """Delete a provider config."""
    await service.delete_provider_config(provider_id, key)
    _invalidate_llm_caches()


# === Model Routes ===


@router.get(
    "/models",
    response_model=list[AIModelPublic],
    operation_id="list_all_models",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-read"))],
)
async def list_all_models(
    include_inactive: bool = False,
    service: AIConfigService = Depends(get_ai_config_service),
) -> list[AIModelPublic]:
    """List all AI models across all providers."""
    models = await service.list_models(None, include_inactive)
    return [AIModelPublic.model_validate(m) for m in models]


@router.get(
    "/providers/{provider_id}/models",
    response_model=list[AIModelPublic],
    operation_id="list_provider_models",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-read"))],
)
async def list_provider_models(
    provider_id: UUID,
    include_inactive: bool = False,
    service: AIConfigService = Depends(get_ai_config_service),
) -> list[AIModelPublic]:
    """List all models for a provider."""
    models = await service.list_models(provider_id, include_inactive)
    return [AIModelPublic.model_validate(m) for m in models]


@router.post(
    "/providers/{provider_id}/models",
    response_model=AIModelPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_ai_model",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-create"))],
)
async def create_model(
    provider_id: UUID,
    model_in: AIModelCreate,
    service: AIConfigService = Depends(get_ai_config_service),
) -> AIModelPublic:
    """Create a new AI model for a provider."""
    model_data = model_in.model_dump()
    model_data["provider_id"] = provider_id
    model = await service.create_model(AIModelCreate(**model_data))
    return AIModelPublic.model_validate(model)


@router.put(
    "/providers/{provider_id}/models/{model_id}",
    response_model=AIModelPublic,
    operation_id="update_ai_model",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-update"))],
)
async def update_model(
    provider_id: UUID,
    model_id: UUID,
    model_in: AIModelUpdate,
    service: AIConfigService = Depends(get_ai_config_service),
) -> AIModelPublic:
    """Update an AI model."""
    try:
        model = await service.update_model(model_id, model_in)
        _invalidate_llm_caches()
        return AIModelPublic.model_validate(model)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/providers/{provider_id}/models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_ai_model",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-delete"))],
)
async def delete_model(
    provider_id: UUID,
    model_id: UUID,
    service: AIConfigService = Depends(get_ai_config_service),
) -> None:
    """Delete an AI model."""
    try:
        await service.delete_model(model_id)
        _invalidate_llm_caches()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# === Assistant Config Routes ===


@router.get(
    "/assistants",
    response_model=list[AIAssistantConfigPublic],
    operation_id="list_assistant_configs",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-read"))],
)
async def list_assistant_configs(
    include_inactive: bool = False,
    agent_type: str | None = None,
    service: AIConfigService = Depends(get_ai_config_service),
) -> list[AIAssistantConfigPublic]:
    """List all assistant configurations."""
    configs = await service.list_assistant_configs(include_inactive, agent_type)
    return [AIAssistantConfigPublic.model_validate(c) for c in configs]


@router.get(
    "/assistants/{assistant_config_id}",
    response_model=AIAssistantConfigPublic,
    operation_id="get_assistant_config",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-read"))],
)
async def get_assistant_config(
    assistant_config_id: UUID,
    service: AIConfigService = Depends(get_ai_config_service),
) -> AIAssistantConfigPublic:
    """Get a specific assistant configuration."""
    config = await service.get_assistant_config(assistant_config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assistant config {assistant_config_id} not found",
        )
    return AIAssistantConfigPublic.model_validate(config)


@router.post(
    "/assistants",
    response_model=AIAssistantConfigPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_assistant_config",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-create"))],
)
async def create_assistant_config(
    config_in: AIAssistantConfigCreate,
    service: AIConfigService = Depends(get_ai_config_service),
) -> AIAssistantConfigPublic:
    """Create a new assistant configuration."""
    config = await service.create_assistant_config(config_in)
    if config.agent_type == "specialist":
        _invalidate_specialist_cache()
    return AIAssistantConfigPublic.model_validate(config)


@router.put(
    "/assistants/{assistant_config_id}",
    response_model=AIAssistantConfigPublic,
    operation_id="update_assistant_config",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-update"))],
)
async def update_assistant_config(
    assistant_config_id: UUID,
    config_in: AIAssistantConfigUpdate,
    service: AIConfigService = Depends(get_ai_config_service),
) -> AIAssistantConfigPublic:
    """Update an assistant configuration."""
    try:
        config = await service.update_assistant_config(assistant_config_id, config_in)
        if config.agent_type == "specialist":
            _invalidate_specialist_cache()
        else:
            _invalidate_llm_caches()
        return AIAssistantConfigPublic.model_validate(config)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/assistants/{assistant_config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_assistant_config",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-delete"))],
)
async def delete_assistant_config(
    assistant_config_id: UUID,
    service: AIConfigService = Depends(get_ai_config_service),
) -> None:
    """Delete an assistant configuration."""
    try:
        await service.delete_assistant_config(assistant_config_id)
        _invalidate_llm_caches()
        _invalidate_specialist_cache()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# === Tool Routes ===


@router.get(
    "/tools",
    response_model=list[AIToolPublic],
    operation_id="list_ai_tools",
    dependencies=[Depends(RoleChecker(required_permission="ai-config-read"))],
)
async def list_ai_tools() -> list[AIToolPublic]:
    """List all available AI tools.

    Imports and registers all tool templates before querying the registry.
    """
    # Discover and register all tools from known modules
    from app.ai.tools.registry import get_all_tools, get_registry

    registry = get_registry()
    registry.discover_and_register("app.ai.tools.context_tools")
    registry.discover_and_register("app.ai.tools.project_tools")
    registry.discover_and_register("app.ai.tools.temporal_tools")
    registry.discover_and_register("app.ai.tools.templates.analysis_template")
    registry.discover_and_register("app.ai.tools.templates.change_order_template")
    registry.discover_and_register("app.ai.tools.templates.project_template")
    registry.discover_and_register("app.ai.tools.templates.cost_element_template")
    registry.discover_and_register("app.ai.tools.templates.control_account_template")
    registry.discover_and_register("app.ai.tools.templates.user_management_template")
    registry.discover_and_register("app.ai.tools.templates.advanced_analysis_template")
    registry.discover_and_register("app.ai.tools.templates.diagram_template")
    registry.discover_and_register(
        "app.ai.tools.templates.forecast_cost_progress_template"
    )
    registry.discover_and_register("app.ai.tools.templates.work_package_template")
    registry.discover_and_register("app.ai.tools.templates.cost_event_type_template")
    registry.discover_and_register("app.ai.tools.document_tools")
    registry.discover_and_register("app.ai.tools.ask_user")
    registry.discover_and_register("app.ai.tools.briefing_tools")
    registry.discover_and_register("app.ai.tools.templates.cost_event_template")

    tools = get_all_tools()

    # Convert domain tools to AIToolPublic
    result: list[AIToolPublic] = [
        AIToolPublic.model_validate(t.to_dict()) for t in tools
    ]

    # Append MCP tools discovered from configured external servers
    from app.ai.mcp.client_manager import MCPClientManager

    mcp_manager = MCPClientManager()
    for mcp_tool in mcp_manager.get_all_tools():
        meta = getattr(mcp_tool, "_tool_metadata", None)
        if meta is not None:
            result.append(AIToolPublic.model_validate(meta.to_dict()))

    # Sort tools by category, then by name
    result.sort(key=lambda t: (t.category or "uncategorized", t.name))

    return result
