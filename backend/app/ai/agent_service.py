"""LangGraph Agent Service for conversation orchestration.

Uses LangGraph StateGraph for conversation flow with tool calling loop.
"""

import asyncio
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Literal
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
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketState

from app.ai.deep_agent_orchestrator import DeepAgentOrchestrator
from app.ai.graph import create_graph
from app.ai.telemetry import (
    initialize_telemetry,
    trace_context,
    trace_subagent_delegation,
)
from app.ai.token_buffer import TokenBuffer, TokenBufferManager
from app.ai.tools import ToolContext, create_project_tools
from app.ai.tools.interrupt_node import InterruptNode
from app.ai.tools.session_manager import ToolSessionManager
from app.ai.tools.types import ExecutionMode
from app.core.config import settings
from app.models.domain.ai import (
    AIAssistantConfig,
    AIConversationSession,
    AIProvider,
)
from app.models.schemas.ai import (
    AIChatResponse,
    AIConversationMessagePublic,
    WSAgentCompleteMessage,
    WSCompleteMessage,
    WSContentResetMessage,
    WSErrorMessage,
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

    @staticmethod
    def _is_websocket_connected(websocket: WebSocket) -> bool:
        """Check if WebSocket is still connected.

        Args:
            websocket: WebSocket connection to check

        Returns:
            True if WebSocket is connected, False otherwise
        """
        return websocket.client_state != WebSocketState.DISCONNECTED

    @property
    def config_service(self) -> AIConfigService:
        """Get or create the AI config service.

        Returns:
            AIConfigService instance for database operations
        """
        if self._config_service is None:
            self._config_service = AIConfigService(self.session)
        return self._config_service

    async def _get_llm_client_config(self, model_id: UUID) -> tuple[dict[str, Any], str, str]:
        """Get LLM client configuration, model name, and provider type for a model.

        Context: Internal helper to resolve the configuration for LangChain's ChatOpenAI.
        Returns configuration dict instead of a client to allow LangChain to create
        its own properly initialized client.

        Args:
            model_id: UUID of the AI model to instantiate

        Returns:
            A tuple containing the client configuration dict, the target model name, and provider type

        Raises:
            ValueError: If the model or its associated provider cannot be found
        """
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
        return client_config, str(model.model_id), provider.provider_type

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
        return ChatOpenAI(
            **client_config,
            model=model_name,
            temperature=temperature or 0.0,
            max_tokens=max_tokens or 2000,
        )

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

        Returns:
            Tuple of (compiled_graph, interrupt_node) where interrupt_node may be None

        Note:
            This is an alternative to create_graph() that uses the Deep Agents SDK
            for planning and subagent delegation. Falls back to create_graph() if
            Deep Agents SDK is not available or encounters errors.

            InterruptNode is integrated via BackcastSecurityMiddleware to handle
            approvals for HIGH/CRITICAL risk tools in standard mode.
        """
        try:
            # Create InterruptNode first (needed for middleware)
            interrupt_node = None
            if websocket and session_id and available_tools:
                # Pass available_tools so InterruptNode can check risk levels
                interrupt_node = InterruptNode(available_tools, tool_context, websocket, session_id)

            # Use pre-configured LLM (ChatOpenAI) instead of model string
            # This ensures the Deep Agent SDK uses our custom configuration (Z.AI base URL, API key)
            logger.info(f"Creating Deep Agent with pre-configured LLM, subagents={enable_subagents}")

            # Log graph creation start
            graph_creation_start = time.time()
            logger.info(
                f"[GRAPH_CREATION_START] _create_deep_agent_graph | "
                f"session_id={session_id} | "
                f"enable_subagents={enable_subagents} | "
                f"provider_type={provider_type} | "
                f"model_name={model_name}"
            )

            orchestrator = DeepAgentOrchestrator(
                model=llm,  # Pass the ChatOpenAI instance directly
                context=tool_context,
                system_prompt=assistant_config.system_prompt or DEFAULT_SYSTEM_PROMPT,
                enable_subagents=enable_subagents,
                interrupt_node=interrupt_node,  # Pass InterruptNode for approval handling
            )

            # Filter tools by assistant config
            allowed_tools = assistant_config.allowed_tools
            logger.info(f"DEBUG: assistant_config.allowed_tools = {allowed_tools}")
            if allowed_tools is not None:
                logger.info(f"DEBUG: allowed_tools count = {len(allowed_tools)}, first few: {allowed_tools[:3]}")

            # Create agent with orchestrator
            graph = orchestrator.create_agent(
                allowed_tools=allowed_tools,
            )
            logger.info("Deep Agent graph created successfully")

            # Log graph creation complete
            graph_creation_duration_ms = (time.time() - graph_creation_start) * 1000
            logger.info(
                f"[GRAPH_CREATION_COMPLETE] _create_deep_agent_graph | "
                f"duration_ms={graph_creation_duration_ms:.2f} | "
                f"session_id={session_id} | "
                f"graph_type={type(graph).__name__}"
            )

            return graph, interrupt_node

        except ImportError:
            # Deep Agents SDK not available, fall back to LangGraph
            logger.warning("Deep Agents SDK not available, falling back to LangGraph")
            return create_graph(llm, create_project_tools(tool_context), tool_context, websocket, session_id)
        except Exception as e:
            # Error creating Deep Agent, fall back to LangGraph
            logger.error(f"Error creating Deep Agent: {e}, falling back to LangGraph")
            return create_graph(llm, create_project_tools(tool_context), tool_context, websocket, session_id)

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
            }
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

        # Create tools
        # Fetch user to get their role for RBAC
        # Use UserService to properly handle temporal versioning
        from app.services.user import UserService

        user_service = UserService(self.session)
        user = await user_service.get_user(user_id)
        user_role = user.role if user else "guest"

        tool_context = ToolContext(self.session, str(user_id), user_role=user_role)
        available_tools = create_project_tools(tool_context)
        tools_dict = {tool.name: tool for tool in available_tools}

        # Filter tools based on assistant config
        if assistant_config.allowed_tools is not None:
            tools_dict = {
                name: tool
                for name, tool in tools_dict.items()
                if name in assistant_config.allowed_tools
            }

        # Create graph with context for RBAC
        graph, _interrupt_node = create_graph(llm=llm, tools=list(tools_dict.values()), context=tool_context)

        # Extract recursion_limit from assistant config with fallback to default
        recursion_limit = assistant_config.recursion_limit if assistant_config.recursion_limit is not None else 25

        # Invoke the graph
        # Note: Task-local sessions are created per tool execution and cleaned up below
        try:
            result = await graph.ainvoke(
                input_state={
                    "messages": history,
                    "tool_call_count": 0,
                    "next": "agent",
                },
                config={
                    "recursion_limit": recursion_limit,
                    "configurable": {"thread_id": str(session_id)}
                },
            )
        finally:
            # Clean up any remaining task-local sessions after graph execution
            # This ensures sessions are properly removed even if tools didn't clean up
            try:
                await ToolSessionManager.commit()
                logger.debug(f"Cleaned up task-local sessions after graph invocation for session {session_id}")
            except Exception as cleanup_error:
                logger.debug(f"No task-local sessions to clean up or cleanup failed: {cleanup_error}")
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
                    tool_calls_data.append({
                        "id": tc.get("id", ""),
                        "name": tc.get("name", ""),
                        "args": tc.get("args", {}),
                    })
            # Note: Tool messages are not directly accessible from the result
            # In a real implementation, you might want to track these separately

        # Save assistant message to session
        # Convert AIMessage content to string (can be str | list)
        content_str = (
            final_message.content
            if isinstance(final_message.content, str)
            else str(final_message.content) if final_message.content else ""
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

    async def chat_stream(
        self,
        message: str,
        assistant_config: AIAssistantConfig,
        session_id: UUID | None,
        user_id: UUID,
        websocket: WebSocket,
        db: AsyncSession,
        title: str | None = None,
        project_id: UUID | None = None,
        branch_id: UUID | None = None,
        as_of: datetime | None = None,
        branch_name: str | None = None,
        branch_mode: Literal["merged", "isolated"] | None = None,
        execution_mode: ExecutionMode = ExecutionMode.STANDARD,
        session_holder: Any | None = None,
    ) -> None:
        """Process a chat message using LangGraph with streaming response.

        Context: Streaming variant of chat() that sends tokens via WebSocket as they arrive.
                Uses LangGraph's astream_events() for event-based streaming with proper
                token, tool call, and tool result handling. Persists the complete message
                to database after streaming completes.

        Args:
            message: The user's input message
            assistant_config: Configuration defining the model and allowed tools
            session_id: Optional existing session ID to continue. If None, a new session is created
            user_id: ID of the user sending the message
            websocket: WebSocket connection for streaming responses
            db: Database session for persistence
            title: Optional title for the session (only used when creating a new session)
            project_id: Optional project context UUID for the session
            branch_id: Optional branch or change order context UUID for the session
            as_of: Optional historical date for temporal queries
            branch_name: Optional branch name for temporal queries
            branch_mode: Optional branch mode for temporal queries ("merged" or "isolated")
            execution_mode: Execution mode for tool filtering (safe/standard/expert)
            session_holder: Optional mutable container to update with new session_id

        Returns:
            None (communicates via WebSocket)

        Raises:
            ValueError: If session creation fails
        """
        # Get or create session
        db_session: AIConversationSession | None
        if session_id:
            db_session = await self.config_service.get_session(session_id)
            if not db_session:
                raise ValueError(f"Session {session_id} not found")
        else:
            # Create new session with context
            db_session = await self.config_service.create_session(
                user_id=user_id,
                assistant_config_id=assistant_config.id,
                title=title,
                project_id=project_id,
                branch_id=branch_id,
            )
            session_id = db_session.id
            # Update session_holder so caller can track the new session_id
            if session_holder is not None:
                session_holder.value = session_id
        if not session_id:
            raise ValueError("Failed to create session")

        # Log chat stream entry with session context
        logger.info(
            f"[CHAT_STREAM_ENTRY] chat_stream | "
            f"session_id={session_id} | "
            f"user_id={user_id} | "
            f"assistant_id={assistant_config.id} | "
            f"execution_mode={execution_mode.value} | "
            f"project_id={project_id} | "
            f"branch_id={branch_id} | "
            f"as_of={as_of} | "
            f"branch_name={branch_name} | "
            f"branch_mode={branch_mode}"
        )

        # Add user message to session
        _ = await self.config_service.add_message(
            session_id=session_id,
            role="user",
            content=message,
        )
        await db.commit()

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

        # Create tools
        # Fetch user to get their role for RBAC
        # Use UserService to properly handle temporal versioning
        from app.services.user import UserService

        user_service = UserService(db)
        user = await user_service.get_user(user_id)
        user_role = user.role if user else "guest"

        tool_context = ToolContext(
            db,
            str(user_id),
            user_role=user_role,
            project_id=str(project_id) if project_id else None,
            branch_id=str(branch_id) if branch_id else None,
            as_of=as_of,
            branch_name=branch_name,
            branch_mode=branch_mode,
            execution_mode=execution_mode,
        )
        # DEBUG: Log execution mode for diagnostics
        logger.info(f"DEBUG: Creating ToolContext with execution_mode={execution_mode.value} for user_id={user_id}")
        available_tools = create_project_tools(tool_context)
        tools_dict = {tool.name: tool for tool in available_tools}

        # Filter tools based on assistant config
        if assistant_config.allowed_tools is not None:
            tools_dict = {
                name: tool
                for name, tool in tools_dict.items()
                if name in assistant_config.allowed_tools
            }

        # Create graph with Deep Agent SDK for planning and subagent delegation
        # Falls back to regular LangGraph if Deep Agent SDK fails
        graph, interrupt_node = await self._create_deep_agent_graph(
            llm=llm,
            tool_context=tool_context,
            assistant_config=assistant_config,
            websocket=websocket,
            session_id=session_id,
            enable_subagents=True,
            provider_type=provider_type,
            model_name=model_name,
            available_tools=available_tools,
        )
        logger.info(f"Created graph: {type(graph).__name__}")

        # Register InterruptNode for approval handling if created
        if interrupt_node is not None:
            self.register_interrupt_node(session_id, interrupt_node)

        # Extract recursion_limit from assistant config with fallback to default
        recursion_limit = assistant_config.recursion_limit if assistant_config.recursion_limit is not None else 25

        # Initialize token buffer manager
        buffer_manager = TokenBufferManager(
            flush_interval_ms=settings.AI_TOKEN_BUFFER_INTERVAL_MS,
            max_buffer_size=settings.AI_TOKEN_BUFFER_MAX_SIZE,
            enabled=settings.AI_TOKEN_BUFFER_ENABLED,
        )

        async def flush_buffer(key: str, buffer: "TokenBuffer") -> None:
            """Flush callback for buffer manager."""
            if not buffer.is_empty() and self._is_websocket_connected(websocket):
                try:
                    # Extract invocation_id from buffer for both main agent and subagents
                    invocation_id = buffer.invocation_id

                    msg_data = WSTokenBatchMessage(
                        type="token_batch",
                        tokens=buffer.get_content(),
                        session_id=buffer.session_id or session_id,
                        source=buffer.source,
                        subagent_name=buffer.subagent_name,
                        invocation_id=invocation_id,
                    ).model_dump(mode="json")
                    logger.info(f"[TOKEN_BATCH] Sending: source={buffer.source}, invocation_id={invocation_id}, tokens_length={len(buffer.get_content())}")
                    await websocket.send_json(msg_data)
                except Exception as e:
                    logger.warning(f"Failed to send token batch: {e}")

        buffer_manager.set_flush_callback(flush_buffer)  # type: ignore[arg-type]
        await buffer_manager.start()

        # Stream using astream_events
        accumulated_content = ""
        all_tool_calls: list[dict[str, Any]] = []
        all_tool_results: list[dict[str, Any]] = []

        # Track main agent content segments by invocation_id for separate message persistence
        # This preserves the bubble separation in the frontend after response completes
        main_agent_segments: dict[str, list[str]] = {}

        # Track subagent messages by the main agent invocation that triggered them
        # This allows us to save messages in conversational order: main segment → subagents → next main segment
        from collections import defaultdict
        subagent_messages_by_main_invocation: dict[str, list[dict[str, Any]]] = defaultdict(list)

        # Track step count for progress indicators
        current_step = 0
        estimated_total_steps = None

        # Track timing for summary log
        stream_start_time = time.time()
        total_tokens = 0
        tool_calls_count = 0

        # Track subagent name and invocation_id for result reporting
        current_subagent_name: str | None = None
        current_invocation_id: str | None = None

        # Track main agent invocation_id for separating main agent content before/after subagents
        main_invocation_id: str | None = None

        # Track whether the current tool was initiated by the main agent (vs subagent)
        main_agent_initiated_tool: bool = False

        # Track the main_invocation_id that initiated the task tool (for subagent result association)
        task_initiating_main_invocation_id: str | None = None

        try:
            logger.info(f"Starting astream_events for session {session_id}")

            # Send thinking event to indicate agent is processing
            if self._is_websocket_connected(websocket):
                try:
                    await websocket.send_json(
                        WSThinkingMessage().model_dump(mode="json")
                    )
                    logger.info("Sent WebSocket thinking event")
                except Exception:
                    logger.debug("Failed to send thinking event, WebSocket may be closed")

            async def _consume_stream() -> None:
                nonlocal current_step, estimated_total_steps, current_subagent_name, current_invocation_id, main_invocation_id, total_tokens, tool_calls_count, accumulated_content, main_agent_initiated_tool, task_initiating_main_invocation_id

                # Generate initial main agent invocation_id at stream start
                main_invocation_id = str(uuid.uuid4())

                async for event in graph.astream_events(
                    {
                        "messages": history,
                        "tool_call_count": 0,
                        "next": "agent",
                    },
                    config={
                        "recursion_limit": recursion_limit,
                        "configurable": {"thread_id": str(session_id)}
                    },
                    version="v1",
                ):
                    event_type = event.get("event", "")
                    data = event.get("data", {})

                    # Handle token streaming
                    if event_type == "on_chat_model_stream":
                        chunk = data.get("chunk")
                        if chunk:
                            # AIMessageChunk objects support .text attribute for simple text content
                            # For more complex content with multiple blocks, we iterate through content_blocks
                            content = ""
                            if hasattr(chunk, "text"):
                                content = chunk.text
                            elif hasattr(chunk, "content"):
                                # Fallback to content attribute if text is not available
                                content = str(chunk.content)

                            if content:
                                # Track main agent content per invocation_id for separate message persistence
                                if current_subagent_name is None:
                                    # Main agent token - accumulate per invocation_id
                                    if main_invocation_id not in main_agent_segments:
                                        main_agent_segments[main_invocation_id] = []
                                    main_agent_segments[main_invocation_id].append(content)

                                # Legacy: also accumulate all content for backward compatibility
                                accumulated_content += content
                                total_tokens += len(content)
                                if self._is_websocket_connected(websocket):
                                    invocation_id_to_use = current_invocation_id if current_subagent_name else main_invocation_id
                                    logger.debug(f"Adding token: source={'subagent' if current_subagent_name else 'main'}, invocation_id={invocation_id_to_use}")
                                    buffer_manager.add_token(
                                        token=content,
                                        session_id=str(session_id),
                                        source="subagent" if current_subagent_name else "main",
                                        subagent_name=current_subagent_name,
                                        invocation_id=invocation_id_to_use,
                                    )

                    # Handle tool start
                    elif event_type == "on_tool_start":
                        tool_name = event.get("name", "")
                        tool_input = data.get("input", {})
                        tool_calls_count += 1

                        # Track whether this tool was initiated by the main agent
                        main_agent_initiated_tool = (current_subagent_name is None)

                        # Flush main agent buffer before tool execution
                        # This ensures main agent content before the tool appears in its own bubble
                        if current_subagent_name is None:
                            logger.info(f"[TOOL_START] Flushing main agent buffer before tool='{tool_name}', invocation_id={main_invocation_id}")
                            await buffer_manager.flush_agent(
                                source="main",
                                invocation_id=main_invocation_id,
                            )

                        # Track subagent name and invocation_id for result reporting
                        if tool_name == "task":
                            current_subagent_name = tool_input.get("subagent_type") if isinstance(tool_input, dict) else None
                            current_invocation_id = str(uuid.uuid4())
                            # Save the main_invocation_id that initiated this task tool
                            # This will be used to associate the subagent result with the correct main segment
                            task_initiating_main_invocation_id = main_invocation_id

                        # Increment step counter for all tool executions
                        current_step += 1

                        # Detect Deep Agent planning (write_todos tool)
                        if tool_name == "write_todos" and self._is_websocket_connected(websocket):
                            try:
                                # Extract plan from tool input
                                plan = tool_input.get("plan") if isinstance(tool_input, dict) else None
                                # Extract steps if available
                                steps = None
                                if isinstance(tool_input, dict):
                                    raw_steps = tool_input.get("steps")
                                    if isinstance(raw_steps, list):
                                        steps = [
                                            {"text": str(s), "done": False} for s in raw_steps
                                        ]
                                        # Update estimated total based on planning steps
                                        estimated_total_steps = len(steps)

                                await websocket.send_json(
                                    WSPlanningMessage(
                                        type="planning",
                                        plan=plan,
                                        steps=steps,
                                        step_number=current_step,
                                        total_steps=estimated_total_steps,
                                        invocation_id=main_invocation_id,
                                    ).model_dump(mode="json")
                                )
                                logger.info(f"Sent WebSocket planning event: plan={plan}, steps={len(steps) if steps else 0}")
                            except Exception:
                                logger.debug("Failed to send planning event")
                            pass

                        # Detect Deep Agent subagent delegation (task tool)
                        elif tool_name == "task" and self._is_websocket_connected(websocket):
                            try:
                                # Extract subagent_type and description from tool input
                                subagent_type = tool_input.get("subagent_type") if isinstance(tool_input, dict) else None
                                description = tool_input.get("description") if isinstance(tool_input, dict) else None

                                logger.info(f"[SUBAGENT_DELEGATION] Main agent delegating to subagent '{subagent_type}': {description}")

                                # Flush main agent buffer before switching to subagent
                                await buffer_manager.flush_agent(source="main")

                                if subagent_type:
                                    # Add telemetry span for subagent delegation
                                    with trace_subagent_delegation(subagent_type, description):
                                        # The actual tool execution happens outside this context
                                        # This span marks when the delegation occurs
                                        pass

                                    await websocket.send_json(
                                        WSSubagentMessage(
                                            type="subagent",
                                            subagent=subagent_type,
                                            message=description,
                                            step_number=current_step,
                                            total_steps=estimated_total_steps,
                                            invocation_id=current_invocation_id,
                                        ).model_dump(mode="json")
                                    )
                                    logger.info(f"Subagent delegation: {subagent_type}")
                            except Exception:
                                logger.debug("Failed to send subagent event")
                            pass

                        # Send standard tool_call message with step information
                        if self._is_websocket_connected(websocket):
                            try:
                                await websocket.send_json(
                                    WSToolCallMessage(
                                        type="tool_call",
                                        tool=tool_name,
                                        args=tool_input,
                                        step_number=current_step,
                                        total_steps=estimated_total_steps,
                                        invocation_id=current_invocation_id if current_subagent_name else main_invocation_id,
                                    ).model_dump(mode="json")
                                )
                            except Exception:
                                # WebSocket may be closed
                                logger.warning("Failed to send tool_call, WebSocket may be closed")
                                pass
                        else:
                            logger.debug("WebSocket not connected, skipping tool_call send")

                    # Handle tool end
                    elif event_type == "on_tool_end":
                        tool_name = event.get("name", "")

                        # Send subagent result when task tool completes
                        if tool_name == "task":
                            # Get subagent content from event output (no longer intercepted by middleware)
                            tool_output = data.get("output", "")
                            subagent_content = ""

                            # Extract content from various output formats
                            if isinstance(tool_output, ToolMessage):
                                # ToolMessage.content can be str | list[str | dict[Any, Any]]
                                raw_content = tool_output.content
                                subagent_content = raw_content if isinstance(raw_content, str) else str(raw_content)
                            elif isinstance(tool_output, Command):
                                # Command objects from langgraph subagent delegation
                                # The subagent's response is in the update field
                                update_dict = tool_output.update
                                if isinstance(update_dict, dict):
                                    # Extract messages from the update
                                    messages = update_dict.get("messages", [])
                                    if messages:
                                        # Get the last message which is the subagent's response
                                        last_msg = messages[-1]
                                        if isinstance(last_msg, dict):
                                            subagent_content = last_msg.get("content", "")
                                        elif hasattr(last_msg, "content"):
                                            subagent_content = str(last_msg.content)
                                        else:
                                            subagent_content = str(last_msg)
                            elif isinstance(tool_output, dict) and "content" in tool_output:
                                subagent_content = tool_output["content"]
                            elif isinstance(tool_output, str):
                                subagent_content = tool_output

                            # Ensure subagent_content is a string
                            if not isinstance(subagent_content, str):
                                subagent_content = str(subagent_content)

                            if subagent_content:
                                # Track subagent message for later persistence in correct order
                                # The subagent should be associated with the CURRENT main_invocation_id
                                # (the one that will become "old" after regeneration below)
                                subagent_type = current_subagent_name or "subagent"
                                if subagent_type not in self._subagent_invocation_counts:
                                    self._subagent_invocation_counts[subagent_type] = 0
                                self._subagent_invocation_counts[subagent_type] += 1
                                invocation_number = self._subagent_invocation_counts[subagent_type]

                                # Store subagent message with the main_invocation_id that initiated the task
                                # Use task_initiating_main_invocation_id to ensure correct association
                                # This ensures subagent messages are saved after the main segment that triggered them
                                target_invocation_id = task_initiating_main_invocation_id or main_invocation_id
                                subagent_messages_by_main_invocation[target_invocation_id].append({
                                    "role": "assistant",
                                    "content": subagent_content,
                                    "message_metadata": {
                                        "subagent_name": subagent_type,
                                        "invocation_number": invocation_number,
                                    } if current_subagent_name else None,
                                })
                                # Send WebSocket message
                                if self._is_websocket_connected(websocket):
                                    try:
                                        await websocket.send_json(
                                            WSSubagentResultMessage(
                                                type="subagent_result",
                                                subagent_name=current_subagent_name or "subagent",
                                                content=subagent_content,
                                                invocation_id=current_invocation_id,
                                            ).model_dump(mode="json")
                                        )
                                        logger.info(
                                            f"Sent subagent result: name={current_subagent_name}, "
                                            f"content_length={len(subagent_content)}"
                                        )
                                    except Exception:
                                        logger.debug("Failed to send subagent result, WebSocket may be closed")

                            # Flush subagent buffer
                            await buffer_manager.flush_agent(
                                source="subagent",
                                subagent_name=current_subagent_name,
                                invocation_id=current_invocation_id,
                            )

                            # Send subagent completion message
                            if self._is_websocket_connected(websocket):
                                try:
                                    await websocket.send_json(
                                        WSAgentCompleteMessage(
                                            type="agent_complete",
                                            agent_type="subagent",
                                            invocation_id=current_invocation_id,
                                            agent_name=current_subagent_name,
                                        ).model_dump(mode="json")
                                    )
                                    logger.debug(f"Sent subagent completion: invocation_id={current_invocation_id}")
                                except Exception:
                                    logger.debug("Failed to send subagent completion, WebSocket may be closed")

                            # Send content reset to signal frontend to start new main agent bubble
                            if self._is_websocket_connected(websocket):
                                try:
                                    await websocket.send_json(
                                        WSContentResetMessage(
                                            type="content_reset",
                                            reason="subagent_completed",
                                        ).model_dump(mode="json")
                                    )
                                    logger.debug("Sent content reset message after subagent completion")
                                except Exception:
                                    logger.debug("Failed to send content reset, WebSocket may be closed")

                            # Note: We NO LONGER reset accumulated_content here
                            # The main agent's thoughts persist across subagent executions
                            # to enable progressive acknowledgment and final synthesis

                            current_subagent_name = None
                            current_invocation_id = None
                            task_initiating_main_invocation_id = None

                        # Generate new invocation_id for main agent's continuation after ANY tool completion
                        # This includes tools initiated by main agent AND tools initiated by subagents
                        # Every tool completion creates a new main agent bubble
                        # Note: old_invocation_id tracked for potential future use in debugging
                        _old_invocation_id = main_invocation_id  # noqa: F841 (tracked for debugging)
                        main_invocation_id = str(uuid.uuid4())

                        tool_output = data.get("output", "")

                        # Extract content from ToolMessage if present
                        result_content = tool_output
                        if isinstance(tool_output, ToolMessage):
                            # ToolMessage objects have a content attribute that may be str, list, or dict
                            result_content = tool_output.content
                        elif isinstance(tool_output, dict) and "content" in tool_output:
                            # Sometimes output is a dict with content field
                            result_content = tool_output["content"]
                        elif isinstance(tool_output, Command):
                            # Command objects from langgraph subagent delegation - convert to dict
                            result_content = {"command": tool_output.update}

                        # Convert to JSON-serializable format (handles nested ToolMessage objects)
                        result_content = self._make_json_serializable(result_content)

                        # Record tool result
                        tool_result: dict[str, Any] = {
                            "tool": tool_name,
                            "success": True,
                            "result": result_content,
                            "error": None,
                        }
                        all_tool_results.append(tool_result)

                    # Handle tool error
                    elif event_type == "on_tool_error":
                        tool_name = event.get("name", "")
                        error = data.get("error")

                        # Record tool error
                        error_result: dict[str, Any] = {
                            "tool": tool_name,
                            "success": False,
                            "result": None,
                            "error": str(error) if error else "Unknown error",
                        }
                        all_tool_results.append(error_result)

                        if self._is_websocket_connected(websocket):
                            try:
                                msg_data = WSToolResultMessage(
                                    type="tool_result",
                                    tool=tool_name,
                                    result=jsonable_encoder(tool_result),
                                    invocation_id=current_invocation_id if current_subagent_name else main_invocation_id,
                                ).model_dump(mode="json")
                                logger.debug(f"Sending tool_result: tool={tool_name}, data_keys={list(tool_result.keys()) if isinstance(tool_result, dict) else 'not_dict'}, result_type={type(tool_result.get('result')).__name__ if isinstance(tool_result, dict) and 'result' in tool_result else 'unknown'}")
                                await websocket.send_json(msg_data)
                            except Exception as e:
                                # WebSocket may be closed or serialization error
                                logger.warning(f"Failed to send tool_result for {tool_name}: {e}")
                                pass
                        else:
                            logger.debug("WebSocket not connected, skipping tool_result send")

                    # Handle completion
                    elif event_type == "on_end":
                        output = data.get("output", {})
                        messages = output.get("messages", [])

                        # Extract tool calls from the final messages
                        for msg in messages:
                            if isinstance(msg, AIMessage) and msg.tool_calls:
                                # Convert ToolCall objects to dict format
                                for tc in msg.tool_calls:
                                    all_tool_calls.append({
                                        "id": tc.get("id", ""),
                                        "name": tc.get("name", ""),
                                        "args": tc.get("args", {}),
                                    })

                        logger.info(f"Graph execution completed for session {session_id}")

            try:
                await asyncio.wait_for(_consume_stream(), timeout=300)
            except TimeoutError:
                logger.error(f"Streaming timeout for session {session_id}")
                if self._is_websocket_connected(websocket):
                    try:
                        await websocket.send_json(
                            WSErrorMessage(
                                type="error",
                                message="Response generation timed out after 5 minutes",
                                code=408,
                            ).model_dump(mode="json")
                        )
                    except Exception:
                        pass

            # CRITICAL: Check for tool errors and rollback session if needed
            # Tool execution failures can leave the database session in a rolled back state
            # We need to rollback explicitly to restore the session to a usable state
            tool_errors_occurred = any(not tr["success"] for tr in all_tool_results)
            if tool_errors_occurred:
                logger.warning(
                    f"Tool errors occurred during execution for session {session_id}. "
                    f"Rolling back database session to restore usable state."
                )
                try:
                    await db.rollback()
                    logger.info(f"Database session rolled back successfully for session {session_id}")
                except Exception as rollback_error:
                    logger.error(f"Error during session rollback: {rollback_error}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in chat_stream astream_events: {e}", exc_info=True)
            # Rollback session on any exception to ensure clean state
            try:
                await db.rollback()
            except Exception:
                pass  # Best effort rollback
            # Send error message via WebSocket
            if self._is_websocket_connected(websocket):
                try:
                    await websocket.send_json(
                        WSErrorMessage(
                            type="error",
                            message=f"An error occurred: {str(e)}",
                            code=500,
                        ).model_dump(mode="json")
                    )
                except Exception:
                    # WebSocket may be closed
                    pass
            else:
                logger.debug("WebSocket not connected, skipping error send")

        finally:
            self.unregister_interrupt_node(session_id)

        # Save assistant messages to session in conversational order
        # Order: main segment → its subagents → next main segment → its subagents, etc.
        # This preserves the correct conversational flow in the frontend after response completes
        # Wrap in try/except to handle any session state issues
        try:
            # Get invocation IDs in the order they were created (maintains chronological order)
            invocation_ids_in_order = list(main_agent_segments.keys())
            total_main_segments = len(invocation_ids_in_order)

            # Save messages in conversational order: main segment → subagents → main segment → subagents
            assistant_msg = None
            message_count = 0
            for idx, inv_id in enumerate(invocation_ids_in_order):
                # Save main agent segment
                segment_content = "".join(main_agent_segments[inv_id])

                # Add metadata to track invocation_id and order
                metadata = {
                    "invocation_id": inv_id,
                    "segment_index": idx,
                    "total_segments": total_main_segments,
                }

                # Only attach tool_calls and tool_results to the first main segment
                # This prevents duplication and maintains backward compatibility
                segment_tool_calls = all_tool_calls if idx == 0 and all_tool_calls else None
                segment_tool_results = all_tool_results if idx == 0 and all_tool_results else None

                logger.info(
                    f"[SAVE_MAIN_SEGMENT] Saving main segment {idx + 1}/{total_main_segments}: "
                    f"invocation_id={inv_id}, content_length={len(segment_content)}, "
                    f"has_tool_calls={segment_tool_calls is not None}"
                )

                segment_msg = await self.config_service.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=segment_content,
                    tool_calls=segment_tool_calls,
                    tool_results=segment_tool_results,
                    message_metadata=metadata,
                )
                await db.commit()
                await db.refresh(segment_msg)
                message_count += 1

                # Keep track of the last message for the completion message
                assistant_msg = segment_msg

                # Save subagent messages that were triggered by this main agent segment
                # These are already tracked in subagent_messages_by_main_invocation[inv_id]
                if inv_id in subagent_messages_by_main_invocation:
                    subagent_msgs = subagent_messages_by_main_invocation[inv_id]
                    logger.info(
                        f"[SAVE_SUBAGENT_MESSAGES] Saving {len(subagent_msgs)} subagent message(s) "
                        f"triggered by main segment invocation_id={inv_id}"
                    )

                    for subagent_msg_data in subagent_msgs:
                        subagent_msg = await self.config_service.add_message(
                            session_id=session_id,
                            **subagent_msg_data
                        )
                        await db.commit()
                        await db.refresh(subagent_msg)
                        message_count += 1

                        # Update assistant_msg to the last message (could be subagent)
                        assistant_msg = subagent_msg

                        logger.info(
                            f"[SAVE_SUBAGENT_MESSAGE] Saved subagent message: "
                            f"subagent_name={subagent_msg_data.get('message_metadata', {}).get('subagent_name')}, "
                            f"content_length={len(subagent_msg_data.get('content', ''))}"
                        )

            logger.info(
                f"[SAVE_COMPLETE] Saved {message_count} total messages to session {session_id} "
                f"({total_main_segments} main segments + {message_count - total_main_segments} subagent messages)"
            )
        except Exception as msg_error:
            logger.error(f"Error saving assistant messages to session {session_id}: {msg_error}", exc_info=True)
            # Rollback to ensure session is clean
            try:
                await db.rollback()
            except Exception:
                pass
            # Try to save messages again with clean session (without tool results if they caused issues)
            try:
                # Fallback: save as single message with accumulated content
                assistant_msg = await self.config_service.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=accumulated_content or "",
                    tool_calls=None,  # Don't include tool calls on retry
                    tool_results=None,  # Don't include tool results on retry
                    message_metadata=None,
                )
                await db.commit()
                await db.refresh(assistant_msg)
                logger.info(f"Successfully saved fallback message to session {session_id} after cleanup")
            except Exception as retry_error:
                logger.error(f"Failed to save message even after cleanup: {retry_error}", exc_info=True)
                # Continue anyway - we've done our best to save the state

        # Flush all remaining buffers before completion
        await buffer_manager.flush_all()

        # Stop the buffer manager to clean up background tasks
        # This ensures the background flush loop is properly terminated
        try:
            await buffer_manager.stop()
        except Exception as buffer_error:
            logger.warning(f"Error stopping buffer manager: {buffer_error}")
            # Continue anyway - buffers are already flushed

        # Send main agent completion message before final completion
        if self._is_websocket_connected(websocket):
            try:
                await websocket.send_json(
                    WSAgentCompleteMessage(
                        type="agent_complete",
                        agent_type="main",
                        invocation_id=main_invocation_id,
                        agent_name="Assistant",
                    ).model_dump(mode="json")
                )
                logger.debug(f"Sent main agent completion: invocation_id={main_invocation_id}")
            except Exception:
                logger.debug("Failed to send main agent completion, WebSocket may be closed")

        # Send complete message
        # Use the last message ID for the completion message (maintains backward compatibility)
        if self._is_websocket_connected(websocket) and assistant_msg:
            try:
                await websocket.send_json(
                    WSCompleteMessage(
                        type="complete",
                        session_id=session_id,
                        message_id=assistant_msg.id,
                    ).model_dump(mode="json")
                )
            except Exception:
                # WebSocket may be closed, but message is persisted
                logger.warning("WebSocket closed before sending complete message")
        elif not assistant_msg:
            logger.warning("No assistant message was saved, skipping completion message")
        else:
            logger.debug("WebSocket not connected, skipping complete send")

        # Log chat stream complete with metrics
        stream_duration_ms = (time.time() - stream_start_time) * 1000
        logger.info(
            f"[CHAT_STREAM_COMPLETE] chat_stream | "
            f"duration_ms={stream_duration_ms:.2f} | "
            f"session_id={session_id} | "
            f"message_id={assistant_msg.id if assistant_msg else 'N/A'} | "
            f"total_tokens={total_tokens} | "
            f"tool_calls_count={tool_calls_count} | "
            f"tool_results_count={len(all_tool_results)}"
        )

    def _build_system_prompt(
        self,
        base_prompt: str,
        project_id: UUID | None = None,
        as_of: datetime | None = None,
        branch_name: str | None = None,
        branch_mode: Literal["merged", "isolated"] | None = None,
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

        Returns:
            Base system prompt with project context information (temporal enforcement
            happens at tool level via ToolContext)
        """
        context_sections = []

        # Add project context awareness if in project scope
        if project_id:
            context_sections.append(
                f"You are operating in the context of a specific project (ID: {project_id}). "
                "Use project-scoped tools to query data within this project. "
                "The user's access is limited to this project's data. "
                "Use get_project_context tool to query project details. "
                "Project scope is locked for this session - you cannot switch to other projects."
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

        Args:
            session_id: The session ID corresponding to the current conversation

        Returns:
            List of LangChain BaseMessage instances (HumanMessage, AIMessage, SystemMessage)

        Raises:
            None
        """
        messages: list[BaseMessage] = []
        db_messages = await self.config_service.list_messages(session_id)
        for msg in db_messages:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
            elif msg.role == "tool":
                # Skip tool messages in history - they're implicit
                pass
        return messages

    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert non-JSON-serializable objects to JSON-serializable format.

        Handles ToolMessage, Command, and other LangChain/LangGraph objects
        that may be nested in tool results.

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
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            # For other types, try string conversion
            return str(obj)

    # Store reference to InterruptNode for approval handling
    # Key: session_id, Value: InterruptNode instance
    _interrupt_nodes: dict[UUID, "InterruptNode"] = {}

    def register_interrupt_node(self, session_id: UUID, interrupt_node: "InterruptNode") -> None:
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

    def register_approval_response(self, session_id: UUID, approval_id: str, approved: bool) -> bool:
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
        logger.info(f"Registered approval response for session {session_id}, approval_id={approval_id}, approved={approved}")
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
                logger.error(f"Failed to execute tool after approval for approval_id={approval_id}")
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
                    logger.debug(f"Sending tool_result after approval: tool={tool_result['tool']}, result_type={type(result.content).__name__}")
                    await websocket.send_json(msg_data)
                except Exception as e:
                    logger.warning(f"Failed to send tool_result after approval: {e}")
            else:
                logger.debug("WebSocket not connected, skipping tool_result send in resume")

            logger.info(f"Successfully resumed and executed tool for approval_id={approval_id}")
            return True

        except Exception as e:
            logger.error(f"Error resuming graph for approval_id={approval_id}: {e}", exc_info=True)
            return False
