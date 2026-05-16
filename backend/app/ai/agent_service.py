"""LangGraph Agent Service for conversation orchestration.

Uses LangGraph StateGraph for conversation flow with tool calling loop.
"""

import asyncio
import logging
import os
import time
import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import UUID

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

if TYPE_CHECKING:
    from langchain_core.tools import (  # noqa: F401
        BaseTool,
        StructuredTool,
        ToolInterface,
    )
from langchain_openai import ChatOpenAI

# langchain-deepseek provides native DeepSeek support with reasoning_content handling
try:
    from langchain_deepseek import ChatDeepSeek

    HAS_DEEPSEEK = True
except ImportError:
    HAS_DEEPSEEK = False
    ChatDeepSeek = ChatOpenAI  # type: ignore

# CRITICAL: DeepSeek's thinking mode requires reasoning_content to be passed back
# in every subsequent assistant turn. langchain-deepseek handles receiving reasoning_content
# from the API but does NOT handle sending it back. We need to patch the message-to-dict
# conversion to include reasoning_content from additional_kwargs.
if HAS_DEEPSEEK:
    import langchain_openai.chat_models.base as _lc_openai_base

    _original_convert_message_to_dict = _lc_openai_base._convert_message_to_dict

    def _patched_convert_message_to_dict(
        message: BaseMessage,
        api: Literal["chat/completions", "responses"] = "chat/completions",
    ) -> dict[str, Any]:
        msg_dict = _original_convert_message_to_dict(message, api=api)
        # Propagate reasoning_content for DeepSeek thinking mode
        if isinstance(message, AIMessage):
            rc = message.additional_kwargs.get("reasoning_content")
            if rc:
                msg_dict["reasoning_content"] = rc
            elif message.tool_calls:
                logger.warning(
                    "AIMessage with tool_calls but no reasoning_content — "
                    "DeepSeek thinking mode will reject this."
                )
        return msg_dict

    _lc_openai_base._convert_message_to_dict = _patched_convert_message_to_dict

    # Patch ChatDeepSeek.bind_tools() to strip tool_choice parameter
    # DeepSeek-reasoner rejects tool_choice, but langchain_create_agent() passes it
    _original_bind_tools = ChatDeepSeek.bind_tools

    def _patched_bind_tools(  # type: ignore[no-untyped-def]
        self,
        tools: Sequence,  # type: ignore[type-arg]  # BaseTool | StructuredTool | ToolInterface - omitted for TYPE_CHECKING
        *,
        tool_choice: (
            dict[str, str] | str | Literal["auto", "none", "required"] | bool | None
        ) = None,
        **kwargs: Any,
    ) -> Any:
        """Strip tool_choice for DeepSeek models — the API rejects it."""
        if tool_choice is not None:
            logger.info(
                "Stripping tool_choice=%s for DeepSeek model (API rejects this parameter)",
                tool_choice,
            )
            tool_choice = None
        return _original_bind_tools(self, tools, tool_choice=tool_choice, **kwargs)

    ChatDeepSeek.bind_tools = _patched_bind_tools  # type: ignore[method-assign]

from langgraph.types import Command
from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.briefing import BriefingDocument
from app.ai.config import AgentConfig, OrchestratorMode
from app.ai.deep_agent_orchestrator import DeepAgentOrchestrator
from app.ai.execution.agent_event import AgentEvent
from app.ai.execution.agent_event_bus import AgentEventBus
from app.ai.execution.agent_metrics import AgentExecutionMetrics
from app.ai.execution.runner_manager import runner_manager
from app.ai.graph import create_graph
from app.ai.graph_cache import (
    BackcastRuntimeContext,
    LLMClientCache,
    clear_request_context,
    set_request_context,
    shared_checkpointer,
)
from app.ai.message_utils import extract_tool_output_content
from app.ai.subagent_compiler import DEFAULT_SYSTEM_PROMPT
from app.ai.subagents import get_all_subagents
from app.ai.supervisor_orchestrator import SupervisorOrchestrator
from app.ai.telemetry import (
    initialize_telemetry,
    trace_context,
)
from app.ai.token_estimator import (
    TokenUsageAccumulator,
    log_actual_usage,
    log_context_usage_estimate,
)
from app.ai.tools import ToolContext, create_project_tools, filter_tools_by_role
from app.ai.tools.interrupt_node import InterruptNode
from app.ai.tools.session_manager import ToolSessionManager
from app.ai.tools.types import ExecutionMode
from app.api.websocket_utils import is_websocket_connected
from app.core.config import settings
from app.models.domain.ai import (
    AIAgentExecution,
    AIAssistantConfig,
    AIConversationSession,
    AIProvider,
)
from app.models.domain.cost_element import CostElement
from app.models.domain.project import Project
from app.models.domain.wbe import WBE
from app.models.schemas.ai import (
    AIChatResponse,
    AIConversationMessagePublic,
    PlanningStep,
    WSBriefingMessage,
    WSCompleteMessage,
)
from app.services.ai_config_service import AIConfigService

# Initialize telemetry on module load (will only instrument once)
_tracer_provider = initialize_telemetry(
    service_name="backcast-ai",
    enable_console=os.getenv("OTEL_CONSOLE_EXPORT", "false").lower() == "true",
)

# NOTE: DeepSeek reasoning_content handling is now provided natively by
# langchain-deepseek package (ChatDeepSeek class). No monkey-patches needed.


def _extract_reasoning_content(message: AIMessage) -> dict[str, Any] | None:
    """Extract reasoning_content from an AIMessage into metadata dict for DB storage."""
    rc = message.additional_kwargs.get("reasoning_content")
    if rc:
        return {"reasoning_content": rc}
    return None


