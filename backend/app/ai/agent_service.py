"""LangGraph Agent Service for conversation orchestration.

Uses LangGraph StateGraph for conversation flow with tool calling loop.
"""

import logging
import os
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import WebSocket
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
from app.ai.tools import ToolContext, create_project_tools
from app.ai.tools.interrupt_node import InterruptNode
from app.ai.tools.types import ExecutionMode
from app.models.domain.ai import (
    AIAssistantConfig,
    AIConversationSession,
    AIProvider,
)
from app.models.schemas.ai import (
    AIChatResponse,
    AIConversationMessagePublic,
    WSCompleteMessage,
    WSErrorMessage,
    WSPlanningMessage,
    WSSubagentMessage,
    WSThinkingMessage,
    WSTokenMessage,
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

        Returns:
            Tuple of (compiled_graph, interrupt_node) where interrupt_node may be None

        Note:
            This is an alternative to create_graph() that uses the Deep Agents SDK
            for planning and subagent delegation. Falls back to create_graph() if
            Deep Agents SDK is not available or encounters errors.
        """
        try:
            # Use pre-configured LLM (ChatOpenAI) instead of model string
            # This ensures the Deep Agent SDK uses our custom configuration (Z.AI base URL, API key)
            logger.info(f"Creating Deep Agent with pre-configured LLM, subagents={enable_subagents}")

            orchestrator = DeepAgentOrchestrator(
                model=llm,  # Pass the ChatOpenAI instance directly
                context=tool_context,
                system_prompt=assistant_config.system_prompt or DEFAULT_SYSTEM_PROMPT,
                enable_subagents=enable_subagents,
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

            # Create InterruptNode for WebSocket approval flow
            # Deep Agents SDK uses interrupt_on for interrupts, but we keep
            # InterruptNode for WebSocket-based approval flow
            interrupt_node = None
            if websocket and session_id:
                interrupt_node = InterruptNode([], tool_context, websocket, session_id)

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
        if not session_id:
            raise ValueError("Failed to create session")

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
        )
        logger.info(f"Created graph: {type(graph).__name__}")

        # Register InterruptNode for approval handling if created
        if interrupt_node is not None:
            self.register_interrupt_node(session_id, interrupt_node)

        # Extract recursion_limit from assistant config with fallback to default
        recursion_limit = assistant_config.recursion_limit if assistant_config.recursion_limit is not None else 25

        # Stream using astream_events
        accumulated_content = ""
        all_tool_calls: list[dict[str, Any]] = []
        all_tool_results: list[dict[str, Any]] = []

        # Track step count for progress indicators
        current_step = 0
        estimated_total_steps = None

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
                            accumulated_content += content
                            if self._is_websocket_connected(websocket):
                                try:
                                    await websocket.send_json(
                                        WSTokenMessage(
                                            type="token",
                                            content=content,
                                            session_id=session_id,
                                        ).model_dump(mode="json")
                                    )
                                except Exception:
                                    # WebSocket may be closed
                                    logger.warning("Failed to send token, WebSocket may be closed")
                                    pass
                            else:
                                logger.debug("WebSocket not connected, skipping token send")

                # Handle tool start
                elif event_type == "on_tool_start":
                    tool_name = event.get("name", "")
                    tool_input = data.get("input", {})

                    # DEBUG: Log which tool is being called
                    if logger.isEnabledFor(20):  # INFO level
                        if tool_name not in ["write_todos", "task", "ls", "read_file", "write_file", "edit_file", "glob", "grep", "execute"]:
                            # Backcast tool being called - log if it's directly from main agent
                            logger.info(f"[TOOL_CALL] Tool '{tool_name}' being called (main agent or subagent)")
                        else:
                            logger.debug(f"[SDK_TOOL_CALL] SDK tool '{tool_name}' being called")

                    # WARNING: Detect if Backcast tool is being called without subagent delegation
                    # This should NOT happen when subagents are enabled
                    if tool_name not in ["write_todos", "task", "ls", "read_file", "write_file", "edit_file", "glob", "grep", "execute"]:
                        # Check if this happened right after a subagent delegation
                        # If not, it's the main agent trying to use tools directly
                        logger.warning(f"[UNEXPECTED_TOOL_CALL] Backcast tool '{tool_name}' being called. Main agent should delegate via task tool when subagents are enabled!")

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
                            await websocket.send_json(
                                WSToolResultMessage(
                                    type="tool_result",
                                    tool=tool_name,
                                    result=tool_result,
                                ).model_dump(mode="json")
                            )
                        except Exception:
                            # WebSocket may be closed
                            logger.warning("Failed to send tool_result, WebSocket may be closed")
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

        # Save assistant message to session
        # Wrap in try/except to handle any session state issues
        try:
            assistant_msg = await self.config_service.add_message(
                session_id=session_id,
                role="assistant",
                content=accumulated_content or "",
                tool_calls=all_tool_calls if all_tool_calls else None,
                tool_results=all_tool_results if all_tool_results else None,
            )
            await db.commit()
            await db.refresh(assistant_msg)
        except Exception as msg_error:
            logger.error(f"Error saving assistant message to session {session_id}: {msg_error}", exc_info=True)
            # Rollback to ensure session is clean
            try:
                await db.rollback()
            except Exception:
                pass
            # Try to save message again with clean session (without tool results if they caused issues)
            try:
                assistant_msg = await self.config_service.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=accumulated_content or "",
                    tool_calls=None,  # Don't include tool calls on retry
                    tool_results=None,  # Don't include tool results on retry
                )
                await db.commit()
                await db.refresh(assistant_msg)
                logger.info(f"Successfully saved message to session {session_id} after cleanup")
            except Exception as retry_error:
                logger.error(f"Failed to save message even after cleanup: {retry_error}", exc_info=True)
                # Continue anyway - we've done our best to save the state

        # Send complete message
        if self._is_websocket_connected(websocket):
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
        else:
            logger.debug("WebSocket not connected, skipping complete send")

        logger.info(
            f"Chat stream completed for session {session_id}, "
            f"message_id={assistant_msg.id}"
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
                await websocket.send_json(
                    WSToolResultMessage(
                        type="tool_result",
                        tool=tool_result["tool"],
                        result=tool_result,
                    ).model_dump(mode="json")
                )
            else:
                logger.debug("WebSocket not connected, skipping tool_result send in resume")

            logger.info(f"Successfully resumed and executed tool for approval_id={approval_id}")
            return True

        except Exception as e:
            logger.error(f"Error resuming graph for approval_id={approval_id}: {e}", exc_info=True)
            return False
