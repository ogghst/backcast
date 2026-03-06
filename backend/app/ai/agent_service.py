"""LangGraph Agent Service for conversation orchestration.

Uses LangGraph StateGraph for conversation flow with tool calling loop.
"""

import json
import logging
from typing import Any, Literal
from uuid import UUID

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


class AgentService:
    """Service for LangGraph agent orchestration."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_llm_client(self, model_id: UUID) -> tuple[AsyncOpenAI, str]:
        """Get LLM client and model name for a model."""
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
        """Determine if we should continue tool calling."""
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
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call the LLM with the current messages and tools."""
        messages = state.messages

        # Convert tools to OpenAI format
        tool_schemas: list[dict[str, Any]] = []
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
            # Build messages for OpenAI
            openai_messages: list[dict[str, Any]] = []
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
                temperature=config.get("temperature", DEFAULT_TEMPERATURE)
                if config
                else DEFAULT_TEMPERATURE,
                max_tokens=config.get("max_tokens", DEFAULT_MAX_TOKENS)
                if config
                else DEFAULT_MAX_TOKENS,
            )

            # Parse response
            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            # Create AIMessage
            ai_tool_calls: list[dict[str, Any]] = []
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
    ) -> dict[str, Any]:
        """Execute tool calls from the last message."""
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
        """Process a chat message using LangGraph."""
        # Get or create session
        db_session: AIConversationSession | None
        if session_id:
            db_session = await self._get_session(session_id)
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

    async def _get_session(self, session_id: UUID) -> AIConversationSession | None:
        """Get a conversation session."""
        stmt = select(AIConversationSession).where(
            AIConversationSession.id == str(session_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _build_conversation_history(self, session_id: UUID) -> list[BaseMessage]:
        """Build conversation history from session messages."""
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
        """Get all messages for a session."""
        stmt = (
            select(AIConversationMessage)
            .where(AIConversationMessage.session_id == str(session_id))
            .order_by(AIConversationMessage.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
