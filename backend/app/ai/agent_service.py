"""LangGraph Agent Service for conversation orchestration.

Uses LangGraph StateGraph for conversation flow with tool calling loop.
"""

import asyncio
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Literal, cast
from uuid import UUID

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.config import AgentConfig
from app.ai.deep_agent_orchestrator import DeepAgentOrchestrator
from app.ai.execution.agent_event import AgentEvent
from app.ai.execution.agent_event_bus import AgentEventBus
from app.ai.execution.runner_manager import runner_manager
from app.ai.graph import create_graph
from app.ai.graph_cache import (
    BackcastRuntimeContext,
    LLMClientCache,
    clear_request_context,
    set_request_context,
    shared_checkpointer,
)
from app.ai.telemetry import (
    initialize_telemetry,
    trace_context,
)
from app.ai.token_estimator import (
    TokenUsageAccumulator,
    log_actual_usage,
    log_context_usage_estimate,
)
from app.ai.tools import ToolContext, create_project_tools
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
from app.models.schemas.ai import (
    AIChatResponse,
    AIConversationMessagePublic,
    PlanningStep,
    WSAgentCompleteMessage,
    WSAgentTransitionMessage,
    WSCompleteMessage,
    WSContentResetMessage,
    WSPlanningMessage,
    WSSubagentMessage,
    WSSubagentResultMessage,
    WSThinkingMessage,
    WSTokenBatchMessage,
    WSToolCallMessage,
    WSToolResultMessage,
)
from app.services.ai_config_service import AIConfigService

# Initialize telemetry on module load (will only instrument once)
_tracer_provider = initialize_telemetry(
    service_name="backcast-ai",
    enable_console=os.getenv("OTEL_CONSOLE_EXPORT", "false").lower() == "true",
)


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

    # Extract config values
    for cfg in config_values:
        if cfg.key == "api_key" and cfg.value is not None:
            client_config["api_key"] = str(cfg.value)
        elif cfg.key == "base_url" and cfg.value is not None:
            client_config["base_url"] = str(cfg.value)
        elif cfg.key == "timeout" and cfg.value is not None:
            client_config["timeout"] = float(cfg.value)
        elif cfg.key == "max_retries" and cfg.value is not None:
            client_config["max_retries"] = int(cfg.value)

    # Set base URL for provider if configured at provider level
    if "base_url" not in client_config and provider.base_url:
        client_config["base_url"] = str(provider.base_url)

    # Handle Azure-specific configuration
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

    return client_config


logger = logging.getLogger(__name__)

# Specialist agent names used for supervisor graph event routing
SPECIALIST_AGENT_NAMES = frozenset({
    "project_manager",
    "evm_analyst",
    "change_order_manager",
    "user_admin",
    "visualization_specialist",
    "forecast_manager",
    "general_purpose",
})

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
    """Get user role with TTL caching."""
    cached = _user_role_cache.get(user_id)
    if cached is not None:
        expires_at, role = cached
        if time.time() < expires_at:
            return role
        del _user_role_cache[user_id]

    from app.services.user import UserService

    user_service = UserService(session)
    user = await user_service.get_user(user_id)
    role = user.role if user else "guest"
    _user_role_cache[user_id] = (time.time() + _USER_ROLE_TTL, role)
    return role


# Constants
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant for the Backcast project budget management system.

You can help with:
- Listing and viewing projects
- Getting detailed project information
- Earned value management calculations

When providing information:
- Be accurate and rely on the project data
- Use three-letter codes for project status (e.g., "ACT" for active, "PLN" for planned)
- Present data in clear, structured formats
- Only use tools you have been explicitly enabled for the assistant

