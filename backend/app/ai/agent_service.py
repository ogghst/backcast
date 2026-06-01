"""LangGraph Agent Service for conversation orchestration.

Uses LangGraph StateGraph for conversation flow with tool calling loop.
"""

import asyncio
import logging
import os
import time
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar, Literal, cast
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
                logger.debug(
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

from app.ai.config import AI_SEQUENTIAL_TOOL_CALLS, AgentConfig
from app.ai.event_types import (
    TOOL_NAME_TASK,
    TOOL_NAME_WRITE_TODOS,
    AgentEventType,
    ExecutionStatus,
)
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
from app.ai.graph_params import (
    GraphContext,
    GraphCreationParams,
    GraphExecutionParams,
    StreamState,
)
from app.ai.message_utils import extract_tool_output_content
from app.ai.message_utils import is_transient_stream_error as _is_transient_stream_error
from app.ai.subagent_compiler import DEFAULT_SYSTEM_PROMPT
from app.ai.supervisor_orchestrator import SupervisorOrchestrator
from app.ai.telemetry import (
    initialize_telemetry,
    trace_context,
)
from app.ai.token_estimator import (
    log_actual_usage,
    log_context_usage_estimate,
)
from app.ai.tools import ToolContext, create_project_tools, filter_tools_by_role
from app.ai.tools.interrupt_node import InterruptNode
from app.ai.tools.sequential_tool_node import patch_tool_node_for_sequential_execution
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
from app.models.domain.wbs_element import WBSElement
from app.models.schemas.ai import (
    AIChatResponse,
    AIConversationMessagePublic,
    PlanningStep,
    WSCompleteMessage,
)
from app.services.ai_config_service import AIConfigService

# Initialize telemetry on module load (will only instrument once)
_tracer_provider = initialize_telemetry(
    service_name="backcast-ai",
    enable_console=os.getenv("OTEL_CONSOLE_EXPORT", "false").lower() == "true",
)

# Defense-in-depth: ensure all ToolNode instances (including specialist
# subgraphs created via langchain_create_agent) execute tools sequentially
if AI_SEQUENTIAL_TOOL_CALLS:
    patch_tool_node_for_sequential_execution()

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

# Skipping ~40-60% of LangGraph events reduces CPU in the hot streaming path.
_HANDLED_EVENTS = frozenset(
    {
        "on_chain_start",
        "on_chain_end",
        "on_chat_model_start",
        "on_chat_model_stream",
        "on_chat_model_end",
        "on_tool_start",
        "on_tool_end",
        "on_tool_error",
        "on_end",
    }
)

# Caches (shared across all requests)
_llm_cache = LLMClientCache()

# LLM client config cache (avoids 3 DB queries per chat message)
_llm_config_cache: dict[UUID, tuple[float, dict[str, Any], str, str]] = {}
_LLM_CONFIG_TTL = 300  # 5 minutes


def invalidate_llm_config_cache() -> None:
    """Clear the LLM client config cache. Called when provider/model configs change."""
    _llm_config_cache.clear()
    _llm_cache.clear()
    logger.info("LLM config cache and client instance cache invalidated")


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

    from app.core.rbac_unified import get_unified_rbac_service, rbac_session

    async with rbac_session(session):
        roles = await get_unified_rbac_service().get_user_roles(user_id, "global", None)
        role = roles[0] if roles else "viewer"

    _user_role_cache[user_id] = (time.time() + _USER_ROLE_TTL, role)
    return role


class AgentService:
    """Service for LangGraph agent orchestration."""

    # Shared across all instances so interrupt nodes registered during
    # execution (which may create a separate AgentService) are visible
    # to the approval-handling instance.
    _interrupt_nodes: ClassVar[dict[UUID, "InterruptNode"]] = {}

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
        config = client_config.copy()
        reasoning_effort = config.pop("reasoning_effort", None)
        thinking_mode = config.pop("thinking_mode", None)

        # Build cache key
        base_url = config.get("base_url", "")
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
                    **config,
                    model=model_name,
                    temperature=temp,
                    max_tokens=tokens,
                    stream_chunk_timeout=300,
                    stream_usage=True,
                    **kwargs,
                )
            return ChatOpenAI(
                **config,
                model=model_name,
                temperature=temp,
                max_tokens=tokens,
                stream_chunk_timeout=300,
                stream_usage=True,
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
        params: GraphCreationParams,
    ) -> tuple[Any, InterruptNode | None]:
        """Create Deep Agent graph with Backcast context.

        Uses DeepAgentOrchestrator to wrap create_deep_agent() from the
        LangChain Deep Agents SDK. Preserves security model and temporal context.

        Args:
            params: Grouped parameters for graph creation.

        Returns:
            Tuple of (compiled_graph, interrupt_node) where interrupt_node may be None

        Note:
            This is an alternative to create_graph() that uses the Deep Agents SDK
            for planning and subagent delegation. Falls back to create_graph() if
            Deep Agents SDK is not available or encounters errors.
        """
        # Destructure for local use
        llm = params.llm
        tool_context = params.tool_context
        assistant_config = params.assistant_config
        websocket = params.websocket
        session_id = params.session_id
        available_tools = params.available_tools
        event_bus = params.event_bus
        user_role = params.user_role

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

            supervisor_orchestrator = SupervisorOrchestrator(
                model=llm,
                context=tool_context,
                system_prompt=system_prompt,
                main_assistant_config=assistant_config,
            )
            graph = await supervisor_orchestrator.create_supervisor_graph(agent_config)

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

        if assistant_config.model_id is None:
            raise ValueError(
                f"Agent '{assistant_config.name}' has no model_id configured"
            )
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

    # ------------------------------------------------------------------
    # Graph execution: preparation, streaming, persistence, finalization
    # ------------------------------------------------------------------

    async def _prepare_graph_execution(
        self,
        params: GraphExecutionParams,
    ) -> tuple[GraphContext, dict[str, Any] | None]:
        """Build history, create LLM, compile graph, and return prepared context.

        Args:
            params: Grouped execution parameters.

        Returns:
            Tuple of (GraphContext, existing_briefing dict or None).
        """
        assistant_config = params.assistant_config
        session_id = params.session_id
        user_id = params.user_id
        event_bus = params.event_bus
        project_id = params.project_id
        branch_id = params.branch_id
        as_of = params.as_of
        branch_name = params.branch_name
        branch_mode = params.branch_mode
        execution_mode = params.execution_mode
        context = params.context

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

        if assistant_config.model_id is None:
            raise ValueError(
                f"Agent '{assistant_config.name}' has no model_id configured"
            )
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
            GraphCreationParams(
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

        ctx = GraphContext(
            history=history,
            llm=llm,
            graph=graph,
            tool_context=tool_context,
            available_tools=available_tools,
            model_name=model_name,
            recursion_limit=recursion_limit,
            user_role=user_role,
            interrupt_node=interrupt_node,
            session_id=session_id,
            event_bus=event_bus,
            project_id=project_id,
            branch_id=branch_id,
            user_id=user_id,
            as_of=as_of,
            branch_name=branch_name,
            branch_mode=branch_mode,
            execution_mode=execution_mode,
            assistant_config=assistant_config,
        )

        existing_briefing = await self.config_service.get_session_briefing(session_id)
        if existing_briefing:
            logger.info(
                "[BRIEFING_PERSIST] Restored briefing from DB with %d sections (streaming)",
                len(existing_briefing.get("sections", [])),
            )

        return ctx, existing_briefing

    # -- Individual event handlers --

    def _handle_chain_start(self, state: StreamState, event: dict[str, Any]) -> None:
        """Handle on_chain_start events for specialist agent transitions."""
        chain_name = event.get("name", "")

        # Track planner node activation to suppress its token streaming.
        # The planner's LLM call produces JSON that must not leak into chat.
        if chain_name == "planner":
            state.planner_active = True
            return

        if chain_name not in state.specialist_names:
            return
        # LangGraph emits on_chain_start twice per specialist
        # (outer node + inner graph) -- deduplicate via last_entered_agent.
        if state.last_entered_agent == chain_name:
            return  # duplicate inner-graph event — skip to prevent double balloon
        state.flush_tokens(state.current_invocation_id or state.main_invocation_id)
        state.current_subagent_name = chain_name
        state.current_invocation_id = str(uuid.uuid4())
        state.last_entered_agent = chain_name
        state.publish(
            AgentEventType.AGENT_TRANSITION,
            {
                "type": AgentEventType.AGENT_TRANSITION,
                "agent_name": chain_name,
                "direction": "enter",
                "invocation_id": state.current_invocation_id,
            },
        )

    def _handle_chain_end(self, state: StreamState, event: dict[str, Any]) -> None:
        """Handle on_chain_end events for specialist, supervisor, and other nodes."""
        chain_name = event.get("name", "")
        data = event.get("data", {})

        # Specialist agent chain end
        if chain_name in state.specialist_names:
            chain_output = data.get("output")

            # Extract briefing data from either dict output or Command.update.
            # Specialist nodes return Command objects, so isinstance(dict) is
            # False -- we must check Command.update as a fallback.
            output_dict: dict[str, Any] | None = None
            is_outer_node = False
            if isinstance(chain_output, dict):
                output_dict = chain_output
            elif hasattr(chain_output, "update") and isinstance(
                getattr(chain_output, "update", None), dict
            ):
                output_dict = chain_output.update
                is_outer_node = True

            if output_dict and "briefing_data" in output_dict:
                # Outer specialist_node (wrapper) completed.  Publish
                # BRIEFING_UPDATE and AGENT_TRANSITION exit with the
                # invocation_id that was active when the specialist entered.
                # Use the invocation_id from the output_dict's plan_data
                # when available, falling back to current tracking state.
                exit_invocation_id = state.current_invocation_id
                state.publish_briefing_update(output_dict, chain_name)
                state.publish(
                    AgentEventType.AGENT_TRANSITION,
                    {
                        "type": AgentEventType.AGENT_TRANSITION,
                        "agent_name": chain_name,
                        "direction": "exit",
                        "invocation_id": exit_invocation_id,
                    },
                )
            elif chain_name == state.current_subagent_name:
                state.flush_tokens(state.current_invocation_id)

            # Reset specialist tracking.  The inner specialist graph chain_end
            # fires first (dict output), followed by the outer specialist_node
            # wrapper chain_end (Command output).  We must preserve
            # current_invocation_id across the inner chain_end so the outer
            # chain_end can emit a correct AGENT_TRANSITION exit with the
            # original invocation_id.  Only clear invocation_id on the outer
            # chain_end; current_subagent_name is always cleared to prevent
            # token misattribution in subsequent stream events.
            state.current_subagent_name = None
            if is_outer_node:
                state.current_invocation_id = None
                state.last_entered_agent = None
            return

        # Supervisor node completion
        if chain_name == "supervisor":
            chain_output = data.get("output", {})
            state.publish_briefing_update(
                chain_output, "supervisor", log_label="SUPERVISOR_END"
            )
            return

        # Other non-specialist chain ends (e.g. initialize_briefing, planner)
        chain_output = data.get("output", {})
        state.publish_briefing_update(
            chain_output, "supervisor", log_label="CHAIN_END_NON_SPECIALIST"
        )

        # Clear planner flag after its chain completes
        if chain_name == "planner":
            state.planner_active = False

    def _handle_chat_model_start(
        self, state: StreamState, event: dict[str, Any]
    ) -> None:
        """Handle on_chat_model_start -- track LLM call count and timing."""
        data = event.get("data", {})
        state.llm_call_count += 1
        state.llm_call_start = time.time()
        inv_data = data.get("invocation_info", {})
        if not inv_data:
            inv_data = event.get("metadata", {})
        fn_name = ""
        if isinstance(inv_data, dict):
            fn_name = inv_data.get("fn_name", "")
        logger.info(
            "[LLM_CALL_START] #%d | model=%s | fn=%s",
            state.llm_call_count,
            state.model_name or "unknown",
            fn_name,
        )

    def _handle_chat_model_stream(
        self, state: StreamState, event: dict[str, Any]
    ) -> None:
        """Handle on_chat_model_stream -- accumulate token output.

        Tokens from the planner node are suppressed to prevent plan JSON
        from leaking into the chat stream. The planner emits a dedicated
        PLAN_UPDATE event instead.
        """
        if state.planner_active:
            return
        data = event.get("data", {})
        chunk = data.get("chunk")
        # Token streaming: accumulate per-invocation, flush in batches.
        if isinstance(chunk, AIMessageChunk):
            # Capture reasoning from chunks -- the final AIMessage may
            # not preserve additional_kwargs.
            rc = chunk.additional_kwargs.get("reasoning_content")
            if rc and isinstance(rc, str):
                if state.reasoning_content_value is None:
                    state.reasoning_content_value = rc
                else:
                    state.reasoning_content_value += rc
        if chunk:
            content = ""
            if hasattr(chunk, "text"):
                content = chunk.text
            elif hasattr(chunk, "content"):
                content = str(chunk.content)

            if content:
                if state.current_subagent_name is None:
                    if state.main_invocation_id not in state.main_agent_segments:
                        state.main_agent_segments[state.main_invocation_id] = []
                    state.main_agent_segments[state.main_invocation_id].append(content)

                state.total_output_chars += len(content)

                # Accumulate tokens per invocation for batched publish
                invocation_id_to_use = (
                    state.current_invocation_id
                    if state.current_subagent_name
                    else state.main_invocation_id
                )
                if invocation_id_to_use is not None:
                    if invocation_id_to_use not in state.token_buffer:
                        state.token_buffer[invocation_id_to_use] = []
                    state.token_buffer[invocation_id_to_use].append(content)

    def _handle_chat_model_end(self, state: StreamState, event: dict[str, Any]) -> None:
        """Handle on_chat_model_end -- capture actual token usage and timing."""
        data = event.get("data", {})
        if state.llm_call_start is not None:
            llm_duration_ms = (time.time() - state.llm_call_start) * 1000
            logger.info(
                "[LLM_CALL_END] #%d | duration_ms=%.0f",
                state.llm_call_count,
                llm_duration_ms,
            )
            state.llm_call_start = None
        state.token_accumulator.accumulate_from_event(data)

    def _handle_tool_start(self, state: StreamState, event: dict[str, Any]) -> None:
        """Handle on_tool_start -- discard intermediate reasoning, track tool invocation."""
        data = event.get("data", {})
        # Discard intermediate model reasoning before tool execution.
        # The user only sees tool call notifications and the final response,
        # not the model's thinking between tool calls.
        state.token_buffer.pop(state.main_invocation_id, [])
        state.main_agent_segments.pop(state.main_invocation_id, None)
        if state.current_invocation_id and state.current_subagent_name:
            state.flush_tokens(state.current_invocation_id)

        tool_name = event.get("name", "")
        tool_input = data.get("input", {})
        state.tool_calls_count += 1
        state.current_step += 1
        state.tool_call_start = time.time()
        logger.info(
            "[TOOL_START] #%d tool=%s | step=%d/%s",
            state.tool_calls_count,
            tool_name,
            state.current_step,
            state.estimated_total_steps or "?",
        )

        if tool_name == TOOL_NAME_TASK:
            state.current_subagent_name = (
                tool_input.get("subagent_type")
                if isinstance(tool_input, dict)
                else None
            )
            state.current_invocation_id = str(uuid.uuid4())
            state.task_initiating_main_invocation_id = state.main_invocation_id

        # Planning event
        if tool_name == TOOL_NAME_WRITE_TODOS:
            plan = tool_input.get("plan") if isinstance(tool_input, dict) else None
            steps = None
            if isinstance(tool_input, dict):
                raw_steps = tool_input.get("steps")
                if isinstance(raw_steps, list):
                    steps = [PlanningStep(text=str(s), done=False) for s in raw_steps]
                    state.estimated_total_steps = len(steps)
            state.publish(
                AgentEventType.PLANNING,
                {
                    "type": AgentEventType.PLANNING,
                    "plan": plan,
                    "steps": (
                        [{"text": s.text, "done": s.done} for s in steps]
                        if steps
                        else None
                    ),
                    "step_number": state.current_step,
                    "total_steps": state.estimated_total_steps,
                    "invocation_id": state.main_invocation_id,
                },
            )

        # Subagent delegation event
        elif tool_name == TOOL_NAME_TASK:
            subagent_type = (
                tool_input.get("subagent_type")
                if isinstance(tool_input, dict)
                else None
            )
            description = (
                tool_input.get("description") if isinstance(tool_input, dict) else None
            )
            if subagent_type:
                state.publish(
                    AgentEventType.SUBAGENT,
                    {
                        "type": AgentEventType.SUBAGENT,
                        "subagent": subagent_type,
                        "message": description,
                        "step_number": state.current_step,
                        "total_steps": state.estimated_total_steps,
                        "invocation_id": state.current_invocation_id,
                    },
                )

        # Standard tool_call event
        state.publish(
            AgentEventType.TOOL_CALL,
            {
                "type": AgentEventType.TOOL_CALL,
                "tool": tool_name,
                "args": tool_input,
                "step_number": state.current_step,
                "total_steps": state.estimated_total_steps,
                "invocation_id": (
                    state.current_invocation_id
                    if state.current_subagent_name
                    else state.main_invocation_id
                ),
            },
        )

    def _handle_tool_end(self, state: StreamState, event: dict[str, Any]) -> None:
        """Handle on_tool_end -- process tool results and subagent completions."""
        data = event.get("data", {})
        tool_name = event.get("name", "")

        if state.tool_call_start is not None:
            tool_duration_ms = (time.time() - state.tool_call_start) * 1000
            logger.info(
                "[TOOL_END] tool=%s | duration_ms=%.0f",
                tool_name,
                tool_duration_ms,
            )
            state.tool_call_start = None

        # Subagent result handling
        if tool_name == TOOL_NAME_TASK and state.current_invocation_id is not None:
            # Flush subagent tokens before processing result
            state.flush_tokens(state.current_invocation_id)

            tool_output = data.get("output", "")
            subagent_content = extract_tool_output_content(tool_output)

            if subagent_content:
                subagent_type = state.current_subagent_name or "subagent"
                if subagent_type not in self._subagent_invocation_counts:
                    self._subagent_invocation_counts[subagent_type] = 0
                self._subagent_invocation_counts[subagent_type] += 1
                invocation_number = self._subagent_invocation_counts[subagent_type]

                target_invocation_id = (
                    state.task_initiating_main_invocation_id or state.main_invocation_id
                )
                state.subagent_messages.setdefault(target_invocation_id, []).append(
                    {
                        "role": "assistant",
                        "content": subagent_content,
                        "message_metadata": (
                            {
                                "subagent_name": subagent_type,
                                "invocation_number": invocation_number,
                            }
                            if state.current_subagent_name
                            else None
                        ),
                    }
                )

                state.publish(
                    AgentEventType.SUBAGENT_RESULT,
                    {
                        "type": AgentEventType.SUBAGENT_RESULT,
                        "subagent_name": state.current_subagent_name or "subagent",
                        "content": subagent_content,
                        "invocation_id": state.current_invocation_id,
                    },
                )

            # Subagent completion
            state.publish(
                AgentEventType.AGENT_COMPLETE,
                {
                    "type": AgentEventType.AGENT_COMPLETE,
                    "agent_type": "subagent",
                    "invocation_id": state.current_invocation_id,
                    "agent_name": state.current_subagent_name,
                },
            )

            # Content reset after subagent
            state.publish(
                AgentEventType.CONTENT_RESET,
                {
                    "type": AgentEventType.CONTENT_RESET,
                    "reason": "subagent_completed",
                },
            )

            state.current_subagent_name = None
            state.current_invocation_id = None
            state.task_initiating_main_invocation_id = None

        # Generate new main invocation_id after task tool completion only
        # (subagent delegation). For other tools, the same agent continues.
        if tool_name == TOOL_NAME_TASK:
            state.main_invocation_id = str(uuid.uuid4())

        tool_output = data.get("output", "")
        result_content = tool_output
        if isinstance(tool_output, ToolMessage):
            result_content = tool_output.content
        elif isinstance(tool_output, dict) and "content" in tool_output:
            result_content = tool_output["content"]
        elif isinstance(tool_output, Command):
            result_content = {"command": tool_output.update}

        result_content = self._make_json_serializable(result_content)

        tool_result_dict: dict[str, Any] = {
            "tool": tool_name,
            "success": True,
            "result": result_content,
            "error": None,
        }
        if state.current_subagent_name is None:
            state.all_tool_results.append(tool_result_dict)

        state.publish(
            AgentEventType.TOOL_RESULT,
            {
                "type": AgentEventType.TOOL_RESULT,
                "tool": tool_name,
                "result": jsonable_encoder(tool_result_dict),
                "invocation_id": (
                    state.current_invocation_id
                    if state.current_subagent_name
                    else state.main_invocation_id
                ),
            },
        )

    def _handle_tool_error(self, state: StreamState, event: dict[str, Any]) -> None:
        """Handle on_tool_error -- record tool failure."""
        data = event.get("data", {})
        tool_name = event.get("name", "")
        error = data.get("error")

        if state.current_subagent_name is None:
            error_result_dict: dict[str, Any] = {
                "tool": tool_name,
                "success": False,
                "result": None,
                "error": (str(error) if error else "Unknown error"),
            }
            state.all_tool_results.append(error_result_dict)

            state.publish(
                AgentEventType.TOOL_RESULT,
                {
                    "type": AgentEventType.TOOL_RESULT,
                    "tool": tool_name,
                    "result": jsonable_encoder(error_result_dict),
                    "invocation_id": (
                        state.current_invocation_id
                        if state.current_subagent_name
                        else state.main_invocation_id
                    ),
                },
            )

    def _handle_graph_end(self, state: StreamState, event: dict[str, Any]) -> None:
        """Handle on_end -- extract final tool calls from graph output."""
        data = event.get("data", {})
        output = data.get("output", {})
        messages = output.get("messages", [])

        for msg in messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    state.all_tool_calls.append(
                        {
                            "id": tc.get("id", ""),
                            "name": tc.get("name", ""),
                            "args": tc.get("args", {}),
                        }
                    )

        logger.info(
            f"Graph execution completed for execution "
            f"event_bus {state.event_bus.execution_id}"
        )

    # -- Main stream processing --

    async def _process_stream_events(
        self,
        ctx: GraphContext,
        state: StreamState,
        history: list[Any],
        existing_briefing: dict[str, Any] | None,
    ) -> None:
        """Run the graph astream_events loop with retry logic.

        Args:
            ctx: Prepared graph context.
            state: Mutable stream state tracking variables.
            history: Message history including system prompt.
            existing_briefing: Previously persisted briefing or None.
        """
        state.publish(AgentEventType.THINKING, {"type": AgentEventType.THINKING})

        max_retries = 2
        retry_delay = 2.0
        events_processed = 0

        for _retry_attempt in range(max_retries + 1):
            try:
                from app.db.session import log_pool_status

                log_pool_status(
                    f"graph.astream_events start | session={ctx.session_id}"
                )

                async for event in ctx.graph.astream_events(
                    {
                        "messages": history,
                        "tool_call_count": 0,
                        "max_tool_iterations": ctx.recursion_limit,
                        "next": "agent",
                        "briefing_data": existing_briefing,
                    },
                    config={
                        # Supervisor orchestrator uses nested subgraphs — each
                        # tool call cycle costs ~5 graph steps internally.  The
                        # recursion_limit must be higher than max_tool_iterations
                        # to avoid premature GraphRecursionError.
                        "recursion_limit": ctx.recursion_limit * 5,
                        "configurable": {"thread_id": str(ctx.session_id)},
                    },
                    version="v1",
                    context=BackcastRuntimeContext(
                        user_id=str(ctx.user_id),
                        user_role=ctx.user_role,
                        project_id=str(ctx.project_id) if ctx.project_id else None,
                        branch_id=str(ctx.branch_id) if ctx.branch_id else None,
                        execution_mode=ctx.execution_mode.value,
                    ),
                ):
                    events_processed += 1
                    event_type = event.get("event", "")
                    if event_type not in _HANDLED_EVENTS:
                        continue

                    # Dispatch to handler methods
                    if event_type == "on_chain_start":
                        self._handle_chain_start(state, event)
                    elif event_type == "on_chain_end":
                        self._handle_chain_end(state, event)
                    elif event_type == "on_chat_model_start":
                        self._handle_chat_model_start(state, event)
                    elif event_type == "on_chat_model_stream":
                        self._handle_chat_model_stream(state, event)
                    elif event_type == "on_chat_model_end":
                        self._handle_chat_model_end(state, event)
                    elif event_type == "on_tool_start":
                        self._handle_tool_start(state, event)
                    elif event_type == "on_tool_end":
                        self._handle_tool_end(state, event)
                    elif event_type == "on_tool_error":
                        self._handle_tool_error(state, event)
                    elif event_type == "on_end":
                        self._handle_graph_end(state, event)

                # -- Post-stream: persist briefing --
                # Flush all remaining accumulated tokens after stream ends
                for inv_id in list(state.token_buffer.keys()):
                    state.flush_tokens(inv_id)

                state.briefing_persisted = await self._persist_briefing_from_checkpoint(
                    ctx.session_id, log_label="BRIEFING_PERSIST_STREAMING"
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
                state.token_buffer.clear()

    # -- Persistence --

    async def _persist_session_messages(
        self,
        state: StreamState,
    ) -> None:
        """Save assistant and subagent messages to session history.

        Args:
            state: Stream state containing message segments and metadata.
        """
        try:
            invocation_ids_in_order = list(state.main_agent_segments.keys())
            total_main_segments = len(invocation_ids_in_order)
            logger.info(
                "[MSG_SAVE] Saving assistant messages for session %s: "
                "%d segments, invocation_ids=%s",
                state.session_id,
                total_main_segments,
                invocation_ids_in_order,
            )

            for idx, inv_id in enumerate(invocation_ids_in_order):
                segment_content = "".join(state.main_agent_segments[inv_id])
                metadata: dict[str, Any] = {
                    "invocation_id": inv_id,
                    "segment_index": idx,
                    "total_segments": total_main_segments,
                }
                if state.reasoning_content_value:
                    metadata["reasoning_content"] = state.reasoning_content_value

                segment_tool_calls = (
                    state.all_tool_calls if idx == 0 and state.all_tool_calls else None
                )
                segment_tool_results = (
                    state.all_tool_results
                    if idx == 0 and state.all_tool_results
                    else None
                )

                await self.config_service.add_message(
                    session_id=state.session_id,
                    role="assistant",
                    content=segment_content,
                    tool_calls=segment_tool_calls,
                    tool_results=segment_tool_results,
                    message_metadata=metadata,
                )
                await self.session.commit()

                if inv_id in state.subagent_messages:
                    for subagent_msg_data in state.subagent_messages[inv_id]:
                        await self.config_service.add_message(
                            session_id=state.session_id,
                            **subagent_msg_data,
                        )
                        await self.session.commit()

        except Exception as msg_error:
            logger.error(
                f"Error saving messages in _run_agent_graph: {msg_error}",
                exc_info=True,
            )
            try:
                await self.session.rollback()
            except Exception:
                pass

        # Persist error message to session history if graph execution failed
        if state.graph_error is not None:
            try:
                await self.config_service.add_message(
                    session_id=state.session_id,
                    role="assistant",
                    content=(
                        f"I encountered an error while processing your request: "
                        f"{state.graph_error}. The work completed before the error has "
                        f"been saved."
                    ),
                    message_metadata={
                        "error": True,
                        "error_type": type(state.graph_error).__name__,
                    },
                )
                await self.session.commit()
            except Exception as persist_error:
                logger.error(f"Failed to persist error message: {persist_error}")

    # -- Finalization --

    def _finalize_execution(
        self,
        state: StreamState,
    ) -> AgentExecutionMetrics:
        """Publish completion events and return execution metrics.

        Args:
            state: Final stream state after graph execution completed.

        Returns:
            AgentExecutionMetrics with aggregated token usage and tool call count.
        """
        # Publish main agent completion
        state.publish(
            AgentEventType.AGENT_COMPLETE,
            {
                "type": AgentEventType.AGENT_COMPLETE,
                "agent_type": "main",
                "invocation_id": state.main_invocation_id,
                "agent_name": "Assistant",
            },
        )

        # Publish execution status so frontend clears activeExecutionIdRef
        state.publish(
            AgentEventType.EXECUTION_STATUS,
            {
                "type": AgentEventType.EXECUTION_STATUS,
                "execution_id": state.event_bus.execution_id,
                "status": ExecutionStatus.COMPLETED,
                "session_id": str(state.session_id),
            },
        )

        # Publish final complete event
        usage_dict = state.token_accumulator.to_dict()
        state.publish(
            AgentEventType.COMPLETE,
            WSCompleteMessage(
                type="complete",
                session_id=state.session_id,
                message_id=None,
                token_usage=usage_dict,
            ).model_dump(mode="json"),
        )

        # Log summary
        stream_duration_ms = (time.time() - state.stream_start_time) * 1000
        logger.info(
            f"[RUN_AGENT_GRAPH_COMPLETE] _run_agent_graph | "
            f"duration_ms={stream_duration_ms:.2f} | "
            f"execution_id={state.event_bus.execution_id} | "
            f"session_id={state.session_id} | "
            f"total_output_chars={state.total_output_chars} | "
            f"prompt_tokens={usage_dict['prompt_tokens']} | "
            f"completion_tokens={usage_dict['completion_tokens']} | "
            f"total_tokens={usage_dict['total_tokens']} | "
            f"tool_calls_count={state.tool_calls_count}"
        )

        # Log actual token usage from API
        log_actual_usage(
            accumulator=state.token_accumulator,
            model_name=state.model_name or "unknown",
            session_id=str(state.session_id),
            execution_id=state.event_bus.execution_id,
        )

        return AgentExecutionMetrics(
            total_tokens=usage_dict["total_tokens"],
            tool_calls_count=state.tool_calls_count,
        )

    # -- Orchestrator --

    async def _run_agent_graph(
        self,
        params: GraphExecutionParams,
    ) -> AgentExecutionMetrics:
        """Run the agent graph and publish streaming events to an AgentEventBus.

        Decoupled from WebSocket: events are published to the bus so any consumer
        (REST SSE, WebSocket reconnection) can subscribe by execution_id.
        Communicates results entirely through event_bus.

        Args:
            params: Grouped parameters for graph execution.

        Returns:
            AgentExecutionMetrics with aggregated token usage and tool call count.
        """
        # Step 1: Prepare execution context
        ctx, existing_briefing = await self._prepare_graph_execution(params)

        # Step 2: Initialize mutable stream state
        # Non-specialist node names in the parent graph.
        _NON_SPECIALIST_NODES = frozenset(
            {
                "__start__",
                "__end__",
                "initialize_briefing",
                "planner",
                "supervisor",
                "tools",
            }
        )
        state = StreamState(
            event_bus=ctx.event_bus,
            session_id=ctx.session_id,
            model_name=ctx.model_name,
            main_invocation_id=str(uuid.uuid4()),
            specialist_names=frozenset(
                n for n in ctx.graph.nodes if n not in _NON_SPECIALIST_NODES
            ),
        )

        # Step 3: Start periodic token flush background task
        async def _periodic_flush() -> None:
            while True:
                await asyncio.sleep(settings.AI_TOKEN_BUFFER_INTERVAL_MS / 1000)
                for inv_id in list(state.token_buffer.keys()):
                    state.flush_tokens(inv_id)

        _flush_task = asyncio.create_task(_periodic_flush())

        try:
            # Step 4: Process stream events (includes retry logic)
            await self._process_stream_events(
                ctx, state, ctx.history, existing_briefing
            )
        except Exception as e:
            state.graph_error = e
            logger.error(f"Error in _run_agent_graph: {e}", exc_info=True)
            state.event_bus.publish(
                AgentEvent(
                    event_type=AgentEventType.ERROR,
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
            for inv_id in list(state.token_buffer.keys()):
                state.flush_tokens(inv_id)
            clear_request_context()
            self.unregister_interrupt_node(ctx.session_id)
            # Commit tool session - critical for cost element persistence
            try:
                await ToolSessionManager.commit()
            except Exception as commit_err:
                logger.error(
                    f"[TOOL_SESSION] Failed to commit tool session: {commit_err}",
                    exc_info=True,
                )
                raise

            # Persist briefing on error if not already done
            if not state.briefing_persisted:
                await self._persist_briefing_from_checkpoint(
                    ctx.session_id, log_label="BRIEFING_PERSIST_ERROR_PATH"
                )

        # Step 5: Persist messages to session history
        await self._persist_session_messages(state)

        # Step 6: Finalize -- publish completion events and return metrics
        return self._finalize_execution(state)

    @staticmethod
    async def _clear_active_execution(db: AsyncSession, session_id: UUID) -> None:
        """Clear active_execution_id on the conversation session (best-effort)."""
        try:
            result = await db.execute(
                select(AIConversationSession).where(
                    AIConversationSession.id == str(session_id)
                )
            )
            row = result.scalar_one_or_none()
            if row is not None:
                row.active_execution_id = None
                await db.commit()
        except Exception:
            pass

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
            from app.db.session import log_pool_status

            log_pool_status(f"start_execution entry | execution_id={execution_id}")

            # Pre-fetch the session row so it is accessible in except/finally blocks
            session_stmt = select(AIConversationSession).where(
                AIConversationSession.id == str(session_id)
            )
            session_result = await db.execute(session_stmt)
            db_session = session_result.scalar_one_or_none()

            try:
                metrics: AgentExecutionMetrics | None = None

                # Create execution tracking row — use execution_id as the PK
                # so the DB row ID matches the event bus key (required for
                # WebSocket re-subscribe: the client sends the DB execution.id
                # and the subscribe handler looks up the bus by the same key).
                execution = AIAgentExecution(
                    id=UUID(execution_id),
                    session_id=str(session_id),
                    status=ExecutionStatus.RUNNING,
                    execution_mode=execution_mode.value,
                )
                db.add(execution)
                await db.commit()
                await db.refresh(execution)

                # Set active_execution_id on session
                if db_session is not None:
                    db_session.active_execution_id = str(execution.id)
                    await db.commit()

                # Capture context before releasing the connection
                session_context = db_session.context if db_session else None

                # Release the DB connection back to the pool before entering
                # the graph. The session stays usable — it will re-checkout a
                # connection on the next query. This prevents holding a
                # connection for the entire graph execution (minutes).
                await db.close()

                # Create agent service with this DB session
                exec_service = AgentService(db)

                # Run the agent graph, publishing events to the bus
                metrics = await exec_service._run_agent_graph(
                    GraphExecutionParams(
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
                        context=session_context,
                    )
                )

                # Re-query since db.close() detached the object
                exec_stmt = select(AIAgentExecution).where(
                    AIAgentExecution.id == str(execution.id)
                )
                exec_result = await db.execute(exec_stmt)
                execution = exec_result.scalar_one()
                execution.status = ExecutionStatus.COMPLETED
                execution.completed_at = datetime.now(UTC)  # type: ignore[assignment]
                execution.total_tokens = metrics.total_tokens
                execution.tool_calls_count = metrics.tool_calls_count
                await db.commit()

                await self._clear_active_execution(db, session_id)

            except Exception as e:
                logger.error(
                    f"Error in start_execution {execution_id}: {e}", exc_info=True
                )
                # Update execution tracking row with error and partial metrics.
                # Always re-query since db.close() may have detached the object.
                try:
                    stmt = select(AIAgentExecution).where(
                        AIAgentExecution.id == str(execution.id)
                    )
                    result = await db.execute(stmt)
                    fresh_execution = result.scalar_one_or_none()
                    if fresh_execution is not None:
                        fresh_execution.status = ExecutionStatus.ERROR
                        fresh_execution.error_message = str(e)[:2000]
                        fresh_execution.completed_at = datetime.now(UTC)  # type: ignore[assignment]
                        if metrics is not None:
                            fresh_execution.total_tokens = metrics.total_tokens
                            fresh_execution.tool_calls_count = metrics.tool_calls_count
                        await db.commit()
                except Exception:
                    await db.rollback()
                    logger.error(
                        "Failed to update execution row on error path",
                        exc_info=True,
                    )

                await self._clear_active_execution(db, session_id)

                # Publish execution status so frontend clears activeExecutionIdRef
                event_bus.publish(
                    AgentEvent(
                        event_type=AgentEventType.EXECUTION_STATUS,
                        data={
                            "type": AgentEventType.EXECUTION_STATUS,
                            "execution_id": execution_id,
                            "status": ExecutionStatus.ERROR,
                            "session_id": str(session_id),
                        },
                        timestamp=datetime.now(UTC),
                    )
                )

                # Publish error event
                event_bus.publish(
                    AgentEvent(
                        event_type=AgentEventType.ERROR,
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
                    select(WBSElement.name)
                    .where(WBSElement.wbs_element_id == entity_uuid)
                    .where(sa_func.upper(WBSElement.valid_time).is_(None))
                    .where(WBSElement.deleted_at.is_(None))
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
                from app.models.domain.cost_element_type import CostElementType as CET

                stmt = (
                    select(CET.name)
                    .join(
                        CostElement,
                        CostElement.cost_element_type_id == CET.cost_element_type_id,
                    )
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
