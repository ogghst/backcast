"""Tests for Phase 4 planner enhancements.

Covers three Phase-4 changes in ``app/ai/planner.py``:

1. **Structured capability-contract catalog.** When every catalog entry's
   ``description`` follows the contract form (``verbs — entities: ... —
   use when: ...``), ``_build_specialist_section`` renders a TABLE
   (``specialist | does (verbs) | over (entities) | when to use``) instead
   of the legacy free-text bullet list.  Free-text entries still render as
   bullets (backward compat).

2. **One-shot re-prompt guard (input validation + re-prompt, NOT regex).**
   When a parsed plan names a specialist NOT in the catalog OR has duplicate
   ``task_description``s, the planner makes ONE retry with a system note
   quoting the violation, then falls back if still invalid.  This replaces
   the old silent ``_convert_planner_output`` default-to-general_purpose for
   the invalid-specialist case (the old path is still the final fallback).

3. ``_extract_json`` is untouched (load-bearing) -- these tests do NOT
   exercise it; see ``test_planner_parse.py``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from app.ai.plan import (
    PlannerOutput,
    PlannerStepOutput,
)
from app.ai.planner import (
    _build_specialist_section,
    _parse_structured_description,
    _validate_planner_output,
    build_planner_system_prompt,
    planner_node,
)

# ---------------------------------------------------------------------------
# Catalog fixtures
# ---------------------------------------------------------------------------

_STRUCTURED_CATALOG: list[dict[str, str]] = [
    {
        "name": "project_manager",
        "description": (
            "create/update/read/delete — entities: Project, WBS, Work Package "
            "— use when: structuring or editing the project breakdown"
        ),
    },
    {
        "name": "evm_analyst",
        "description": (
            "calculate/read — entities: EVM metrics, cost events — use when: "
            "performance analysis or earned-value questions"
        ),
    },
]

_LEGACY_CATALOG: list[dict[str, str]] = [
    {"name": "evm_analyst", "description": "EVM metric analysis"},
    {"name": "visualization_specialist", "description": "Charts and dashboards"},
]


# ===========================================================================
# Part 1: structured catalog table
# ===========================================================================


def test_structured_catalog_renders_a_table_with_headers_and_names() -> None:
    """All-structured catalog -> markdown table with the 4 contract columns
    and one row per specialist name."""
    section = _build_specialist_section(_STRUCTURED_CATALOG)

    assert "| specialist | does (verbs) | over (entities) | when to use |" in section
    assert "|---|---|---|---|" in section
    assert "| project_manager |" in section
    assert "| evm_analyst |" in section
    # Legacy bullet form must NOT appear.
    assert "- project_manager:" not in section


def test_structured_catalog_table_populates_contract_columns() -> None:
    """The verbs / entities / when columns carry the parsed contract values."""
    section = _build_specialist_section(_STRUCTURED_CATALOG)

    assert "create/update/read/delete" in section
    assert "Project, WBS, Work Package" in section
    assert "structuring or editing the project breakdown" in section


def test_legacy_free_text_catalog_falls_back_to_bullets() -> None:
    """A free-text (non-contract) description renders as the legacy bullet."""
    section = _build_specialist_section(_LEGACY_CATALOG)

    assert "- evm_analyst: EVM metric analysis" in section
    # Table header must NOT appear.
    assert "| specialist |" not in section


def test_mixed_catalog_falls_back_to_bullets_when_any_entry_is_free_text() -> None:
    """If any single entry is free-text, the whole section uses bullets
    (all-or-nothing) so a partially-enriched roster degrades cleanly."""
    mixed = [
        _STRUCTURED_CATALOG[0],
        {"name": "x", "description": "just free text, no contract"},
    ]
    section = _build_specialist_section(mixed)
    assert "| specialist |" not in section
    assert "- project_manager:" in section


def test_build_planner_system_prompt_contains_the_table() -> None:
    """The end-to-end rendered planner system prompt embeds the table."""
    prompt = build_planner_system_prompt(_STRUCTURED_CATALOG)
    assert "| specialist | does (verbs) | over (entities) | when to use |" in prompt
    # Granularity guardrails are present too.
    assert "Granularity Rules" in prompt
    assert "Anti-over" in prompt


def test_build_planner_system_prompt_contains_granularity_guardrails() -> None:
    """The default template carries the new granularity principles."""
    prompt = build_planner_system_prompt()  # default catalog
    for phrase in (
        "DEFAULT to single-step",
        "2-4 tool calls",
        "PREFER parallel steps",
        "Anti-under",
    ):
        assert phrase in prompt, phrase


# ===========================================================================
# _parse_structured_description unit cases
# ===========================================================================


@pytest.mark.parametrize(
    "desc",
    [
        # em-dash separator
        "create/read — entities: Project — use when: editing",
        # " - " separator
        "create/read - entities: Project - use when: editing",
        # en-dash separator
        "create/read – entities: Project – use when: editing",
    ],
)
def test_parse_structured_description_accepts_dash_variants(desc: str) -> None:
    parsed = _parse_structured_description(desc)
    assert parsed is not None
    assert parsed["verbs"] == "create/read"
    assert parsed["entities"] == "Project"
    assert parsed["when"] == "editing"


def test_parse_structured_description_returns_none_for_free_text() -> None:
    assert _parse_structured_description("EVM metric analysis") is None
    assert _parse_structured_description("no markers here at all") is None


# ===========================================================================
# Part 2: _validate_planner_output (input validation helper)
# ===========================================================================


_VALID: frozenset[str] = frozenset({"project_manager", "evm_analyst"})


def _output(steps: list[tuple[str, str]]) -> PlannerOutput:
    return PlannerOutput(
        original_request="x",
        requires_planning=True,
        estimated_complexity="moderate",
        steps=[
            PlannerStepOutput(
                step_index=i,
                specialist=spec,
                task_description=desc,
                dependencies=[],
                expected_output=f"out {i}",
            )
            for i, (spec, desc) in enumerate(steps)
        ],
    )


def test_validate_returns_none_for_valid_plan() -> None:
    out = _output([("evm_analyst", "calc CPI"), ("project_manager", "list WBS")])
    assert _validate_planner_output(out, _VALID) is None


def test_validate_flags_unknown_specialist() -> None:
    out = _output([("forecast_manager", "gather forecasts")])
    reason = _validate_planner_output(out, _VALID)
    assert reason is not None
    assert "forecast_manager" in reason
    assert "evm_analyst" in reason  # valid list quoted


def test_validate_flags_duplicate_task_descriptions() -> None:
    out = _output(
        [("evm_analyst", "Calculate CPI"), ("project_manager", "Calculate CPI")]
    )
    reason = _validate_planner_output(out, _VALID)
    assert reason is not None
    assert "duplicate task_descriptions" in reason


def test_validate_duplicate_is_case_insensitive_and_whitespace_insensitive() -> None:
    out = _output(
        [
            ("evm_analyst", "  Calculate CPI  "),
            ("project_manager", "calculate cpi"),
        ]
    )
    reason = _validate_planner_output(out, _VALID)
    assert reason is not None and "duplicate" in reason


# ===========================================================================
# Part 3: one-shot re-prompt guard in planner_node (fresh-plan path)
# ===========================================================================


def _make_llm_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    return msg


def _invalid_specialist_json() -> str:
    """A well-formed plan JSON that names a specialist NOT in the catalog."""
    return (
        '{"original_request":"do x","requires_planning":true,'
        '"estimated_complexity":"moderate","steps":['
        '{"step_index":0,"specialist":"forecast_manager",'
        '"task_description":"gather forecasts","dependencies":[],'
        '"expected_output":"forecasts"}]}'
    )


def _valid_specialist_json() -> str:
    return (
        '{"original_request":"do x","requires_planning":true,'
        '"estimated_complexity":"moderate","steps":['
        '{"step_index":0,"specialist":"evm_analyst",'
        '"task_description":"calc CPI","dependencies":[],'
        '"expected_output":"CPI"}]}'
    )


def _duplicate_task_json() -> str:
    return (
        '{"original_request":"do x","requires_planning":true,'
        '"estimated_complexity":"moderate","steps":['
        '{"step_index":0,"specialist":"evm_analyst",'
        '"task_description":"Calculate CPI","dependencies":[],'
        '"expected_output":"CPI"},'
        '{"step_index":1,"specialist":"project_manager",'
        '"task_description":"Calculate CPI","dependencies":[],'
        '"expected_output":"CPI"}]}'
    )


@pytest.mark.asyncio
async def test_invalid_specialist_triggers_one_retry_then_success() -> None:
    """First call returns an unknown specialist; the re-prompt retry returns
    a valid plan.  Exactly TWO ainvoke calls; the plan is NOT the fallback."""
    responses = [
        _make_llm_response(_invalid_specialist_json()),
        _make_llm_response(_valid_specialist_json()),
    ]
    call_contents: list[str] = []

    class _LLM:
        def __init__(self) -> None:
            self.ainvoke_count = 0

        async def ainvoke(self, messages: Any) -> MagicMock:  # noqa: ANN001
            self.ainvoke_count += 1
            # Capture the system message so we can assert the violation was quoted.
            sys_msg = messages[0].content
            call_contents.append(sys_msg)
            return responses[self.ainvoke_count - 1]

    llm = _LLM()
    state = {"messages": [HumanMessage(content="do x")]}
    result = await planner_node(state, llm, specialist_catalog=_STRUCTURED_CATALOG)
    plan = result["plan_data"]

    assert llm.ainvoke_count == 2  # one initial + one re-prompt
    # The re-prompt system message quoted the violation.
    assert any("forecast_manager" in c for c in call_contents[1:])
    # Not the fallback: specialist is the corrected one.
    assert plan["steps"][0]["specialist"] == "evm_analyst"
    assert plan["requires_planning"] is True


@pytest.mark.asyncio
async def test_invalid_specialist_then_still_invalid_falls_back() -> None:
    """Both calls return an unknown specialist; after ONE retry the planner
    falls back to the single-step general_purpose plan."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = _make_llm_response(_invalid_specialist_json())

    state = {"messages": [HumanMessage(content="do x")]}
    result = await planner_node(state, mock_llm, specialist_catalog=_STRUCTURED_CATALOG)
    plan = result["plan_data"]

    assert mock_llm.ainvoke.await_count == 2  # one initial + one retry, then give up
    # Fallback single-step general_purpose.
    assert len(plan["steps"]) == 1
    assert plan["steps"][0]["specialist"] == "general_purpose"


