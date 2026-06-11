"""Middleware that restricts supervisor tools when a multi-step plan is active.

When the planner produces a plan with ``requires_planning=True`` and specialist
assignments, the supervisor must delegate ALL work -- it should never execute
domain tools directly.  This middleware intercepts the model call, inspects the
graph state for an active plan, and strips non-delegation tools from the
request so the LLM never sees them.

Additionally injects a strong delegation-only instruction into the system
prompt so the LLM understands it MUST delegate every step.

As a safety net, response post-filtering strips any tool calls for disallowed
tools that the LLM may hallucinate despite the pre-filtered tool list.

If no plan exists (simple request or single-step fallback), all tools pass
through unchanged.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.ai.config import AI_DELEGATION_ENFORCED
from app.ai.plan import PlanDocument

logger = logging.getLogger(__name__)

# Tool name prefixes that are ALWAYS allowed, even under a plan.
# ask_user is also permitted so the supervisor can ask clarifying questions mid-plan.
_ALLOWED_PREFIXES = ("get_briefing", "handoff_to_", "ask_user")

_PLAN_DELEGATION_SUFFIX = (
    "\n\n"
    "## CRITICAL: PLAN-DRIVEN EXECUTION MODE\n"
    "An execution plan with multiple steps is active. You are in DELEGATION-ONLY mode.\n\n"
    "Your ONLY job is to:\n"
    "1. Call get_briefing to review specialist findings from completed steps\n"
    "2. Call handoff_to_{specialist} to delegate the NEXT pending plan step\n\n"
    "You MUST NOT:\n"
    "- Answer the user's question directly\n"
    "- Use any domain tools (get_project, global_search, find_users, etc.)\n"
    "- Attempt to gather information yourself\n"
    "- Skip delegation because you think you can answer\n\n"
    "Delegate every step in order. The briefing will be updated after each specialist completes."
)


def _has_active_plan(state: dict[str, Any]) -> bool:
    """Return True if state carries a multi-step plan with specialist steps."""
    plan_data = state.get("plan_data")
    if not plan_data:
        return False
    plan = PlanDocument.from_state(plan_data)
    return bool(plan.requires_planning and plan.steps)


def _allowed_tool_names(
    tools: list[BaseTool | dict[str, Any]],
) -> set[str]:
    """Return the set of tool names that match the allowed prefixes."""
    names: set[str] = set()
    for t in tools:
        name = t.name if isinstance(t, BaseTool) else str(t.get("name", ""))
        if any(name.startswith(prefix) for prefix in _ALLOWED_PREFIXES):
            names.add(name)
    return names


def _filter_tools_for_plan(
    tools: list[BaseTool | dict[str, Any]],
) -> list[BaseTool | dict[str, Any]]:
    """Keep only get_briefing + handoff_to_* tools."""
    kept: list[BaseTool | dict[str, Any]] = []
    for t in tools:
        name = t.name if isinstance(t, BaseTool) else str(t.get("name", ""))
        if any(name.startswith(prefix) for prefix in _ALLOWED_PREFIXES):
            kept.append(t)
    return kept


def _strip_disallowed_tool_calls(
    ai_message: AIMessage,
    allowed_names: set[str],
) -> AIMessage:
    """Remove tool_calls for tools not in *allowed_names*.

    If all tool_calls are stripped the returned message has ``tool_calls=[]``
    so the agent loop exits naturally.
    """
    if not ai_message.tool_calls:
        return ai_message

    filtered_calls = [
        tc for tc in ai_message.tool_calls if tc.get("name", "") in allowed_names
    ]

    if len(filtered_calls) == len(ai_message.tool_calls):
        return ai_message  # nothing to strip

    removed_names = [
        tc.get("name", "?") for tc in ai_message.tool_calls if tc not in filtered_calls
    ]
    logger.warning(
        "[PLAN_AWARE_TOOLS] Post-filter: stripped %d disallowed tool_call(s) "
        "from LLM response (removed: %s, allowed: %s)",
        len(ai_message.tool_calls) - len(filtered_calls),
        removed_names,
        allowed_names,
    )

    # Build a new AIMessage keeping content and metadata but with filtered tool_calls
    return AIMessage(
        content=ai_message.content,
        tool_calls=filtered_calls,
        additional_kwargs=ai_message.additional_kwargs,
    )


class PlanAwareToolMiddleware(AgentMiddleware):
    """Restrict supervisor tools to delegation-only when a plan is active.

    Inspects ``request.state["plan_data"]`` on every model call.  When a
    multi-step plan exists:

    1. Pre-filters the tool list to only briefing and handoff tools so the LLM
       cannot bypass specialist delegation.
    2. Appends a strong delegation-only instruction to the system prompt
       so the LLM understands it MUST delegate every step.
    3. Post-filters the LLM response to strip any tool_calls for disallowed
       tools (safety net for hallucinated tool calls).
    """

    async def awrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Any,
    ) -> Any:
        state = dict(request.state) if request.state else {}
        if AI_DELEGATION_ENFORCED and _has_active_plan(state) and request.tools:
            original_count = len(request.tools)
            filtered = _filter_tools_for_plan(request.tools)
            if len(filtered) < original_count:
                removed_names = [
                    t.name if isinstance(t, BaseTool) else str(t.get("name", ""))
                    for t in request.tools
                    if not any(
                        (
                            t.name
                            if isinstance(t, BaseTool)
                            else str(t.get("name", ""))
                        ).startswith(prefix)
                        for prefix in _ALLOWED_PREFIXES
                    )
                ]
                logger.info(
                    "[PLAN_AWARE_TOOLS] Multi-step plan active: "
                    "filtering supervisor tools %d -> %d "
                    "(removed: %s)",
                    original_count,
                    len(filtered),
                    removed_names,
                )
                request = request.override(tools=filtered)

            # Inject strong delegation-only instruction into system prompt
            current_prompt = (
                request.system_message.text if request.system_message else ""
            )
            if _PLAN_DELEGATION_SUFFIX.strip() not in current_prompt:
                new_prompt = current_prompt + _PLAN_DELEGATION_SUFFIX
                request = request.override(
                    system_message=SystemMessage(content=new_prompt),
                )

            # --- Execute model with pre-filtered tools ---
            response = await handler(request)

            # --- Post-filter: strip hallucinated disallowed tool calls ---
            allowed = _allowed_tool_names(filtered)
            if allowed and isinstance(response.result, list) and response.result:
                first_msg = response.result[0]
                if isinstance(first_msg, AIMessage) and first_msg.tool_calls:
                    cleaned = _strip_disallowed_tool_calls(first_msg, allowed)
                    if cleaned is not first_msg:
                        response.result[0] = cleaned

            return response

        return await handler(request)


__all__ = ["PlanAwareToolMiddleware"]
