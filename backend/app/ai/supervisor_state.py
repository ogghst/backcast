"""Shared state schema for the supervisor + handoff agent graph.

All specialist agents and the supervisor share this state when embedded
as subgraph nodes in the parent StateGraph. This ensures full message
history is visible to every agent during handoff.
"""

import operator
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class BackcastSupervisorState(TypedDict):
    """State for the supervisor graph with shared message history.

    Attributes:
        messages: Full conversation history with append behavior.
            All agents see the complete message history during handoff.
        active_agent: Name of the currently active specialist agent.
            Updated on handoff for event bus tracking.
        structured_response: Optional structured output from specialist
            agents (e.g., EVMMetricsRead, ImpactAnalysisResponse).
        tool_call_count: Accumulated tool call count across all agents.
        max_tool_iterations: Maximum allowed tool call iterations.
    """

    messages: Annotated[list[BaseMessage], operator.add]
    active_agent: str
    structured_response: Any | None
    tool_call_count: Annotated[int, operator.add]
    max_tool_iterations: int


__all__ = ["BackcastSupervisorState"]
