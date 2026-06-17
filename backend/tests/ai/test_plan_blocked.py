"""Tests for failed-step containment in plan-mode execution.

Two failure modes were corrected by the "blocked-step containment" fix:

1. When a plan step FAILS, every step depending on it is permanently
   non-dispatchable (``are_dependencies_met`` requires ``"completed"``).
   The supervisor used to keep delegating, the specialist_node found
   ``active_step is None`` and FELL THROUGH to the non-plan branch,
   running the specialist with stale task context until the iteration
   cap force-ended the graph.  Now, in plan mode with ``active_step is
   None``, the node returns early with guidance telling the supervisor
   to replan or respond.

2. On the failure path (``specialist_graph.ainvoke`` raised), no
   guidance message was injected into ``error_update``, so the
   supervisor had no instruction after a failure.  Now a SystemMessage
   is injected that names blocked dependents (or confirms none exist).

Test level chosen: real ``specialist_node`` closure.  We instantiate
``SupervisorOrchestrator`` directly (mirroring
``test_replan_integration.py``) with a mock ``ToolContext`` and call
``_create_specialist_wrapper`` to obtain the real closure.  The fake
``specialist_graph.ainvoke`` would ``pytest.fail`` if called, proving
the specialist is NOT run on the containment path.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

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


def _make_blocked_plan() -> PlanDocument:
    """3-step plan where step 0 FAILED and step 1 depends on it.

    Step 0: evm_analyst, FAILED.
    Step 1: evm_analyst, PENDING, depends on [0] -> permanently blocked.
    Step 2: visualization_specialist, PENDING, depends on [0, 1] -> blocked.
    """
    return PlanDocument(
        original_request="Analyze EVM and build a dashboard",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI and SPI",
                status="failed",
                result_summary="Specialist error: timeout",
            ),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="Calculate composite EVM indices",
                dependencies=[0],
                status="pending",
            ),
            PlanStep(
                step_index=2,
                specialist="visualization_specialist",
                task_description="Build dashboard",
                dependencies=[0, 1],
                status="pending",
            ),
        ],
        estimated_complexity="moderate",
        requires_planning=True,
    )


def _make_failing_specialist_graph() -> Any:
    """A graph whose ainvoke raises -- used on the success-path containment
    test to prove the specialist is NEVER invoked."""
    graph = AsyncMock()

    async def _explode(*_a: Any, **_kw: Any) -> dict[str, Any]:
        pytest.fail("specialist_graph.ainvoke must NOT be called in containment")

    graph.ainvoke.side_effect = _explode
    return graph


# ===========================================================================
# Part A: PlanDocument.blocked_step_indices()
# ===========================================================================


def test_blocked_step_indices_no_failed_steps() -> None:
    """No failed steps -> empty list."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(step_index=0, specialist="a", task_description="t"),
            PlanStep(
                step_index=1,
                specialist="b",
                task_description="t",
                dependencies=[0],
            ),
        ],
    )
    assert plan.blocked_step_indices() == []


def test_blocked_step_indices_failed_dep_blocks_pending() -> None:
    """Step 1 failed, step 2 (pending) depends on [1] -> [2]."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(step_index=0, specialist="a", task_description="t"),
            PlanStep(
                step_index=1,
                specialist="b",
                task_description="t",
                status="failed",
            ),
            PlanStep(
                step_index=2,
                specialist="c",
                task_description="t",
                dependencies=[1],
            ),
        ],
    )
    assert plan.blocked_step_indices() == [2]


def test_blocked_step_indices_completed_dependent_not_listed() -> None:
    """Step 1 failed, step 2 depends on [1] but step 2 is COMPLETED -> []."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(step_index=0, specialist="a", task_description="t"),
            PlanStep(
                step_index=1,
                specialist="b",
                task_description="t",
                status="failed",
            ),
            PlanStep(
                step_index=2,
                specialist="c",
                task_description="t",
                dependencies=[1],
                status="completed",
            ),
        ],
    )
    assert plan.blocked_step_indices() == []


