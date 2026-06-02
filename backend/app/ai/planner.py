"""Planner node for request decomposition into structured PlanDocument steps.

Single LLM call that analyzes the user request and produces a PlanDocument:
- Simple requests -> single-step plan (requires_planning=False)
- Complex requests -> multi-step plan with specialist assignments and
  dependencies (requires_planning=True)

Inserted between initialize_briefing and supervisor in the graph flow:
    START -> initialize_briefing -> planner -> supervisor <-> specialists -> END
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.plan import VALID_SPECIALISTS, PlanDocument, PlanStep

logger = logging.getLogger(__name__)


_PLANNER_PROMPT_TEMPLATE = """\
You are a request planner for the Backcast project budget management system.

Analyze the user's request and decide whether it needs multi-step execution \
or can be handled by a single specialist.

{specialist_section}

## Your Task

Return a JSON object with this structure:
{{
  "original_request": "<the user's request>",
  "requires_planning": true/false,
  "estimated_complexity": "simple" | "moderate" | "complex",
  "steps": [
    {{
      "step_index": 0,
      "specialist": "<specialist_name>",
      "task_description": "<focused description of what this step should do>",
      "dependencies": [],
      "expected_output": "<what this step should produce>"
    }}
  ]
}}

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
- Maximum 5 steps
- Return ONLY valid JSON, no markdown fences, no commentary
"""

_DEFAULT_SPECIALIST_CATALOG: list[dict[str, str]] = [
    {
        "name": "project_manager",
        "description": "Project CRUD, WBS elements, cost elements, cost tracking, progress entries",
    },
    {
        "name": "evm_analyst",
        "description": "Earned Value Management calculations, performance indices, variance analysis",
    },
    {
        "name": "change_order_manager",
        "description": "Change orders, impact analysis, branch operations",
    },
    {
        "name": "user_admin",
        "description": "User accounts, departments, role management",
    },
    {
        "name": "visualization_specialist",
        "description": "Charts, diagrams, visual representations",
    },
    {
        "name": "forecast_manager",
        "description": "Forecasts, schedule baselines, projection models",
    },
    {
        "name": "mcp_specialist",
        "description": "External tools via MCP servers (web search, database queries)",
    },
    {
        "name": "accountant",
        "description": "Cost registrations, cost events, documentation, financial tracking",
    },
    {
        "name": "general_purpose",
        "description": "Unclear or cross-cutting requests that don't fit one domain",
    },
]


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
        return template.replace("{specialist_section}", specialist_section, 1)
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


def _parse_plan_response(raw: str, user_request: str) -> PlanDocument:
    """Parse the LLM response into a PlanDocument.

    Handles common LLM output issues: markdown fences, trailing commas,
    missing fields. Falls back to a single-step plan on any parse failure.

    Args:
        raw: Raw text from the LLM response.
        user_request: Original user request (used in fallback).

    Returns:
        Parsed PlanDocument, or a single-step fallback.
    """
    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        first_newline = text.index("\n") if "\n" in text else len(text)
        text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[: -len("```")]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("[PLANNER] JSON parse failed, falling back to single step")
        return _fallback_plan(user_request)

    # Validate required fields exist
    if not isinstance(data, dict) or "steps" not in data:
        logger.warning("[PLANNER] Unexpected response shape, falling back")
        return _fallback_plan(user_request)

    # Normalize steps
    steps: list[PlanStep] = []
    raw_steps = data.get("steps", [])
    if not isinstance(raw_steps, list):
        return _fallback_plan(user_request)

    for i, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, dict):
            continue

        specialist = raw_step.get("specialist", "general_purpose")
        if specialist not in VALID_SPECIALISTS:
            logger.warning(
                "[PLANNER] Unknown specialist '%s', defaulting to general_purpose",
                specialist,
            )
            specialist = "general_purpose"

        steps.append(
            PlanStep(
                step_index=i,
                specialist=specialist,
                task_description=raw_step.get("task_description", ""),
                dependencies=raw_step.get("dependencies", []),
                expected_output=raw_step.get("expected_output", ""),
            )
        )

    if not steps:
        return _fallback_plan(user_request)

    return PlanDocument(
        original_request=data.get("original_request", user_request),
        steps=steps,
        estimated_complexity=data.get("estimated_complexity", "simple"),
        requires_planning=bool(data.get("requires_planning", False)),
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


async def planner_node(
    state: dict[str, Any],
    llm: BaseChatModel,
    specialist_catalog: list[dict[str, str]] | None = None,
    planner_prompt_template: str | None = None,
) -> dict[str, Any]:
    """LangGraph planner node that decomposes requests into structured steps.

    Makes a single LLM call to analyze the user request and produce a
    PlanDocument. Falls back to a single-step plan on any error.

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
    messages = state.get("messages", [])
    user_request = _extract_user_request(messages)

    if not user_request:
        logger.warning("[PLANNER] No user request found, using fallback plan")
        plan = _fallback_plan("(no request)")
        return {"plan_data": plan.model_dump()}

    # Extract briefing context for follow-up messages
    briefing_context: str | None = None
    briefing_data = state.get("briefing_data")
    if briefing_data:
        from app.ai.briefing import BriefingDocument

        doc = BriefingDocument.from_state(briefing_data)
        if doc.sections:
            briefing_context = doc.to_markdown()

    prompt = _build_planner_prompt(user_request, briefing_context)

    try:
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content=build_planner_system_prompt(
                        specialist_catalog, custom_template=planner_prompt_template
                    )
                ),
                HumanMessage(content=prompt),
            ]
        )
        raw_text = response.content
        if isinstance(raw_text, list):
            raw_text = " ".join(part for part in raw_text if isinstance(part, str))
        plan = _parse_plan_response(raw_text, user_request)
    except Exception:
        logger.exception("[PLANNER] LLM call failed, falling back to single step")
        plan = _fallback_plan(user_request)

    logger.info(
        "[PLANNER] Plan created: complexity=%s, steps=%d, requires_planning=%s",
        plan.estimated_complexity,
        len(plan.steps),
        plan.requires_planning,
    )

    return {"plan_data": plan.model_dump()}


__all__ = ["PLANNER_SYSTEM_PROMPT", "build_planner_system_prompt", "planner_node"]
