"""Planner node for request decomposition into structured PlanDocument steps.

Single LLM call that analyzes the user request and produces a PlanDocument:
- Simple requests -> single-step plan (requires_planning=False)
- Complex requests -> multi-step plan with specialist assignments and
  dependencies (requires_planning=True)

Inserted between initialize_briefing and supervisor in the graph flow:
    START -> initialize_briefing -> planner -> supervisor <-> specialists -> END
"""

from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from app.ai.execution.llm_retry import invoke_with_retry
from app.ai.plan import PlanDocument, PlannerOutput, PlanStep
from app.ai.prompt_template import render_prompt
from app.core.config import settings

logger = logging.getLogger(__name__)


_PLANNER_PROMPT_TEMPLATE = """\
You are a request planner for the Backcast project budget management system.

Analyze the user's request and decide whether it needs multi-step execution \
or can be handled by a single specialist.

{specialist_section}

## Decision Guide

Single-step (requires_planning=false, one step):
- "Show me project ACME-001 budget status" -> project_manager
- "What is the CPI for project PRJ-100?" -> evm_analyst
- "List all change orders for project X" -> change_order_manager

Multi-step (requires_planning=true, ordered steps with dependencies):
- "Analyze project ACME-001 EVM performance and create a dashboard" ->
  Step 0: evm_analyst (calculate EVM metrics)
  Step 1: visualization_specialist (depends on 0, build dashboard from metrics)
- "Compare forecasts across all active projects and identify risks" ->
  Step 0: project_manager (list active projects)
  Step 1: forecast_manager (depends on 0, gather forecasts)
  Step 2: evm_analyst (depends on 1, risk analysis)

## Rules

- Use ONLY specialist names from the list above
- Keep task descriptions focused and actionable
- Only add dependencies when step N genuinely needs output from step M
- Maximum 5 steps  # enforced in code by _MAX_PLAN_STEPS
"""

_DEFAULT_SPECIALIST_CATALOG: list[dict[str, str]] = [
    {
        "name": "general_purpose",
        "description": "Unclear or cross-cutting requests that don't fit one domain",
    },
]

#: Hard cap on plan step count. The prompt requests "Maximum 5 steps"; this
#: enforces it in code so an LLM that ignores the prompt cannot inflate the
#: supervisor iteration budget and context cost.
_MAX_PLAN_STEPS: int = 5

_REPLANNER_PROMPT_TEMPLATE = """\
You are revising an execution plan based on new findings from completed specialists.

## Replan Reason
{replan_reason}

## Existing Plan (completed steps are LOCKED)
{existing_plan_text}

## Specialist Findings So Far
{briefing_context}

{specialist_section}

## Rules for Replanning
- COMPLETED steps (marked [completed]) MUST be preserved exactly as-is
- Only revise PENDING steps (marked [pending])
- New/revised steps get step_index values starting AFTER the last completed step
- You may REMOVE pending steps that are now redundant
- You may ADD new steps if findings reveal additional work
- Maximum 5 total steps (completed + revised)  # enforced in code by _MAX_PLAN_STEPS
- Use ONLY specialist names from the list above
- Provide the FULL plan including completed steps in your output
"""


def _build_specialist_section(catalog: list[dict[str, str]]) -> str:
    """Build the ## Available Specialists section from a catalog."""
    lines = ["## Available Specialists", ""]
    for entry in catalog:
        lines.append(f"- {entry['name']}: {entry['description']}")
    lines.append("")
    return "\n".join(lines)


def build_planner_system_prompt(
    specialist_catalog: list[dict[str, str]] | None = None,
    custom_template: str | None = None,
) -> str:
    """Build the planner system prompt with a dynamic specialist list.

    Args:
        specialist_catalog: Optional list of dicts with ``name`` and
            ``description`` keys.  Falls back to the hardcoded default.
        custom_template: Optional custom prompt template.  Supports the
            ``{specialist_section}`` placeholder.  If the placeholder is
            absent, the specialist section is appended after a blank line.

    Returns:
        Complete planner system prompt string.
    """
    catalog = specialist_catalog or _DEFAULT_SPECIALIST_CATALOG
    specialist_section = _build_specialist_section(catalog)
    template = custom_template or _PLANNER_PROMPT_TEMPLATE
    if "{specialist_section}" in template:
        return render_prompt(template, specialist_section=specialist_section)
    return template + "\n\n" + specialist_section