def test_blocked_step_indices_in_progress_dep_not_blocking() -> None:
    """Step 1 in_progress, step 2 depends on [1] -> [] (still runnable)."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=1,
                specialist="b",
                task_description="t",
                status="in_progress",
            ),
            PlanStep(
                step_index=2,
                specialist="c",
                task_description="t",
                dependencies=[1],
            ),
        ],
    )
    assert plan.blocked_step_indices() == []


# ===========================================================================
# Part B: specialist_node containment when active_step is None (plan mode)
# ===========================================================================


@pytest.mark.asyncio
async def test_specialist_node_blocked_step_returns_guidance() -> None:
    """Step 0 failed; handing off to step 1's specialist (evm_analyst) must
    NOT run the specialist.  Instead it returns a Command with guidance
    mentioning blocked steps + request_replan, increments iterations, and
    routes to supervisor.
    """
    plan = _make_blocked_plan()
    ctx = _make_tool_context()
    fake_graph = _make_failing_specialist_graph()

    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    node = orchestrator._create_specialist_wrapper(
        specialist_name="evm_analyst",
        specialist_graph=fake_graph,
    )

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze EVM")],
        "active_agent": "evm_analyst",
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "briefing_data": {
            "original_request": "Analyze EVM",
            "sections": [],
            "supervisor_analysis": "",
            "task_history": [],
        },
        "supervisor_iterations": 2,
        "max_supervisor_iterations": 10,
        "completed_specialists": set(),
        "plan_data": plan.model_dump(),
        "completed_steps": set(),
        "current_step_index": 0,
        "current_invocation_id": "inv-001",
        "replan_count": 0,
        "max_replan_count": 2,
        "replan_context": "",
    }

    result = await node(state)

    # Routes to supervisor (not END), increments iterations.
    assert hasattr(result, "goto")
    assert result.goto == "supervisor"
    update = result.update
    assert update["active_agent"] == "supervisor"
    assert update["supervisor_iterations"] == 3

    # A guidance SystemMessage is injected.
    msgs = update.get("messages")
    assert msgs and isinstance(msgs[0], SystemMessage)
    text = msgs[0].content.lower()
    assert "blocked" in text or "request_replan" in text

    # The specialist graph was NOT invoked.
    assert fake_graph.ainvoke.await_count == 0
    assert fake_graph.ainvoke.call_count == 0


@pytest.mark.asyncio
async def test_specialist_node_no_pending_steps_resolved() -> None:
    """All steps resolved (some failed, none pending) -> guidance tells the
    supervisor to respond, not delegate, and the specialist is NOT run."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="t",
                status="completed",
            ),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="t",
                status="failed",
            ),
        ],
        requires_planning=True,
    )
    ctx = _make_tool_context()
    fake_graph = _make_failing_specialist_graph()

    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    node = orchestrator._create_specialist_wrapper(
        specialist_name="evm_analyst",
        specialist_graph=fake_graph,
    )

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="x")],
        "active_agent": "evm_analyst",
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
        "completed_steps": {0},
    }

    result = await node(state)
    assert result.goto == "supervisor"
    msgs = result.update.get("messages")
    assert msgs and isinstance(msgs[0], SystemMessage)
    text = msgs[0].content.lower()
    assert "do not delegate" in text or "respond" in text
    assert fake_graph.ainvoke.call_count == 0


