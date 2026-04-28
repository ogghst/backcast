"""State schema for the supervisor + briefing agent graph.

The supervisor routes requests to specialist agents via handoff tools.
Specialists do NOT share message history — instead, each receives the
compiled briefing document as context and contributes findings back.

Messages carry only the outer conversation (user + supervisor response).
The briefing field is the primary knowledge carrier between turns.
"""

import operator
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class BackcastSupervisorState(TypedDict):
    """State for the briefing-based supervisor graph.

    Messages carry only the outer conversation. The briefing field is
    the primary knowledge carrier between supervisor and specialist turns.

    Attributes:
        messages: User message + supervisor final response only.
            Not shared with specialists.
        active_agent: Currently active specialist for event routing.
        structured_response: Optional structured output from specialists.
        tool_call_count: Accumulated across all agents.
        max_tool_iterations: Hard cap on tool calls.
        briefing: Compiled markdown briefing document.
        briefing_data: Serialized BriefingDocument dict.
        supervisor_iterations: Completed supervisor cycles (add reducer).
        max_supervisor_iterations: Hard cap on supervisor loops.
        completed_specialists: Specialists that have finished (union reducer).
    """

    messages: Annotated[list[BaseMessage], operator.add]
    active_agent: str
    structured_response: Any | None
    tool_call_count: Annotated[int, operator.add]
    max_tool_iterations: int
    briefing: str
    briefing_data: dict[str, Any]
    supervisor_iterations: Annotated[int, operator.add]
    max_supervisor_iterations: int
    completed_specialists: Annotated[set[str], operator.or_]


__all__ = ["BackcastSupervisorState"]