# Backward-compatible alias
PLANNER_SYSTEM_PROMPT = build_planner_system_prompt()


def _build_planner_prompt(
    user_request: str,
    briefing_context: str | None = None,
) -> str:
    """Build the human message for the planner LLM call.

    Args:
        user_request: The user's message text.
        briefing_context: Optional existing briefing summary for follow-ups.

    Returns:
        Prompt string for the planner.
    """
    parts = [f"User request: {user_request}"]
    if briefing_context:
        parts.append(
            f"\nExisting briefing context (this is a follow-up):\n{briefing_context}"
        )
    return "\n".join(parts)


def _convert_planner_output(
    output: PlannerOutput,
    valid_specialists: frozenset[str] | None = None,
) -> PlanDocument:
    """Convert a PlannerOutput from structured LLM call into a PlanDocument.

    Validates specialist names against the catalog and converts LLM-only
    fields into runtime PlanStep instances with default status.

    Args:
        output: Structured output from the planner LLM call.
        valid_specialists: Set of specialist names considered valid.
            Defaults to ``{general_purpose}`` when not provided.

    Returns:
        PlanDocument with validated steps, or a single-step fallback.
    """
    allowed = valid_specialists or frozenset({"general_purpose"})
    steps: list[PlanStep] = []
    for i, raw_step in enumerate(output.steps):
        specialist = raw_step.specialist
        if specialist not in allowed:
            logger.warning(
                "[PLANNER] Unknown specialist '%s', defaulting to general_purpose",
                specialist,
            )
            specialist = "general_purpose"
        steps.append(
            PlanStep(
                step_index=i,
                specialist=specialist,
                task_description=raw_step.task_description,
                dependencies=raw_step.dependencies,
                expected_output=raw_step.expected_output,
            )
        )

    # Enforce the hard step cap. Truncating the built list before the
    # empty-steps check keeps ``step_index`` contiguous (0..n-1) since the
    # indices were assigned positionally via ``enumerate`` above.
    if len(steps) > _MAX_PLAN_STEPS:
        logger.warning(
            "[PLANNER] Plan has %d steps, truncating to %d",
            len(steps),
            _MAX_PLAN_STEPS,
        )
        steps = steps[:_MAX_PLAN_STEPS]

    if not steps:
        logger.warning("[PLANNER] Empty steps from structured output, falling back")
        return _fallback_plan(output.original_request)

    return PlanDocument(
        original_request=output.original_request,
        steps=steps,
        estimated_complexity=output.estimated_complexity,
        requires_planning=output.requires_planning,
    )


