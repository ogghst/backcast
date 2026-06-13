"""Middleware that restricts supervisor tools when a multi-step plan is active.

When the planner produces a plan with ``requires_planning=True`` and specialist
assignments, the supervisor must delegate ALL work -- it should never execute
domain tools directly.  This middleware intercepts the model call, inspects the
graph state for an active plan, and strips non-delegation tools from the
request so the LLM never sees them.

When the assistant is configured with ``direct_tools``, those tools are
preserved so the supervisor can still perform lookups while delegating plan
steps.  A softer suffix is used in that case.

Additionally injects a delegation instruction into the system prompt so the
LLM understands it MUST delegate every step.

As a safety net, response post-filtering strips any tool calls for disallowed
tools that the LLM may hallucinate despite the pre-filtered tool list.

If no plan exists (simple request or single-step fallback), all tools pass
through unchanged.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.ai.config import AI_DELEGATION_ENFORCED
from app.ai.plan import PlanDocument
from app.ai.prompt_template import render_prompt

logger = logging.getLogger(__name__)

# Tool name prefixes that are ALWAYS allowed, even under a plan.
# ask_user is also permitted so the supervisor can ask clarifying questions mid-plan.
_ALLOWED_PREFIXES = ("get_briefing", "handoff_to_", "ask_user", "request_replan")

_PLAN_DELEGATION_SUFFIX = (
    "\n\n"
    "## CRITICAL: PLAN-DRIVEN EXECUTION MODE\n"
    "An execution plan with multiple steps is active. You are in DELEGATION-ONLY mode.\n\n"
    "Your ONLY job is to:\n"
    "1. Call get_briefing to review specialist findings from completed steps\n"
    "2. Call handoff_to_{specialist} to delegate the NEXT pending plan step\n"
    "3. Call request_replan if findings make remaining steps redundant or conflicting\n\n"
    "You MUST NOT:\n"
    "- Answer the user's question directly\n"
    "- Use any domain tools (get_project, global_search, find_users, etc.)\n"
    "- Attempt to gather information yourself\n"
    "- Skip delegation because you think you can answer\n\n"
    "Delegate every step in order. The briefing will be updated after each specialist completes."
)

_PLAN_WITH_DIRECT_TOOLS_SUFFIX = (
    "\n\n"
    "## PLAN-DRIVEN EXECUTION MODE\n"
    "An execution plan with multiple steps is active.\n\n"
    "Your job is to:\n"
    "1. Call get_briefing to review specialist findings from completed steps\n"
    "2. Call handoff_to_{specialist} to delegate the NEXT pending plan step\n"
    "3. Call request_replan if findings make remaining steps redundant or conflicting\n\n"
    "You MAY use your direct tools for lookups and context gathering between steps.\n\n"
    "You MUST NOT:\n"
    "- Answer the user's question directly instead of delegating plan steps\n"
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


def _tool_name(tool: BaseTool | dict[str, Any]) -> str:
    return tool.name if isinstance(tool, BaseTool) else str(tool.get("name", ""))


def _allowed_tool_names(
    tools: list[BaseTool | dict[str, Any]],
    direct_tool_names: set[str],
) -> set[str]:
    """Return the set of tool names that match the allowed prefixes or are direct tools."""
    names: set[str] = set()
    for t in tools:
        name = _tool_name(t)
        if any(name.startswith(prefix) for prefix in _ALLOWED_PREFIXES):
            names.add(name)
        elif name in direct_tool_names:
            names.add(name)
    return names


def _filter_tools_for_plan(
    tools: list[BaseTool | dict[str, Any]],
    direct_tool_names: set[str],
) -> list[BaseTool | dict[str, Any]]:
    """Keep delegation tools (briefing, handoff, ask_user, replan) + direct tools."""
    kept: list[BaseTool | dict[str, Any]] = []
    for t in tools:
        name = _tool_name(t)
        if any(name.startswith(prefix) for prefix in _ALLOWED_PREFIXES):
            kept.append(t)
        elif name in direct_tool_names:
            kept.append(t)
    return kept


def _strip_disallowed_tool_calls(
    ai_message: AIMessage,
    allowed_names: set[str],
) -> AIMessage:
    """Remove tool_calls for tools not in *allowed_names*.

    If ALL tool_calls are stripped (which would leave ``tool_calls=[]`` and
    cause LangGraph to route to END), a synthetic ``get_briefing`` call is
    injected instead so the supervisor gets another iteration to call the
    correct tool.  This prevents premature graph termination when pending
    plan steps remain.
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

    # If ALL tool calls were stripped, inject a corrective get_briefing call
    # to prevent the graph from terminating with pending plan steps.
    if not filtered_calls and "get_briefing" in allowed_names:
        logger.info(
            "[PLAN_AWARE_TOOLS] All tool calls stripped — injecting corrective "
            "get_briefing call to prevent premature graph termination"
        )
        filtered_calls = [
            {
                "name": "get_briefing",
                "args": {},
                "id": f"corrective-{uuid.uuid4().hex[:12]}",
                "type": "tool_call",
            }
        ]

    # Build a new AIMessage keeping content and metadata but with filtered tool_calls
    was_stripped = len(ai_message.tool_calls) != len(filtered_calls)
    new_content: str | list[str | dict[str, Any]] = ai_message.content
    if was_stripped and isinstance(new_content, str):
        new_content = (
            new_content
            + "\n\n[System: All your tool calls were disallowed under the active plan. "
            "Use get_briefing to review progress, then delegate the next pending "
            "step via handoff_to_*.]"
        )
    return AIMessage(
        content=new_content,
        tool_calls=filtered_calls,
        additional_kwargs=ai_message.additional_kwargs,
    )


