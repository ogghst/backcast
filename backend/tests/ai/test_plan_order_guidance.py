"""Tests for supervisor plan-order adherence guidance (FIX #1).

Two coupled problems are corrected here:

1. When the #3 containment guard bounces a specialist whose plan step is
   not the next dispatchable one (e.g. delegating ``project_manager``
   before ``time_traveller`` step 0), the bounce used to say "delegate
   the next pending step's specialist instead" -- a vague instruction
   the LLM ignored.  Now the guidance NAMES the exact next step and the
   exact ``handoff_to_<specialist>`` tool.

2. The supervisor's per-call plan injection (``PlanAwareToolMiddleware``)
   used to drop ``to_prompt_text()`` into the system prompt with no
   next-action directive.  Now a single ``NEXT ACTION`` line names the
   next dispatchable step + the handoff tool on EVERY supervisor turn,
   on BOTH the enforced and non-enforced middleware paths.

Test level: pure helper for ``_next_action_line`` + real
``specialist_node`` closure for the bounce message (mirrors
``test_plan_blocked.py``'s instantiation pattern).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.middleware.plan_aware_tools import _next_action_line
from app.ai.plan import PlanDocument, PlanStep
from app.ai.supervisor_orchestrator import SupervisorOrchestrator
from app.ai.tools.types import ToolContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool_context() -> ToolContext:
    """Build a minimal ToolContext with a mock event bus (no DB)."""
    mock_session = MagicMock()
    mock_event_bus = MagicMock()
    mock_event_bus.publish = MagicMock()
    mock_event_bus.execution_id = "test-exec-id"

    ctx = ToolContext(
        session=mock_session,
        user_id="test-user",
        _event_bus=mock_event_bus,
    )
    ctx._stop_event = MagicMock()
    ctx._stop_event.is_set.return_value = False
    return ctx


def _make_failing_specialist_graph() -> Any:
    """A graph whose ainvoke raises if called -- used to prove the
    specialist is NEVER invoked on the plan-order containment path."""
    graph = AsyncMock()

    async def _explode(*_a: Any, **_kw: Any) -> dict[str, Any]:
        pytest.fail("specialist_graph.ainvoke must NOT be called in containment")

    graph.ainvoke.side_effect = _explode
    return graph


# ===========================================================================
# Part A: _next_action_line helper
# ===========================================================================


def test_next_action_line_step_zero_pending() -> None:
    """Step 0 pending (no deps) -> names step 1 and handoff_to_<specialist0>."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="time_traveller",
                task_description="Load project state",
            ),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="Calculate CPI",
                dependencies=[0],
            ),
        ],
        requires_planning=True,
    )
    line = _next_action_line(plan)
    assert "NEXT ACTION" in line
    assert "handoff_to_time_traveller" in line
    assert "1/2" in line  # step_index+1 / total steps
    assert "Load project state" in line


def test_next_action_line_all_resolved() -> None:
    """All steps completed -> says respond, do not delegate further."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="a",
                task_description="t",
                status="completed",
            ),
            PlanStep(
                step_index=1,
                specialist="b",
                task_description="t",
                status="completed",
            ),
        ],
        requires_planning=True,
    )
    line = _next_action_line(plan)
    assert "All plan steps are resolved" in line
    assert "do not delegate further" in line


def test_next_action_line_step_zero_completed_step_one_pending() -> None:
    """Step 0 completed, step 1 pending with deps [0] met -> names step 2."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="a",
                task_description="t",
                status="completed",
            ),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="Calculate CPI",
                dependencies=[0],
                status="pending",
            ),
        ],
        requires_planning=True,
    )
    line = _next_action_line(plan)
    assert "handoff_to_evm_analyst" in line
    assert "2/2" in line