def _restore_reasoning_content(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Build additional_kwargs to restore reasoning_content from DB metadata."""
    if metadata and isinstance(metadata, dict):
        rc = metadata.get("reasoning_content")
        if rc:
            return {"additional_kwargs": {"reasoning_content": rc}}
    return {}


async def _extract_client_config(
    provider: AIProvider,
    config: AIConfigService,
) -> dict[str, Any]:
    """Extract client configuration from provider for LangChain.

    Context: Helper to extract configuration values that will be passed directly
    to LangChain's ChatOpenAI, allowing LangChain to create its own client
    instead of wrapping a pre-existing one.

    Args:
        provider: AI provider configuration definition
        config: AI config service for getting decrypted config values

    Returns:
        Dictionary of configuration parameters for ChatOpenAI initialization
    """
    config_values = await config.list_provider_configs(provider.id, decrypt=True)

    client_config: dict[str, Any] = {}

    for cfg in config_values:
        if cfg.key == "api_key" and cfg.value is not None:
            client_config["api_key"] = str(cfg.value)
        elif cfg.key == "base_url" and cfg.value is not None:
            client_config["base_url"] = str(cfg.value)
        elif cfg.key == "timeout" and cfg.value is not None:
            client_config["timeout"] = float(cfg.value)
        elif cfg.key == "max_retries" and cfg.value is not None:
            client_config["max_retries"] = int(cfg.value)

    if "base_url" not in client_config and provider.base_url:
        client_config["base_url"] = str(provider.base_url)

    if provider.provider_type == "azure":
        azure_deployment = next(
            (
                str(cfg.value)
                for cfg in config_values
                if cfg.key == "azure_deployment" and cfg.value is not None
            ),
            None,
        )
        if azure_deployment:
            # For Azure, we need to pass deployment info
            client_config["model"] = azure_deployment

    elif provider.provider_type == "deepseek":
        for cfg in config_values:
            if cfg.key == "reasoning_effort" and cfg.value is not None:
                client_config["reasoning_effort"] = str(cfg.value)
            elif cfg.key == "thinking_mode" and cfg.value is not None:
                client_config["thinking_mode"] = str(cfg.value)

    return client_config


logger = logging.getLogger(__name__)

SPECIALIST_AGENT_NAMES = frozenset(cfg["name"] for cfg in get_all_subagents())

# Caches (shared across all requests)
_llm_cache = LLMClientCache()

# LLM client config cache (avoids 3 DB queries per chat message)
_llm_config_cache: dict[UUID, tuple[float, dict[str, Any], str, str]] = {}
_LLM_CONFIG_TTL = 300  # 5 minutes


def invalidate_llm_config_cache() -> None:
    """Clear the LLM client config cache. Called when provider/model configs change."""
    _llm_config_cache.clear()
    logger.info("LLM config cache invalidated")


# User role cache (avoids DB query per chat message)
_user_role_cache: dict[UUID, tuple[float, str]] = {}  # user_id -> (expires_at, role)
_USER_ROLE_TTL = 300  # 5 minutes


async def _get_user_role(session: AsyncSession, user_id: UUID) -> str:
    """Get user role with TTL caching via unified RBAC."""
    cached = _user_role_cache.get(user_id)
    if cached is not None:
        expires_at, role = cached
        if time.time() < expires_at:
            return role
        del _user_role_cache[user_id]

    from app.core.rbac_unified import (
        get_unified_rbac_service,
        set_unified_rbac_session,
    )

    try:
        set_unified_rbac_session(session)
        roles = await get_unified_rbac_service().get_user_roles(
            user_id, "global", None
        )
        role = roles[0] if roles else "viewer"
    finally:
        set_unified_rbac_session(None)

    _user_role_cache[user_id] = (time.time() + _USER_ROLE_TTL, role)
    return role


def _is_transient_stream_error(exc: Exception) -> bool:
    """Check if a streaming error is transient and worth retrying."""
    if isinstance(exc, (ConnectionResetError, OSError)):
        return True
    # httpcore/httpx errors — check by name to avoid hard imports
    err_type = type(exc).__name__
    err_module = type(exc).__module__
    return (err_type == "ReadError" and "httpcore" in err_module) or (
        err_type == "RemoteProtocolError" and "httpx" in err_module
    )


class AgentService:
    """Service for LangGraph agent orchestration."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._config_service: AIConfigService | None = None
        self._subagent_invocation_counts: dict[str, int] = {}

    @property
    def config_service(self) -> AIConfigService:
        """Get or create the AI config service.

        Returns:
            AIConfigService instance for database operations
        """
        if self._config_service is None:
            self._config_service = AIConfigService(self.session)
        return self._config_service

    async def _get_llm_client_config(
        self, model_id: UUID
    ) -> tuple[dict[str, Any], str, str]:
        """Get LLM client configuration, model name, and provider type for a model.

        Context: Internal helper to resolve the configuration for LangChain's ChatOpenAI.
        Returns configuration dict instead of a client to allow LangChain to create
        its own properly initialized client. Results are cached by model_id with a
        5-minute TTL to avoid repeated DB queries for stable configuration.

        Args:
            model_id: UUID of the AI model to instantiate

        Returns:
            A tuple containing the client configuration dict, the target model name, and provider type

        Raises:
            ValueError: If the model or its associated provider cannot be found
        """
        cached = _llm_config_cache.get(model_id)
        if cached is not None:
            expires_at, client_config, model_name, provider_type = cached
            if time.time() < expires_at:
                logger.debug("LLM config cache hit for model %s", model_id)
                return client_config, model_name, provider_type
            else:
                del _llm_config_cache[model_id]
        config_service = AIConfigService(self.session)
        model = await config_service.get_model(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        # model.provider_id is stored as string in the database
        provider = await config_service.get_provider(UUID(str(model.provider_id)))
        if not provider:
            raise ValueError(f"Provider {model.provider_id} not found")

        # Extract configuration for LangChain
        client_config = await _extract_client_config(provider, config_service)
        model_name = str(model.model_id)
        provider_type = provider.provider_type

        _llm_config_cache[model_id] = (
            time.time() + _LLM_CONFIG_TTL,
            client_config,
            model_name,
            provider_type,
        )
        logger.debug("LLM config cache miss for model %s, cached", model_id)

        return client_config, model_name, provider_type

    async def _create_langchain_llm(
        self,
        client_config: dict[str, Any],
        model_name: str,
        temperature: float | None,
        max_tokens: int | None,
    ) -> ChatOpenAI | ChatDeepSeek:
        """Create a LangChain ChatOpenAI or ChatDeepSeek instance from client configuration.

        Context: Creates a ChatOpenAI or ChatDeepSeek instance by passing configuration
        directly to LangChain, allowing it to create and manage its own client properly.
        This ensures compatibility with LangChain's streaming implementation.

        For DeepSeek models, uses ChatDeepSeek which provides native reasoning_content
        support without requiring monkey-patches.

        Args:
            client_config: Configuration dictionary for the OpenAI client
            model_name: Model identifier to use
            temperature: Optional temperature setting
            max_tokens: Optional max tokens setting

        Returns:
            ChatOpenAI or ChatDeepSeek instance configured with the provided parameters
        """
        # Pop provider-specific params that aren't standard OpenAI client args
        reasoning_effort = client_config.pop("reasoning_effort", None)
        thinking_mode = client_config.pop("thinking_mode", None)

        # Build cache key
        base_url = client_config.get("base_url", "")
        base_url_hash = str(hash(base_url))
        temp = temperature or 0.0
        tokens = max_tokens or 2000

        cache_key = (
            model_name,
            temp,
            tokens,
            base_url_hash,
            reasoning_effort,
            thinking_mode,
        )

        def factory() -> ChatOpenAI | ChatDeepSeek:
            kwargs: dict[str, Any] = {}
            if thinking_mode:
                kwargs["extra_body"] = {"thinking": {"type": thinking_mode}}
                if thinking_mode != "disabled" and reasoning_effort:
                    kwargs["reasoning_effort"] = reasoning_effort

            # Use ChatDeepSeek for DeepSeek models (native reasoning_content support)
            if HAS_DEEPSEEK and model_name.startswith("deepseek"):
                return ChatDeepSeek(
                    **client_config,
                    model=model_name,
                    temperature=temp,
                    max_tokens=tokens,
                    stream_chunk_timeout=300,
                    **kwargs,
                )
            return ChatOpenAI(
                **client_config,
                model=model_name,
                temperature=temp,
                max_tokens=tokens,
                stream_chunk_timeout=300,
                **kwargs,
            )

        return _llm_cache.get_or_create(cache_key, factory)

    def _construct_model_string(
        self,
        provider_type: str | None,
        model_name: str | None,
    ) -> str:
        """Construct a model string for Deep Agents SDK.

        Args:
            provider_type: Provider type (e.g., 'openai', 'azure', 'ollama', 'z.ai')
            model_name: Model identifier (e.g., 'gpt-4o', 'glm-4.7')

        Returns:
            Model string in format '<provider>:<model>'

        Example:
            >>> self._construct_model_string("openai", "gpt-4o")
            'openai:gpt-4o'
        """
        # Map provider types to Deep Agents SDK format
        provider_mapping = {
            "openai": "openai",
            "azure": "azure",
            "ollama": "ollama",
            "z.ai": "openai",  # Z.AI uses OpenAI-compatible API
            "deepseek": "openai",  # DeepSeek uses OpenAI-compatible API
        }

        provider = provider_mapping.get(provider_type or "", "openai")

        # Clean model name to remove any provider prefix
        clean_model = model_name or ""
        if ":" in clean_model:
            clean_model = clean_model.split(":")[-1]

        return f"{provider}:{clean_model}"

    async def _create_deep_agent_graph(
        self,
        llm: ChatOpenAI | ChatDeepSeek,
        tool_context: ToolContext,
        assistant_config: AIAssistantConfig,
        websocket: WebSocket | None = None,
        session_id: UUID | None = None,
        enable_subagents: bool = True,
        provider_type: str | None = None,
        model_name: str | None = None,
        available_tools: list[Any] | None = None,
        event_bus: AgentEventBus | None = None,
        user_role: str = "guest",
    ) -> tuple[Any, InterruptNode | None]:
        """Create Deep Agent graph with Backcast context.

        Uses DeepAgentOrchestrator to wrap create_deep_agent() from the
        LangChain Deep Agents SDK. Preserves security model and temporal context.

        Args:
            llm: The language model to use (ChatOpenAI or ChatDeepSeek)
            tool_context: ToolContext with user permissions and temporal parameters
            assistant_config: AI assistant configuration
            websocket: Optional WebSocket connection for InterruptNode
            session_id: Optional session ID for InterruptNode
            enable_subagents: Whether to enable subagent delegation
            provider_type: Optional provider type for model string construction
            model_name: Optional model name for model string construction
            available_tools: Optional list of available tools for InterruptNode
            event_bus: Optional event bus for InterruptNode
            user_role: Per-user RBAC role for tool visibility filtering

        Returns:
            Tuple of (compiled_graph, interrupt_node) where interrupt_node may be None

        Note:
            This is an alternative to create_graph() that uses the Deep Agents SDK
            for planning and subagent delegation. Falls back to create_graph() if
            Deep Agents SDK is not available or encounters errors.

            InterruptNode is integrated via BackcastSecurityMiddleware to handle
            approvals for HIGH risk tools in standard mode. CRITICAL tools are blocked entirely.
        """
        # Create InterruptNode first (needed for middleware and always per-request)
        interrupt_node = None
        if available_tools and session_id and (websocket or event_bus):
            interrupt_node = InterruptNode(
                available_tools,
                tool_context,
                websocket=websocket,
                session_id=session_id,
                event_bus=event_bus,
            )

        system_prompt = assistant_config.system_prompt or DEFAULT_SYSTEM_PROMPT
        assistant_role = assistant_config.default_role

        # Compile graph
        try:
            logger.info(f"[GRAPH_COMPILE] Compiling new graph for session {session_id}")
            graph_creation_start = time.time()

            agent_config = AgentConfig(
                allowed_tools=None,
                checkpointer=shared_checkpointer,
                context_schema=BackcastRuntimeContext,
                assistant_role=assistant_role,
                user_role=user_role,
            )

            if settings.AI_ORCHESTRATOR == OrchestratorMode.SUPERVISOR:
                supervisor_orchestrator = SupervisorOrchestrator(
                    model=llm,
                    context=tool_context,
                    system_prompt=system_prompt,
                )
                graph = await supervisor_orchestrator.create_supervisor_graph(
                    agent_config
                )
            else:
                deep_orchestrator = DeepAgentOrchestrator(
                    model=llm,
                    context=tool_context,
                    system_prompt=system_prompt,
                    enable_subagents=enable_subagents,
                    interrupt_node=None,
                )
                graph = await deep_orchestrator.create_agent(agent_config)

            graph_creation_duration_ms = (time.time() - graph_creation_start) * 1000
            logger.info(
                f"[GRAPH_CREATION_COMPLETE] _create_deep_agent_graph | "
                f"duration_ms={graph_creation_duration_ms:.2f} | "
                f"session_id={session_id} | "
                f"graph_type={type(graph).__name__}"
            )

            return graph, interrupt_node

        except ImportError:
            logger.warning("Deep Agents SDK not available, falling back to LangGraph")
            return create_graph(
                llm,
                create_project_tools(tool_context),
                tool_context,
                websocket,
                session_id,
            )
        except Exception as e:
            logger.error(f"Error creating Deep Agent: {e}, falling back to LangGraph")
            return create_graph(
                llm,
                create_project_tools(tool_context),
                tool_context,
                websocket,
                session_id,
            )

    async def chat(
        self,
        message: str,
        assistant_config: AIAssistantConfig,
        session_id: UUID | None,
        user_id: UUID,
    ) -> AIChatResponse:
        """Process a chat message using LangGraph.

        Context: Main entry point for the AI conversation. Manages the session, invokes the graph, and saves history.
                Uses the new StateGraph with ainvoke for non-streaming responses.

        Args:
            message: The user's input message
            assistant_config: Configuration defining the model and allowed tools
            session_id: Optional existing session ID to continue. If None, a new session is created
            user_id: ID of the user sending the message

        Returns:
            Structured response containing the assistant's message, any tool calls, and the session ID

        Raises:
            ValueError: If session creation fails or no assistant response is generated
        """
        with trace_context(
            "agent.chat",
            attributes={
                "session_id": str(session_id) if session_id else "new",
                "user_id": str(user_id),
                "assistant_id": str(assistant_config.id),
            },
        ):
            return await self._chat_impl(message, assistant_config, session_id, user_id)

    async def _chat_impl(
        self,
        message: str,
        assistant_config: AIAssistantConfig,
        session_id: UUID | None,
        user_id: UUID,
    ) -> AIChatResponse:
        """Internal implementation of chat processing.

        Args:
            message: The user's input message
            assistant_config: Configuration defining the model and allowed tools
            session_id: Optional existing session ID to continue. If None, a new session is created
            user_id: ID of the user sending the message

        Returns:
            Structured response containing the assistant's message, any tool calls, and the session ID

        Raises:
            ValueError: If session creation fails or no assistant response is generated
        """
        db_session: AIConversationSession | None
        if session_id:
            db_session = await self.config_service.get_session(session_id)
            if not db_session:
                raise ValueError(f"Session {session_id} not found")
        else:
            # Create new session
            db_session = await self.config_service.create_session(
                user_id=user_id,
                assistant_config_id=assistant_config.id,
            )
            session_id = db_session.id
        if not session_id:
            raise ValueError("Failed to create session")

        _ = await self.config_service.add_message(
            session_id=session_id,
            role="user",
            content=message,
        )

        # Load context from session
        session_project_id = (
            UUID(db_session.project_id)
            if db_session and db_session.project_id
            else None
        )
        session_context = db_session.context if db_session else None

        # Build history first (needed before system prompt)
        history = await self._build_conversation_history(session_id)

        # Enrich context with entity names from DB
        enriched_context = session_context
        if session_context:
            enriched_context = await self._resolve_context_names(
                session_context, session_project_id
            )

        base_prompt = assistant_config.system_prompt or DEFAULT_SYSTEM_PROMPT
        system_prompt = self._build_system_prompt(
            base_prompt=base_prompt,
            project_id=session_project_id,
            context=enriched_context,
        )
        history.insert(0, SystemMessage(content=system_prompt))

        client_config, model_name, provider_type = await self._get_llm_client_config(
            UUID(str(assistant_config.model_id))
        )

        llm = await self._create_langchain_llm(
            client_config,
            model_name,
            assistant_config.temperature,
            assistant_config.max_tokens,
        )

        user_role = await _get_user_role(self.session, user_id)

        tool_context = ToolContext(
            self.session,
            str(user_id),
            user_role=user_role,
            project_id=str(session_project_id) if session_project_id else None,
        )
        available_tools = create_project_tools(tool_context)
        tools_dict = {tool.name: tool for tool in available_tools}

        if assistant_config.default_role:
            filtered = await filter_tools_by_role(
                list(tools_dict.values()), assistant_config.default_role
            )
            tools_dict = {t.name: t for t in filtered}

        # Filter by user's actual role
        filtered = await filter_tools_by_role(list(tools_dict.values()), user_role)
        tools_dict = {t.name: t for t in filtered}

        graph, _interrupt_node = create_graph(
            llm=llm, tools=list(tools_dict.values()), context=tool_context
        )

        recursion_limit = (
            assistant_config.recursion_limit
            if assistant_config.recursion_limit is not None
            else 25
        )

        # Invoke the graph
        try:
            existing_briefing = await self.config_service.get_session_briefing(
                session_id
            )
            if existing_briefing:
                logger.info(
                    "[BRIEFING_PERSIST] Restored briefing from DB with %d sections (non-streaming)",
                    len(existing_briefing.get("sections", [])),
                )

            result = await graph.ainvoke(
                input_state={
                    "messages": history,
                    "tool_call_count": 0,
                    "max_tool_iterations": recursion_limit,
                    "next": "agent",
                    "briefing_data": existing_briefing,
                },
                config={
                    "recursion_limit": recursion_limit,
                    "configurable": {"thread_id": str(session_id)},
                },
            )

            final_briefing = result.get("briefing_data")
            if final_briefing:
                section_count = len(final_briefing.get("sections", []))
                await self.config_service.save_session_briefing(
                    session_id, final_briefing
                )
                logger.info(
                    "[BRIEFING_PERSIST_SUCCESS] Saved briefing to DB with %d sections (non-streaming) | session_id=%s",
                    section_count,
                    session_id,
                )
            else:
                logger.info(
                    "[BRIEFING_PERSIST_SUCCESS] No briefing_data to save (non-streaming) | session_id=%s",
                    session_id,
                )

            shared_checkpointer.delete_thread(str(session_id))
            logger.info(
                "[BRIEFING_PERSIST_SUCCESS] Deleted checkpoint after save (non-streaming) | session_id=%s",
                session_id,
            )
        finally:
            try:
                await ToolSessionManager.commit()
                logger.debug(
                    f"Cleaned up task-local sessions after graph invocation for session {session_id}"
                )
            except Exception as cleanup_error:
                logger.debug(
                    f"No task-local sessions to clean up or cleanup failed: {cleanup_error}"
                )
                # Ignore cleanup errors - sessions may have already been removed

        final_message = None
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                final_message = msg
                break

        if not final_message:
            raise ValueError("No assistant response generated")

        tool_calls_data: list[dict[str, Any]] = []

        for msg in messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                # Convert ToolCall objects to dict format
                for tc in msg.tool_calls:
                    tool_calls_data.append(
                        {
                            "id": tc.get("id", ""),
                            "name": tc.get("name", ""),
                            "args": tc.get("args", {}),
                        }
                    )
            # Note: Tool messages are not directly accessible from the result
            # In a real implementation, you might want to track these separately

        # Convert AIMessage content to string (can be str | list)
        content_str = (
            final_message.content
            if isinstance(final_message.content, str)
            else str(final_message.content)
            if final_message.content
            else ""
        )
        rc_metadata = _extract_reasoning_content(final_message)
        assistant_msg = await self.config_service.add_message(
            session_id=session_id,
            role="assistant",
            content=content_str,
            tool_calls=tool_calls_data if tool_calls_data else None,
            tool_results=None,  # No tool results in non-streaming mode
            message_metadata=rc_metadata,
        )

        # Build response
        return AIChatResponse(
            session_id=session_id,
            message=AIConversationMessagePublic.model_validate(assistant_msg),
            tool_calls=tool_calls_data if tool_calls_data else None,
        )

    async def _persist_briefing_from_checkpoint(
        self,
        session_id: UUID,
        log_label: str = "BRIEFING_PERSIST",
    ) -> bool:
        """Load briefing from checkpoint and persist to database.

        Extracts briefing_data from the LangGraph checkpoint, saves it to the
        session via config_service, and deletes the checkpoint. Returns True
        if briefing was found and saved.

        We persist from checkpoint (not graph state) because the streaming
        events don't carry the final briefing -- it's only in the checkpoint
        after graph completes.
        """
        try:
            checkpoint_state = await shared_checkpointer.aget(
                {"configurable": {"thread_id": str(session_id)}}
            )
            if not checkpoint_state:
                return False

            channel_values = checkpoint_state.get("channel_values", {})
            briefing_data: dict[str, Any] | None = cast(
                Any, channel_values.get("briefing_data")
            )
            if not briefing_data:
                logger.debug(
                    "[%s] No briefing_data in checkpoint | session_id=%s",
                    log_label,
                    session_id,
                )
                return False

            section_count = len(briefing_data.get("sections", []))
            await self.config_service.save_session_briefing(session_id, briefing_data)
            # Checkpoint is always deleted to prevent state bloat across sessions.
            shared_checkpointer.delete_thread(str(session_id))
            logger.info(
                "[%s] Saved briefing (%d sections) and deleted checkpoint | session_id=%s",
                log_label,
                section_count,
                session_id,
            )
            return True
        except Exception as exc:
            logger.error(
                "[%s] Failed: %s | session_id=%s",
                log_label,
                exc,
                session_id,
                exc_info=True,
            )
            return False

    async def _run_agent_graph(
        self,
        message: str,
        assistant_config: AIAssistantConfig,
        session_id: UUID,
        user_id: UUID,
        event_bus: AgentEventBus,
        project_id: UUID | None = None,
        branch_id: UUID | None = None,
        as_of: datetime | None = None,
        branch_name: str | None = None,
        branch_mode: Literal["merged", "isolated"] | None = None,
        execution_mode: ExecutionMode = ExecutionMode.STANDARD,
        context: dict[str, Any] | None = None,
    ) -> AgentExecutionMetrics:
        """Run the agent graph and publish streaming events to an AgentEventBus.

        Decoupled from WebSocket: events are published to the bus so any consumer
        (REST SSE, WebSocket reconnection) can subscribe by execution_id.
        Communicates results entirely through event_bus.

        Args:
            message: The user's input message
            assistant_config: Configuration defining the model and allowed tools
            session_id: Existing session ID to continue
            user_id: ID of the user who sent the message
            event_bus: AgentEventBus to publish events to
            project_id: Optional project context UUID
            branch_id: Optional branch context UUID
            as_of: Optional historical date for temporal queries
            branch_name: Optional branch name for temporal queries
            branch_mode: Optional branch mode for temporal queries
            execution_mode: Execution mode for tool filtering

        Returns:
            AgentExecutionMetrics with aggregated token usage and tool call count.
        """
        self._subagent_invocation_counts.clear()
        history = await self._build_conversation_history(session_id)

        # Enrich context with entity names from DB
        enriched_context = context
        if context:
            enriched_context = await self._resolve_context_names(context, project_id)

        base_prompt = assistant_config.system_prompt or DEFAULT_SYSTEM_PROMPT
        system_prompt = self._build_system_prompt(
            base_prompt=base_prompt,
            project_id=project_id,
            as_of=as_of,
            branch_name=branch_name,
            branch_mode=branch_mode,
            context=enriched_context,
        )
        history.insert(0, SystemMessage(content=system_prompt))

        client_config, model_name, provider_type = await self._get_llm_client_config(
            UUID(str(assistant_config.model_id))
        )

        llm = await self._create_langchain_llm(
            client_config,
            model_name,
            assistant_config.temperature,
            assistant_config.max_tokens,
        )

        user_role = await _get_user_role(self.session, user_id)

        tool_context = ToolContext(
            self.session,
            str(user_id),
            user_role=user_role,
            project_id=str(project_id) if project_id else None,
            branch_id=str(branch_id) if branch_id else None,
            as_of=as_of,
            branch_name=branch_name,
            branch_mode=branch_mode,
            execution_mode=execution_mode,
            _event_bus=event_bus,
        )
        available_tools = create_project_tools(tool_context)

        graph, interrupt_node = await self._create_deep_agent_graph(
            llm=llm,
            tool_context=tool_context,
            assistant_config=assistant_config,
            websocket=None,
            session_id=session_id,
            enable_subagents=True,
            provider_type=provider_type,
            model_name=model_name,
            available_tools=available_tools,
            event_bus=event_bus,
            user_role=user_role,
        )

        set_request_context(tool_context, interrupt_node)

        if interrupt_node is not None:
            self.register_interrupt_node(session_id, interrupt_node)

        log_context_usage_estimate(
            messages=history,
            model_name=model_name,
            session_id=str(session_id),
            execution_id=event_bus.execution_id,
        )

        recursion_limit = (
            assistant_config.recursion_limit
            if assistant_config.recursion_limit is not None
            else 25
        )

        # -- Stream state --
        all_tool_calls: list[dict[str, Any]] = []
        all_tool_results: list[dict[str, Any]] = []
        main_agent_segments: dict[str, list[str]] = {}
        reasoning_content_value: str | None = None  # DeepSeek thinking mode

        subagent_messages_by_main_invocation: dict[str, list[dict[str, Any]]] = (
            defaultdict(list)
        )

        current_step = 0
        estimated_total_steps: int | None = None
        stream_start_time = time.time()
        total_output_chars = 0
        token_accumulator = TokenUsageAccumulator()
        tool_calls_count = 0
        current_subagent_name: str | None = None
        current_invocation_id: str | None = None
        main_invocation_id: str = ""
        task_initiating_main_invocation_id: str | None = None
        last_entered_agent: str | None = None

        # Skipping ~40-60% of LangGraph events reduces CPU in the hot streaming path.
        _HANDLED_EVENTS = frozenset(
            {
                "on_chain_start",
                "on_chain_end",
                "on_chat_model_stream",
                "on_chat_model_end",
                "on_tool_start",
                "on_tool_end",
                "on_tool_error",
                "on_end",
            }
        )

        # Per-invocation token accumulator for batched publishing
        _token_accumulator: dict[str, list[str]] = {}

        # -- Event helpers (closures over stream state) --
        def _publish(event_type: str, data: dict[str, Any]) -> None:
            event_bus.publish(
                AgentEvent(
                    event_type=event_type,
                    data=data,
                    timestamp=datetime.now(UTC),
                )
            )

        def _flush_accumulated_tokens(invocation_id: str | None) -> None:
            """Flush accumulated tokens for a given invocation to the event bus."""
            if invocation_id is None:
                return
            buffered = _token_accumulator.pop(invocation_id, [])
            if not buffered:
                return
            concatenated = "".join(buffered)
            _publish(
                "token_batch",
                {
                    "type": "token_batch",
                    "tokens": concatenated,
                    "session_id": str(session_id),
                    "source": "subagent" if current_subagent_name else "main",
                    "subagent_name": current_subagent_name,
                    "invocation_id": invocation_id,
                },
            )

        def _publish_briefing_update(
            chain_output: Any,
            chain_name: str,
            *,
            log_label: str | None = None,
        ) -> None:
            """Extract briefing data from a chain output and publish a briefing_update event."""
            if (
                not isinstance(chain_output, dict)
                or "briefing_data" not in chain_output
            ):
                return
            briefing_data = chain_output.get("briefing_data") or {}
            try:
                briefing_md = BriefingDocument.model_validate(
                    briefing_data
                ).to_markdown()
            except Exception:
                return
            if not briefing_md:
                return
            completed = chain_output.get("completed_specialists", set())
            completed_list = sorted(completed) if isinstance(completed, set) else []
            _publish(
                "briefing_update",
                WSBriefingMessage(
                    type="briefing_update",
                    briefing=briefing_md,
                    specialist_name=chain_name,
                    completed_specialists=completed_list,
                ).model_dump(mode="json"),
            )
            if log_label:
                logger.info(
                    "[%s] name=%s | sections=%d | completed=%s",
                    log_label,
                    chain_name,
                    len(briefing_data.get("sections", [])),
                    completed_list,
                )

        # Background task to flush tokens periodically for real-time streaming
        async def _periodic_flush() -> None:
            while True:
                await asyncio.sleep(settings.AI_TOKEN_BUFFER_INTERVAL_MS / 1000)
                for inv_id in list(_token_accumulator.keys()):
                    _flush_accumulated_tokens(inv_id)

        _flush_task = asyncio.create_task(_periodic_flush())

        graph_error: Exception | None = None
        briefing_persisted = False

        try:
            # -- Graph invocation with retry --
            main_invocation_id = str(uuid.uuid4())

            existing_briefing = await self.config_service.get_session_briefing(
                session_id
            )
            if existing_briefing:
                logger.info(
                    "[BRIEFING_PERSIST] Restored briefing from DB with %d sections (streaming)",
                    len(existing_briefing.get("sections", [])),
                )

            # Send thinking event
            _publish("thinking", {"type": "thinking"})

            # Retry loop for transient network errors during streaming
            max_retries = 2
            retry_delay = 2.0
            events_processed = 0

            for _retry_attempt in range(max_retries + 1):
                try:
                    async for event in graph.astream_events(
                        {
                            "messages": history,
                            "tool_call_count": 0,
                            "max_tool_iterations": recursion_limit,
                            "next": "agent",
                            "briefing_data": existing_briefing,
                        },
                        config={
                            "recursion_limit": recursion_limit,
                            "configurable": {"thread_id": str(session_id)},
                        },
                        version="v1",
                        context=BackcastRuntimeContext(
                            user_id=str(user_id),
                            user_role=user_role,
                            project_id=str(project_id) if project_id else None,
                            branch_id=str(branch_id) if branch_id else None,
                            execution_mode=execution_mode.value,
                        ),
                    ):
                        events_processed += 1
                        event_type = event.get("event", "")
                        data = event.get("data", {})
                        if event_type not in _HANDLED_EVENTS:
                            continue
                        # Handle agent transitions in supervisor graph
                        # When a specialist subgraph node starts/ends, detect by chain name
                        chain_name = event.get("name", "")
                        if (
                            event_type == "on_chain_start"
                            and chain_name in SPECIALIST_AGENT_NAMES
                        ):
                            # LangGraph emits on_chain_start twice per specialist
                            # (outer node + inner graph) — deduplicate via last_entered_agent.
                            if last_entered_agent == chain_name:
                                pass
                            else:
                                _flush_accumulated_tokens(
                                    current_invocation_id or main_invocation_id
                                )
                                current_subagent_name = chain_name
                                current_invocation_id = str(uuid.uuid4())
                                last_entered_agent = chain_name
                                _publish(
                                    "agent_transition",
                                    {
                                        "type": "agent_transition",
                                        "agent_name": chain_name,
                                        "direction": "enter",
                                        "invocation_id": current_invocation_id,
                                    },
                                )
                        elif (
                            event_type == "on_chain_end"
                            and chain_name in SPECIALIST_AGENT_NAMES
                        ):
                            chain_output = data.get("output")

                            # Extract briefing data from either dict
                            # output or Command.update.  Specialist
                            # nodes return Command objects, so
                            # isinstance(dict) is False -- we must
                            # check Command.update as a fallback.
                            output_dict: dict[str, Any] | None = None
                            if isinstance(chain_output, dict):
                                output_dict = chain_output
                            elif hasattr(chain_output, "update") and isinstance(
                                getattr(chain_output, "update", None), dict
                            ):
                                output_dict = chain_output.update

                            if output_dict and "briefing_data" in output_dict:
                                _publish_briefing_update(output_dict, chain_name)
                                _publish(
                                    "agent_transition",
                                    {
                                        "type": "agent_transition",
                                        "agent_name": chain_name,
                                        "direction": "exit",
                                        "invocation_id": current_invocation_id,
                                    },
                                )
                            elif chain_name == current_subagent_name:
                                _flush_accumulated_tokens(current_invocation_id)

                            # Always reset specialist tracking on chain end
                            current_subagent_name = None
                            current_invocation_id = None
                            last_entered_agent = None

                        # Handle supervisor node completion - send briefing to frontend
                        elif (
                            event_type == "on_chain_end" and chain_name == "supervisor"
                        ):
                            chain_output = data.get("output", {})
                            _publish_briefing_update(
                                chain_output, "supervisor", log_label="SUPERVISOR_END"
                            )

                        # Handle initialize_briefing node completion - send briefing to frontend
                        elif event_type == "on_chain_end":
                            chain_output = data.get("output", {})
                            if chain_name not in SPECIALIST_AGENT_NAMES:
                                _publish_briefing_update(
                                    chain_output,
                                    "supervisor",
                                    log_label="CHAIN_END_NON_SPECIALIST",
                                )

                        # Handle token streaming
                        if event_type == "on_chat_model_stream":
                            chunk = data.get("chunk")
                            # Token streaming: accumulate per-invocation, flush in batches.
                            if isinstance(chunk, AIMessageChunk):
                                # Capture reasoning from chunks — the final AIMessage may
                                # not preserve additional_kwargs.
                                rc = chunk.additional_kwargs.get("reasoning_content")
                                if rc and isinstance(rc, str):
                                    if reasoning_content_value is None:
                                        reasoning_content_value = rc
                                    else:
                                        reasoning_content_value += rc
                            if chunk:
                                content = ""
                                if hasattr(chunk, "text"):
                                    content = chunk.text
                                elif hasattr(chunk, "content"):
                                    content = str(chunk.content)

                                if content:
                                    if current_subagent_name is None:
                                        if (
                                            main_invocation_id
                                            not in main_agent_segments
                                        ):
                                            main_agent_segments[main_invocation_id] = []
                                        main_agent_segments[main_invocation_id].append(
                                            content
                                        )

                                    total_output_chars += len(content)

                                    # Accumulate tokens per invocation for batched publish
                                    invocation_id_to_use = (
                                        current_invocation_id
                                        if current_subagent_name
                                        else main_invocation_id
                                    )
                                    if invocation_id_to_use is not None:
                                        if (
                                            invocation_id_to_use
                                            not in _token_accumulator
                                        ):
                                            _token_accumulator[
                                                invocation_id_to_use
                                            ] = []
                                        _token_accumulator[invocation_id_to_use].append(
                                            content
                                        )

                        # Handle chat model end -- capture actual token usage
                        elif event_type == "on_chat_model_end":
                            token_accumulator.accumulate_from_event(data)

                        # Handle tool start
                        elif event_type == "on_tool_start":
                            # Flush tokens before tool execution to maintain ordering.
                            _flush_accumulated_tokens(main_invocation_id)
                            if current_invocation_id and current_subagent_name:
                                _flush_accumulated_tokens(current_invocation_id)

                            tool_name = event.get("name", "")
                            tool_input = data.get("input", {})
                            tool_calls_count += 1
                            current_step += 1

                            if tool_name == "task":
                                current_subagent_name = (
                                    tool_input.get("subagent_type")
                                    if isinstance(tool_input, dict)
                                    else None
                                )
                                current_invocation_id = str(uuid.uuid4())
                                task_initiating_main_invocation_id = main_invocation_id

                            # Planning event
                            if tool_name == "write_todos":
                                plan = (
                                    tool_input.get("plan")
                                    if isinstance(tool_input, dict)
                                    else None
                                )
                                steps = None
                                if isinstance(tool_input, dict):
                                    raw_steps = tool_input.get("steps")
                                    if isinstance(raw_steps, list):
                                        steps = [
                                            PlanningStep(text=str(s), done=False)
                                            for s in raw_steps
                                        ]
                                        estimated_total_steps = len(steps)
                                _publish(
                                    "planning",
                                    {
                                        "type": "planning",
                                        "plan": plan,
                                        "steps": [
                                            {"text": s.text, "done": s.done}
                                            for s in steps
                                        ]
                                        if steps
                                        else None,
                                        "step_number": current_step,
                                        "total_steps": estimated_total_steps,
                                        "invocation_id": main_invocation_id,
                                    },
                                )

                            # Subagent delegation event
                            elif tool_name == "task":
                                subagent_type = (
                                    tool_input.get("subagent_type")
                                    if isinstance(tool_input, dict)
                                    else None
                                )
                                description = (
                                    tool_input.get("description")
                                    if isinstance(tool_input, dict)
                                    else None
                                )
                                if subagent_type:
                                    _publish(
                                        "subagent",
                                        {
                                            "type": "subagent",
                                            "subagent": subagent_type,
                                            "message": description,
                                            "step_number": current_step,
                                            "total_steps": estimated_total_steps,
                                            "invocation_id": current_invocation_id,
                                        },
                                    )

                            # Standard tool_call event
                            _publish(
                                "tool_call",
                                {
                                    "type": "tool_call",
                                    "tool": tool_name,
                                    "args": tool_input,
                                    "step_number": current_step,
                                    "total_steps": estimated_total_steps,
                                    "invocation_id": current_invocation_id
                                    if current_subagent_name
                                    else main_invocation_id,
                                },
                            )

                        # Handle tool end
                        elif event_type == "on_tool_end":
                            # After a task (subagent delegation) completes, generate a
                            # new main invocation_id to start a fresh response segment.
                            tool_name = event.get("name", "")

                            # Subagent result handling
                            if (
                                tool_name == "task"
                                and current_invocation_id is not None
                            ):
                                # Flush subagent tokens before processing result
                                _flush_accumulated_tokens(current_invocation_id)

                                tool_output = data.get("output", "")
                                subagent_content = extract_tool_output_content(
                                    tool_output
                                )

                                if subagent_content:
                                    subagent_type = current_subagent_name or "subagent"
                                    if (
                                        subagent_type
                                        not in self._subagent_invocation_counts
                                    ):
                                        self._subagent_invocation_counts[
                                            subagent_type
                                        ] = 0
                                    self._subagent_invocation_counts[subagent_type] += 1
                                    invocation_number = (
                                        self._subagent_invocation_counts[subagent_type]
                                    )

                                    target_invocation_id = (
                                        task_initiating_main_invocation_id
                                        or main_invocation_id
                                    )
                                    subagent_messages_by_main_invocation[
                                        target_invocation_id
                                    ].append(
                                        {
                                            "role": "assistant",
                                            "content": subagent_content,
                                            "message_metadata": {
                                                "subagent_name": subagent_type,
                                                "invocation_number": invocation_number,
                                            }
                                            if current_subagent_name
                                            else None,
                                        }
                                    )

                                    _publish(
                                        "subagent_result",
                                        {
                                            "type": "subagent_result",
                                            "subagent_name": current_subagent_name
                                            or "subagent",
                                            "content": subagent_content,
                                            "invocation_id": current_invocation_id,
                                        },
                                    )

                                # Subagent completion
                                _publish(
                                    "agent_complete",
                                    {
                                        "type": "agent_complete",
                                        "agent_type": "subagent",
                                        "invocation_id": current_invocation_id,
                                        "agent_name": current_subagent_name,
                                    },
                                )

                                # Content reset after subagent
                                _publish(
                                    "content_reset",
                                    {
                                        "type": "content_reset",
                                        "reason": "subagent_completed",
                                    },
                                )

                                current_subagent_name = None
                                current_invocation_id = None
                                task_initiating_main_invocation_id = None

                            # Generate new main invocation_id after task tool
                            # completion only (subagent delegation). For other
                            # tools, the same agent continues — keep one segment.
                            if tool_name == "task":
                                main_invocation_id = str(uuid.uuid4())

                            tool_output = data.get("output", "")
                            result_content = tool_output
                            if isinstance(tool_output, ToolMessage):
                                result_content = tool_output.content
                            elif (
                                isinstance(tool_output, dict)
                                and "content" in tool_output
                            ):
                                result_content = tool_output["content"]
                            elif isinstance(tool_output, Command):
                                result_content = {"command": tool_output.update}

                            result_content = self._make_json_serializable(
                                result_content
                            )

                            tool_result_dict: dict[str, Any] = {
                                "tool": tool_name,
                                "success": True,
                                "result": result_content,
                                "error": None,
                            }
                            if current_subagent_name is None:
                                all_tool_results.append(tool_result_dict)

                            _publish(
                                "tool_result",
                                {
                                    "type": "tool_result",
                                    "tool": tool_name,
                                    "result": jsonable_encoder(tool_result_dict),
                                    "invocation_id": current_invocation_id
                                    if current_subagent_name
                                    else main_invocation_id,
                                },
                            )

                        # Handle tool error
                        elif event_type == "on_tool_error":
                            tool_name = event.get("name", "")
                            error = data.get("error")

                            if current_subagent_name is None:
                                error_result_dict: dict[str, Any] = {
                                    "tool": tool_name,
                                    "success": False,
                                    "result": None,
                                    "error": (str(error) if error else "Unknown error"),
                                }
                                all_tool_results.append(error_result_dict)

                                _publish(
                                    "tool_result",
                                    {
                                        "type": "tool_result",
                                        "tool": tool_name,
                                        "result": jsonable_encoder(error_result_dict),
                                        "invocation_id": current_invocation_id
                                        if current_subagent_name
                                        else main_invocation_id,
                                    },
                                )

                        # Handle completion
                        elif event_type == "on_end":
                            output = data.get("output", {})
                            messages = output.get("messages", [])

                            for msg in messages:
                                if isinstance(msg, AIMessage) and msg.tool_calls:
                                    for tc in msg.tool_calls:
                                        all_tool_calls.append(
                                            {
                                                "id": tc.get("id", ""),
                                                "name": tc.get("name", ""),
                                                "args": tc.get("args", {}),
                                            }
                                        )

                            logger.info(
                                f"Graph execution completed for execution "
                                f"event_bus {event_bus.execution_id}"
                            )

                    # -- Post-stream: persist briefing and cleanup --
                    # Flush all remaining accumulated tokens after stream ends
                    for inv_id in list(_token_accumulator.keys()):
                        _flush_accumulated_tokens(inv_id)

                    briefing_persisted = await self._persist_briefing_from_checkpoint(
                        session_id, log_label="BRIEFING_PERSIST_STREAMING"
                    )

                    break  # successful completion, exit retry loop

                except Exception as stream_err:
                    if (
                        not _is_transient_stream_error(stream_err)
                        or _retry_attempt >= max_retries
                    ):
                        if _retry_attempt >= max_retries:
                            logger.error(
                                f"Stream failed after {max_retries + 1} "
                                f"attempts: {stream_err}"
                            )
                        raise
                    logger.warning(
                        f"Transient stream error (attempt "
                        f"{_retry_attempt + 1}/{max_retries + 1}), "
                        f"retrying in {retry_delay}s: {stream_err}"
                    )
                    await asyncio.sleep(retry_delay)
                    events_processed = 0
                    _token_accumulator.clear()

        except Exception as e:
            graph_error = e  # capture for later persistence
            logger.error(f"Error in _run_agent_graph: {e}", exc_info=True)
            event_bus.publish(
                AgentEvent(
                    event_type="error",
                    data={"message": str(e), "code": 500},
                    timestamp=datetime.now(UTC),
                )
            )
        finally:
            # Cleanup: cancel background flush, flush remaining tokens,
            # clear per-request state.
            _flush_task.cancel()
            try:
                await _flush_task
            except asyncio.CancelledError:
                pass
            for inv_id in list(_token_accumulator.keys()):
                _flush_accumulated_tokens(inv_id)
            clear_request_context()
            self.unregister_interrupt_node(session_id)
            # Commit tool session - critical for cost element persistence
            try:
                await ToolSessionManager.commit()
            except Exception as commit_err:
                logger.error(
                    f"[TOOL_SESSION] Failed to commit tool session: {commit_err}",
                    exc_info=True,
                )
                # Re-raise to ensure commit failures are surfaced
                raise

            # Persist briefing on error if not already done — specialist
            # findings survive even when streaming fails.
            if not briefing_persisted:
                await self._persist_briefing_from_checkpoint(
                    session_id, log_label="BRIEFING_PERSIST_ERROR_PATH"
                )

        # -- Persist messages to session history --
        # Save assistant messages to session
        try:
            invocation_ids_in_order = list(main_agent_segments.keys())
            total_main_segments = len(invocation_ids_in_order)
            assistant_msg = None
            logger.info(
                "[MSG_SAVE] Saving assistant messages for session %s: %d segments, invocation_ids=%s",
                session_id,
                total_main_segments,
                invocation_ids_in_order,
            )

            for idx, inv_id in enumerate(invocation_ids_in_order):
                segment_content = "".join(main_agent_segments[inv_id])
                metadata: dict[str, Any] = {
                    "invocation_id": inv_id,
                    "segment_index": idx,
                    "total_segments": total_main_segments,
                }
                if reasoning_content_value:
                    metadata["reasoning_content"] = reasoning_content_value

                segment_tool_calls = (
                    all_tool_calls if idx == 0 and all_tool_calls else None
                )
                segment_tool_results = (
                    all_tool_results if idx == 0 and all_tool_results else None
                )

                segment_msg = await self.config_service.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=segment_content,
                    tool_calls=segment_tool_calls,
                    tool_results=segment_tool_results,
                    message_metadata=metadata,
                )
                await self.session.commit()
                await self.session.refresh(segment_msg)
                assistant_msg = segment_msg

                if inv_id in subagent_messages_by_main_invocation:
                    for subagent_msg_data in subagent_messages_by_main_invocation[
                        inv_id
                    ]:
                        subagent_msg = await self.config_service.add_message(
                            session_id=session_id,
                            **subagent_msg_data,
                        )
                        await self.session.commit()
                        await self.session.refresh(subagent_msg)
                        assistant_msg = subagent_msg

        except Exception as msg_error:
            logger.error(
                f"Error saving messages in _run_agent_graph: {msg_error}", exc_info=True
            )
            try:
                await self.session.rollback()
            except Exception:
                pass

        # Persist error message to session history if graph execution failed
        if graph_error is not None:
            try:
                await self.config_service.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=(
                        f"I encountered an error while processing your request: "
                        f"{graph_error}. The work completed before the error has "
                        f"been saved."
                    ),
                    message_metadata={
                        "error": True,
                        "error_type": type(graph_error).__name__,
                    },
                )
                await self.session.commit()
            except Exception as persist_error:
                logger.error(f"Failed to persist error message: {persist_error}")

        # Publish main agent completion
        _publish(
            "agent_complete",
            {
                "type": "agent_complete",
                "agent_type": "main",
                "invocation_id": main_invocation_id,
                "agent_name": "Assistant",
            },
        )

        # Publish execution status so frontend clears activeExecutionIdRef
        _publish(
            "execution_status",
            {
                "type": "execution_status",
                "execution_id": event_bus.execution_id,
                "status": "completed",
                "session_id": str(session_id),
            },
        )

        # Publish final complete event
        _publish(
            "complete",
            WSCompleteMessage(
                type="complete",
                session_id=session_id,
                message_id=assistant_msg.id if assistant_msg else None,
                token_usage=token_accumulator.to_dict(),
            ).model_dump(mode="json"),
        )

        # Log summary
        stream_duration_ms = (time.time() - stream_start_time) * 1000
        usage_dict = token_accumulator.to_dict()
        logger.info(
            f"[RUN_AGENT_GRAPH_COMPLETE] _run_agent_graph | "
            f"duration_ms={stream_duration_ms:.2f} | "
            f"execution_id={event_bus.execution_id} | "
            f"session_id={session_id} | "
            f"total_output_chars={total_output_chars} | "
            f"prompt_tokens={usage_dict['prompt_tokens']} | "
            f"completion_tokens={usage_dict['completion_tokens']} | "
            f"total_tokens={usage_dict['total_tokens']} | "
            f"tool_calls_count={tool_calls_count}"
        )

        # Log actual token usage from API
        log_actual_usage(
            accumulator=token_accumulator,
            model_name=model_name,
            session_id=str(session_id),
            execution_id=event_bus.execution_id,
        )

        return AgentExecutionMetrics(
            total_tokens=usage_dict["total_tokens"],
            tool_calls_count=tool_calls_count,
        )

    async def start_execution(
        self,
        message: str,
        assistant_config: AIAssistantConfig,
        session_id: UUID,
        user_id: UUID,
        project_id: UUID | None = None,
        branch_id: UUID | None = None,
        as_of: datetime | None = None,
        branch_name: str | None = None,
        branch_mode: Literal["merged", "isolated"] | None = None,
        execution_mode: ExecutionMode = ExecutionMode.STANDARD,
        execution_id: str | None = None,
        event_bus: AgentEventBus | None = None,
    ) -> str:
        """Start a background agent execution with its own DB session and event bus.

        Context: Creates an independent execution context that decouples the agent
        run from any specific WebSocket connection. Events are published to an
        AgentEventBus registered with the runner_manager, allowing any consumer
        (REST SSE, WebSocket reconnection) to subscribe by execution ID.

        The caller may pre-create an execution_id and event_bus and pass them in.
        This is useful when the caller needs to subscribe to the bus immediately
        (e.g., a WebSocket handler that starts the execution and forwards events
        in parallel).

        Args:
            message: The user's input message
            assistant_config: Configuration defining the model and allowed tools
            session_id: Existing session ID to continue
            user_id: ID of the user who sent the message
            project_id: Optional project context UUID
            branch_id: Optional branch context UUID
            as_of: Optional historical date for temporal queries
            branch_name: Optional branch name for temporal queries
            branch_mode: Optional branch mode for temporal queries
            execution_mode: Execution mode for tool filtering
            execution_id: Optional pre-generated execution ID. If not provided,
                a new UUID is generated.
            event_bus: Optional pre-created event bus. If not provided, a new
                bus is created and registered with the runner_manager.

        Returns:
            execution_id string for tracking the agent execution

        Raises:
            ValueError: If session creation fails
        """
        from app.db.session import async_session_maker

        if execution_id is None:
            execution_id = str(uuid.uuid4())

        # Use provided bus or create a new one
        should_remove_bus = False
        if event_bus is None:
            event_bus = runner_manager.create_bus(execution_id)
            should_remove_bus = True

        # Create independent DB session for this execution
        async with async_session_maker() as db:
            # Pre-fetch the session row so it is accessible in except/finally blocks
            session_stmt = select(AIConversationSession).where(
                AIConversationSession.id == str(session_id)
            )
            session_result = await db.execute(session_stmt)
            db_session = session_result.scalar_one_or_none()

            try:
                metrics: AgentExecutionMetrics | None = None

                # Create execution tracking row
                execution = AIAgentExecution(
                    session_id=str(session_id),
                    status="running",
                    execution_mode=execution_mode.value,
                )
                db.add(execution)
                await db.commit()
                await db.refresh(execution)

                # Set active_execution_id on session
                if db_session is not None:
                    db_session.active_execution_id = str(execution.id)
                    await db.commit()

                # Create agent service with this DB session
                exec_service = AgentService(db)

                # Run the agent graph, publishing events to the bus
                metrics = await exec_service._run_agent_graph(
                    message=message,
                    assistant_config=assistant_config,
                    session_id=session_id,
                    user_id=user_id,
                    event_bus=event_bus,
                    project_id=project_id,
                    branch_id=branch_id,
                    as_of=as_of,
                    branch_name=branch_name,
                    branch_mode=branch_mode,
                    execution_mode=execution_mode,
                    context=db_session.context if db_session else None,
                )

                # Update execution tracking row with metrics
                execution.status = "completed"
                execution.completed_at = datetime.now(UTC)  # type: ignore[assignment]
                execution.total_tokens = metrics.total_tokens
                execution.tool_calls_count = metrics.tool_calls_count
                await db.commit()

                # Clear active_execution_id on session
                if db_session is not None:
                    db_session.active_execution_id = None
                    await db.commit()

            except Exception as e:
                logger.error(
                    f"Error in start_execution {execution_id}: {e}", exc_info=True
                )
                # Update execution tracking row with error and partial metrics
                try:
                    execution.status = "error"
                    execution.error_message = str(e)[:2000]
                    execution.completed_at = datetime.now(UTC)  # type: ignore[assignment]
                    # Persist partial metrics if available
                    if metrics is not None:
                        execution.total_tokens = metrics.total_tokens
                        execution.tool_calls_count = metrics.tool_calls_count
                    await db.commit()
                except Exception:
                    await db.rollback()
                    # Retry with a fresh query in case the session was invalidated
                    try:
                        stmt = select(AIAgentExecution).where(
                            AIAgentExecution.id == str(execution.id)
                        )
                        result = await db.execute(stmt)
                        fresh_execution = result.scalar_one_or_none()
                        if fresh_execution is not None:
                            fresh_execution.status = "error"
                            fresh_execution.error_message = str(e)[:2000]
                            fresh_execution.completed_at = datetime.now(UTC)  # type: ignore[assignment]
                            if metrics is not None:
                                fresh_execution.total_tokens = metrics.total_tokens
                                fresh_execution.tool_calls_count = (
                                    metrics.tool_calls_count
                                )
                            await db.commit()
                    except Exception:
                        logger.error(
                            "Failed to update execution row on error path",
                            exc_info=True,
                        )

                # Clear active_execution_id on session (best-effort)
                if db_session is not None:
                    try:
                        db_session.active_execution_id = None
                        await db.commit()
                    except Exception:
                        pass

                # Publish execution status so frontend clears activeExecutionIdRef
                event_bus.publish(
                    AgentEvent(
                        event_type="execution_status",
                        data={
                            "type": "execution_status",
                            "execution_id": execution_id,
                            "status": "error",
                            "session_id": str(session_id),
                        },
                        timestamp=datetime.now(UTC),
                    )
                )

                # Publish error event
                event_bus.publish(
                    AgentEvent(
                        event_type="error",
                        data={"message": str(e), "code": 500},
                        timestamp=datetime.now(UTC),
                    )
                )

                raise
            finally:
                # Clean up the event bus from runner_manager only if we created it
                if should_remove_bus:
                    runner_manager.remove_bus(execution_id)

        return execution_id

    async def _resolve_context_names(
        self,
        context: dict[str, Any],
        project_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Enrich context dict with entity names looked up from the database.

        Looks up the human-readable name for the entity referenced in *context*
        so that the system prompt can identify it by name rather than by ID only.
        Name lookup failure is non-fatal -- the original context is returned
        without a ``name`` key if the query fails.

        Args:
            context: Context dictionary with at least ``type`` and ``id`` keys.
            project_id: Optional parent project ID (used to look up the project
                name when the context refers to a WBE or cost element).

        Returns:
            A **copy** of *context* with the ``name`` field populated when found.
        """
        enriched = dict(context)
        context_type = context.get("type")
        entity_id = context.get("id")

        if not context_type or not entity_id:
            return enriched

        try:
            entity_uuid = UUID(str(entity_id))
        except (ValueError, AttributeError):
            return enriched

        try:
            if context_type == "project":
                stmt = (
                    select(Project.name)
                    .where(Project.project_id == entity_uuid)
                    .where(sa_func.upper(Project.valid_time).is_(None))
                    .where(Project.deleted_at.is_(None))
                    .limit(1)
                )
                result = await self.session.execute(stmt)
                name = result.scalar_one_or_none()
                if name:
                    enriched["name"] = name

            elif context_type == "wbe":
                stmt = (
                    select(WBE.name)
                    .where(WBE.wbe_id == entity_uuid)
                    .where(sa_func.upper(WBE.valid_time).is_(None))
                    .where(WBE.deleted_at.is_(None))
                    .limit(1)
                )
                result = await self.session.execute(stmt)
                name = result.scalar_one_or_none()
                if name:
                    enriched["name"] = name
                # Also look up parent project name when project_id is available
                pid = context.get("project_id") or project_id
                if pid:
                    try:
                        pid_uuid = UUID(str(pid))
                        p_stmt = (
                            select(Project.name)
                            .where(Project.project_id == pid_uuid)
                            .where(sa_func.upper(Project.valid_time).is_(None))
                            .where(Project.deleted_at.is_(None))
                            .limit(1)
                        )
                        p_result = await self.session.execute(p_stmt)
                        p_name = p_result.scalar_one_or_none()
                        if p_name:
                            enriched["project_name"] = p_name
                    except (ValueError, AttributeError):
                        pass

            elif context_type == "cost_element":
                stmt = (
                    select(CostElement.name)
                    .where(CostElement.cost_element_id == entity_uuid)
                    .where(sa_func.upper(CostElement.valid_time).is_(None))
                    .where(CostElement.deleted_at.is_(None))
                    .limit(1)
                )
                result = await self.session.execute(stmt)
                name = result.scalar_one_or_none()
                if name:
                    enriched["name"] = name
                # Also look up parent project name when project_id is available
                pid = context.get("project_id") or project_id
                if pid:
                    try:
                        pid_uuid = UUID(str(pid))
                        p_stmt = (
                            select(Project.name)
                            .where(Project.project_id == pid_uuid)
                            .where(sa_func.upper(Project.valid_time).is_(None))
                            .where(Project.deleted_at.is_(None))
                            .limit(1)
                        )
                        p_result = await self.session.execute(p_stmt)
                        p_name = p_result.scalar_one_or_none()
                        if p_name:
                            enriched["project_name"] = p_name
                    except (ValueError, AttributeError):
                        pass

        except Exception:
            logger.warning(
                "Failed to resolve context name for %s %s",
                context_type,
                entity_id,
                exc_info=True,
            )

        return enriched

    def _build_system_prompt(
        self,
        base_prompt: str,
        project_id: UUID | None = None,
        as_of: datetime | None = None,
        branch_name: str | None = None,
        branch_mode: Literal["merged", "isolated"] | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Build system prompt with context awareness.

        Context: Project context is enforced at the tool level via ToolContext,
        not in the system prompt. This provides maximum security by preventing prompt injection
        attacks from bypassing constraints. The system prompt provides the LLM with awareness
        of context for better responses, but enforcement happens at the tool level.

        Temporal context (as_of, branch_name, branch_mode) is initialized from the session
        but can be changed by the LLM via the set_temporal_context tool. Changes propagate
        to all subsequent tool calls via the shared mutable ToolContext instance.

        Args:
            base_prompt: Base system prompt
            project_id: Optional project ID for project-scoped queries
            as_of: Optional historical date for temporal queries
            branch_name: Optional branch name for temporal queries
            branch_mode: Optional branch mode for temporal queries
            context: Optional context dictionary with type, id, and name

        Returns:
            Base system prompt with context information
        """
        context_sections = []

        # Add context awareness from session context
        if context:
            context_type = context.get("type", "general")
            context_name = context.get("name", "")

            if context_type == "general":
                context_sections.append(
                    "This is a general conversation without specific context. "
                    "You can help with projects, WBEs, and cost elements as needed."
                )
            elif context_type == "project":
                name_part = f" the project: {context_name}" if context_name else ""
                context_sections.append(
                    f"This conversation is about{name_part}. "
                    f"Context is scoped to this project (ID: {context.get('id', project_id)}). "
                    "Use project-scoped tools to query data within this project. "
                    "The user's access is limited to this project's data. "
                    "Use get_project_context tool to query project details. "
                    "Project scope is locked for this session - you cannot switch to other projects. "
                    "If the user asks about other projects, explain that this session is scoped to "
                    "this project and they should open a different chat session for other projects."
                )
            elif context_type == "wbe":
                name_part = (
                    f" the Work Breakdown Element (WBE): {context_name}"
                    if context_name
                    else " a Work Breakdown Element (WBE)"
                )
                context_sections.append(
                    f"This conversation is about{name_part}. "
                    f"WBE ID: {context.get('id')}. "
                    f"Parent project ID: {context.get('project_id', project_id)}. "
                    "Focus your responses on this specific WBE. "
                    "Use WBE-scoped tools to query and analyze this element."
                )
            elif context_type == "cost_element":
                name_part = (
                    f" the Cost Element: {context_name}"
                    if context_name
                    else " a Cost Element"
                )
                context_sections.append(
                    f"This conversation is about{name_part}. "
                    f"Cost Element ID: {context.get('id')}. "
                    f"Parent project ID: {context.get('project_id', project_id)}. "
                    "Focus your responses on this specific cost element. "
                    "Use cost element tools to query and analyze this element."
                )
        elif project_id:
            # Legacy support for project_id without context
            context_sections.append(
                f"You are operating in the context of a specific project (ID: {project_id}). "
                "Use project-scoped tools to query data within this project. "
                "The user's access is limited to this project's data. "
                "Use get_project_context tool to query project details. "
                "Project scope is locked for this session - you cannot switch to other projects."
            )

        # Add temporal context information when applicable
        if branch_name and branch_name != "main":
            context_sections.append(
                f"[TEMPORAL CONTEXT]\n"
                f"You are operating in branch '{branch_name}' (mode: {branch_mode}). "
                f"Changes made in this branch are isolated from the main branch until merged. "
                f"You can change the temporal context using the set_temporal_context tool "
                f"(e.g., switch branches, change as_of date, or toggle branch mode)."
            )
        elif as_of:
            context_sections.append(
                f"[TEMPORAL CONTEXT]\n"
                f"You are viewing historical data as of {as_of.strftime('%B %d, %Y at %I:%M %p')}. "
                f"You can change the temporal context using the set_temporal_context tool "
                f"to view a different date, switch branches, or change branch mode."
            )

        # Combine base prompt with context sections
        if context_sections:
            return base_prompt + "\n\n" + "\n\n".join(context_sections)

        # Return base prompt without context additions
        # Project enforcement happens at tool level via ToolContext
        # Temporal context can be changed via set_temporal_context tool
        return base_prompt

    async def _build_conversation_history(self, session_id: UUID) -> list[BaseMessage]:
        """Build conversation history from session messages.

        Context: Converts DB messages into LangChain message objects for context window.
        Includes attachment metadata for multimodal messages with vision support.

        Args:
            session_id: The session ID corresponding to the current conversation

        Returns:
            List of LangChain BaseMessage instances (HumanMessage, AIMessage, SystemMessage).
            For user messages with attachments, HumanMessage content will be a list of
            content blocks (text + image_url) for vision models.

        Raises:
            None
        """
        messages: list[BaseMessage] = []
        db_messages = await self.config_service.list_messages(session_id)
        for msg in db_messages:
            if msg.role == "user":
                # Check if message has attachments and format accordingly
                if msg.attachments:
                    # Build attachment metadata for format_multimodal_messages
                    attachment_dicts = [
                        {
                            "file_id": str(a.id),
                            "filename": a.filename,
                            "content_type": a.content_type,
                            "content": a.content,
                            "file_size": a.size,
                        }
                        for a in msg.attachments
                    ]

                    # Use format_multimodal_messages for proper LLM formatting
                    content_blocks = await self.format_multimodal_messages(
                        msg.content, attachments=attachment_dicts
                    )
                    # Type cast needed: list[dict[str, Any]] -> list[str | dict[Any, Any]]
                    # for HumanMessage compatibility with MyPy strict mode
                    messages.append(
                        HumanMessage(
                            content=cast(list[str | dict[Any, Any]], content_blocks)
                        )
                    )
                else:
                    # Plain text message without attachments
                    messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(
                    AIMessage(
                        content=msg.content,
                        **_restore_reasoning_content(msg.message_metadata),
                    )
                )
            elif msg.role == "tool":
                # Skip tool messages in history - they're implicit
                pass
        return messages

    async def format_multimodal_messages(
        self,
        text_content: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Format message content for vision models with image attachments.

        Context: Vision models like GPT-4 Vision require messages with mixed content
        types (text and image_url). This method formats user messages to include
        image attachments as base64 data URLs and document attachments as inline
        text blocks.

        Args:
            text_content: The text content of the user message
            attachments: Optional list of attachment metadata dictionaries.
                Each dict should have keys: content_type, filename, content.

        Returns:
            List of content blocks suitable for OpenAI API. Each block is a dict
            with either:
                - {"type": "text", "text": "..."}
                - {"type": "image_url", "image_url": {"url": "data:image/...;base64,..."}}

        Example:
            >>> format_multimodal_messages(
            ...     "What's in this image?",
            ...     [{"content_type": "image/png", "content": "<base64>"}]
            ... )
            [
                {"type": "text", "text": "What's in this image?"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,<base64>"}}
            ]
        """
        content_blocks: list[dict[str, Any]] = [{"type": "text", "text": text_content}]

        if attachments:
            # Process image attachments: use base64 data URLs
            for attachment in attachments:
                if not attachment.get("content_type", "").startswith("image/"):
                    continue
                attachment_content = attachment.get("content")
                if attachment_content:
                    content_type = attachment.get("content_type", "image/png")
                    data_url = f"data:{content_type};base64,{attachment_content}"
                    content_blocks.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        }
                    )

            # Process non-image attachments: inline as text blocks
            non_image_attachments = [
                a
                for a in attachments
                if not a.get("content_type", "").startswith("image/")
            ]
            for attachment in non_image_attachments:
                filename = attachment.get("filename", "unknown file")
                attachment_content = attachment.get("content")
                if attachment_content:
                    content_blocks.append(
                        {
                            "type": "text",
                            "text": f"[File: {filename}]\n{attachment_content}",
                        }
                    )
                else:
                    content_blocks.append(
                        {
                            "type": "text",
                            "text": f"[User attached: {filename}]",
                        }
                    )

        return content_blocks

    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert non-JSON-serializable objects to JSON-serializable format.

        Handles ToolMessage, Command, and other LangChain/LangGraph objects
        that may be nested in tool results.

        Also parses JSON strings back to objects to prevent type information
        loss when tool results return stringified JSON (e.g., from ToolMessage.content).

        Args:
            obj: The object to convert

        Returns:
            A JSON-serializable version of the object
        """
        if isinstance(obj, ToolMessage):
            # Extract content from ToolMessage
            return {
                "content": self._make_json_serializable(obj.content),
                "tool_call_id": getattr(obj, "tool_call_id", ""),
            }
        elif isinstance(obj, Command):
            # Command objects from subagent delegation
            return self._make_json_serializable(obj.update)
        elif isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, str):
            obj_size = len(obj)
            if obj_size > 100_000:  # 100KB limit
                return obj
            # Cheap pre-check: only attempt json.loads if string starts with a JSON opener
            if not obj or obj[0] not in ("{", "[", '"'):
                return obj
            try:
                import json

                parsed = json.loads(obj)
                return self._make_json_serializable(parsed)
            except (json.JSONDecodeError, TypeError):
                return obj
        elif isinstance(obj, (int, float, bool, type(None))):
            return obj
        else:
            # For other types, try string conversion
            return str(obj)

    _interrupt_nodes: dict[UUID, "InterruptNode"] = {}

    def register_interrupt_node(
        self, session_id: UUID, interrupt_node: "InterruptNode"
    ) -> None:
        """Register an InterruptNode for a session.

        Args:
            session_id: The session ID
            interrupt_node: The InterruptNode instance to register
        """
        self._interrupt_nodes[session_id] = interrupt_node

    def get_interrupt_node(self, session_id: UUID) -> "InterruptNode | None":
        """Get the InterruptNode for a session.

        Args:
            session_id: The session ID

        Returns:
            The InterruptNode instance if found, None otherwise
        """
        return self._interrupt_nodes.get(session_id)

    def unregister_interrupt_node(self, session_id: UUID) -> None:
        """Remove an InterruptNode for a session and clean up its state."""
        interrupt_node = self._interrupt_nodes.pop(session_id, None)
        if interrupt_node is not None:
            interrupt_node.pending_approvals.clear()
            interrupt_node.interrupt_state.clear()

    def register_approval_response(
        self, session_id: UUID, approval_id: str, approved: bool
    ) -> bool:
        """Register an approval response from the user.

        Args:
            session_id: The session ID
            approval_id: The approval ID being responded to
            approved: True if user approved, False if rejected

        Returns:
            True if the approval was registered successfully, False otherwise
        """
        interrupt_node = self.get_interrupt_node(session_id)
        if interrupt_node is None:
            logger.warning(f"No InterruptNode found for session {session_id}")
            return False

        interrupt_node.register_approval_response(approval_id, approved)
        logger.info(
            f"Registered approval response for session {session_id}, approval_id={approval_id}, approved={approved}"
        )
        return True

    async def resume_graph_after_approval(
        self,
        session_id: UUID,
        approval_id: str,
        websocket: WebSocket,
    ) -> bool:
        """Resume graph execution after user approval.

        Args:
            session_id: The session ID
            approval_id: The approval ID that was granted
            websocket: WebSocket connection for sending results

        Returns:
            True if resume was successful, False otherwise
        """
        interrupt_node = self.get_interrupt_node(session_id)
        if interrupt_node is None:
            logger.warning(f"No InterruptNode found for session {session_id}")
            return False

        # Check if there's interrupt state for this approval
        interrupt_state = interrupt_node.get_interrupt_state(approval_id)
        if interrupt_state is None:
            logger.warning(f"No interrupt state found for approval_id={approval_id}")
            return False

        # Execute the tool after approval
        try:
            result = await interrupt_node.execute_after_approval(approval_id)

            if result is None:
                logger.error(
                    f"Failed to execute tool after approval for approval_id={approval_id}"
                )
                return False

            # Send the result via WebSocket
            from app.models.schemas.ai import WSToolResultMessage

            tool_result = {
                "tool": interrupt_state.get("tool_name", "unknown"),
                "success": True,
                "result": result.content,
                "error": None,
            }

            if is_websocket_connected(websocket):
                try:
                    msg_data = WSToolResultMessage(
                        type="tool_result",
                        tool=tool_result["tool"],
                        result=jsonable_encoder(tool_result),
                    ).model_dump(mode="json")
                    logger.debug(
                        f"Sending tool_result after approval: tool={tool_result['tool']}, result_type={type(result.content).__name__}"
                    )
                    await websocket.send_json(msg_data)
                except Exception as e:
                    logger.warning(f"Failed to send tool_result after approval: {e}")
            else:
                logger.debug(
                    "WebSocket not connected, skipping tool_result send in resume"
                )

            logger.info(
                f"Successfully resumed and executed tool for approval_id={approval_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error resuming graph for approval_id={approval_id}: {e}",
                exc_info=True,
            )
            return False