class PlanAwareToolMiddleware(AgentMiddleware):
    """Restrict supervisor tools to delegation-only when a plan is active.

    Inspects ``request.state["plan_data"]`` on every model call.  When a
    multi-step plan exists:

    1. Pre-filters the tool list to delegation tools + direct tools so the
       LLM cannot bypass specialist delegation while retaining lookup access.
    2. Appends a delegation instruction to the system prompt.  Uses a softer
       variant when direct tools are present.
    3. Post-filters the LLM response to strip any tool_calls for disallowed
       tools (safety net for hallucinated tool calls).

    Args:
        direct_tool_names: Tool names the supervisor may use directly even
            when a plan is active.  Sourced from the assistant's
            ``delegation_config.direct_tools``.
    """

    def __init__(self, direct_tool_names: list[str] | None = None) -> None:
        self._direct_tool_names: set[str] = set(direct_tool_names or [])

    async def awrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Any,
    ) -> Any:
        state = dict(request.state) if request.state else {}
        if AI_DELEGATION_ENFORCED and _has_active_plan(state) and request.tools:
            original_count = len(request.tools)
            filtered = _filter_tools_for_plan(request.tools, self._direct_tool_names)
            if len(filtered) < original_count:
                removed_names = [
                    _tool_name(t)
                    for t in request.tools
                    if not any(
                        _tool_name(t).startswith(prefix) for prefix in _ALLOWED_PREFIXES
                    )
                    and _tool_name(t) not in self._direct_tool_names
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

            # --- Inject plan steps into system prompt ---
            current_prompt = (
                request.system_message.text if request.system_message else ""
            )
            plan_data: dict[str, Any] | None = state.get("plan_data")  # type: ignore[assignment]
            if plan_data:
                plan = PlanDocument.from_state(plan_data)
                plan_text = plan.to_prompt_text()

                if "{plan_section}" in current_prompt:
                    current_prompt = render_prompt(
                        current_prompt, plan_section=plan_text
                    )
                elif plan_text not in current_prompt:
                    current_prompt = current_prompt + "\n\n" + plan_text

            # --- Inject delegation instruction into system prompt ---
            # Use softer suffix when direct tools are preserved.
            has_direct_tools = self._direct_tool_names and any(
                _tool_name(t) in self._direct_tool_names for t in filtered
            )
            suffix = (
                _PLAN_WITH_DIRECT_TOOLS_SUFFIX
                if has_direct_tools
                else _PLAN_DELEGATION_SUFFIX
            )
            if suffix.strip() not in current_prompt:
                current_prompt = current_prompt + suffix
                request = request.override(
                    system_message=SystemMessage(content=current_prompt),
                )
            elif plan_data:
                # Plan text was injected but suffix already present — still
                # need to update the system message with the plan text.
                request = request.override(
                    system_message=SystemMessage(content=current_prompt),
                )

            # --- Execute model with pre-filtered tools ---
            response = await handler(request)

            # --- Post-filter: strip hallucinated disallowed tool calls ---
            allowed = _allowed_tool_names(filtered, self._direct_tool_names)
            if allowed and isinstance(response.result, list) and response.result:
                first_msg = response.result[0]
                if isinstance(first_msg, AIMessage) and first_msg.tool_calls:
                    cleaned = _strip_disallowed_tool_calls(first_msg, allowed)
                    if cleaned is not first_msg:
                        response.result[0] = cleaned

            return response

        # No active plan — clean up {plan_section} placeholder if present so
        # the supervisor never sees the literal template tag.
        current_prompt = request.system_message.text if request.system_message else ""
        if "{plan_section}" in current_prompt:
            current_prompt = render_prompt(
                current_prompt, plan_section="No execution plan — delegate directly."
            )
            request = request.override(
                system_message=SystemMessage(content=current_prompt),
            )

        return await handler(request)


__all__ = ["PlanAwareToolMiddleware"]