@pytest.mark.asyncio
async def test_duplicate_task_descriptions_triggers_re_prompt_guard() -> None:
    """Duplicate task_descriptions are an anti-over violation -> one retry."""
    responses = [
        _make_llm_response(_duplicate_task_json()),
        _make_llm_response(_valid_specialist_json()),
    ]
    call_contents: list[str] = []

    class _LLM:
        def __init__(self) -> None:
            self.ainvoke_count = 0

        async def ainvoke(self, messages: Any) -> MagicMock:  # noqa: ANN001
            self.ainvoke_count += 1
            call_contents.append(messages[0].content)
            return responses[self.ainvoke_count - 1]

    llm = _LLM()
    state = {"messages": [HumanMessage(content="do x")]}
    result = await planner_node(state, llm, specialist_catalog=_STRUCTURED_CATALOG)

    assert llm.ainvoke_count == 2
    # The retry message quoted the duplicate violation.
    assert any("duplicate task_descriptions" in c for c in call_contents[1:])
    # Corrected plan survived.
    assert result["plan_data"]["steps"][0]["specialist"] == "evm_analyst"


@pytest.mark.asyncio
async def test_valid_plan_does_not_trigger_re_prompt() -> None:
    """A valid first plan makes exactly ONE ainvoke call (no retry)."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = _make_llm_response(_valid_specialist_json())

    state = {"messages": [HumanMessage(content="do x")]}
    await planner_node(state, mock_llm, specialist_catalog=_STRUCTURED_CATALOG)

    assert mock_llm.ainvoke.await_count == 1


@pytest.mark.asyncio
async def test_re_prompt_guard_uses_input_validation_not_output_regex(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The guard is input-validation + re-prompt, signalled by the
    ``invalid_plan (re-prompting once)`` log tag, not output surgery."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = _make_llm_response(_invalid_specialist_json())

    with caplog.at_level(__import__("logging").WARNING, logger="app.ai.planner"):
        await planner_node(
            {"messages": [HumanMessage(content="do x")]},
            mock_llm,
            specialist_catalog=_STRUCTURED_CATALOG,
        )

    messages = [r.getMessage() for r in caplog.records]
    assert any("invalid_plan (re-prompting once)" in m for m in messages), messages
