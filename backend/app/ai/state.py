"""AgentState TypedDict for LangGraph agent.

LangGraph 1.0+ requires TypedDict (not Pydantic BaseModel) for state definition.
Uses Annotated with operator.add for append behavior on messages.
"""

import operator
from typing import Annotated, Literal

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State for LangGraph agent with tool call tracking.

    Attributes:
        messages: Conversation history with append behavior via operator.add
        tool_call_count: Accumulated tool call count via operator.add reducer.
            Each node returns 1 (tool calls made) or 0 (no tool calls) as a delta.
        max_tool_iterations: Maximum allowed tool call iterations (set once, no reducer).
        next: Routing direction for conditional edges ("agent", "tools", or "end")

    Note:
        LangGraph 1.0+ requires TypedDict, not Pydantic BaseModel.
        The messages and tool_call_count fields use Annotated with operator.add
        to enable append/accumulate behavior when StateGraph updates state.
    """

    messages: Annotated[list[BaseMessage], operator.add]
    tool_call_count: Annotated[int, operator.add]
    max_tool_iterations: int
    next: Literal["agent", "tools", "end"]
