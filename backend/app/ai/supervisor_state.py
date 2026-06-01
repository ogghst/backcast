"""State schema for the supervisor + briefing agent graph.

The supervisor routes requests to specialist agents via handoff tools.
Specialists do NOT share message history — instead, each receives the
compiled briefing document as context and contributes findings back.

Messages carry only the outer conversation (user + supervisor response).
The ``briefing_data`` dict is the single source of truth, rendered to
markdown on demand via ``BriefingDocument.to_markdown()``.

Plan-execute mode extends the state with ``plan_data`` and step-tracking
fields so the supervisor can decompose complex requests into ordered
steps, execute them sequentially, and track overall progress.
"""

import operator
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class BackcastSupervisorState(TypedDict):
    """State for the briefing-based supervisor graph.

    Messages carry only the outer conversation. The ``briefing_data``
    dict is the primary knowledge carrier — rendered to markdown on
    demand by read sites (get_briefing tool, specialist wrapper).

    When a plan is active, ``plan_data`` holds the serialized PlanDocument
    and the step-tracking fields drive sequential execution.

    Attributes:
        messages: User message + supervisor final response only.
            Not shared with specialists.
        active_agent: Currently active specialist for event routing.
        tool_call_count: Accumulated across all agents.
        max_tool_iterations: Hard cap on tool calls.
        briefing_data: Serialized BriefingDocument dict (single source of truth).
        supervisor_iterations: Completed supervisor cycles (add reducer).
        max_supervisor_iterations: Hard cap on supervisor loops.
        completed_specialists: Specialists that have finished (union reducer).
        plan_data: Serialized PlanDocument dict when plan-execute mode is
            active. ``None`` or empty when no plan has been generated.
        completed_steps: Indices of plan steps that have finished execution
            (union reducer — tracks progress across graph cycles).
        current_step_index: Zero-based index of the plan step currently
            being executed. ``-1`` means no plan or between steps.
    """

    messages: Annotated[list[BaseMessage], operator.add]
    active_agent: str
    tool_call_count: Annotated[int, operator.add]
    max_tool_iterations: int
    briefing_data: dict[str, Any]
    supervisor_iterations: Annotated[int, operator.add]
    max_supervisor_iterations: int
    completed_specialists: Annotated[set[str], operator.or_]
    plan_data: dict[str, Any]
    completed_steps: Annotated[set[int], operator.or_]
    current_step_index: int


__all__ = ["BackcastSupervisorState"]
