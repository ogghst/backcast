"""LangGraph Agent Service for conversation orchestration.

Uses LangGraph StateGraph for conversation flow with tool calling loop.
"""

import json
import logging
from collections.abc import Sequence
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
from langchain_core.tools import StructuredTool
from openai import AsyncOpenAI, BadRequestError
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import TypedDict

from app.ai.llm_client import (
    LLMClientFactory,
    LLMStreamingError,
    stream_with_error_handling,
)
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
MAX_TOOL_ITERATIONS = 5
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
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 2000


class AgentState(BaseModel):
    """State for LangGraph agent with tool call tracking."""

    messages: list[BaseMessage]
    tool_call_count: int = 0
    next: Literal["agent", "tools", "end"] = "agent"


class ModelResult(TypedDict):
    """Return type for model execution."""

    messages: Sequence[BaseMessage]
    tool_call_count: int


class ToolResult(TypedDict):
    """Return type for tool execution."""

    messages: Sequence[BaseMessage]


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

    def _should_continue(self, state: AgentState) -> Literal["agent", "tools", "end"]:
        """Determine if we should continue tool calling.

        Context: Agent loop condition to decide the next step based on the last message and tool iterations.

        Args:
            state: The current conversation state

        Returns:
            Next node step: "agent", "tools", or "end"
        """
        messages = state.messages
        last_message = messages[-1] if messages else None

        # If the last message is from a tool, continue to agent
        if isinstance(last_message, ToolMessage):
            return "agent"

        # If the last message has tool calls, continue to tools
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            # Check iteration limit
            if state.tool_call_count >= MAX_TOOL_ITERATIONS:
                logger.warning(f"Max tool iterations ({MAX_TOOL_ITERATIONS}) reached")
                return "end"
            return "tools"

        # Otherwise, end
        return "end"

    async def _call_model(
        self,
        state: AgentState,
        client: AsyncOpenAI,
        model_name: str,
        tools: list[StructuredTool],
        config: dict[str, float | int | None] | None = None,
    ) -> ModelResult:
        """Call the LLM with the current messages and tools.

        Context: Internal method called during the agent loop to generate a response or tool call request.

        Args:
            state: Current agent state containing conversation history
            client: Configured AsyncOpenAI client
            model_name: Model identifier to use for the completion
            tools: List of tools available for the LLM to call
            config: Optional configuration limits (temperature, max_tokens)

        Returns:
            Dictionary containing the generated AIMessage and the updated tool_call_count

        Raises:
            None (Exceptions are caught and returned as AIMessage errors)
        """
        messages = state.messages

        # Convert tools to OpenAI format
        tool_schemas: list[dict[str, object]] = []
        for tool in tools:
            schema = (
                tool.args_schema.schema() if hasattr(tool.args_schema, "schema") else {}
            )
            tool_schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": schema,
                    },
                }
            )

        try:
            temp = config.get("temperature") if config else None
            max_tok = config.get("max_tokens") if config else None

            # Build messages for OpenAI
            openai_messages: list[dict[str, object]] = []
            for m in messages:
                if isinstance(m, SystemMessage):
                    openai_messages.append({"role": "system", "content": m.content})
                elif isinstance(m, HumanMessage):
                    openai_messages.append({"role": "user", "content": m.content})
                elif isinstance(m, AIMessage) and not m.tool_calls:
                    openai_messages.append({"role": "assistant", "content": m.content})

            # Call OpenAI API
            response = await client.chat.completions.create(
                model=model_name,
                messages=openai_messages,  # type: ignore[arg-type]
                tools=tool_schemas if tool_schemas else None,  # type: ignore[arg-type]
                temperature=float(temp) if temp is not None else DEFAULT_TEMPERATURE,
                max_tokens=int(max_tok) if max_tok is not None else DEFAULT_MAX_TOKENS,

            )

            # Parse response
            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            # Create AIMessage
            ai_tool_calls: list[dict[str, object]] = []
            for tc in tool_calls:
                # Handle both function and custom tool calls
                if hasattr(tc, "function") and tc.function:
                    ai_tool_calls.append(
                        {
                            "id": tc.id,
                            "name": tc.function.name,
                            "args": json.loads(tc.function.arguments),
                        }
                    )
                elif hasattr(tc, "name"):
                    # Handle custom tool calls
                    ai_tool_calls.append(
                        {
                            "id": tc.id,
                            "name": str(tc.name) if tc.name else "",
                            "args": {},
                        }
                    )

            ai_message = AIMessage(
                content=message.content or "",
                tool_calls=ai_tool_calls,
            )

            # Update iteration count if tools were called
            new_count = state.tool_call_count
            if tool_calls:
                new_count += 1

            return {"messages": [ai_message], "tool_call_count": new_count}

        except BadRequestError as e:
            logger.error(f"OpenAI API error: {e}")
            # Return error message
            error_message = AIMessage(
                content=f"I encountered an error processing your request: {str(e)}"
            )
            return {
                "messages": [error_message],
                "tool_call_count": state.tool_call_count,
            }
        except Exception as e:
            logger.error(f"Unexpected error in _call_model: {e}")
            error_message = AIMessage(
                content="I encountered an unexpected error. Please try again."
            )
            return {
                "messages": [error_message],
                "tool_call_count": state.tool_call_count,
            }

    async def _execute_tools(
        self,
        state: AgentState,
        tools: dict[str, StructuredTool],
    ) -> ToolResult:
        """Execute tool calls from the last message.

        Context: Called when the model response contains tool calls that need execution.

        Args:
            state: Current agent state containing the messages
            tools: Dictionary of available initialized tools

        Returns:
            Dictionary containing the ToolMessages with execution results

        Raises:
            None (tool execution errors are caught and returned as ToolMessages)
        """
        messages = state.messages
        last_message = messages[-1] if messages else None

        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {"messages": []}

        tool_results = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id", "")

            if tool_name not in tools:
                result = f"Error: Tool '{tool_name}' not found"
            else:
                try:
                    # Execute the tool
                    tool = tools[tool_name]
                    result = await tool.ainvoke(tool_args)
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    result = f"Error executing tool: {str(e)}"

            tool_results.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_id,
                )
            )

        return {"messages": tool_results}

    async def chat(
        self,
        message: str,
        assistant_config: AIAssistantConfig,
        session_id: UUID | None,
        user_id: UUID,
    ) -> AIChatResponse:
        """Process a chat message using LangGraph.

        Context: Main entry point for the AI conversation. Manages the session, invokes the agent loop, and saves history.

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

        # Run the agent loop
        current_state = AgentState(messages=history, tool_call_count=0)

        for _ in range(MAX_TOOL_ITERATIONS + 1):
            # Call model
            model_result = await self._call_model(
                current_state,
                client,
                model_name,
                list(tools_dict.values()),
                {
                    "temperature": assistant_config.temperature,
                    "max_tokens": assistant_config.max_tokens,
                },
            )
            current_state.messages.extend(model_result["messages"])
            current_state.tool_call_count = model_result["tool_call_count"]

            # Check if we should continue
            last_message = current_state.messages[-1]
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                # Execute tools
                tool_result = await self._execute_tools(current_state, tools_dict)
                current_state.messages.extend(tool_result["messages"])
            else:
                # No more tool calls, break
                break

        # Extract final AI response
        final_message = None
        for msg in reversed(current_state.messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                final_message = msg
                break

        if not final_message:
            raise ValueError("No assistant response generated")

        # Save assistant message to session
        tool_calls_data = None
        if final_message.tool_calls:
            tool_calls_data = [
                {
                    "id": tc.get("id", ""),
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                }
                for tc in final_message.tool_calls
            ]

        assistant_msg = AIConversationMessage(
            session_id=str(session_id),
            role="assistant",
            content=final_message.content or "",
            tool_calls=tool_calls_data,
            tool_results=None,
        )
        self.session.add(assistant_msg)
        await self.session.flush()

        # Build response
        return AIChatResponse(
            session_id=session_id,
            message=AIConversationMessagePublic.model_validate(assistant_msg),
            tool_calls=tool_calls_data,
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
                Handles tool calls by sending events before and after execution. Persists the
                complete message to database after streaming completes.

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

        # Run the agent loop with streaming
        current_state = AgentState(messages=history, tool_call_count=0)
        accumulated_content = ""
        all_tool_calls: list[dict[str, Any]] = []
        all_tool_results: list[dict[str, Any]] = []
        session_id_for_ws = session_id

        try:
            for iteration in range(MAX_TOOL_ITERATIONS + 1):
                # Convert tools to OpenAI format
                tool_schemas: list[dict[str, object]] = []
                for tool in tools_dict.values():
                    schema = (
                        tool.args_schema.schema()
                        if hasattr(tool.args_schema, "schema")
                        else {}
                    )
                    tool_schemas.append(
                        {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": schema,
                            },
                        }
                    )

                # Build messages for OpenAI
                openai_messages: list[dict[str, object]] = []
                for m in current_state.messages:
                    if isinstance(m, SystemMessage):
                        openai_messages.append({"role": "system", "content": m.content})
                    elif isinstance(m, HumanMessage):
                        openai_messages.append({"role": "user", "content": m.content})
                    elif isinstance(m, AIMessage) and not m.tool_calls:
                        openai_messages.append(
                            {"role": "assistant", "content": m.content}
                        )

                # Stream the response
                temp = assistant_config.temperature or DEFAULT_TEMPERATURE
                max_tok = assistant_config.max_tokens or DEFAULT_MAX_TOKENS

                logger.info(
                    f"Starting LLM stream for session {session_id_for_ws}, "
                    f"iteration {iteration + 1}/{MAX_TOOL_ITERATIONS + 1}"
                )

                streamed_content = ""
                tool_calls_in_response: list[dict[str, Any]] = []

                async for chunk in stream_with_error_handling(
                    client,
                    model_name,
                    openai_messages,
                    tools=tool_schemas if tool_schemas else None,
                    temperature=float(temp),
                    max_tokens=int(max_tok),
                ):
                    try:
                        # Extract delta content
                        delta = chunk.choices[0].delta
                        if delta.content:
                            streamed_content += delta.content
                            # Send token via WebSocket
                            await websocket.send_json(
                                WSTokenMessage(
                                    type="token",
                                    content=delta.content,
                                    session_id=session_id_for_ws,
                                ).model_dump(mode='json')
                            )

                        # Check for tool calls in the chunk
                        if (
                            hasattr(delta, "tool_calls")
                            and delta.tool_calls
                            and chunk.choices[0].finish_reason == "tool_calls"
                        ):
                            # Extract tool calls from the complete response
                            response_message = chunk.choices[0].message
                            if (
                                hasattr(response_message, "tool_calls")
                                and response_message.tool_calls
                            ):
                                for tc in response_message.tool_calls:
                                    if hasattr(tc, "function") and tc.function:
                                        tool_calls_in_response.append(
                                            {
                                                "id": tc.id,
                                                "name": tc.function.name,
                                                "args": json.loads(
                                                    tc.function.arguments
                                                ),
                                            }
                                        )

                    except LLMStreamingError as e:
                        logger.error(f"Streaming error: {e.message}")
                        # Send error message via WebSocket
                        try:
                            await websocket.send_json(
                                WSErrorMessage(
                                    type="error",
                                    message=e.message,
                                    code=500,
                                ).model_dump(mode='json')
                            )
                        except Exception:
                            # WebSocket may be closed
                            pass
                        # Continue with partial content
                        break
                    except Exception as e:
                        logger.error(f"Unexpected error during streaming: {type(e).__name__}: {e}", exc_info=True)
                        break

                accumulated_content += streamed_content

                # Check if we have tool calls to execute
                if tool_calls_in_response:
                    # Record tool calls for database persistence
                    all_tool_calls.extend(tool_calls_in_response)

                    # Create AIMessage with tool calls
                    ai_message = AIMessage(
                        content=streamed_content or "",
                        tool_calls=tool_calls_in_response,
                    )
                    current_state.messages.append(ai_message)
                    current_state.tool_call_count += 1

                    # Execute tools and send events
                    for tool_call in tool_calls_in_response:
                        tool_name = tool_call.get("name", "")
                        tool_args = tool_call.get("args", {})

                        # Send tool call event
                        try:
                            await websocket.send_json(
                                WSToolCallMessage(
                                    type="tool_call",
                                    tool=tool_name,
                                    args=tool_args,
                                ).model_dump(mode='json')
                            )
                        except Exception:
                            # WebSocket may be closed
                            pass

                        # Execute the tool
                        tool_result: dict[str, Any] = {
                            "tool": tool_name,
                            "success": False,
                            "result": None,
                            "error": None,
                        }

                        if tool_name in tools_dict:
                            try:
                                tool = tools_dict[tool_name]
                                result = await tool.ainvoke(tool_args)
                                tool_result["success"] = True
                                tool_result["result"] = result
                                all_tool_results.append(tool_result)

                                # Send tool result event
                                try:
                                    await websocket.send_json(
                                        WSToolResultMessage(
                                            type="tool_result",
                                            tool=tool_name,
                                            result=tool_result,
                                        ).model_dump(mode='json')
                                    )
                                except Exception:
                                    # WebSocket may be closed
                                    pass

                                # Add ToolMessage to state
                                current_state.messages.append(
                                    ToolMessage(
                                        content=str(result),
                                        tool_call_id=tool_call.get("id", ""),
                                    )
                                )
                            except Exception as e:
                                logger.error(f"Error executing tool {tool_name}: {e}")
                                tool_result["error"] = str(e)
                                all_tool_results.append(tool_result)

                                # Send error result
                                try:
                                    await websocket.send_json(
                                        WSToolResultMessage(
                                            type="tool_result",
                                            tool=tool_name,
                                            result=tool_result,
                                        ).model_dump(mode='json')
                                    )
                                except Exception:
                                    # WebSocket may be closed
                                    pass

                                current_state.messages.append(
                                    ToolMessage(
                                        content=f"Error: {str(e)}",
                                        tool_call_id=tool_call.get("id", ""),
                                    )
                                )
                        else:
                            error_msg = f"Tool '{tool_name}' not found"
                            tool_result["error"] = error_msg
                            all_tool_results.append(tool_result)

                            try:
                                await websocket.send_json(
                                    WSToolResultMessage(
                                        type="tool_result",
                                        tool=tool_name,
                                        result=tool_result,
                                    ).model_dump()
                                )
                            except Exception:
                                # WebSocket may be closed
                                pass

                            current_state.messages.append(
                                ToolMessage(
                                    content=error_msg,
                                    tool_call_id=tool_call.get("id", ""),
                                )
                            )
                else:
                    # No tool calls, add AI message and break
                    ai_message = AIMessage(content=streamed_content or "")
                    current_state.messages.append(ai_message)
                    break

        except Exception as e:
            logger.error(f"Error in chat_stream: {e}")
            # Send error message via WebSocket
            try:
                await websocket.send_json(
                    WSErrorMessage(
                        type="error",
                        message=f"An error occurred: {str(e)}",
                        code=500,
                    ).model_dump(mode='json')
                )
            except Exception:
                # WebSocket may be closed
                pass

        # Extract final AI response content
        final_content = accumulated_content

        # Save assistant message to session
        assistant_msg = AIConversationMessage(
            session_id=str(session_id),
            role="assistant",
            content=final_content or "",
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
                ).model_dump(mode='json')
            )
        except Exception:
            # WebSocket may be closed, but message is persisted
            logger.warning("WebSocket closed before sending complete message")

        logger.info(
            f"Chat stream completed for session {session_id_for_ws}, "
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