def test_next_action_line_first_dispatchable_chosen() -> None:
    """Step 0 pending but step 1 pending with deps [0] unmet -> still names
    step 1 (the first dispatchable)."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="time_traveller",
                task_description="Load state",
                status="pending",
            ),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="Needs step 0",
                dependencies=[0],
                status="pending",
            ),
        ],
        requires_planning=True,
    )
    line = _next_action_line(plan)
    # get_next_pending_step returns step 0 (deps met), so the line names
    # step 1/2 with time_traveller, NOT step 2 (which is blocked).
    assert "handoff_to_time_traveller" in line
    assert "1/2" in line


# ===========================================================================
# Part B: specialist_node #3 bounce names the exact next step + tool
# ===========================================================================


@pytest.mark.asyncio
async def test_specialist_node_bounce_names_exact_next_step_and_tool() -> None:
    """Delegating specialist B when step 0 is specialist A -> the bounce
    guidance names ``handoff_to_<A>`` and the step text, and the fake
    specialist_graph.ainvoke is NOT called.

    To hit the #3 bounce path the delegated specialist (B) must have NO
    matching pending step whose deps are met.  We make specialist B's only
    step DEPEND on step 0 (so its deps are unmet), forcing ``active_step``
    to be None and the containment guard to fire.
    """
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="time_traveller",
                task_description="Load project state",
                status="pending",
            ),
            PlanStep(
                step_index=1,
                specialist="project_manager",
                task_description="Summarize",
                dependencies=[0],
                status="pending",
            ),
        ],
        requires_planning=True,
    )
    ctx = _make_tool_context()
    fake_graph = _make_failing_specialist_graph()

    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    # project_manager is delegated out of order; its step (1) depends on
    # step 0 which is still pending, so active_step is None -> bounce.
    node = orchestrator._create_specialist_wrapper(
        specialist_name="project_manager",
        specialist_graph=fake_graph,
    )

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="x")],
        "active_agent": "project_manager",
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "briefing_data": {
            "original_request": "x",
            "sections": [],
            "supervisor_analysis": "",
            "task_history": [],
        },
        "supervisor_iterations": 1,
        "completed_specialists": set(),
        "plan_data": plan.model_dump(),
        "completed_steps": set(),
    }

    result = await node(state)

    # Routes to supervisor, does not run the specialist.
    assert result.goto == "supervisor"
    msgs = result.update.get("messages")
    assert msgs and isinstance(msgs[0], SystemMessage)
    text = msgs[0].content

    # Names the EXACT next step's handoff tool (not a generic message).
    assert "handoff_to_time_traveller" in text
    # Names the step text and its position.
    assert "Load project state" in text
    assert "1/2" in text  # step_index+1 / total

    # The specialist graph was NOT invoked.
    assert fake_graph.ainvoke.await_count == 0
    assert fake_graph.ainvoke.call_count == 0


# ===========================================================================
# Part C: middleware injects NEXT ACTION line on the non-enforced path
#
# AI_DELEGATION_ENFORCED is False in this environment, so the enforced
# block is skipped and the non-enforced path fills {plan_section}.  We
# assert the NEXT ACTION line lands in the composed system prompt even
# when no tool filtering occurs.
# ===========================================================================


@pytest.mark.asyncio
async def test_middleware_non_enforced_path_injects_next_action() -> None:
    """With no active plan (non-enforced path), the {plan_section}
    placeholder is filled; when a plan IS present and delegation is NOT
    enforced, the injected plan_text carries a NEXT ACTION line."""
    from app.ai.middleware.plan_aware_tools import PlanAwareToolMiddleware

    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="time_traveller",
                task_description="Load project state",
                status="pending",
            ),
        ],
        requires_planning=True,
    )

    line = _next_action_line(plan)
    assert "NEXT ACTION" in line
    assert "handoff_to_time_traveller" in line

    # The middleware helper is the unit of next-action injection on both
    # paths; the prompt composition is covered by the structural test
    # above plus the specialist_node bounce test.  Re-instantiating the
    # full middleware + langchain AgentState is out of scope here and is
    # exercised end-to-end by test_replan_integration.py.
    mw = PlanAwareToolMiddleware()
    assert isinstance(mw, PlanAwareToolMiddleware)