When using tools:
- Always use the exact field names expected by the tools
- For status filters, use three-letter codes like 'ACT', 'PLN', 'CLS'
- Use search to find projects by code or name
"""


class AgentService:
    """Service for LangGraph agent orchestration."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._config_service: AIConfigService | None = None
        self._subagent_invocation_counts: dict[str, int] = {}
        self._cancellation_tokens: dict[UUID, asyncio.Event] = {}

    @staticmethod
    def _is_websocket_connected(websocket: WebSocket) -> bool:
        """Check if WebSocket is still connected.

        Delegates to the shared is_websocket_connected utility.

        Args:
            websocket: WebSocket connection to check

        Returns:
            True if WebSocket is connected, False otherwise
        """
        return is_websocket_connected(websocket)

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
        # Check cache first
        cached = _llm_config_cache.get(model_id)
        if cached is not None:
            expires_at, client_config, model_name, provider_type = cached
            if time.time() < expires_at:
                logger.debug("LLM config cache hit for model %s", model_id)
                return client_config, model_name, provider_type
            else:
                del _llm_config_cache[model_id]

        # Cache miss — query DB
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

        # Store in cache
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
    ) -> ChatOpenAI:
        """Create a LangChain ChatOpenAI instance from client configuration.

        Context: Creates a ChatOpenAI instance by passing configuration directly
        to LangChain, allowing it to create and manage its own client properly.
        This ensures compatibility with LangChain's streaming implementation.

        Args:
            client_config: Configuration dictionary for the OpenAI client
            model_name: Model identifier to use
            temperature: Optional temperature setting
            max_tokens: Optional max tokens setting

        Returns:
            ChatOpenAI instance configured with the provided parameters
        """
        # Build cache key
        base_url = client_config.get("base_url", "")
        base_url_hash = str(hash(base_url))
        temp = temperature or 0.0
        tokens = max_tokens or 2000

        cache_key = (model_name, temp, tokens, base_url_hash)

        def factory() -> ChatOpenAI:
            return ChatOpenAI(
                **client_config,
                model=model_name,
                temperature=temp,
                max_tokens=tokens,
                stream_chunk_timeout=300,
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
        }

        provider = provider_mapping.get(provider_type or "", "openai")

        # Clean model name to remove any provider prefix
        clean_model = model_name or ""
        if ":" in clean_model:
            clean_model = clean_model.split(":")[-1]

        return f"{provider}:{clean_model}"

    async def _create_deep_agent_graph(
        self,
        llm: ChatOpenAI,
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
            llm: The language model to use (for fallback to LangGraph)
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
            logger.info(
                f"[GRAPH_COMPILE] Compiling new graph for session {session_id}"
            )
            graph_creation_start = time.time()

            orchestrator = DeepAgentOrchestrator(
                model=llm,
                context=tool_context,
                system_prompt=system_prompt,
                enable_subagents=enable_subagents,
                interrupt_node=None,  # Don't bake InterruptNode into graph
            )

            graph = orchestrator.create_agent(
                config=AgentConfig(
                    allowed_tools=None,  # RBAC role filtering only
                    checkpointer=shared_checkpointer,
                    context_schema=BackcastRuntimeContext,
                    assistant_role=assistant_role,
                    user_role=user_role,
                    use_supervisor=settings.AI_ORCHESTRATOR == "supervisor",
                ),
            )

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
        # Get or create session
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

        # Add user message to session
        _ = await self.config_service.add_message(
            session_id=session_id,
            role="user",
            content=message,
        )

        # Build conversation history
        history = await self._build_conversation_history(session_id)

        # Add system prompt (no temporal context for non-streaming chat)
        system_prompt = assistant_config.system_prompt or DEFAULT_SYSTEM_PROMPT
        history.insert(0, SystemMessage(content=system_prompt))

        # Get LLM client configuration
        client_config, model_name, provider_type = await self._get_llm_client_config(
            UUID(str(assistant_config.model_id))
        )

        # Create LangChain LLM wrapper
        llm = await self._create_langchain_llm(
            client_config,
            model_name,
            assistant_config.temperature,
            assistant_config.max_tokens,
        )

        # Create tools with RBAC
        user_role = await _get_user_role(self.session, user_id)

        tool_context = ToolContext(self.session, str(user_id), user_role=user_role)
        available_tools = create_project_tools(tool_context)
        tools_dict = {tool.name: tool for tool in available_tools}

        # Filter by assistant config's role ceiling
        if assistant_config.default_role:
            from app.ai.tools import filter_tools_by_role

            filtered = filter_tools_by_role(
                list(tools_dict.values()), assistant_config.default_role
            )
            tools_dict = {t.name: t for t in filtered}

        # Filter by user's actual role
        from app.ai.tools import filter_tools_by_role

        filtered = filter_tools_by_role(list(tools_dict.values()), user_role)
        tools_dict = {t.name: t for t in filtered}

        # Create graph with context for RBAC
        graph, _interrupt_node = create_graph(
            llm=llm, tools=list(tools_dict.values()), context=tool_context
        )

        # Extract recursion_limit from assistant config with fallback to default
        recursion_limit = (
            assistant_config.recursion_limit
            if assistant_config.recursion_limit is not None
            else 25
        )

        # Invoke the graph
        # Note: Task-local sessions are created per tool execution and cleaned up below
        try:
            result = await graph.ainvoke(
                input_state={
                    "messages": history,
                    "tool_call_count": 0,
                    "max_tool_iterations": recursion_limit,
                    "next": "agent",
                },
                config={
                    "recursion_limit": recursion_limit,
                    "configurable": {"thread_id": str(session_id)},
                },
            )
        finally:
            # Clean up any remaining task-local sessions after graph execution
            # This ensures sessions are properly removed even if tools didn't clean up
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

        # Extract final AI response
        final_message = None
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                final_message = msg
                break

        if not final_message:
            raise ValueError("No assistant response generated")

        # Collect tool calls and results
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

        # Save assistant message to session
        # Convert AIMessage content to string (can be str | list)
        content_str = (
            final_message.content
            if isinstance(final_message.content, str)
            else str(final_message.content)
            if final_message.content
            else ""
        )
        assistant_msg = await self.config_service.add_message(
            session_id=session_id,
            role="assistant",
            content=content_str,
            tool_calls=tool_calls_data if tool_calls_data else None,
            tool_results=None,  # No tool results in non-streaming mode
        )

        # Build response
        return AIChatResponse(
            session_id=session_id,
            message=AIConversationMessagePublic.model_validate(assistant_msg),
            tool_calls=tool_calls_data if tool_calls_data else None,
        )

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
    ) -> None:
        """Run the agent graph publishing all events to an AgentEventBus.

        Context: Decoupled variant of chat_stream() that publishes events to an
        event bus instead of a WebSocket. Used by start_execution() for
        background agent runs that can be consumed via REST or WebSocket
        reconnection.

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
            None (communicates via event_bus)
        """
        # Build conversation history
        history = await self._build_conversation_history(session_id)

        # Add system prompt with temporal context
        base_prompt = assistant_config.system_prompt or DEFAULT_SYSTEM_PROMPT
        system_prompt = self._build_system_prompt(
            base_prompt=base_prompt,
            project_id=project_id,
            as_of=as_of,
            branch_name=branch_name,
            branch_mode=branch_mode,
            context=context,
        )
        history.insert(0, SystemMessage(content=system_prompt))

        # Get LLM client configuration
        client_config, model_name, provider_type = await self._get_llm_client_config(
            UUID(str(assistant_config.model_id))
        )

        # Create LangChain LLM wrapper
        llm = await self._create_langchain_llm(
            client_config,
            model_name,
            assistant_config.temperature,
            assistant_config.max_tokens,
        )

        # Create tools with RBAC
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
        )
        available_tools = create_project_tools(tool_context)

        # Create graph (no websocket, but pass event_bus for InterruptNode)
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

        # Set per-request context for middleware
        set_request_context(tool_context, interrupt_node)

        # Register InterruptNode for approval handling if created
        if interrupt_node is not None:
            self.register_interrupt_node(session_id, interrupt_node)

        # Estimate context window usage before graph invocation
        log_context_usage_estimate(
            messages=history,
            model_name=model_name,
            session_id=str(session_id),
            execution_id=event_bus.execution_id,
        )

        # Extract recursion_limit
        recursion_limit = (
            assistant_config.recursion_limit
            if assistant_config.recursion_limit is not None
            else 25
        )

        all_tool_calls: list[dict[str, Any]] = []
        all_tool_results: list[dict[str, Any]] = []
        main_agent_segments: dict[str, list[str]] = {}
        from collections import defaultdict

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
        main_invocation_id: str = str(uuid.uuid4())
        task_initiating_main_invocation_id: str | None = None

        # Per-invocation token accumulator for batched publishing
        _token_accumulator: dict[str, list[str]] = {}

        # Helper to publish events
        def _publish(event_type: str, data: dict[str, Any]) -> None:
            event_bus.publish(
                AgentEvent(
                    event_type=event_type,
                    data=data,
                    timestamp=datetime.now(),
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
                WSTokenBatchMessage(
                    type="token_batch",
                    tokens=concatenated,
                    session_id=str(session_id),
                    source="subagent" if current_subagent_name else "main",
                    subagent_name=current_subagent_name,
                    invocation_id=invocation_id,
                ).model_dump(mode="json"),
            )

        # Background task to flush tokens periodically for real-time streaming
        async def _periodic_flush() -> None:
            while True:
                await asyncio.sleep(settings.AI_TOKEN_BUFFER_INTERVAL_MS / 1000)
                for inv_id in list(_token_accumulator.keys()):
                    _flush_accumulated_tokens(inv_id)

        _flush_task = asyncio.create_task(_periodic_flush())

        graph_error: Exception | None = None

        try:
            main_invocation_id = str(uuid.uuid4())

            # Clear previous checkpoint to prevent message duplication.
            # DB is the source of truth for conversation history; the checkpointer
            # would otherwise append the full history to its stored state via
            # operator.add, causing "system after assistant" role ordering errors.
            shared_checkpointer.delete_thread(str(session_id))

            # Send thinking event
            _publish(
                "thinking",
                WSThinkingMessage().model_dump(mode="json"),
            )

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

                        # Handle agent transitions in supervisor graph
                        # When a specialist subgraph node starts/ends, detect by chain name
                        chain_name = event.get("name", "")
                        if event_type == "on_chain_start" and chain_name in SPECIALIST_AGENT_NAMES:
                            _flush_accumulated_tokens(
                                current_invocation_id or main_invocation_id
                            )
                            current_subagent_name = chain_name
                            current_invocation_id = str(uuid.uuid4())
                            _publish(
                                "agent_transition",
                                WSAgentTransitionMessage(
                                    type="agent_transition",
                                    agent_name=chain_name,
                                    direction="enter",
                                    invocation_id=current_invocation_id,
                                ).model_dump(mode="json"),
                            )
                        elif (
                            event_type == "on_chain_end"
                            and chain_name == current_subagent_name
                        ):
                            _flush_accumulated_tokens(current_invocation_id)
                            _publish(
                                "agent_transition",
                                WSAgentTransitionMessage(
                                    type="agent_transition",
                                    agent_name=chain_name,
                                    direction="exit",
                                    invocation_id=current_invocation_id,
                                ).model_dump(mode="json"),
                            )
                            current_subagent_name = None
                            current_invocation_id = None

                        # Handle token streaming
                        if event_type == "on_chat_model_stream":
                            chunk = data.get("chunk")
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
                                            main_agent_segments[
                                                main_invocation_id
                                            ] = []
                                        main_agent_segments[
                                            main_invocation_id
                                        ].append(content)

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
                                        _token_accumulator[
                                            invocation_id_to_use
                                        ].append(content)

                        # Handle chat model end -- capture actual token usage
                        elif event_type == "on_chat_model_end":
                            token_accumulator.accumulate_from_event(data)

                        # Handle tool start
                        elif event_type == "on_tool_start":
                            # Flush any accumulated main-agent tokens before tool execution
                            _flush_accumulated_tokens(main_invocation_id)

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
                                task_initiating_main_invocation_id = (
                                    main_invocation_id
                                )

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
                                    WSPlanningMessage(
                                        type="planning",
                                        plan=plan,
                                        steps=steps,
                                        step_number=current_step,
                                        total_steps=estimated_total_steps,
                                        invocation_id=main_invocation_id,
                                    ).model_dump(mode="json"),
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
                                        WSSubagentMessage(
                                            type="subagent",
                                            subagent=subagent_type,
                                            message=description,
                                            step_number=current_step,
                                            total_steps=estimated_total_steps,
                                            invocation_id=current_invocation_id,
                                        ).model_dump(mode="json"),
                                    )

                            # Standard tool_call event
                            _publish(
                                "tool_call",
                                WSToolCallMessage(
                                    type="tool_call",
                                    tool=tool_name,
                                    args=tool_input,
                                    step_number=current_step,
                                    total_steps=estimated_total_steps,
                                    invocation_id=current_invocation_id
                                    if current_subagent_name
                                    else main_invocation_id,
                                ).model_dump(mode="json"),
                            )

                        # Handle tool end
                        elif event_type == "on_tool_end":
                            tool_name = event.get("name", "")

                            # Subagent result handling
                            if (
                                tool_name == "task"
                                and current_invocation_id is not None
                            ):
                                # Flush subagent tokens before processing result
                                _flush_accumulated_tokens(current_invocation_id)

                                tool_output = data.get("output", "")
                                subagent_content = ""

                                if isinstance(tool_output, ToolMessage):
                                    raw_content = tool_output.content
                                    subagent_content = (
                                        raw_content
                                        if isinstance(raw_content, str)
                                        else str(raw_content)
                                    )
                                elif isinstance(tool_output, Command):
                                    update_dict = tool_output.update
                                    if isinstance(update_dict, dict):
                                        messages = update_dict.get(
                                            "messages", []
                                        )
                                        if messages:
                                            last_msg = messages[-1]
                                            if isinstance(last_msg, dict):
                                                subagent_content = (
                                                    last_msg.get(
                                                        "content", ""
                                                    )
                                                )
                                            elif hasattr(last_msg, "content"):
                                                subagent_content = str(
                                                    last_msg.content
                                                )
                                            else:
                                                subagent_content = str(
                                                    last_msg
                                                )
                                elif isinstance(
                                    tool_output, dict
                                ) and "content" in tool_output:
                                    subagent_content = tool_output["content"]
                                elif isinstance(tool_output, str):
                                    subagent_content = tool_output

                                if not isinstance(subagent_content, str):
                                    subagent_content = str(subagent_content)

                                if subagent_content:
                                    subagent_type = (
                                        current_subagent_name or "subagent"
                                    )
                                    if (
                                        subagent_type
                                        not in self._subagent_invocation_counts
                                    ):
                                        self._subagent_invocation_counts[
                                            subagent_type
                                        ] = 0
                                    self._subagent_invocation_counts[
                                        subagent_type
                                    ] += 1
                                    invocation_number = (
                                        self._subagent_invocation_counts[
                                            subagent_type
                                        ]
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
                                        WSSubagentResultMessage(
                                            type="subagent_result",
                                            subagent_name=current_subagent_name
                                            or "subagent",
                                            content=subagent_content,
                                            invocation_id=current_invocation_id,
                                        ).model_dump(mode="json"),
                                    )

                                # Subagent completion
                                _publish(
                                    "agent_complete",
                                    WSAgentCompleteMessage(
                                        type="agent_complete",
                                        agent_type="subagent",
                                        invocation_id=current_invocation_id,
                                        agent_name=current_subagent_name,
                                    ).model_dump(mode="json"),
                                )

                                # Content reset after subagent
                                _publish(
                                    "content_reset",
                                    WSContentResetMessage(
                                        type="content_reset",
                                        reason="subagent_completed",
                                    ).model_dump(mode="json"),
                                )

                                current_subagent_name = None
                                current_invocation_id = None
                                task_initiating_main_invocation_id = None

                            # Generate new main invocation_id after tool completion
                            _old_invocation_id = main_invocation_id  # noqa: F841
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
                                result_content = {
                                    "command": tool_output.update
                                }

                            result_content = self._make_json_serializable(
                                result_content
                            )

                            if current_subagent_name is None:
                                tool_result_dict: dict[str, Any] = {
                                    "tool": tool_name,
                                    "success": True,
                                    "result": result_content,
                                    "error": None,
                                }
                                all_tool_results.append(tool_result_dict)

                                _publish(
                                    "tool_result",
                                    WSToolResultMessage(
                                        type="tool_result",
                                        tool=tool_name,
                                        result=jsonable_encoder(
                                            tool_result_dict
                                        ),
                                        invocation_id=current_invocation_id
                                        if current_subagent_name
                                        else main_invocation_id,
                                    ).model_dump(mode="json"),
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
                                    "error": (
                                        str(error) if error else "Unknown error"
                                    ),
                                }
                                all_tool_results.append(error_result_dict)

                                _publish(
                                    "tool_result",
                                    WSToolResultMessage(
                                        type="tool_result",
                                        tool=tool_name,
                                        result=jsonable_encoder(
                                            error_result_dict
                                        ),
                                        invocation_id=current_invocation_id
                                        if current_subagent_name
                                        else main_invocation_id,
                                    ).model_dump(mode="json"),
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

                    # Flush all remaining accumulated tokens after stream ends
                    for inv_id in list(_token_accumulator.keys()):
                        _flush_accumulated_tokens(inv_id)

                    break  # successful completion, exit retry loop

                except (
                    ConnectionResetError,
                    OSError,
                ) as stream_err:
                    if _retry_attempt < max_retries:
                        logger.warning(
                            f"Transient stream error (attempt "
                            f"{_retry_attempt + 1}/{max_retries + 1}), "
                            f"retrying in {retry_delay}s: {stream_err}"
                        )
                        await asyncio.sleep(retry_delay)
                        events_processed = 0
                    else:
                        logger.error(
                            f"Stream failed after {max_retries + 1} "
                            f"attempts: {stream_err}"
                        )
                        raise
                except Exception as stream_err:
                    # Check if it's a transient httpcore/httpx error by
                    # inspecting type name and module to avoid hard imports
                    err_type_name = type(stream_err).__name__
                    err_module = type(stream_err).__module__
                    is_transient = (
                        err_type_name == "ReadError"
                        and "httpcore" in err_module
                    ) or (
                        err_type_name == "RemoteProtocolError"
                        and "httpx" in err_module
                    )
                    if is_transient and _retry_attempt < max_retries:
                        logger.warning(
                            f"Transient stream error (attempt "
                            f"{_retry_attempt + 1}/{max_retries + 1}), "
                            f"retrying in {retry_delay}s: {stream_err}"
                        )
                        await asyncio.sleep(retry_delay)
                        events_processed = 0
                    else:
                        raise

        except Exception as e:
            graph_error = e  # capture for later persistence
            logger.error(f"Error in _run_agent_graph: {e}", exc_info=True)
            event_bus.publish(
                AgentEvent(
                    event_type="error",
                    data={"message": str(e), "code": 500},
                    timestamp=datetime.now(),
                )
            )
        finally:
            _flush_task.cancel()
            # Flush any remaining tokens (covers error path)
            for inv_id in list(_token_accumulator.keys()):
                _flush_accumulated_tokens(inv_id)
            clear_request_context()
            self.unregister_interrupt_node(session_id)

        # Save assistant messages to session
        try:
            invocation_ids_in_order = list(main_agent_segments.keys())
            total_main_segments = len(invocation_ids_in_order)
            assistant_msg = None

            for idx, inv_id in enumerate(invocation_ids_in_order):
                segment_content = "".join(main_agent_segments[inv_id])
                metadata = {
                    "invocation_id": inv_id,
                    "segment_index": idx,
                    "total_segments": total_main_segments,
                }

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
            WSAgentCompleteMessage(
                type="agent_complete",
                agent_type="main",
                invocation_id=main_invocation_id,
                agent_name="Assistant",
            ).model_dump(mode="json"),
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
                await exec_service._run_agent_graph(
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

                # Update execution tracking row
                execution.status = "completed"
                execution.completed_at = datetime.now()  # type: ignore[assignment]
                await db.commit()

                # Clear active_execution_id on session
                if db_session is not None:
                    db_session.active_execution_id = None
                    await db.commit()

            except Exception as e:
                logger.error(
                    f"Error in start_execution {execution_id}: {e}", exc_info=True
                )
                # Update execution tracking row with error
                try:
                    execution.status = "error"
                    execution.error_message = str(e)
                    execution.completed_at = datetime.now()  # type: ignore[assignment]
                    await db.commit()
                except Exception:
                    await db.rollback()

                # Clear active_execution_id on session (best-effort)
                if db_session is not None:
                    try:
                        db_session.active_execution_id = None
                        await db.commit()
                    except Exception:
                        pass

                # Publish error event
                event_bus.publish(
                    AgentEvent(
                        event_type="error",
                        data={"message": str(e), "code": 500},
                        timestamp=datetime.now(),
                    )
                )

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
                        timestamp=datetime.now(),
                    )
                )

                raise
            finally:
                # Clean up the event bus from runner_manager only if we created it
                if should_remove_bus:
                    runner_manager.remove_bus(execution_id)

        return execution_id

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

        Context: Project and temporal context are enforced at the tool level via ToolContext,
        not in the system prompt. This provides maximum security by preventing prompt injection
        attacks from bypassing constraints. The system prompt provides the LLM with awareness
        of context for better responses, but enforcement happens at the tool level.

        The LLM has no control over temporal parameters (as_of, branch_name, branch_mode) or
        project_id. These are applied automatically by tools based on the session context.

        Args:
            base_prompt: Base system prompt
            project_id: Optional project ID for project-scoped queries
            as_of: Optional historical date for temporal queries (unused in prompt)
            branch_name: Optional branch name for temporal queries (unused in prompt)
            branch_mode: Optional branch mode for temporal queries (unused in prompt)
            context: Optional context dictionary with type, id, and name

        Returns:
            Base system prompt with context information (temporal enforcement
            happens at tool level via ToolContext)
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
            elif context_type == "project" and context_name:
                context_sections.append(
                    f"This conversation is about the project: {context_name}. "
                    f"Context is scoped to this project (ID: {context.get('id', project_id)}). "
                    "Use project-scoped tools to query data within this project. "
                    "The user's access is limited to this project's data. "
                    "Use get_project_context tool to query project details. "
                    "Project scope is locked for this session - you cannot switch to other projects."
                )
            elif context_type == "wbe" and context_name:
                context_sections.append(
                    f"This conversation is about the Work Breakdown Element (WBE): {context_name}. "
                    f"WBE ID: {context.get('id')}. "
                    f"Parent project ID: {context.get('project_id', project_id)}. "
                    "Focus your responses on this specific WBE. "
                    "Use WBE-scoped tools to query and analyze this element."
                )
            elif context_type == "cost_element" and context_name:
                context_sections.append(
                    f"This conversation is about the Cost Element: {context_name}. "
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
                f"Use branch-aware tools to query and modify data in this branch."
            )
        elif as_of:
            context_sections.append(
                f"[TEMPORAL CONTEXT]\n"
                f"You are viewing historical data as of {as_of.strftime('%B %d, %Y at %I:%M %p')}. "
                f"Use time-travel tools to query data at this point in time. "
                f"Note: Historical views are read-only."
            )

        # Combine base prompt with context sections
        if context_sections:
            return base_prompt + "\n\n" + "\n\n".join(context_sections)

        # Return base prompt without context additions
        # Temporal and project enforcement happens at tool level via ToolContext
        # This provides maximum security against prompt injection attacks
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
                messages.append(AIMessage(content=msg.content))
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
            logger.debug(f"_make_json_serializable: string size={obj_size:,} chars")
            # Skip JSON parsing for very large strings to prevent CPU spikes
            if obj_size > 100_000:  # 100KB limit
                return obj
            # Try to parse JSON strings back to objects
            # This handles stringified JSON from ToolMessage.content
            try:
                import json

                parsed = json.loads(obj)
                # Recursively process parsed object to handle nested structures
                return self._make_json_serializable(parsed)
            except (json.JSONDecodeError, TypeError):
                # Not valid JSON, return as-is
                return obj
        elif isinstance(obj, (int, float, bool, type(None))):
            return obj
        else:
            # For other types, try string conversion
            return str(obj)

    # Store reference to InterruptNode for approval handling
    # Key: session_id, Value: InterruptNode instance
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

            if self._is_websocket_connected(websocket):
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