@pytest.mark.asyncio
async def test_specialist_node_no_step_for_specialist_but_pending_exists() -> None:
    """active_step is None because no pending step is assigned to THIS
    specialist, but other pending steps exist -> guidance says delegate the
    next pending step instead."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="t",
                status="completed",
            ),
            PlanStep(
                step_index=1,
                specialist="visualization_specialist",
                task_description="t",
                status="pending",
                dependencies=[0],
            ),
        ],
        requires_planning=True,
    )
    ctx = _make_tool_context()
    fake_graph = _make_failing_specialist_graph()

    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    # evm_analyst is handed off, but its only step is completed.
    node = orchestrator._create_specialist_wrapper(
        specialist_name="evm_analyst",
        specialist_graph=fake_graph,
    )

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="x")],
        "active_agent": "evm_analyst",
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "briefing_data": {
            "original_request": "x",
            "sections": [],
            "supervisor_analysis": "",
            "task_history": [],
        },
        "supervisor_iterations": 1,
        "completed_specialists": {"evm_analyst"},
        "plan_data": plan.model_dump(),
        "completed_steps": {0},
    }

    result = await node(state)
    # Should NOT early-exit to END via the completed-specialist guard
    # because a pending step still exists for another specialist.
    assert result.goto == "supervisor"
    msgs = result.update.get("messages")
    assert msgs and isinstance(msgs[0], SystemMessage)
    text = msgs[0].content.lower()
    # The bounce names the EXACT next handoff tool (FIX #1: replaces the
    # old generic "delegate the next pending step's specialist instead"
    # with the precise handoff_to_<specialist> directive).
    assert "handoff_to_visualization_specialist" in text
    assert fake_graph.ainvoke.call_count == 0


# ===========================================================================
# Part C: failure-path guidance injection
# ===========================================================================


@pytest.mark.asyncio
async def test_specialist_failure_with_dependents_names_blocked() -> None:
    """specialist_graph.ainvoke raises; active step has dependents -> the
    error Command injects a SystemMessage naming the blocked dependents."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI",
                status="pending",
            ),
            PlanStep(
                step_index=1,
                specialist="visualization_specialist",
                task_description="Build dashboard",
                dependencies=[0],
                status="pending",
            ),
        ],
        requires_planning=True,
    )
    ctx = _make_tool_context()

    failing_graph = AsyncMock()

    async def _boom(*_a: Any, **_kw: Any) -> dict[str, Any]:
        raise RuntimeError("provider 500")

    failing_graph.ainvoke.side_effect = _boom

    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    node = orchestrator._create_specialist_wrapper(
        specialist_name="evm_analyst",
        specialist_graph=failing_graph,
    )

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="x")],
        "active_agent": "evm_analyst",
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
        "current_invocation_id": "inv-002",
    }

    result = await node(state)
    assert result.goto == "supervisor"
    update = result.update

    # Plan step 0 is marked failed.
    failed_plan = PlanDocument.from_state(update["plan_data"])
    assert failed_plan.get_step(0).status == "failed"

    # Guidance message names the failed step AND the blocked dependent.
    msgs = update.get("messages")
    assert msgs and isinstance(msgs[0], SystemMessage)
    text = msgs[0].content
    assert "FAILED" in text
    # Dependent step index 1 is named as blocked.
    assert "1" in text or "Step(s)" in text


@pytest.mark.asyncio
async def test_specialist_failure_no_dependents_continues() -> None:
    """specialist fails but no other step depends on it (a pending step
    remains) -> guidance tells the user the step failed AND allows
    delegating the next pending step / replanning."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI",
                status="pending",
            ),
            PlanStep(
                step_index=1,
                specialist="visualization_specialist",
                task_description="Build dashboard (independent)",
                dependencies=[],
                status="pending",
            ),
        ],
        requires_planning=True,
    )
    ctx = _make_tool_context()

    failing_graph = AsyncMock()

    async def _boom(*_a: Any, **_kw: Any) -> dict[str, Any]:
        raise RuntimeError("provider 500")

    failing_graph.ainvoke.side_effect = _boom

    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    node = orchestrator._create_specialist_wrapper(
        specialist_name="evm_analyst",
        specialist_graph=failing_graph,
    )

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="x")],
        "active_agent": "evm_analyst",
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
        "current_invocation_id": "inv-003",
    }

    result = await node(state)
    update = result.update
    msgs = update.get("messages")
    assert msgs and isinstance(msgs[0], SystemMessage)
    text = msgs[0].content
    assert "FAILED" in text
    # The failure nudge must name the error and, because a pending step
    # remains, allow delegating it / replanning (see _build_failure_nudge).
    assert "provider 500" in text
    assert (
        "briefly inform the user" in text.lower() or "inform the user" in text.lower()
    )
    assert (
        "delegate the next pending step" in text.lower()
        or "request_replan" in text.lower()
    )
