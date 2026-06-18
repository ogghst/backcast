"""LangGraph Agent Service for conversation orchestration.

Uses LangGraph StateGraph for conversation flow with tool calling loop.
"""

import asyncio
import logging
import os
import time
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar, Literal, cast
from uuid import UUID

from fastapi import WebSocket
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

    # Patch ChatDeepSeek.bind_tools() to strip tool_choice parameter.
    # DeepSeek V4 Flash with thinking mode rejects tool_choice.
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
        """Strip tool_choice for DeepSeek models — thinking mode rejects it."""
        if tool_choice is not None:
            logger.info(
                "Stripping tool_choice=%s for DeepSeek model (thinking mode rejects this parameter)",
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
from app.ai.exceptions import ExecutionStoppedError
from app.ai.execution.agent_event import AgentEvent
from app.ai.execution.agent_event_bus import AgentEventBus
from app.ai.execution.agent_metrics import AgentExecutionMetrics
from app.ai.execution.lifecycle import execution_lifecycle
from app.ai.execution.llm_retry import iter_with_pausable_deadline
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
from app.ai.message_utils import extract_tool_output_content, strip_think_tags
from app.ai.message_utils import is_transient_stream_error as _is_transient_stream_error
from app.ai.subagent_compiler import DEFAULT_SYSTEM_PROMPT
from app.ai.subagents.db_loader import load_specialists_from_db
from app.ai.supervisor_orchestrator import SupervisorOrchestrator
from app.ai.telemetry import initialize_telemetry
from app.ai.token_estimator import (
    log_actual_usage,
    log_context_usage_estimate,
)
from app.ai.tools import ToolContext, create_project_tools
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
from app.models.domain.work_package import WorkPackage
from app.models.schemas.ai import (
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


def _message_text(message: BaseMessage) -> str:
    """Render a message to a single text blob for size measurement.

    Joins multimodal content blocks (vision/list content) into a string,
    and appends any tool-call argument text (``AIMessage.tool_calls``) and
    tool-call ID / name metadata, since all of that is sent to the LLM and
    counts toward the request payload size. Purely for diagnostics -- not
    an exact serialization, but close enough to attribute bloat by role.
    """
    content = message.content
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                # Common block shapes: {"type": "text", "text": ...},
                # image blocks ({"type":"image_url",...}) carry little text.
                t = block.get("text")
                if isinstance(t, str):
                    parts.append(t)
        text = "".join(parts)
    else:
        text = str(content)

    # AIMessage.tool_calls (args) are part of what's sent -- include them.
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        for tc in tool_calls:
            args = tc.get("args") if isinstance(tc, dict) else None
            if args:
                text += str(args)

    return text


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

# Non-specialist node names in the parent graph.  Specialist names are
# everything NOT in this set — used to detect subagent transitions.
_NON_SPECIALIST_NODES = frozenset(
    {
        "__start__",
        "__end__",
        "agent",
        "initialize_briefing",
        "planner",
        "supervisor",
        "tools",
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


def _make_stop_predicate(
    stop_event: asyncio.Event | None,
) -> Callable[[], bool] | None:
    """Build a should_stop predicate bound to *stop_event*, or None.

    Capturing the event in a local lets mypy narrow the type inside the
    returned closure (a bare ``lambda: ctx.stop_event.is_set()`` would
    not narrow because the closure captures the ``ctx`` attribute access
    rather than a value).
    """
    if stop_event is None:
        return None
    return lambda: bool(stop_event.is_set())


def _extract_resume_state_from_checkpoint(
    checkpoint_state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Extract resume state from a LangGraph checkpoint's channel_values.

    Returns a dict with keys ``briefing_data``, ``plan_data``,
    ``completed_steps`` and ``completed_specialists`` (the latter two
    coerced to ``set``, defaulting to empty).  Returns ``None`` when
    ``checkpoint_state`` is falsy or has no ``briefing_data`` in
    ``channel_values`` -- the signal that no progress was checkpointed.
    """
    if not checkpoint_state:
        return None
    channel_values = checkpoint_state.get("channel_values", {}) or {}
    briefing_data = channel_values.get("briefing_data")
    if not briefing_data:
        return None
    completed_steps = channel_values.get("completed_steps") or []
    completed_specialists = channel_values.get("completed_specialists") or []
    return {
        "briefing_data": briefing_data,
        "plan_data": channel_values.get("plan_data"),
        "completed_steps": set(completed_steps),
        "completed_specialists": set(completed_specialists),
    }


class AgentService:
    """Service for LangGraph agent orchestration."""

    # Shared across all instances so interrupt nodes registered during
    # execution (which may create a separate AgentService) are visible
    # to the approval-handling instance.
    _interrupt_nodes: ClassVar[dict[UUID, "InterruptNode"]] = {}

    # Shared stop-event registry: maps execution_id -> asyncio.Event.
    # Kept as a thin alias alongside the transport-agnostic
    # :class:`ExecutionLifecycle` registry (the source of truth).  The
    # supervisor loop reads the Event via ``ToolContext._stop_event`` (set in
    # ``_prepare_graph_execution``), NOT via this dict, so the registry can
    # move without affecting the stop check.  ``_STOP_EVENTS_MAX`` is retained
    # for backwards compatibility but no longer caps eviction — the lifecycle
    # registry's ``settings.AI_EXECUTION_REGISTRY_MAX`` does.
    _stop_events: ClassVar[dict[str, asyncio.Event]] = {}
    _STOP_EVENTS_MAX: ClassVar[int] = 50

    @classmethod
    def request_stop(cls, execution_id: str) -> bool:
        """Signal a running execution to stop gracefully.

        Delegates to :meth:`ExecutionLifecycle.request_stop`, which sets the
        ``asyncio.Event`` associated with *execution_id*.  The supervisor loop
        checks this event after each specialist completes and raises
        :class:`ExecutionStoppedError` when set.

        Args:
            execution_id: The execution to stop.

        Returns:
            ``True`` if the execution was found and signalled, ``False`` otherwise.
        """
        return execution_lifecycle.request_stop(execution_id)

    @classmethod
    def _register_stop_event(
        cls,
        execution_id: str,
        bus: AgentEventBus,
        run_in_background: bool = False,
    ) -> asyncio.Event:
        """Create and register a stop event for an execution.

        Registers with the transport-agnostic :class:`ExecutionLifecycle`
        (the source of truth).  Eviction is **non-destructive**: when the
        lifecycle registry reaches ``settings.AI_EXECUTION_REGISTRY_MAX`` the
        OLDEST entry is dropped with a warning and is NEVER ``.set()`` — a
        live execution keeps running, just untracked.  (The previous inline
        eviction here ``.set()`` the evicted event, which could spuriously
        stop a live execution — fixed.)

        Also mirrors the entry into the legacy ``_stop_events`` alias so any
        pre-existing reader and the ``start_execution`` finally teardown
        still work.

        Args:
            execution_id: The execution to register a stop event for.
            bus: The execution's event bus (registered with the lifecycle for
                terminal cleanup).
            run_in_background: When True the execution survives a transport
                disconnect (no grace-stop on last-observer detach).

        Returns:
            The newly created :class:`asyncio.Event` for *execution_id*.
        """
        event = asyncio.Event()
        execution_lifecycle.register(
            execution_id, event, bus, run_in_background=run_in_background
        )
        cls._stop_events[execution_id] = event
        return event

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

        _supervisor_prompt = getattr(assistant_config, "supervisor_prompt", None)
        system_prompt = (
            _supervisor_prompt
            if _supervisor_prompt is not None
            else assistant_config.system_prompt
        ) or DEFAULT_SYSTEM_PROMPT
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
                specialist_models=params.specialist_models,
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

    async def _persist_briefing_from_checkpoint(
        self,
        session_id: UUID,
        log_label: str = "BRIEFING_PERSIST",
    ) -> bool:
        """Load briefing and plan from checkpoint and persist to database.

        Extracts briefing_data and plan_data from the LangGraph checkpoint,
        saves them to the session via config_service, and deletes the
        checkpoint.  Returns True if briefing was found and saved.

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
            plan_data: dict[str, Any] | None = cast(
                Any, channel_values.get("plan_data")
            )
            await self.config_service.save_session_briefing(
                session_id, briefing_data, plan_data=plan_data
            )
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

    async def _extract_termination_notice(
        self,
        session_id: UUID,
        state: StreamState,
    ) -> None:
        """Pull ``termination_notice`` from the graph checkpoint into StreamState.

        The ``bounded_terminate`` node sets ``termination_notice`` in the graph
        state when the supervisor hits a silent force-END cap (max-iterations
        or max-replan). That state lives only in the LangGraph checkpoint after
        the run (it is not carried by stream events), so we read it here and
        surface it on ``state.termination_message`` for
        ``_persist_session_messages`` to deliver as a final assistant message.

        Best-effort: any error is logged and leaves ``termination_message``
        unset (the run already completed; the notice is additive, not load-
        bearing for correctness). Reuses the same ``channel_values`` unpacking
        as ``_persist_briefing_from_checkpoint`` /
        ``_extract_resume_state_from_checkpoint``.

        Args:
            session_id: The session whose checkpoint to read.
            state: The StreamState to populate (sets ``termination_message``).
        """
        try:
            checkpoint_state = await shared_checkpointer.aget(
                {"configurable": {"thread_id": str(session_id)}}
            )
            if not checkpoint_state:
                return
            channel_values = checkpoint_state.get("channel_values", {}) or {}
            notice = channel_values.get("termination_notice")
            if isinstance(notice, str) and notice:
                state.termination_message = notice
                logger.info(
                    "[TERMINATION_NOTICE] Bounded-termination notice extracted "
                    "from checkpoint | session_id=%s | len=%d",
                    session_id,
                    len(notice),
                )
        except Exception as exc:
            logger.error(
                "[TERMINATION_NOTICE] Failed to read from checkpoint: %s "
                "| session_id=%s",
                exc,
                session_id,
                exc_info=True,
            )

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

        # Resolve specialist-specific models (each specialist may use a different provider)
        specialist_models: dict[str, ChatOpenAI | ChatDeepSeek] = {}
        try:
            specialist_configs = await load_specialists_from_db()
        except Exception as exc:
            logger.warning(
                "[SPECIALIST_MODELS] Failed to load specialist configs: %s", exc
            )
            specialist_configs = []

        for sc in specialist_configs:
            smid = sc.get("model_id")
            if smid is None:
                continue
            try:
                s_client_config, s_model_name, _ = await self._get_llm_client_config(
                    UUID(smid)
                )
                s_llm = await self._create_langchain_llm(
                    s_client_config,
                    s_model_name,
                    temperature=sc.get("temperature"),
                    max_tokens=sc.get("max_tokens"),
                )
                specialist_models[sc["name"]] = s_llm
                logger.info(
                    "[SPECIALIST_MODELS] Resolved specialist '%s' -> model %s",
                    sc["name"],
                    s_model_name,
                )
            except Exception as exc:
                logger.warning(
                    "[SPECIALIST_MODELS] Failed to resolve model for specialist '%s': %s",
                    sc["name"],
                    exc,
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
            session_id=str(session_id) if session_id else None,
            _event_bus=event_bus,
        )
        tool_context._stop_event = params.stop_event
        available_tools = create_project_tools(tool_context)

        graph, interrupt_node = await self._create_deep_agent_graph(
            GraphCreationParams(
                llm=llm,
                tool_context=tool_context,
                assistant_config=assistant_config,
                websocket=None,
                session_id=session_id,
                available_tools=available_tools,
                event_bus=event_bus,
                user_role=user_role,
                specialist_models=specialist_models,
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
            stop_event=params.stop_event,
        )

        existing_briefing = await self.config_service.get_session_briefing(session_id)
        if existing_briefing:
            logger.info(
                "[BRIEFING_PERSIST] Restored briefing from DB with %d sections (streaming)",
                len(existing_briefing.get("sections", [])),
            )

        # Resume injection: when the session has persisted plan_data with
        # incomplete steps, load it so the planner can skip the LLM call and
        # the supervisor can skip completed specialist steps.  Detected
        # automatically from session state — no explicit parameter needed.
        resume_plan_data: dict[str, Any] | None = None
        # Load plan_data directly from the session row
        stmt = select(AIConversationSession).where(
            AIConversationSession.id == str(session_id)
        )
        result = await self.session.execute(stmt)
        db_session = result.scalar_one_or_none()
        if db_session and db_session.plan_data:
            from app.ai.plan import PlanDocument

            plan = PlanDocument.from_state(db_session.plan_data)
            if plan.get_first_incomplete_step_index() is not None:
                resume_plan_data = db_session.plan_data
                logger.info(
                    "[RESUME] Loaded plan_data for session %s: %d steps, "
                    "%d incomplete — will inject into graph state",
                    session_id,
                    len(plan.steps),
                    len(plan.steps) - len(plan.completed_step_indices()),
                )

        ctx.resume_plan_data = resume_plan_data

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

        # Specialist chain start — set the invocation_id from the graph state
        # so that specialist-internal TOOL_CALL/TOOL_RESULT events (from ainvoke
        # callback propagation) are tagged with the correct invocation_id.
        # The SUBAGENT event is published directly by the specialist wrapper.
        if chain_name in state.specialist_names:
            # Read the invocation_id generated by the handoff tool from the
            # chain input (graph state).  astream_events v1 may not always
            # emit on_chain_start for plain async function nodes — if the
            # event fires, great; if not, the wrapper already publishes the
            # SUBAGENT event directly.
            data = event.get("data", {})
            input_state = data.get("input", {})
            inv_id = input_state.get("current_invocation_id", "")
            if inv_id and not state.current_invocation_id:
                state.current_invocation_id = inv_id
                logger.info(
                    "[SPECIALIST_CHAIN_START] name=%s | invocation_id=%s",
                    chain_name,
                    inv_id,
                )
            return

        # Non-specialist, non-planner chains — currently no handling needed.

    def _handle_chain_end(self, state: StreamState, event: dict[str, Any]) -> None:
        """Handle on_chain_end events for specialist, supervisor, and other nodes."""
        chain_name = event.get("name", "")
        data = event.get("data", {})

        # Specialist chain end — clear StreamState tracking.  The wrapper
        # publishes SUBAGENT / token_batch / AGENT_COMPLETE directly via the
        # event bus, so we only flush any remaining buffered tokens and reset
        # the tracking state.  Guard against double-fire (LangGraph may emit
        # multiple on_chain_end for the same specialist node).
        if chain_name in state.specialist_names:
            if state.current_invocation_id:
                state.flush_tokens(state.current_invocation_id)
                logger.info(
                    "[SPECIALIST_CHAIN_END] name=%s | invocation_id=%s",
                    chain_name,
                    state.current_invocation_id,
                )
                # Clear subagent tracking — prevent subsequent supervisor
                # tokens from being misrouted to the specialist bubble.
                state.current_subagent_name = None
                state.current_invocation_id = None
                state.task_initiating_main_invocation_id = None
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
        # Suppress the planner's own LLM tokens so its JSON does not leak
        # into the chat. The planner runs as a top-level graph node named
        # "planner" and calls ``llm.ainvoke`` directly; astream_events tags
        # those events' ``metadata.langgraph_node`` / ``langgraph_checkpoint_ns``
        # with "planner" -- a reliable per-call signal, unlike on_chain_start/
        # end (which v1 does not emit reliably for plain async nodes). Set
        # authoritatively here on every LLM call (start always fires before
        # stream for the same call) so the flag is correct for the
        # about-to-stream tokens. Supervisor/specialist calls lack the
        # signal so their tokens stream normally -- this fixes BOTH the
        # planner-JSON-into-chat leak AND TD-015's supervisor-text
        # suppression (the old code cleared the flag unconditionally here,
        # which let planner JSON stream while it was meant to do the opposite).
        _meta = event.get("metadata") or {}
        state.planner_active = ("planner" in (_meta.get("langgraph_node") or "")) or (
            "planner" in (_meta.get("langgraph_checkpoint_ns") or "")
        )

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

        # Per-call request-payload size diagnostic. Correlated to the
        # [LLM_CALL_START] line above via llm_call_count. Never raises;
        # degrades to ``bytes=N/A`` on any failure so a diagnostics log
        # can never break a run.
        self._log_llm_call_payload(state, data)

    def _log_llm_call_payload(self, state: StreamState, data: dict[str, Any]) -> None:
        """Log the size of the request message payload for one LLM call.

        Computes ``msg_count`` / ``total_chars`` / ``total_bytes`` and a
        per-role char breakdown from the input messages so we can see WHAT
        is bloating each call (e.g. accumulated tool results vs system
        prompt vs history). Driven by a real incident: a glm-4.7 run sent a
        ~247k-prompt-token request to the project_manager specialist,
        causing 120s timeouts.

        Known limitation: this measures the MESSAGE payload only. LangChain
        sends bound TOOLS separately (via ``.bind_tools()``), so tool JSON
        schemas are NOT counted here. That is acceptable for bloat
        diagnosis -- the message history (especially accumulated tool
        results) is the dominant factor. We intentionally do not hook the
        httpx/openai client (out of scope, too invasive).

        Robust to event shape: astream_events v2 ``on_chat_model_start``
        exposes ``data["messages"]`` as ``list[list[BaseMessage]]``; v1
        nested it under ``data["input"]["messages"]``. Older LLMs used
        ``data["prompts"]`` (list[str]). All three are handled; if none is
        present the call degrades to ``bytes=N/A``.
        """
        try:
            messages = self._extract_event_messages(data)
            if messages is None:
                payload_part = "msgs=0 | chars=0 | bytes=N/A | by_role="
            else:
                msg_count = len(messages)
                by_role: dict[str, int] = {}
                total_chars = 0
                total_bytes = 0
                for msg in messages:
                    text = _message_text(msg)
                    chars = len(text)
                    total_chars += chars
                    total_bytes += len(text.encode("utf-8"))
                    role = type(msg).__name__.removesuffix("Message").lower()
                    by_role[role] = by_role.get(role, 0) + chars
                role_str = ",".join(f"{r}:{c}" for r, c in by_role.items())
                payload_part = (
                    f"msgs={msg_count} | chars={total_chars} | "
                    f"bytes={total_bytes} | by_role={role_str}"
                )
        except Exception as exc:  # noqa: BLE001 -- diagnostics must never raise
            payload_part = (
                f"msgs=N/A | chars=N/A | bytes=N/A | err={type(exc).__name__}"
            )

        subagent_part = (
            f" | subagent={state.current_subagent_name}"
            if state.current_subagent_name
            else ""
        )
        logger.info(
            "[LLM_CALL_PAYLOAD] #%d | %s%s",
            state.llm_call_count,
            payload_part,
            subagent_part,
        )

    @staticmethod
    def _extract_event_messages(
        data: dict[str, Any],
    ) -> list[BaseMessage] | None:
        """Pull the input messages out of an ``on_chat_model_start`` event.

        Accepts the astream_events v2 shape (``data["messages"]``),
        the v1 shape (``data["input"]["messages"]``), and the legacy
        ``data["prompts"]`` shape (returned as zero-content messages).
        Returns a flat ``list[BaseMessage]`` or ``None`` if no usable
        payload is present.
        """
        raw: Any = None
        if isinstance(data.get("messages"), list):
            raw = data["messages"]
        elif isinstance(data.get("input"), dict) and isinstance(
            data["input"].get("messages"), list
        ):
            raw = data["input"]["messages"]
        elif isinstance(data.get("prompts"), list):
            raw = data["prompts"]

        if raw is None:
            return None

        flat: list[BaseMessage] = []
        for item in raw:
            if isinstance(item, BaseMessage):
                flat.append(item)
            elif isinstance(item, list):
                # v2 wraps messages per-batch: list[list[BaseMessage]].
                flat.extend(m for m in item if isinstance(m, BaseMessage))
            elif isinstance(item, str):
                # Legacy prompts shape -- synthesize a minimal message so
                # the size is still counted (content-only, generic role).
                flat.append(HumanMessage(content=item))
        return flat

    def _filter_think_tokens(self, state: StreamState, content: str) -> str:
        """Stateful inline ``<think>...</think>`` filter for streamed tokens.

        Suppresses chain-of-thought tokens while inside a ``<think>`` span so
        they never reach ``main_agent_segments`` / ``token_buffer`` (and thus
        never reach the live chat). Handles tags split across chunk boundaries
        by holding back a small tail that could be the start of ``<think>`` or
        ``</think>`` until the next chunk resolves it.

        NOTE: this filter cannot catch the "dangling close / opening already
        stripped" shape -- it never sees an opening tag to start suppression.
        The persistence backstop (``strip_think_tags`` in
        ``_persist_session_messages``) handles that case. Both are required.
        """
        OPEN = "<think>"
        CLOSE = "</think>"
        # Longest partial prefix we might need to hold back. A tag can be split
        # anywhere, so we may need to buffer up to len(CLOSE)-1 = 7 chars.
        MAX_PREFIX = len(CLOSE) - 1

        # Prepend any tail held back from the previous chunk.
        buf = state.think_pending_buffer + content
        state.think_pending_buffer = ""

        out: list[str] = []
        i = 0
        n = len(buf)
        while i < n:
            if state.in_think_block:
                # Discard everything until we find the closing tag.
                close_idx = buf.find(CLOSE, i)
                if close_idx == -1:
                    # No close yet. But the tail of what we consumed could be a
                    # partial CLOSE prefix (e.g. "</thin"). Hold it back.
                    hold_start = max(i, n - MAX_PREFIX)
                    state.think_pending_buffer = buf[hold_start:]
                    i = n
                    break
                # Skip to just after the closing tag; resume emitting.
                i = close_idx + len(CLOSE)
                state.in_think_block = False
            else:
                # Emit until we hit an opening tag.
                open_idx = buf.find(OPEN, i)
                if open_idx == -1:
                    # No full open tag. The tail of [i:] could still be a
                    # partial OPEN prefix (e.g. "<thi") -- hold it back rather
                    # than emit it prematurely. Only the last MAX_PREFIX chars
                    # can possibly be a tag prefix.
                    partial_start = None
                    check_from = max(i, n - MAX_PREFIX)
                    for s in range(check_from, n):
                        if OPEN.startswith(buf[s:n]) or CLOSE.startswith(buf[s:n]):
                            partial_start = s
                            break
                    if partial_start is not None:
                        out.append(buf[i:partial_start])
                        state.think_pending_buffer = buf[partial_start:]
                    else:
                        out.append(buf[i:n])
                    i = n
                    break
                # Emit up to the opening tag, then enter the think block.
                out.append(buf[i:open_idx])
                i = open_idx + len(OPEN)
                state.in_think_block = True

        return "".join(out)

    def _handle_chat_model_stream(
        self, state: StreamState, event: dict[str, Any]
    ) -> None:
        """Handle on_chat_model_stream -- accumulate token output.

        Tokens from the planner node are suppressed to prevent plan JSON
        from leaking into the chat stream. The planner emits a dedicated
        PLAN_UPDATE event instead. Inline ``<think>...</think>`` reasoning is
        stripped by ``_filter_think_tokens`` before reaching the segments.
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
                # Filter inline <think> reasoning BEFORE it reaches the
                # persisted segments and the live token buffer.
                content = self._filter_think_tokens(state, content)

                if content:
                    if state.current_subagent_name is None:
                        if state.main_invocation_id not in state.main_agent_segments:
                            state.main_agent_segments[state.main_invocation_id] = []
                        state.main_agent_segments[state.main_invocation_id].append(
                            content
                        )

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
        # Phase-0 observability: per-call prompt-token composition log.
        # Pure diagnostics -- never raises, never changes control flow.
        self._log_llm_call_usage(state, data)

    def _log_llm_call_usage(self, state: StreamState, data: dict[str, Any]) -> None:
        """Emit one structured ``[LLM_CALL_USAGE]`` line per LLM call.

        Captures the prompt-token cost of a single model call and a
        best-effort breakdown of its composition so we can decide whether
        specialist timeouts are dominated by tool *definitions* (roughly
        constant ~5k tok/call) or accumulated tool *results* (growing).
        This is the decision gate for the deferred roster-split work
        (plan: ``check-last-ai-chat-hashed-seahorse.md``, Phase 0).

        Observability only: every field is None-safe and the whole method is
        wrapped so a diagnostics log can never break a run. ``bound_tools`` /
        ``est_tool_def_tokens`` are logged as best-effort (the per-agent
        bound-tool list is not reachable from this callback without invading
        the compiled graph); ``accumulated_tool_msgs`` / chars come from
        ``state.all_tool_results`` (supervisor-visible results; specialist
        results are not tracked there and will read 0 -- labelled below).
        """
        try:
            prompt_tokens, completion_tokens = self._extract_call_usage(data)

            agent_label = (
                f"specialist:{state.current_subagent_name}"
                if state.current_subagent_name
                else ("planner" if state.planner_active else "supervisor")
            )

            # Running distinct tool NAMES invoked so far this run. NB:
            # ``all_tool_calls`` is only populated from the FINAL graph output
            # AIMessage at on_chain_end, so mid-run this is best-effort --
            # ``tool_calls_count`` (cumulative) is the live signal.
            distinct_tools = {
                str(tc.get("name", ""))
                for tc in state.all_tool_calls
                if isinstance(tc, dict) and tc.get("name")
            }

            # Accumulated tool-result messages visible in the supervisor stream.
            # Specialist-internal results are intentionally NOT appended to
            # ``all_tool_results`` (see _handle_tool_end), so for specialist
            # calls these read 0 -- a known limitation, labelled below.
            acc_tool_msgs = len(state.all_tool_results)
            acc_tool_chars = 0
            for tr in state.all_tool_results:
                if isinstance(tr, dict):
                    content = tr.get("result")
                    if content is not None:
                        acc_tool_chars += len(str(content))

            logger.info(
                "[LLM_CALL_USAGE] #%d | agent=%s | prompt_tokens=%s | "
                "completion_tokens=%s | bound_tools=N/A(best-effort) | "
                "invoked_tools_running=%d(distinct_seen=%d) | "
                "accumulated_tool_msgs=%d(chars=%d,est_tokens=%d,supervisor_stream_only)",
                state.llm_call_count,
                agent_label,
                prompt_tokens if prompt_tokens is not None else "N/A",
                completion_tokens if completion_tokens is not None else "N/A",
                state.tool_calls_count,
                len(distinct_tools),
                acc_tool_msgs,
                acc_tool_chars,
                acc_tool_chars // 4,
            )
        except Exception as exc:  # noqa: BLE001 -- diagnostics must never raise
            logger.warning(
                "[LLM_CALL_USAGE] #%d failed to emit (non-fatal): %s: %s",
                state.llm_call_count,
                type(exc).__name__,
                exc,
            )

    @staticmethod
    def _extract_call_usage(
        data: dict[str, Any],
    ) -> tuple[int | None, int | None]:
        """Extract PER-CALL prompt/completion tokens from an on_chat_model_end event.

        Mirrors ``TokenUsageAccumulator.accumulate_from_event`` but returns the
        single-call values instead of accumulating. Returns ``(None, None)``
        when usage is absent (some providers/events omit it) -- callers must
        treat that as "unknown", never as zero.
        """
        output = data.get("output")
        if output is None:
            return None, None

        def _from_message(msg: Any) -> tuple[int | None, int | None]:
            usage_metadata = getattr(msg, "usage_metadata", None)
            if isinstance(usage_metadata, dict):
                inp = usage_metadata.get("input_tokens")
                out = usage_metadata.get("output_tokens")
                if isinstance(inp, int) and isinstance(out, int):
                    return inp, out
            response_metadata = getattr(msg, "response_metadata", None)
            if isinstance(response_metadata, dict):
                token_usage = response_metadata.get("token_usage")
                if isinstance(token_usage, dict):
                    p = token_usage.get("prompt_tokens")
                    c = token_usage.get("completion_tokens")
                    if isinstance(p, int) and isinstance(c, int):
                        return p, c
            return None, None

        # astream_events v1 nests generations under a dict output.
        if isinstance(output, dict):
            generations = output.get("generations", [])
            if isinstance(generations, list):
                for gen_list in generations:
                    if isinstance(gen_list, list):
                        for gen in gen_list:
                            if isinstance(gen, dict):
                                msg = gen.get("message")
                                if msg is not None:
                                    p, c = _from_message(msg)
                                    if p is not None and c is not None:
                                        return p, c
            llm_output = output.get("llm_output")
            if isinstance(llm_output, dict):
                token_usage = llm_output.get("token_usage")
                if isinstance(token_usage, dict):
                    p = token_usage.get("prompt_tokens")
                    c = token_usage.get("completion_tokens")
                    if isinstance(p, int) and isinstance(c, int):
                        return p, c
            return None, None

        # Direct AIMessage object.
        return _from_message(output)

    @staticmethod
    def _is_delegation_tool(tool_name: str) -> bool:
        """Return True if this tool delegates to a specialist subgraph."""
        return tool_name == TOOL_NAME_TASK or tool_name.startswith("handoff_to_")

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

        if self._is_delegation_tool(tool_name):
            if tool_name == TOOL_NAME_TASK:
                state.current_subagent_name = (
                    tool_input.get("subagent_type")
                    if isinstance(tool_input, dict)
                    else None
                )
                # Legacy task tool — generate invocation_id here
                state.current_invocation_id = str(uuid.uuid4())
            else:
                # handoff_to_* — extract specialist name from tool name.
                # The invocation_id is generated inside the handoff tool
                # and passed through the graph state; the specialist
                # wrapper reads it and uses it for all published events.
                # We set current_subagent_name here only so that
                # specialist-internal TOOL_CALL/TOOL_RESULT events from
                # ainvoke callback propagation are tagged with the
                # subagent source.  The invocation_id will be set by
                # _handle_chain_start when the specialist node starts.
                state.current_subagent_name = tool_name.removeprefix("handoff_to_")
            state.task_initiating_main_invocation_id = state.main_invocation_id
            logger.info(
                "[DELEGATION] tool=%s -> specialist=%s | invocation_id=%s",
                tool_name,
                state.current_subagent_name,
                state.current_invocation_id,
            )

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

        # Subagent delegation event — only for the legacy `task` tool.
        # For handoff_to_* the specialist wrapper publishes the SUBAGENT
        # event directly via the event bus with the invocation_id from the
        # graph state, ensuring a single consistent ID across all events.
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

        # Subagent result handling — only for the `task` tool where the specialist
        # completes INSIDE the tool execution.  handoff_to_* tools return a
        # Command(goto=…) and the specialist runs afterwards as a separate
        # subgraph; its completion is handled by _handle_chain_end.
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
            self._complete_subagent(state, reason="subagent_completed")

        # Generate new main invocation_id after `task` tool completion only.
        # handoff_to_* tools return a Command — the specialist hasn't run yet,
        # so we must not orphan the invocation_id the specialist will use.
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
                "result": tool_result_dict,
                "invocation_id": (
                    state.current_invocation_id
                    if state.current_subagent_name
                    else state.main_invocation_id
                ),
            },
        )

    def _complete_subagent(self, state: StreamState, *, reason: str) -> None:
        """Publish AGENT_COMPLETE + CONTENT_RESET and clear subagent tracking state.

        Captures invocation_id and agent_name BEFORE clearing to ensure the
        frontend can correlate the completion with the preceding AGENT_TRANSITION
        enter event.
        """
        inv_id = state.current_invocation_id
        agent_name = state.current_subagent_name
        state.publish(
            AgentEventType.AGENT_COMPLETE,
            {
                "type": AgentEventType.AGENT_COMPLETE,
                "agent_type": "subagent",
                "invocation_id": inv_id,
                "agent_name": agent_name,
            },
        )
        state.publish(
            AgentEventType.CONTENT_RESET,
            {
                "type": AgentEventType.CONTENT_RESET,
                "reason": reason,
            },
        )
        state.current_subagent_name = None
        state.current_invocation_id = None
        state.task_initiating_main_invocation_id = None

    def _handle_tool_error(self, state: StreamState, event: dict[str, Any]) -> None:
        """Handle on_tool_error -- record tool failure."""
        data = event.get("data", {})
        tool_name = event.get("name", "")
        error = data.get("error")

        error_result_dict: dict[str, Any] = {
            "tool": tool_name,
            "success": False,
            "result": None,
            "error": (str(error) if error else "Unknown error"),
        }

        if state.current_subagent_name is None:
            state.all_tool_results.append(error_result_dict)

            state.publish(
                AgentEventType.TOOL_RESULT,
                {
                    "type": AgentEventType.TOOL_RESULT,
                    "tool": tool_name,
                    "result": error_result_dict,
                    "invocation_id": state.main_invocation_id,
                },
            )
        else:
            # Subagent task tool threw — publish error and clear subagent state
            state.publish(
                AgentEventType.TOOL_RESULT,
                {
                    "type": AgentEventType.TOOL_RESULT,
                    "tool": tool_name,
                    "result": error_result_dict,
                    "invocation_id": state.current_invocation_id,
                },
            )
            self._complete_subagent(state, reason="subagent_error")

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
        from app.ai.plan import PlanDocument

        state.publish(AgentEventType.THINKING, {"type": AgentEventType.THINKING})

        max_retries = 2
        retry_delay = 2.0
        events_processed = 0

        # Loop-scoped graph-input variables.  Initialised to the pre-stream
        # values for attempt 0; refreshed from the live LangGraph checkpoint
        # on retry so progress made during the failed attempt (briefing
        # sections, completed plan steps, completed specialists) is NOT
        # discarded and completed specialists are not re-run.
        cur_briefing: dict[str, Any] | None = existing_briefing
        cur_resume_plan: dict[str, Any] | None = ctx.resume_plan_data
        cur_completed_steps: set[int] = (
            PlanDocument.from_state(ctx.resume_plan_data).completed_step_indices()
            if ctx.resume_plan_data is not None
            else set()
        )
        cur_completed_specialists: set[str] = set()

        for _retry_attempt in range(max_retries + 1):
            try:
                from app.db.session import log_pool_status

                log_pool_status(
                    f"graph.astream_events start | session={ctx.session_id}"
                )

                async for event in iter_with_pausable_deadline(
                    ctx.graph.astream_events(
                        {
                            "messages": history,
                            "tool_call_count": 0,
                            "max_tool_iterations": ctx.recursion_limit,
                            "next": "agent",
                            "briefing_data": cur_briefing,
                            "completed_specialists": cur_completed_specialists,
                            # Inline resume state injection: when plan_data was
                            # loaded from the session, pass it with completed step
                            # indices so the planner skips the LLM call and the
                            # supervisor skips completed specialist steps.
                            **(
                                {
                                    "plan_data": cur_resume_plan,
                                    "completed_steps": cur_completed_steps,
                                }
                                if cur_resume_plan is not None
                                else {}
                            ),
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
                            stop_event=ctx.stop_event,
                        ),
                    ),
                    # Graph-level pausable deadline: bounds stalls anywhere
                    # outside a specialist body (planner, supervisor reasoning,
                    # handoff tools, middleware).  PAUSES while an ask_user
                    # human-wait is pending (via is_awaiting_user/is_ask_user_pending).
                    # should_stop interrupts the supervisor mid-flight (e.g. mid
                    # reasoning, mid handoff) within a single tick window when the
                    # user clicks stop.
                    timeout=float(settings.AI_GRAPH_EXECUTION_TIMEOUT),
                    execution_id=state.event_bus.execution_id,
                    should_stop=_make_stop_predicate(ctx.stop_event),
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
                # A graph-level pausable-deadline timeout (from
                # ``iter_with_pausable_deadline``) surfaces as a retryable
                # ``TimeoutError``: treat it as transient so a single graph
                # stall retries ONCE and then surfaces (mirrors the
                # specialist retry predicate).
                is_retryable = isinstance(
                    stream_err, (asyncio.TimeoutError, TimeoutError)
                ) or _is_transient_stream_error(stream_err)
                if not is_retryable or _retry_attempt >= max_retries:
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
                # Checkpoint-aware resume (FIX #2): pull the live briefing /
                # plan / completed-steps / completed-specialists from the
                # LangGraph checkpoint so the retry re-runs from the progress
                # made during the failed attempt, then delete the checkpoint
                # thread so the retry is a clean restart (not layered on an
                # interrupted checkpoint).
                checkpoint_state = await shared_checkpointer.aget(
                    {"configurable": {"thread_id": str(ctx.session_id)}}
                )
                # ``aget`` returns a LangGraph ``Checkpoint | None`` (a
                # TypedDict); the helper only reads ``channel_values`` so we
                # cast to the dict view it expects (mirrors the cast pattern
                # in ``_persist_briefing_from_checkpoint``).
                resume = _extract_resume_state_from_checkpoint(
                    cast(dict[str, Any] | None, checkpoint_state)
                )
                if resume:
                    section_count = len(resume["briefing_data"].get("sections", []))
                    cur_briefing = resume["briefing_data"]
                    cur_resume_plan = resume["plan_data"]
                    cur_completed_steps = resume["completed_steps"]
                    cur_completed_specialists = resume["completed_specialists"]
                    shared_checkpointer.delete_thread(str(ctx.session_id))
                    logger.info(
                        "[STREAM_RETRY] resumed from checkpoint: "
                        f"{section_count} briefing sections, "
                        f"completed_steps={sorted(cur_completed_steps)}, "
                        f"completed_specialists={sorted(cur_completed_specialists)}, "
                        f"deleting thread | session={ctx.session_id}"
                    )
                else:
                    logger.warning(
                        "[STREAM_RETRY] no checkpoint found for session "
                        f"{ctx.session_id} -- retry will use the pre-stream "
                        "state (progress made during the failed attempt may "
                        "be lost)"
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
                # Backstop: strip any inline <think>...</think> reasoning that
                # survived the streaming filter (e.g. a dangling </think> from
                # a provider that stripped the opening tag -- the stream filter
                # never saw an open tag to suppress). Guarantees the saved and
                # final-rendered DB message is clean.
                segment_content = strip_think_tags(segment_content)
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

                segment_msg = await self.config_service.add_message(
                    session_id=state.session_id,
                    role="assistant",
                    content=segment_content,
                    tool_calls=segment_tool_calls,
                    tool_results=segment_tool_results,
                    message_metadata=metadata,
                )
                await self.session.commit()
                state.last_persisted_message_id = segment_msg.id

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

        # Persist the bounded-termination notice as a final assistant message
        # when the supervisor graph hit a silent force-END cap (max-iterations
        # or max-replan). The notice is system-generated from plan STATE
        # (Completed / Failed-with-error / Not-started sections) by the
        # ``bounded_terminate`` node -- legitimate like the ``graph_error``
        # message above, NOT model-output rewriting. Setting
        # ``last_persisted_message_id`` makes the COMPLETE event point at this
        # message so the frontend surfaces it as the run's final answer.
        if state.termination_message:
            try:
                term_msg = await self.config_service.add_message(
                    session_id=state.session_id,
                    role="assistant",
                    content=state.termination_message,
                    message_metadata={
                        "bounded_termination": True,
                    },
                )
                await self.session.commit()
                state.last_persisted_message_id = term_msg.id
            except Exception as persist_error:
                logger.error(f"Failed to persist termination notice: {persist_error}")

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
                message_id=state.last_persisted_message_id,
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
        except ExecutionStoppedError:
            # Graceful stop — re-raise so start_execution() can persist
            # partial state with STOPPED status.  Briefing and messages
            # are saved in the finally block below before propagating.
            logger.info(
                "[RUN_AGENT_GRAPH] ExecutionStoppedError caught, "
                "persisting partial state before re-raise"
            )
            # Persist briefing before re-raising (finally also tries, but
            # the re-raise skips the normal briefing persist path).
            if not state.briefing_persisted:
                await self._persist_briefing_from_checkpoint(
                    ctx.session_id, log_label="BRIEFING_PERSIST_STOPPED"
                )
            raise
        except asyncio.CancelledError:
            # Task cancelled externally — persist what we have and re-raise.
            logger.info(
                "[RUN_AGENT_GRAPH] CancelledError caught, "
                "persisting partial state before re-raise"
            )
            if not state.briefing_persisted:
                await self._persist_briefing_from_checkpoint(
                    ctx.session_id, log_label="BRIEFING_PERSIST_CANCELLED"
                )
            raise
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

        # Step 5: Extract a bounded-termination notice (if any) from the
        # graph checkpoint, then persist messages to session history. The
        # checkpoint still exists at this point (briefing persist in the
        # finally block above does NOT run on the success path -- it runs
        # only on error/stop/cancel). We read termination_notice from the
        # channel_values (mirrors the unpacking in
        # _persist_briefing_from_checkpoint / _extract_resume_state_from_checkpoint).
        await self._extract_termination_notice(ctx.session_id, state)

        # Step 6: Persist messages to session history
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

    @staticmethod
    async def _preflight_execution(
        execution_id: str,
        session_id: UUID,
        execution_mode: ExecutionMode,
        run_in_background: bool = False,
        name: str | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Create execution row and capture session context in a short-lived session.

        Opens its own DB session, creates the AIAgentExecution tracking row,
        sets active_execution_id on the conversation session, and returns the
        session context dict plus the session's persisted project_id.  No live
        ORM objects escape — only serializable data.

        Args:
            execution_id: Pre-generated execution UUID string.
            session_id: Conversation session UUID.
            execution_mode: Execution mode stored on the row.
            run_in_background: When True persisted on the row so the Agents
                History page and any restart can tell this execution survives
                disconnects.
            name: Prompt-derived display name (truncated by caller) persisted
                on the row for the Agents History page.

        Returns:
            Tuple of (session context dict or None, session project_id string or None).
            The project_id reflects any cross-turn scope set via set_project_context.
        """
        from app.db.session import async_session_maker

        async with async_session_maker() as db:
            # Fetch conversation session row
            session_stmt = select(AIConversationSession).where(
                AIConversationSession.id == str(session_id)
            )
            session_result = await db.execute(session_stmt)
            db_session = session_result.scalar_one_or_none()

            # Create execution tracking row — use execution_id as the PK
            # so the DB row ID matches the event bus key (required for
            # WebSocket re-subscribe: the client sends the DB execution.id
            # and the subscribe handler looks up the bus by the same key).
            execution = AIAgentExecution(
                id=UUID(execution_id),
                session_id=str(session_id),
                status=ExecutionStatus.RUNNING,
                execution_mode=execution_mode.value,
                run_in_background=run_in_background,
                name=name,
            )
            db.add(execution)
            await db.commit()

            # Set active_execution_id on session
            if db_session is not None:
                db_session.active_execution_id = str(execution.id)
                await db.commit()

            # Capture serializable context + persisted project scope — no ORM
            # objects escape.
            return (
                db_session.context if db_session else None,
                str(db_session.project_id)
                if (db_session and db_session.project_id)
                else None,
            )

    @staticmethod
    async def _finalize_stopped_execution(
        execution_id: str,
        session_id: UUID,
        metrics: AgentExecutionMetrics | None,
        event_bus: AgentEventBus,
    ) -> None:
        """Run postflight and publish STOPPED status event.

        Shared by ExecutionStoppedError and CancelledError handlers
        so the same cleanup logic doesn't need to be duplicated.
        """
        await AgentService._postflight_execution(
            execution_id,
            session_id,
            metrics=metrics,
            status=ExecutionStatus.STOPPED,
        )
        event_bus.publish(
            AgentEvent(
                event_type=AgentEventType.EXECUTION_STATUS,
                data={
                    "type": AgentEventType.EXECUTION_STATUS,
                    "execution_id": execution_id,
                    "status": ExecutionStatus.STOPPED,
                    "session_id": str(session_id),
                },
                timestamp=datetime.now(UTC),
            )
        )

    @staticmethod
    async def _postflight_execution(
        execution_id: str,
        session_id: UUID,
        metrics: AgentExecutionMetrics | None = None,
        error: Exception | None = None,
        status: ExecutionStatus | None = None,
    ) -> None:
        """Update execution status and metrics in a short-lived session.

        Opens its own DB session, queries the execution row by ID (fresh
        session, no detachment issues), sets COMPLETED or ERROR status,
        and clears active_execution_id.  Best-effort: logs failures but
        does not re-raise.

        Args:
            execution_id: The execution row UUID as string.
            session_id: The conversation session UUID.
            metrics: Optional aggregated token usage and tool call count.
            error: If provided, status is set to ERROR with this message.
            status: Explicit status override (e.g. ``ExecutionStatus.STOPPED``).
                Takes precedence over the error/completed default.
        """
        from app.db.session import async_session_maker

        try:
            async with async_session_maker() as db:
                stmt = select(AIAgentExecution).where(
                    AIAgentExecution.id == execution_id
                )
                result = await db.execute(stmt)
                row = result.scalar_one_or_none()

                if row is None:
                    logger.warning(
                        "[POSTFLIGHT] Execution row %s not found", execution_id
                    )
                    return

                if status is not None:
                    row.status = status
                elif error is not None:
                    row.status = ExecutionStatus.ERROR
                    row.error_message = str(error)[:2000]
                else:
                    row.status = ExecutionStatus.COMPLETED

                row.completed_at = datetime.now(UTC)  # type: ignore[assignment]

                if metrics is not None:
                    row.total_tokens = metrics.total_tokens
                    row.tool_calls_count = metrics.tool_calls_count

                await db.commit()

                # Clear active_execution_id on the conversation session
                session_stmt = select(AIConversationSession).where(
                    AIConversationSession.id == str(session_id)
                )
                session_result = await db.execute(session_stmt)
                session_row = session_result.scalar_one_or_none()
                if session_row is not None:
                    session_row.active_execution_id = None
                    await db.commit()

        except Exception:
            logger.error(
                "[POSTFLIGHT] Failed to update execution %s",
                execution_id,
                exc_info=True,
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
        run_in_background: bool = False,
    ) -> str:
        """Start a background agent execution with its own DB session and event bus.

        Context: Creates an independent execution context that decouples the agent
        run from any specific WebSocket connection. Events are published to an
        AgentEventBus registered with the runner_manager, allowing any consumer
        (REST SSE, WebSocket reconnection) to subscribe by execution ID.

        Uses three independent DB sessions for resilient connection management:
        1. Pre-flight: creates execution row, captures context (~ms)
        2. Graph execution: runs the agent graph (~minutes)
        3. Post-flight: updates execution status and metrics (~ms)

        Each phase opens and closes its own session, so connections are returned
        to the pool between phases instead of being held for the full duration.

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
            run_in_background: When True the execution survives a transport
                disconnect — the lifecycle will NOT grace-stop it on
                last-observer detach.  Persisted on the execution row and used
                to derive the Agents History display name from *message*.

        Returns:
            execution_id string for tracking the agent execution

        Raises:
            ValueError: If session creation fails
        """
        from app.db.session import async_session_maker

        if execution_id is None:
            execution_id = str(uuid.uuid4())

        # Use provided bus or create a new one.  Terminal cleanup
        # (ExecutionLifecycle.terminate) removes the bus unconditionally on
        # every path: the WS flow creates its bus via runner_manager.create_bus
        # so removal is symmetric; a caller that needs the bus after the run
        # should read replay() before start_execution returns.
        if event_bus is None:
            event_bus = runner_manager.create_bus(execution_id)

        # Create and register stop event for graceful cancellation.
        # Registering with the transport-agnostic ExecutionLifecycle (source
        # of truth) also registers the bus so terminal cleanup can remove it.
        # run_in_background makes the lifecycle skip the grace-stop on
        # last-observer detach so the execution survives a disconnect.
        stop_event = self._register_stop_event(
            execution_id, event_bus, run_in_background=run_in_background
        )

        # Display name for the Agents History page: the user's prompt truncated
        # to a sensible length (the column cap is 255; 120 keeps the UI tidy).
        exec_name = message.strip()[:120] if message else None

        try:
            # Phase 1: Pre-flight — create execution row, capture context
            session_context, session_project_id = await self._preflight_execution(
                execution_id,
                session_id,
                execution_mode,
                run_in_background=run_in_background,
                name=exec_name,
            )

            # Persisted project scope (set via set_project_context) applies when
            # the incoming request carries no project_id (general chat). An
            # explicit request project_id always wins, so project-scoped chats
            # are unaffected.
            effective_project_id = project_id or (
                UUID(session_project_id) if session_project_id else None
            )

            # Phase 2: Graph execution — own session for the full graph run
            metrics: AgentExecutionMetrics | None = None
            async with async_session_maker() as db:
                exec_service = AgentService(db)
                metrics = await exec_service._run_agent_graph(
                    GraphExecutionParams(
                        message=message,
                        assistant_config=assistant_config,
                        session_id=session_id,
                        user_id=user_id,
                        event_bus=event_bus,
                        project_id=effective_project_id,
                        branch_id=branch_id,
                        as_of=as_of,
                        branch_name=branch_name,
                        branch_mode=branch_mode,
                        execution_mode=execution_mode,
                        context=session_context,
                        stop_event=stop_event,
                    )
                )

            # Phase 3: Post-flight — update execution status and metrics
            await self._postflight_execution(
                execution_id,
                session_id,
                metrics=metrics,
            )

        except ExecutionStoppedError:
            logger.info("[EXECUTION_STOPPED] %s — saving partial state", execution_id)
            # Post-flight with STOPPED status (briefing already persisted
            # inside _run_agent_graph before re-raise).
            await self._finalize_stopped_execution(
                execution_id,
                session_id,
                metrics,
                event_bus,
            )

        except asyncio.CancelledError:
            logger.info("[EXECUTION_CANCELLED] %s — saving partial state", execution_id)
            # Persist briefing if not already done
            try:
                async with async_session_maker() as db:
                    svc = AgentService(db)
                    await svc._persist_briefing_from_checkpoint(
                        session_id, log_label="BRIEFING_PERSIST_CANCELLED"
                    )
            except Exception:
                logger.error(
                    "[EXECUTION_CANCELLED] Failed to persist briefing for %s",
                    execution_id,
                    exc_info=True,
                )
            await self._finalize_stopped_execution(
                execution_id,
                session_id,
                metrics,
                event_bus,
            )
            raise

        except Exception as e:
            logger.error(
                "Error in start_execution %s: %s", execution_id, e, exc_info=True
            )

            # Best-effort error status update (own session)
            await self._postflight_execution(
                execution_id,
                session_id,
                metrics=metrics,
                error=e,
            )

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
            # Single terminal cleanup: route ask-cancel + bus-remove +
            # registry-drop through ExecutionLifecycle.terminate so no
            # registry/bus/ask entry leaks on ANY terminal path (complete,
            # stop, cancel, error).  Idempotent.  The DB status write,
            # active_execution_id clear, and terminal event publish already
            # happened in the try/except blocks above (per-path).
            execution_lifecycle.terminate(execution_id)
            # Mirror-drop from the legacy _stop_events alias.
            self._stop_events.pop(execution_id, None)

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

            elif context_type == "work_package":
                stmt = (
                    select(WorkPackage.name)
                    .where(WorkPackage.work_package_id == entity_uuid)
                    .where(sa_func.upper(WorkPackage.valid_time).is_(None))
                    .where(WorkPackage.deleted_at.is_(None))
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
            elif context_type == "work_package":
                name_part = (
                    f" the Work Package: {context_name}"
                    if context_name
                    else " a Work Package"
                )
                context_sections.append(
                    f"This conversation is about{name_part}. "
                    f"Work Package ID: {context.get('id')}. "
                    f"Parent project ID: {context.get('project_id', project_id)}. "
                    "Focus your responses on this specific work package. "
                    "Use work package tools to query and analyze this element."
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

    _INTERRUPT_NODE_MAX = 20

    def register_interrupt_node(
        self, session_id: UUID, interrupt_node: "InterruptNode"
    ) -> None:
        """Register an InterruptNode for a session.

        Args:
            session_id: The session ID
            interrupt_node: The InterruptNode instance to register
        """
        # Auto-evict oldest entry to prevent unbounded growth
        if len(self._interrupt_nodes) >= self._INTERRUPT_NODE_MAX:
            oldest_key = next(iter(self._interrupt_nodes))
            evicted = self._interrupt_nodes.pop(oldest_key, None)
            if evicted is not None:
                evicted.pending_approvals.clear()
                evicted.interrupt_state.clear()
            logger.warning(
                "Interrupt node registry reached %d entries — evicted oldest "
                "(session=%s) to make room for session=%s",
                self._INTERRUPT_NODE_MAX,
                oldest_key,
                session_id,
            )
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
                "result": self._make_json_serializable(result.content),
                "error": None,
            }

            if is_websocket_connected(websocket):
                try:
                    msg_data = WSToolResultMessage(
                        type="tool_result",
                        tool=tool_result["tool"],
                        result=tool_result,
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
