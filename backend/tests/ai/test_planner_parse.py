"""Tests for resilient LLM-output parsing in the planner node.

Covers the two chokepoints where a raw LLM response is turned into a
``PlanDocument``: the fresh-plan path and the replan path. DeepSeek-thinking
and GLM routinely emit reasoning prose before (or instead of) the JSON, so the
planner must (a) tolerate fenced/unfenced JSON buried in prose and (b) report
the two distinct failure modes -- ``llm_call_failed`` vs ``parse_failed`` --
with greppable, distinguishable log tags.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from app.ai.plan import (
    PlanDocument,
    PlannerOutput,
    PlannerStepOutput,
    PlanStep,
)
from app.ai.planner import _extract_json, planner_node

# ---------------------------------------------------------------------------
# Catalog + fixtures shared with test_replan_integration.py conventions
# ---------------------------------------------------------------------------

_SPECIALIST_CATALOG: list[dict[str, str]] = [
    {"name": "evm_analyst", "description": "EVM metric analysis"},
    {"name": "visualization_specialist", "description": "Charts and dashboards"},
]


def _two_step_output() -> PlannerOutput:
    """Valid 2-step planner output used across fresh-plan tests."""
    return PlannerOutput(
        original_request="Analyze EVM and build a dashboard",
        requires_planning=True,
        estimated_complexity="moderate",
        steps=[
            PlannerStepOutput(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI and SPI for the project",
                dependencies=[],
                expected_output="CPI and SPI values",
            ),
            PlannerStepOutput(
                step_index=1,
                specialist="visualization_specialist",
                task_description="Build EVM performance dashboard",
                dependencies=[0],
                expected_output="Interactive EVM dashboard",
            ),
        ],
    )


def _make_llm_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    return msg


# ---------------------------------------------------------------------------
# Fresh-plan path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fresh_plan_recovers_json_from_fenced_reasoning_preamble() -> None:
    """Fenced JSON after reasoning prose yields the full 2-step plan.

    Regression for DeepSeek-thinking/GLM behaviour: the model emits a chain
    of reasoning BEFORE the fenced ```json ... ``` block. Extraction must
    recover the block so the multi-step intent does not silently collapse
    into the single-step fallback.
    """
    valid = _two_step_output()
    raw_content = (
        "Let me analyze this request.\n"
        "First I'll consider the EVM metrics, then the dashboard.\n"
        "```json\n" + valid.model_dump_json() + "\n```\n"
    )

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = _make_llm_response(raw_content)

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze EVM and build a dashboard")],
    }

    result = await planner_node(state, mock_llm, specialist_catalog=_SPECIALIST_CATALOG)
    plan = PlanDocument.from_state(result["plan_data"])

    # NOT the 1-step fallback: the 2-step intent must survive.
    assert plan.requires_planning is True
    assert len(plan.steps) == 2
    assert plan.steps[0].specialist == "evm_analyst"
    assert plan.steps[1].specialist == "visualization_specialist"
    assert plan.steps[1].dependencies == [0]
    mock_llm.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_fresh_plan_recovers_unfenced_json_with_leading_and_trailing_prose() -> (
    None
):
    """Unfenced JSON surrounded by prose is recovered via balanced-brace extraction."""
    valid = _two_step_output()
    payload = valid.model_dump()
    raw_content = (
        "Here is my plan for this request.\n\n"
        + json.dumps(payload)
        + "\n\nLet me know if you need adjustments."
    )

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = _make_llm_response(raw_content)

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze EVM and build a dashboard")],
    }

    result = await planner_node(state, mock_llm, specialist_catalog=_SPECIALIST_CATALOG)
    plan = PlanDocument.from_state(result["plan_data"])

    assert plan.requires_planning is True
    assert len(plan.steps) == 2
    assert plan.steps[0].specialist == "evm_analyst"
    assert plan.steps[1].specialist == "visualization_specialist"


@pytest.mark.asyncio
async def test_fresh_plan_unparseable_content_falls_back_and_logs_parse_failed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Pure prose with no JSON falls back to single step AND logs ``parse_failed``.

    Crucially the tag must be ``parse_failed`` (NOT ``llm_call_failed``) so the
    two failure modes are distinguishable in logs.
    """
    raw_content = (
        "I'm not sure how to structure this. "
        "The request is ambiguous and I cannot produce a plan."
    )

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = _make_llm_response(raw_content)

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="do something vague")],
    }

    with caplog.at_level(logging.WARNING, logger="app.ai.planner"):
        result = await planner_node(
            state, mock_llm, specialist_catalog=_SPECIALIST_CATALOG
        )

    plan = PlanDocument.from_state(result["plan_data"])

    # Single-step fallback
    assert len(plan.steps) == 1
    assert plan.steps[0].specialist == "general_purpose"
    assert plan.requires_planning is False

    # parse_failed logged at WARNING; llm_call_failed must NOT appear.
    messages = [r.getMessage() for r in caplog.records]
    assert any("parse_failed" in m for m in messages), messages
    assert not any("llm_call_failed" in m for m in messages), messages


