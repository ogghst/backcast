"""LangGraph Agent Service for conversation orchestration.

Uses LangGraph StateGraph for conversation flow with tool calling loop.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.graph import create_graph
from app.ai.llm_client import LLMClientFactory
from app.ai.tools import ToolContext, create_project_tools
from app.models.domain.ai import (
    AIAssistantConfig,
    AIConversationMessage,
    AIConversationSession,
)
from app.models.schemas.ai import (
    AIChatResponse,
    AIConversationMessagePublic,
    WSCompleteMessage,
    WSErrorMessage,
    WSTokenMessage,
    WSToolCallMessage,
    WSToolResultMessage,
)
from app.services.ai_config_service import AIConfigService

logger = logging.getLogger(__name__)


# Constants
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant for the Backcast EVS project budget management system.

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

    async def _get_llm_client(self, model_id: UUID) -> tuple[AsyncOpenAI, str]:
        """Get LLM client and model name for a model.

        Context: Internal helper to resolve the client factory for the configured provider.

        Args:
            model_id: UUID of the AI model to instantiate

        Returns:
            A tuple containing the instantiated LLM client and the target model name

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
        client = await LLMClientFactory.create_client(provider, config_service)
        return client, str(model.model_id)

    async def _create_langchain_llm(
        self,
        client: AsyncOpenAI,
        model_name: str,
        temperature: float | None,
        max_tokens: int | None,
    ) -> ChatOpenAI:
        """Create a LangChain ChatOpenAI wrapper from AsyncOpenAI client.

        Context: Converts the AsyncOpenAI client to a LangChain-compatible ChatOpenAI instance
        for use with LangGraph's StateGraph.

        Args:
            client: The AsyncOpenAI client to wrap
            model_name: Model identifier to use
            temperature: Optional temperature setting
            max_tokens: Optional max tokens setting

        Returns:
            ChatOpenAI instance configured with the provided client and parameters
        """
        return ChatOpenAI(
            client=client,
            model=model_name,
            temperature=temperature or 0.0,
            max_tokens=max_tokens or 2000,
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
        # Get or create session
        db_session: AIConversationSession | None
        if session_id:
            db_session = await self._get_session(session_id)
            if not db_session:
                raise ValueError(f"Session {session_id} not found")
        else:
            # Create new session
            db_session = AIConversationSession(
                user_id=str(user_id),
                assistant_config_id=str(assistant_config.id),
            )
            self.session.add(db_session)
            await self.session.flush()
            await self.session.refresh(db_session)
            session_id = db_session.id
        if not session_id:
            raise ValueError("Failed to create session")

        # Add user message to session
        user_msg = AIConversationMessage(
            session_id=str(session_id),
            role="user",
            content=message,
        )
        self.session.add(user_msg)
        await self.session.flush()

        # Build conversation history
        history = await self._build_conversation_history(session_id)

        # Add system prompt
        system_prompt = assistant_config.system_prompt or DEFAULT_SYSTEM_PROMPT
        history.insert(0, SystemMessage(content=system_prompt))

        # Get LLM client
        client, model_name = await self._get_llm_client(
            UUID(str(assistant_config.model_id))
        )

        # Create LangChain LLM wrapper
        llm = await self._create_langchain_llm(
            client,
            model_name,
            assistant_config.temperature,
            assistant_config.max_tokens,
        )

        # Create tools
        tool_context = ToolContext(self.session, str(user_id))
        available_tools = create_project_tools(tool_context)
        tools_dict = {tool.name: tool for tool in available_tools}

        # Filter tools based on assistant config
        if assistant_config.allowed_tools:
            tools_dict = {
                name: tool
                for name, tool in tools_dict.items()
                if name in assistant_config.allowed_tools
            }

        # Create graph
        graph = create_graph(llm=llm, tools=list(tools_dict.values()))

        # Invoke the graph
        result = await graph.ainvoke(
            input_state={
                "messages": history,
                "tool_call_count": 0,
                "next": "agent",
            },
            config={"configurable": {"thread_id": str(session_id)}},
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
        tool_results_data: list[dict[str, Any]] = []

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
        assistant_msg = AIConversationMessage(
            session_id=str(session_id),
            role="assistant",
            content=final_message.content or "",
            tool_calls=tool_calls_data if tool_calls_data else None,
            tool_results=tool_results_data if tool_results_data else None,
        )
        self.session.add(assistant_msg)
        await self.session.flush()

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

        Returns:
            None (communicates via WebSocket)

        Raises:
            ValueError: If session creation fails
        """
        # Get or create session
        db_session: AIConversationSession | None
        if session_id:
            db_session = await self._get_session(session_id)
            if not db_session:
                raise ValueError(f"Session {session_id} not found")
        else:
            # Create new session
            db_session = AIConversationSession(
                user_id=str(user_id),
                assistant_config_id=str(assistant_config.id),
            )
            db.add(db_session)
            await db.flush()
            await db.refresh(db_session)
            session_id = db_session.id
        if not session_id:
            raise ValueError("Failed to create session")

        # Add user message to session
        user_msg = AIConversationMessage(
            session_id=str(session_id),
            role="user",
            content=message,
        )
        db.add(user_msg)
        await db.flush()
        await db.commit()

        # Build conversation history
        history = await self._build_conversation_history(session_id)

        # Add system prompt
        system_prompt = assistant_config.system_prompt or DEFAULT_SYSTEM_PROMPT
        history.insert(0, SystemMessage(content=system_prompt))

        # Get LLM client
        client, model_name = await self._get_llm_client(
            UUID(str(assistant_config.model_id))
        )

        # Create LangChain LLM wrapper
        llm = await self._create_langchain_llm(
            client,
            model_name,
            assistant_config.temperature,
            assistant_config.max_tokens,
        )

        # Create tools
        tool_context = ToolContext(db, str(user_id))
        available_tools = create_project_tools(tool_context)
        tools_dict = {tool.name: tool for tool in available_tools}

        # Filter tools based on assistant config
        if assistant_config.allowed_tools:
            tools_dict = {
                name: tool
                for name, tool in tools_dict.items()
                if name in assistant_config.allowed_tools
            }

        # Create graph
        graph = create_graph(llm=llm, tools=list(tools_dict.values()))

        # Stream using astream_events
        accumulated_content = ""
        all_tool_calls: list[dict[str, Any]] = []
        all_tool_results: list[dict[str, Any]] = []

        try:
            logger.info(f"Starting astream_events for session {session_id}")

            async for event in graph.astream_events(
                input_state={
                    "messages": history,
                    "tool_call_count": 0,
                    "next": "agent",
                },
                config={"configurable": {"thread_id": str(session_id)}},
                version="v1",
            ):
                event_type = event.get("event", "")
                data = event.get("data", {})

                # Handle token streaming
                if event_type == "on_chat_model_stream":
                    chunk = data.get("chunk", {})
                    content = chunk.get("content", "")
                    if content:
                        accumulated_content += content
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

                # Handle tool start
                elif event_type == "on_tool_start":
                    tool_name = data.get("name", "")
                    tool_input = data.get("input", {})
                    try:
                        await websocket.send_json(
                            WSToolCallMessage(
                                type="tool_call",
                                tool=tool_name,
                                args=tool_input,
                            ).model_dump(mode="json")
                        )
                    except Exception:
                        # WebSocket may be closed
                        logger.warning("Failed to send tool_call, WebSocket may be closed")
                        pass

                # Handle tool end
                elif event_type == "on_tool_end":
                    tool_name = data.get("name", "")
                    tool_output = data.get("output", "")

                    # Record tool result
                    tool_result: dict[str, Any] = {
                        "tool": tool_name,
                        "success": True,
                        "result": tool_output,
                        "error": None,
                    }
                    all_tool_results.append(tool_result)

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

        except Exception as e:
            logger.error(f"Error in chat_stream astream_events: {e}", exc_info=True)
            # Send error message via WebSocket
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

        # Save assistant message to session
        assistant_msg = AIConversationMessage(
            session_id=str(session_id),
            role="assistant",
            content=accumulated_content or "",
            tool_calls=all_tool_calls if all_tool_calls else None,
            tool_results=all_tool_results if all_tool_results else None,
        )
        db.add(assistant_msg)
        await db.flush()
        await db.refresh(assistant_msg)
        await db.commit()

        # Send complete message
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

        logger.info(
            f"Chat stream completed for session {session_id}, "
            f"message_id={assistant_msg.id}"
        )

    async def _get_session(self, session_id: UUID) -> AIConversationSession | None:
        """Get a conversation session.

        Context: Internal DB helper.

        Args:
            session_id: ID of the session to retrieve

        Returns:
            The session object if found, otherwise None

        Raises:
            None
        """
        stmt = select(AIConversationSession).where(
            AIConversationSession.id == str(session_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

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
        db_messages = await self._get_session_messages(session_id)
        for msg in db_messages:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
            elif msg.role == "tool":
                # Skip tool messages in history - they're implicit
                pass
        return messages

    async def _get_session_messages(
        self, session_id: UUID
    ) -> list[AIConversationMessage]:
        """Get all messages for a session.

        Context: Internal DB helper.

        Args:
            session_id: The session ID

        Returns:
            List of AIConversationMessage instances ordered by creation time

        Raises:
            None
        """
        stmt = (
            select(AIConversationMessage)
            .where(AIConversationMessage.session_id == str(session_id))
            .order_by(AIConversationMessage.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
