"""Tests for resilience hardening of the planner's LLM call.

The planner's ``llm.ainvoke([...])`` (both the fresh-plan and the replan
path) is now wrapped in
:func:`app.ai.execution.llm_retry.invoke_with_retry`, so a transient
provider/network error is retried instead of silently collapsing the
plan into the single-step fallback.  Crucially only the *transport* call
(``ainvoke``) is retried; a parse failure must NOT be retried and must
keep falling back exactly once.

These tests use a fake LLM with controllable ``.ainvoke`` behaviour and
patch ``asyncio.sleep`` so the exponential backoff does not slow the
suite (the hang test uses a tiny real sleep).
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import HumanMessage

from app.ai.plan import PlanDocument
from app.ai.planner import planner_node

_SPECIALIST_CATALOG: list[dict[str, str]] = [
    {"name": "evm_analyst", "description": "EVM metric analysis"},
    {"name": "visualization_specialist", "description": "Charts and dashboards"},
]


class FakeLLM:
    """Minimal async LLM stub: records calls, raises or returns per-call."""

    def __init__(self, behaviors: list[Any]) -> None:
        """``behaviors`` are either Exceptions to raise or values to return."""
        self._behaviors = list(behaviors)
        self.ainvoke_count = 0

    async def ainvoke(self, _messages: Any) -> MagicMock:  # noqa: D401, ANN001
        if self.ainvoke_count >= len(self._behaviors):
            raise AssertionError(
                f"FakeLLM.ainvoke called {self.ainvoke_count + 1} times but only "
                f"{len(self._behaviors)} behaviours configured"
            )
        behavior = self._behaviors[self.ainvoke_count]
        self.ainvoke_count += 1
        if isinstance(behavior, BaseException):
            raise behavior
        return behavior


def _response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    return msg


def _valid_two_step_json() -> str:
    """Valid 2-step plan JSON the parser accepts."""
    return (
        '{"original_request":"Analyze EVM and build a dashboard",'
        '"requires_planning":true,"estimated_complexity":"moderate",'
        '"steps":['
        '{"step_index":0,"specialist":"evm_analyst",'
        '"task_description":"Calculate CPI/SPI","dependencies":[],'
        '"expected_output":"CPI and SPI"},'
        '{"step_index":1,"specialist":"visualization_specialist",'
        '"task_description":"Build dashboard","dependencies":[0],'
        '"expected_output":"Dashboard"}'
        "]}"
    )


def _patch_sleep_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``asyncio.sleep`` so backoff delays are instant."""

    async def _no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)


# =====================================================================
# Fresh plan: transient error then success -> NO fallback
# =====================================================================


@pytest.mark.asyncio
async def test_fresh_plan_transient_then_success_produces_multi_step_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transient transport error on attempt 0 is retried; the recovered
    response yields the full 2-step plan (NOT the single-step fallback)."""
    _patch_sleep_noop(monkeypatch)

    llm = FakeLLM(
        [
            ConnectionResetError("transient reset"),  # attempt 0: retryable
            _response(_valid_two_step_json()),  # attempt 1: success
        ]
    )

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze EVM and build a dashboard")],
    }
    result = await planner_node(state, llm, specialist_catalog=_SPECIALIST_CATALOG)
    plan = PlanDocument.from_state(result["plan_data"])

    assert llm.ainvoke_count == 2  # retried once
    assert plan.requires_planning is True
    assert len(plan.steps) == 2
    assert plan.steps[0].specialist == "evm_analyst"
    assert plan.steps[1].specialist == "visualization_specialist"


# =====================================================================
# Fresh plan: unparseable content -> parse failure NOT retried
# =====================================================================


@pytest.mark.asyncio
async def test_fresh_plan_unparseable_content_not_retried_falls_back_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A parse failure (not a transport failure) must NOT be retried.

    ``ainvoke`` must be called exactly once; the fallback single-step plan
    is produced.
    """
    _patch_sleep_noop(monkeypatch)

    llm = FakeLLM([_response("cannot produce JSON, sorry")])

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="do something vague")],
    }
    result = await planner_node(state, llm, specialist_catalog=_SPECIALIST_CATALOG)
    plan = PlanDocument.from_state(result["plan_data"])

    assert llm.ainvoke_count == 1  # parse failure NOT retried
    assert len(plan.steps) == 1
    assert plan.steps[0].specialist == "general_purpose"