@pytest.mark.asyncio
async def test_fresh_plan_ainvoke_raises_falls_back_and_logs_llm_call_failed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When ainvoke itself raises, fallback fires AND the tag is ``llm_call_failed``.

    This must be distinguishable from a parse failure so operators can tell
    provider/network errors apart from parsing errors.
    """
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = RuntimeError("provider timeout")

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="do something")],
    }

    with caplog.at_level(logging.WARNING, logger="app.ai.planner"):
        result = await planner_node(
            state, mock_llm, specialist_catalog=_SPECIALIST_CATALOG
        )

    plan = PlanDocument.from_state(result["plan_data"])

    # Single-step fallback
    assert len(plan.steps) == 1
    assert plan.steps[0].specialist == "general_purpose"

    messages = [r.getMessage() for r in caplog.records]
    assert any("llm_call_failed" in m for m in messages), messages
    assert not any("parse_failed" in m for m in messages), messages


# ---------------------------------------------------------------------------
# Replan path
# ---------------------------------------------------------------------------


def _existing_plan_with_completed_step0() -> PlanDocument:
    return PlanDocument(
        original_request="Analyze EVM and build a dashboard",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI and SPI for the project",
                status="completed",
                result_summary="CPI=0.94, SPI=1.02",
            ),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="Calculate EVM composite metrics",
                status="pending",
                dependencies=[0],
            ),
        ],
        estimated_complexity="moderate",
        requires_planning=True,
    )


def _revised_output() -> PlannerOutput:
    return PlannerOutput(
        original_request="Analyze EVM and build a dashboard",
        requires_planning=True,
        estimated_complexity="moderate",
        steps=[
            PlannerStepOutput(
                step_index=0,
                specialist="visualization_specialist",
                task_description="Build EVM dashboard from CPI/SPI data",
                dependencies=[],
                expected_output="Interactive EVM dashboard",
            ),
        ],
    )


@pytest.mark.asyncio
async def test_replan_recovers_json_from_fenced_reasoning_preamble() -> None:
    """Replan merges the LLM's revision even when JSON is buried in prose.

    Must NOT keep the existing plan verbatim (which is what happens today when
    the bare ``except`` swallows the parse error).
    """
    existing_plan = _existing_plan_with_completed_step0()
    revised = _revised_output()
    raw_content = (
        "Revising the plan based on findings.\n"
        "Step 1 is redundant because composites are derivable.\n"
        "```json\n" + revised.model_dump_json() + "\n```\n"
    )

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = _make_llm_response(raw_content)

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze EVM and build a dashboard")],
        "plan_data": existing_plan.model_dump(),
        "replan_context": "Step 1 redundant after step 0 findings",
        "briefing_data": None,
    }

    result = await planner_node(state, mock_llm, specialist_catalog=_SPECIALIST_CATALOG)
    plan = PlanDocument.from_state(result["plan_data"])

    # Completed step 0 preserved; revised step merged at index 1.
    assert len(plan.steps) == 2
    assert plan.steps[0].status == "completed"
    assert plan.steps[0].specialist == "evm_analyst"
    assert plan.steps[1].status == "pending"
    assert plan.steps[1].specialist == "visualization_specialist"
    assert "CPI/SPI data" in plan.steps[1].task_description


@pytest.mark.asyncio
async def test_replan_unparseable_keeps_existing_plan_and_logs_parse_failed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unparseable replan content keeps the existing plan AND logs ``parse_failed``."""
    existing_plan = _existing_plan_with_completed_step0()

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = _make_llm_response("Cannot revise, no JSON here.")

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze EVM and build a dashboard")],
        "plan_data": existing_plan.model_dump(),
        "replan_context": "Step 1 redundant",
        "briefing_data": None,
    }

    with caplog.at_level(logging.WARNING, logger="app.ai.planner"):
        result = await planner_node(
            state, mock_llm, specialist_catalog=_SPECIALIST_CATALOG
        )

    plan = PlanDocument.from_state(result["plan_data"])

    # Existing plan kept verbatim.
    assert len(plan.steps) == 2
    assert plan.steps[0].status == "completed"
    assert plan.steps[1].specialist == "evm_analyst"

    messages = [r.getMessage() for r in caplog.records]
    assert any("parse_failed" in m for m in messages), messages
    assert not any("llm_call_failed" in m for m in messages), messages


