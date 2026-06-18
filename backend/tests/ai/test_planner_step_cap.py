"""Tests for the hard cap on plan step count (D2).

The planner prompt requests "Maximum 5 steps" but, before D2, nothing
enforced that in code. An LLM that ignored the prompt could emit an
8-step plan, which inflated the supervisor iteration budget
(``len(plan.steps) + 1``) and compounded token cost / context growth.

These tests lock in the two enforcement points:
- ``_convert_planner_output`` truncates a fresh plan to ``_MAX_PLAN_STEPS``.
- ``_merge_replanned_steps`` caps revised steps so completed + revised
  stays at or below ``_MAX_PLAN_STEPS`` (completed steps are LOCKED).
- The supervisor router bounds ``plan_max`` at ``_MAX_PLAN_STEPS + 1`` so
  even a pathological plan cannot inflate the iteration budget.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from app.ai.plan import (
    PlanDocument,
    PlannerOutput,
    PlannerStepOutput,
    PlanStep,
)
from app.ai.planner import (
    _MAX_PLAN_STEPS,
    _convert_planner_output,
    _merge_replanned_steps,
)
from app.ai.supervisor_orchestrator import SupervisorOrchestrator

_VALID_SPECIALISTS: frozenset[str] = frozenset(
    {"project_manager", "evm_analyst", "visualization_specialist"}
)


def _make_planner_output(n_steps: int) -> PlannerOutput:
    """Build a PlannerOutput with ``n_steps`` valid specialist steps."""
    return PlannerOutput(
        original_request="Complex multi-step request",
        requires_planning=True,
        estimated_complexity="complex",
        steps=[
            PlannerStepOutput(
                step_index=i,
                specialist="evm_analyst",
                task_description=f"Step {i} task",
                dependencies=[],
                expected_output=f"Step {i} output",
            )
            for i in range(n_steps)
        ],
    )


# ---------------------------------------------------------------------------
# _convert_planner_output (fresh plans)
# ---------------------------------------------------------------------------


def test_convert_planner_output_truncates_above_max(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An 8-step plan is truncated to _MAX_PLAN_STEPS with a WARNING.

    Indices must be renumbered positionally to stay 0..n-1 contiguous.
    """
    output = _make_planner_output(n_steps=8)

    with caplog.at_level(logging.WARNING, logger="app.ai.planner"):
        plan = _convert_planner_output(output, valid_specialists=_VALID_SPECIALISTS)

    assert len(plan.steps) == _MAX_PLAN_STEPS
    # Indices contiguous 0..n-1 after truncation.
    assert [s.step_index for s in plan.steps] == list(range(_MAX_PLAN_STEPS))
    # Truncation was logged.
    messages = [r.getMessage() for r in caplog.records]
    assert any("truncating to" in m and str(_MAX_PLAN_STEPS) in m for m in messages), (
        messages
    )


def test_convert_planner_output_leaves_at_or_below_max_unchanged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A 3-step plan is unchanged and no truncation WARNING is logged."""
    output = _make_planner_output(n_steps=3)

    with caplog.at_level(logging.WARNING, logger="app.ai.planner"):
        plan = _convert_planner_output(output, valid_specialists=_VALID_SPECIALISTS)

    assert len(plan.steps) == 3
    assert [s.step_index for s in plan.steps] == [0, 1, 2]
    messages = [r.getMessage() for r in caplog.records]
    assert not any("truncating to" in m for m in messages), messages


# ---------------------------------------------------------------------------
# _merge_replanned_steps (replan)
# ---------------------------------------------------------------------------


def _existing_plan_with_completed(n_completed: int) -> PlanDocument:
    return PlanDocument(
        original_request="Complex multi-step request",
        steps=[
            PlanStep(
                step_index=i,
                specialist="project_manager",
                task_description=f"Completed {i}",
                status="completed",
                result_summary=f"Result {i}",
            )
            for i in range(n_completed)
        ],
        requires_planning=True,
    )


def test_merge_replanned_steps_caps_revised_preserving_completed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """3 completed + 4 revised -> 3 completed + 2 revised (= 5 total).

    Completed steps are LOCKED and preserved verbatim. Revised steps are
    capped so completed + revised <= _MAX_PLAN_STEPS, renumbered after the
    last completed index, and a WARNING is logged for the truncation.
    """
    existing = _existing_plan_with_completed(n_completed=3)
    revised_output = _make_planner_output(n_steps=4)

    with caplog.at_level(logging.WARNING, logger="app.ai.planner"):
        merged = _merge_replanned_steps(existing, revised_output, _VALID_SPECIALISTS)

    # Completed preserved verbatim.
    assert len(merged.steps) == _MAX_PLAN_STEPS
    completed = merged.steps[:3]
    for i, step in enumerate(completed):
        assert step.step_index == i
        assert step.status == "completed"
        assert step.specialist == "project_manager"
        assert step.result_summary == f"Result {i}"

    # Revised capped to 2 (= _MAX_PLAN_STEPS - 3), renumbered after last completed.
    revised = merged.steps[3:]
    assert len(revised) == 2
    assert [s.step_index for s in revised] == [3, 4]
    assert all(s.status == "pending" for s in revised)

    messages = [r.getMessage() for r in caplog.records]
    assert any("truncating" in m for m in messages), messages


def test_merge_replanned_steps_completed_already_at_or_above_cap(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """5 completed + 2 revised -> 5 completed, 0 revised, with WARNING.

    Defensive edge: when completed already meets the cap, no revised steps
    are admitted and the (already-capped) completed steps are returned.
    """
    existing = _existing_plan_with_completed(n_completed=_MAX_PLAN_STEPS)
    revised_output = _make_planner_output(n_steps=2)

    with caplog.at_level(logging.WARNING, logger="app.ai.planner"):
        merged = _merge_replanned_steps(existing, revised_output, _VALID_SPECIALISTS)

    assert len(merged.steps) == _MAX_PLAN_STEPS
    assert all(s.status == "completed" for s in merged.steps)
    messages = [r.getMessage() for r in caplog.records]
    assert any("truncating" in m for m in messages), messages


# ---------------------------------------------------------------------------
# Supervisor router iteration bound
# ---------------------------------------------------------------------------


def test_router_bounds_iteration_cap_for_pathological_plan() -> None:
    """A 7-step plan cannot push max_iterations above _MAX_PLAN_STEPS + 1.

    Without the bound, plan_max = 7 + 1 = 8, so an iteration counter of 6
    would be BELOW the cap and the router would NOT force END. With the
    bound, plan_max = min(8, _MAX_PLAN_STEPS + 1) = 6, so iterations == 6
    meets the cap. As of the bounded-termination fix, the max-iterations
    force-END path routes to ``bounded_terminate`` (which emits a grounded
    notice and then END) instead of bare END, so the user is always told
    when a run is bounded.
    """
    router = SupervisorOrchestrator._make_supervisor_router(
        specialist_names=["evm_analyst"],
    )

    pathological_plan = PlanDocument(
        original_request="Pathological 7-step request",
        requires_planning=True,
        steps=[
            PlanStep(step_index=i, specialist="evm_analyst", task_description=f"s{i}")
            for i in range(7)
        ],
    )

    state: dict[str, Any] = {
        "messages": [],
        # Exactly at the bounded cap (6 == _MAX_PLAN_STEPS + 1).
        "supervisor_iterations": _MAX_PLAN_STEPS + 1,
        "max_supervisor_iterations": 5,  # would otherwise be raised to 8
        "plan_data": pathological_plan.model_dump(),
    }

    assert router(state) == "bounded_terminate"
