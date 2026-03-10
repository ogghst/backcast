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
        tool_call_count: Number of tool calls made in current iteration
        next: Routing direction for conditional edges ("agent", "tools", or "end")

    Note:
        LangGraph 1.0+ requires TypedDict, not Pydantic BaseModel.
        The messages field uses Annotated with operator.add to enable
        append behavior when StateGraph updates state.
    """

    messages: Annotated[list[BaseMessage], operator.add]
    tool_call_count: int
    next: Literal["agent", "tools", "end"]