def _merge_replanned_steps(
    existing_plan: PlanDocument,
    new_steps_output: PlannerOutput,
    valid_specialists: frozenset[str],
) -> PlanDocument:
    """Merge replanned steps: completed steps stay, new steps get fresh indices.

    Args:
        existing_plan: The current plan with potentially completed steps.
        new_steps_output: The LLM's revised step output (pending steps only).
        valid_specialists: Set of valid specialist names for fallback.

    Returns:
        PlanDocument with completed steps preserved and revised steps
        re-indexed after the last completed step.
    """
    completed = [s for s in existing_plan.steps if s.status == "completed"]
    max_completed_idx = max((s.step_index for s in completed), default=-1)

    # Enforce the hard step cap. Completed steps are LOCKED, so the cap is
    # applied to the revised portion: completed + revised <= _MAX_PLAN_STEPS.
    # Defensive: if completed already meets/exceeds the cap (shouldn't happen
    # in normal flow), keep only the first _MAX_PLAN_STEPS completed and no
    # revised steps.
    if len(completed) >= _MAX_PLAN_STEPS:
        logger.warning(
            "[PLANNER] Replan has %d completed steps (>= cap %d), truncating "
            "completed and dropping revised",
            len(completed),
            _MAX_PLAN_STEPS,
        )
        completed = completed[:_MAX_PLAN_STEPS]
        max_completed_idx = max((s.step_index for s in completed), default=-1)
        revised_steps: list[PlanStep] = []
        return PlanDocument(
            original_request=existing_plan.original_request,
            steps=completed,
            estimated_complexity=new_steps_output.estimated_complexity
            or existing_plan.estimated_complexity,
            requires_planning=True,
        )

    revised_capacity = max(0, _MAX_PLAN_STEPS - len(completed))
    raw_revised = new_steps_output.steps
    if len(raw_revised) > revised_capacity:
        logger.warning(
            "[PLANNER] Replan has %d revised steps, truncating to %d to keep "
            "total <= %d",
            len(raw_revised),
            revised_capacity,
            _MAX_PLAN_STEPS,
        )
        raw_revised = raw_revised[:revised_capacity]

    revised_steps = []
    for i, raw_step in enumerate(raw_revised):
        specialist = (
            raw_step.specialist
            if raw_step.specialist in valid_specialists
            else "general_purpose"
        )
        revised_steps.append(
            PlanStep(
                step_index=max_completed_idx + 1 + i,
                specialist=specialist,
                task_description=raw_step.task_description,
                dependencies=raw_step.dependencies,
                expected_output=raw_step.expected_output,
            )
        )

    return PlanDocument(
        original_request=existing_plan.original_request,
        steps=completed + revised_steps,
        estimated_complexity=new_steps_output.estimated_complexity
        or existing_plan.estimated_complexity,
        requires_planning=True,
    )


def _fallback_plan(user_request: str) -> PlanDocument:
    """Create a single-step fallback plan using general_purpose.

    Args:
        user_request: The user's original request.

    Returns:
        PlanDocument with a single general_purpose step.
    """
    return PlanDocument(
        original_request=user_request,
        steps=[
            PlanStep(
                step_index=0,
                specialist="general_purpose",
                task_description=user_request,
                dependencies=[],
                expected_output="Address the user's request",
            )
        ],
        estimated_complexity="simple",
        requires_planning=False,
    )


def _extract_user_request(messages: list[Any]) -> str:
    """Extract the user request from the message list.

    Scans messages in reverse to find the most recent HumanMessage,
    matching the pattern used by initialize_briefing_node.

    Args:
        messages: List of LangGraph message objects.

    Returns:
        User request text, or empty string if none found.
    """
    from langchain_core.messages import HumanMessage

    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            content = msg.content
            return content if isinstance(content, str) else str(content)
    return ""