# =====================================================================
# Fresh plan: ainvoke hangs -> deadline fires -> fallback
# =====================================================================


@pytest.mark.asyncio
async def test_fresh_plan_hanging_ainvoke_deadline_fires_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A provider stall (no exception) trips the planner step-timeout.

    The default ``AI_PLANNER_STEP_TIMEOUT`` is 120s -- too long for a test.
    Patch the setting to 0.2s so the hang trips the deadline quickly.
    """
    _patch_sleep_noop(monkeypatch)
    monkeypatch.setattr("app.ai.planner.settings.AI_PLANNER_STEP_TIMEOUT", 2)
    monkeypatch.setattr("app.ai.planner.settings.AI_SPECIALIST_MAX_RETRIES", 0)

    class _HangLLM:
        async def ainvoke(self, _messages: Any) -> MagicMock:  # noqa: ANN001
            await asyncio.sleep(5.0)  # well past the 2s deadline
            return _response("never reached")

    llm = _HangLLM()
    state: dict[str, Any] = {
        "messages": [HumanMessage(content="do something")],
    }
    result = await planner_node(state, llm, specialist_catalog=_SPECIALIST_CATALOG)
    plan = PlanDocument.from_state(result["plan_data"])

    # Fallback single-step plan because the deadline fired and retries
    # were exhausted.
    assert len(plan.steps) == 1
    assert plan.steps[0].specialist == "general_purpose"


# =====================================================================
# Replan path: transient then success -> keeps existing plan structure
# =====================================================================


def _existing_plan() -> PlanDocument:
    from app.ai.plan import PlanStep

    return PlanDocument(
        original_request="Analyze EVM and build a dashboard",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI/SPI",
                status="completed",
                result_summary="CPI=0.94",
            ),
            PlanStep(
                step_index=1,
                specialist="visualization_specialist",
                task_description="Build dashboard",
                status="pending",
                dependencies=[0],
            ),
        ],
        estimated_complexity="moderate",
        requires_planning=True,
    )


@pytest.mark.asyncio
async def test_replan_transient_then_success_keeps_and_revises_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replan path also retries transient transport errors.

    After recovery the replan merge still runs (existing completed step 0
    preserved)."""
    _patch_sleep_noop(monkeypatch)

    revised_json = (
        '{"original_request":"Analyze EVM and build a dashboard",'
        '"requires_planning":true,"estimated_complexity":"moderate",'
        '"steps":[{"step_index":0,"specialist":"visualization_specialist",'
        '"task_description":"Build dashboard from CPI/SPI",'
        '"dependencies":[],"expected_output":"Dashboard"}]}'
    )
    llm = FakeLLM(
        [
            ConnectionResetError("transient reset"),  # attempt 0: retryable
            _response(revised_json),  # attempt 1: success
        ]
    )

    existing = _existing_plan()
    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze EVM and build a dashboard")],
        "plan_data": existing.model_dump(),
        "replan_context": "step 1 needs revision",
        "briefing_data": None,
    }
    result = await planner_node(state, llm, specialist_catalog=_SPECIALIST_CATALOG)
    plan = PlanDocument.from_state(result["plan_data"])

    assert llm.ainvoke_count == 2  # retried once
    # Completed step preserved; revised step merged.
    assert plan.steps[0].status == "completed"
    assert any(
        s.specialist == "visualization_specialist" and s.status == "pending"
        for s in plan.steps
    )