@pytest.mark.asyncio
async def test_replan_ainvoke_raises_keeps_existing_plan_and_logs_llm_call_failed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When ainvoke raises during replan, existing plan is kept AND tag is ``llm_call_failed``."""
    existing_plan = _existing_plan_with_completed_step0()

    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = RuntimeError("provider 503")

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze EVM and build a dashboard")],
        "plan_data": existing_plan.model_dump(),
        "replan_context": "Step 1 redundant",
        "briefing_data": None,
    }

    with caplog.at_level(logging.WARNING, logger="app.ai.planner"):
        result = await planner_node(
            state, mock_llm, specialist_catalog=_SPECIALIST_CATALOG
        )

    plan = PlanDocument.from_state(result["plan_data"])

    assert len(plan.steps) == 2
    assert plan.steps[0].status == "completed"

    messages = [r.getMessage() for r in caplog.records]
    assert any("llm_call_failed" in m for m in messages), messages
    assert not any("parse_failed" in m for m in messages), messages


# ---------------------------------------------------------------------------
# _extract_json unit tests (the tolerant pre-extraction helper)
# ---------------------------------------------------------------------------


def test_extract_json_returns_fenced_block_when_present() -> None:
    """A ```json ... ``` block is preferred over balanced-brace scanning."""
    raw = 'prose before\n```json\n{"a": 1}\n```\nprose after'
    assert _extract_json(raw) == '{"a": 1}'


def test_extract_json_returns_generic_fenced_block_without_language_tag() -> None:
    """A bare ``` ... ``` fence (no language) is also recovered."""
    raw = 'reasoning\n```\n{"a": 1}\n```\n'
    assert _extract_json(raw) == '{"a": 1}'


def test_extract_json_balances_outer_braces_ignoring_braces_inside_strings() -> None:
    """Without a fence, the first balanced top-level object is returned.

    Braces inside JSON string values must NOT unbalance the scan.
    """
    raw = 'leading prose {"nested": {"k": "}{ unbalanced }{"}, "n": 1} trailing'
    assert _extract_json(raw) == '{"nested": {"k": "}{ unbalanced }{"}, "n": 1}'


def test_extract_json_returns_original_when_no_object_found() -> None:
    """No fence and no balanced object -> return content unchanged so parser.parse raises normally."""
    raw = "just prose, nothing parseable here"
    assert _extract_json(raw) == raw


def test_extract_json_handles_escaped_quotes_inside_strings() -> None:
    """Escaped quotes (``\\"``) inside string literals do not confuse the scanner.

    The value ``"a }{ b \\" c"`` contains a brace pair and an escaped quote
    all inside a single well-formed JSON string; the scanner must treat the
    brace pair as ordinary characters and the escaped quote as non-terminating.
    """
    raw = 'pretext {"msg": "a }{ b \\" c", "n": 2} post'
    assert _extract_json(raw) == '{"msg": "a }{ b \\" c", "n": 2}'