# Matches a fenced block with an optional language tag (```` ```json ```` or
# bare ``` ``` ```).  DOTALL so the body may span newlines.
_FENCE_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]*)?\s*\n(.*?)\n```", re.DOTALL)


def _extract_json(content: str) -> str:
    """Return the most-likely JSON substring from raw LLM output.

    DeepSeek-thinking and GLM routinely emit reasoning prose before the JSON.
    This recovers the JSON so ``PydanticOutputParser.parse`` does not fail on
    otherwise-valid output.  Strategy, in priority order:

    1. A fenced ```` ```json ... ``` ```` (or bare ``` ``` ```) block.
    2. The first balanced top-level ``{ ... }`` object, scanning with string
       awareness so braces inside JSON string literals do not unbalance it.
    3. The original content unchanged (let ``parser.parse`` raise normally).

    Args:
        content: Raw LLM response text.

    Returns:
        The extracted JSON substring, or *content* unchanged when nothing
        resembling JSON was found.
    """
    fenced = _FENCE_RE.search(content)
    if fenced:
        return fenced.group(1).strip()

    # Balanced-brace scan, string-aware: braces inside "..." (with escaped
    # \") must not affect the depth counter.
    start = content.find("{")
    if start == -1:
        return content

    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(content)):
        ch = content[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return content[start : i + 1]

    # Unbalanced -- let the parser raise with the original content.
    return content


async def planner_node(
    state: dict[str, Any],
    llm: BaseChatModel,
    specialist_catalog: list[dict[str, str]] | None = None,
    planner_prompt_template: str | None = None,
) -> dict[str, Any]:
    """LangGraph planner node that decomposes requests into structured steps.

    Makes a single LLM call to analyze the user request and produce a
    PlanDocument. Falls back to a single-step plan on any error.

    Three execution paths (checked in order):

    1. **Replan**: When ``replan_context`` is present alongside an existing
       plan, revises pending steps while preserving completed ones.
    2. **Resume**: When ``plan_data`` already exists with incomplete steps,
       returns it unchanged without an LLM call.
    3. **Fresh plan**: Analyzes the user request from scratch.

    Args:
        state: Current BackcastSupervisorState dict.
        llm: LangChain chat model for the planning call.
        specialist_catalog: Optional specialist catalog for dynamic prompts.
            Each entry must have ``name`` and ``description`` keys.
        planner_prompt_template: Optional custom prompt template for the
            planner system message.  Supports ``{specialist_section}``
            placeholder.

    Returns:
        State update dict with ``plan_data`` field containing the
        serialized PlanDocument.
    """
    # Replan path: takes priority over resume path
    replan_context = state.get("replan_context", "")
    if replan_context and state.get("plan_data"):
        existing_plan = PlanDocument.from_state(state["plan_data"])
        briefing_data = state.get("briefing_data")
        briefing_context: str | None = None
        if briefing_data:
            from app.ai.briefing import BriefingDocument

            doc = BriefingDocument.from_state(briefing_data)
            if doc.sections:
                briefing_context = doc.to_markdown()

        catalog = specialist_catalog or _DEFAULT_SPECIALIST_CATALOG
        valid_names = frozenset(entry["name"] for entry in catalog)

        specialist_section = _build_specialist_section(catalog)
        replan_prompt = render_prompt(
            _REPLANNER_PROMPT_TEMPLATE,
            replan_reason=replan_context,
            existing_plan_text=existing_plan.to_prompt_text(),
            briefing_context=briefing_context or "No findings yet.",
            specialist_section=specialist_section,
        )

        messages = state.get("messages", [])
        user_request = _extract_user_request(messages) or existing_plan.original_request
        prompt = _build_planner_prompt(user_request, briefing_context)

        parser: PydanticOutputParser[PlannerOutput] = PydanticOutputParser(
            pydantic_object=PlannerOutput
        )
        system_content = replan_prompt + "\n\n" + parser.get_format_instructions()

        try:
            # Retry the TRANSPORT call only.  A transient provider/network
            # error is retried with backoff so a single hiccup does not
            # silently collapse the replan.  A parse failure below is NOT
            # retried (handled in its own branch).
            response = await invoke_with_retry(
                lambda: llm.ainvoke(
                    [
                        SystemMessage(content=system_content),
                        HumanMessage(content=prompt),
                    ]
                ),
                label="planner",
                max_retries=settings.AI_SPECIALIST_MAX_RETRIES,
                timeout=float(settings.AI_PLANNER_STEP_TIMEOUT),
            )
        except Exception:
            logger.exception("[PLANNER] replan llm_call_failed, keeping existing plan")
            plan = existing_plan
        else:
            content = response.content
            if not isinstance(content, str):
                content = str(content)
            try:
                planner_output = parser.parse(_extract_json(content))
            except Exception:
                logger.warning(
                    "[PLANNER] replan parse_failed, keeping existing plan: %s",
                    content[:200],
                )
                plan = existing_plan
            else:
                plan = _merge_replanned_steps(
                    existing_plan, planner_output, valid_names
                )

        logger.info(
            "[PLANNER] Replan complete: %d steps (%d completed preserved, %d revised)",
            len(plan.steps),
            len([s for s in plan.steps if s.status == "completed"]),
            len([s for s in plan.steps if s.status == "pending"]),
        )

        return {
            "plan_data": plan.model_dump(),
            "replan_context": "",  # Clear so it's not re-triggered
        }

    # Resume path: if plan_data already exists with incomplete steps,
    # skip the LLM call and return the existing plan.
    existing_plan_data = state.get("plan_data")
    if existing_plan_data:
        existing_plan = PlanDocument.from_state(existing_plan_data)
        first_incomplete = existing_plan.get_first_incomplete_step_index()
        if first_incomplete is not None:
            logger.info(
                "[PLANNER] Resuming existing plan: %d steps, first incomplete at %d",
                len(existing_plan.steps),
                first_incomplete,
            )
            return {"plan_data": existing_plan.model_dump()}

    messages = state.get("messages", [])
    user_request = _extract_user_request(messages)

    if not user_request:
        logger.warning("[PLANNER] No user request found, using fallback plan")
        plan = _fallback_plan("(no request)")
        return {"plan_data": plan.model_dump()}

    # Extract briefing context for follow-up messages
    briefing_context = None
    briefing_data = state.get("briefing_data")
    if briefing_data:
        from app.ai.briefing import BriefingDocument

        doc = BriefingDocument.from_state(briefing_data)
        if doc.sections:
            briefing_context = doc.to_markdown()

    prompt = _build_planner_prompt(user_request, briefing_context)

    # Extract valid specialist names from catalog for validation
    catalog = specialist_catalog or _DEFAULT_SPECIALIST_CATALOG
    valid_names = frozenset(entry["name"] for entry in catalog)

    # Use PydanticOutputParser instead of with_structured_output.
    # with_structured_output uses function_calling internally (tool_choice),
    # which DeepSeek rejects in thinking mode and z.ai/GLM can't parse
    # reliably. PydanticOutputParser works purely via prompt instructions.
    parser = PydanticOutputParser(pydantic_object=PlannerOutput)
    system_content = (
        build_planner_system_prompt(
            specialist_catalog, custom_template=planner_prompt_template
        )
        + "\n\n"
        + parser.get_format_instructions()
    )
    try:
        # Retry the TRANSPORT call only.  A transient provider/network
        # error is retried with backoff so a single hiccup does not
        # silently collapse a multi-step plan into the single-step
        # fallback.  A parse failure below is NOT retried (handled in its
        # own branch).
        response = await invoke_with_retry(
            lambda: llm.ainvoke(
                [
                    SystemMessage(content=system_content),
                    HumanMessage(content=prompt),
                ]
            ),
            label="planner",
            max_retries=settings.AI_SPECIALIST_MAX_RETRIES,
            timeout=float(settings.AI_PLANNER_STEP_TIMEOUT),
        )
    except Exception:
        logger.exception("[PLANNER] llm_call_failed, falling back to single step")
        plan = _fallback_plan(user_request)
    else:
        content = response.content
        if not isinstance(content, str):
            content = str(content)
        try:
            planner_output = parser.parse(_extract_json(content))
        except Exception:
            logger.warning(
                "[PLANNER] parse_failed, falling back to single step: %s",
                content[:200],
            )
            plan = _fallback_plan(user_request)
        else:
            logger.debug("[PLANNER] Parsed output: %s", planner_output)
            plan = _convert_planner_output(
                planner_output, valid_specialists=valid_names
            )

    logger.info(
        "[PLANNER] Plan created: complexity=%s, steps=%d, requires_planning=%s",
        plan.estimated_complexity,
        len(plan.steps),
        plan.requires_planning,
    )

    return {"plan_data": plan.model_dump()}


__all__ = [
    "PLANNER_SYSTEM_PROMPT",
    "build_planner_system_prompt",
    "planner_node",
    "_MAX_PLAN_STEPS",
    "_merge_replanned_steps",
]
