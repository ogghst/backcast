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
from collections import Counter
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


def _merge_dispatch_counts(
    left: dict[str, int], right: dict[str, int]
) -> dict[str, int]:
    """Sum per-specialist dispatch counts across graph transitions.

    A custom reducer (rather than ``operator.or_`` on sets) so each specialist
    dispatch increments its own counter, enabling the per-specialist
    re-dispatch cap enforced in the specialist dispatch node.
    """
    merged: Counter[str] = Counter(left)
    merged.update(right)
    return dict(merged)


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
        current_invocation_id: UUID tracking the current specialist
            invocation, passed from the handoff tool through the graph
            state so that the specialist wrapper can publish chat events
            (SUBAGENT, token_batch, AGENT_COMPLETE) with a single
            consistent identifier.
        replan_count: Number of replan cycles completed. Set explicitly
            by the replan tool (current + 1). NOT a reducer to avoid
            spurious increments on every graph transition.
        max_replan_count: Hard cap on replan cycles. Default 2, set at
            graph creation time.
        replan_context: Supervisor's reason string consumed by the
            planner on replan. Overwritten each time (last writer wins).
            Cleared after the planner processes it.
        specialist_dispatch_counts: Per-specialist dispatch counter
            (sum reducer). Drives the code-enforced re-dispatch cap: a
            specialist may be dispatched at most ``_MAX_DISPATCHES_PER_SPECIALIST``
            times in plan mode before the dispatch node routes to the
            supervisor with a request_replan nudge, preventing the
            Swarm-style infinite re-dispatch loop.
        specialist_failure_counts: Per-specialist CONSECUTIVE-failure counter
            in PURE non-plan mode (sum reducer). Drives the bounded-failure
            guard in the specialist node: when the same specialist fails twice
            in a row with no active plan, the graph force-ends (goto END) with
            a user-facing message so a weak model cannot re-dispatch a failing
            specialist until ``max_supervisor_iterations`` (~5x120s timeouts).
            Not used in plan mode (the per-step dispatch cap handles that).
        termination_notice: User-facing termination message emitted by the
            ``bounded_terminate`` node when the supervisor graph hits a silent
            force-END path (max-iterations or max-replan cap). Built from plan
            STATE (Completed / Failed-with-error / Not-started sections) so the
            user is ALWAYS told when a run is bounded, even when the supervisor
            was misbehaving. NOT a reducer (last writer wins, like
            ``replan_context``); ``None`` means no bounded termination occurred.
            Read by ``agent_service`` from the checkpoint and persisted as a
            final assistant message.
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
    current_invocation_id: str
    replan_count: int
    max_replan_count: int
    replan_context: str
    specialist_dispatch_counts: Annotated[dict[str, int], _merge_dispatch_counts]
    specialist_failure_counts: Annotated[dict[str, int], _merge_dispatch_counts]
    termination_notice: str | None


__all__ = ["BackcastSupervisorState"]
