"""Tests for the bounded-termination guard.

Covers the two silent force-END paths in the supervisor router
(``_make_supervisor_router``):

* **max-iterations:** ``iterations >= max_iterations`` previously returned
  ``END`` with no user-facing message.
* **max-replan:** inside the ``request_replan`` branch,
  ``replan_count >= max_replan`` previously returned ``END`` with no
  user-facing message.

Both now route to ``"bounded_terminate"`` -- a static node that builds a
GROUNDED termination notice from the plan state (Completed / Failed(error
quoted) / Not-started sections) and returns ``Command(goto=END)`` with
``termination_notice`` set.  The notice is delivered to the user by
``agent_service._persist_session_messages``.

Mirrors the ``test_premature_completion_integration.py`` instantiation
pattern (component-level node + router tests; no full LangGraph engine).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END

from app.ai.plan import PlanDocument, PlanStep
from app.ai.supervisor_orchestrator import (
    SupervisorOrchestrator,
    _build_bounded_termination_notice,
)
from app.ai.tools.types import ToolContext

# ---------------------------------------------------------------------------
# Fixtures (mirror test_premature_completion_integration.py)
# ---------------------------------------------------------------------------


def _make_tool_context() -> ToolContext:
    mock_event_bus = MagicMock()
    mock_event_bus.publish = MagicMock()
    mock_event_bus.execution_id = "test-exec-id"
    ctx = ToolContext(
        session=MagicMock(),
        user_id="test-user",
        _event_bus=mock_event_bus,
    )
    ctx._stop_event = MagicMock()
    ctx._stop_event.is_set.return_value = False
    return ctx


def _mixed_status_plan() -> PlanDocument:
    """Plan with one completed, one failed (with error), and one not-started step."""
    return PlanDocument(
        original_request="Research and summarize the project",
        steps=[
            PlanStep(
                step_index=0,
                specialist="document_manager",
                task_description="Fetch the project document",
                status="completed",
                result_summary="Loaded doc PRJ-001 (12 pages).",
            ),
            PlanStep(
                step_index=1,
                specialist="web_researcher",
                task_description="Research market benchmarks online",
                status="failed",
                result_summary=(
                    "web_researcher: Tavily API error: "
                    "you exceeded your monthly usage limit"
                ),
            ),
            PlanStep(
                step_index=2,
                specialist="evm_analyst",
                task_description="Summarize EVM metrics from the document",
                status="pending",
            ),
        ],
        requires_planning=True,
    )


def _no_plan_state() -> dict[str, Any]:
    return {
        "messages": [HumanMessage(content="go")],
        "active_agent": "supervisor",
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "briefing_data": {},
        "supervisor_iterations": 5,
        "max_supervisor_iterations": 5,
        "completed_specialists": set(),
        "plan_data": {},
        "completed_steps": set(),
        "current_step_index": -1,
        "replan_count": 0,
        "max_replan_count": 2,
        "replan_context": "",
        "specialist_dispatch_counts": {},
        "specialist_failure_counts": {},
        "premature_reprompts": 0,
    }


def _state(plan: PlanDocument, **overrides: Any) -> dict[str, Any]:
    base = _no_plan_state()
    base.update(
        {
            "plan_data": plan.model_dump(),
            "completed_steps": set(plan.completed_step_indices()),
            "supervisor_iterations": overrides.pop(
                "supervisor_iterations", base["supervisor_iterations"]
            ),
        }
    )
    base.update(overrides)
    return base


# ===========================================================================
# _build_bounded_termination_notice: grounded from plan STATE
# ===========================================================================


def test_notice_lists_completed_failed_with_error_and_not_started() -> None:
    """The notice is built from plan STATE: a Completed section (with
    result_summary), a Failed section QUOTING the step's result_summary
    (this carries the real error), and a Not-started section listing the
    pending step's task_description."""
    plan = _mixed_status_plan()
    notice = _build_bounded_termination_notice(plan)

    # Header states the execution limit was reached.
    assert (
        "execution limit" in notice.lower()
        or "could not be completed" in notice.lower()
    )

    # Completed section with the completed step's result_summary.
    assert "completed" in notice.lower()
    assert "PRJ-001" in notice  # result_summary of step 0

    # Failed section quotes the error verbatim (the real error carrier).
    assert "failed" in notice.lower()
    assert "Tavily" in notice
    assert "usage limit" in notice

    # Not-started section names the pending step's task.
    assert "not started" in notice.lower() or "pending" in notice.lower()
    assert "Summarize EVM metrics" in notice

    # Footer suggests retry / simplify.
    assert "retry" in notice.lower() or "simplif" in notice.lower()


def test_notice_handles_no_plan() -> None:
    """In non-plan mode a simpler notice is emitted (no plan sections)."""
    notice = _build_bounded_termination_notice(None)
    assert "execution limit" in notice.lower()
    # No Completed/Failed/Not-started sections.
    assert "PRJ-001" not in notice
    assert "Tavily" not in notice


def test_notice_uses_none_when_section_empty() -> None:
    """Sections with no steps render '(none)' rather than disappearing."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="web_researcher",
                task_description="research",
                status="pending",
            ),
        ],
        requires_planning=True,
    )
    notice = _build_bounded_termination_notice(plan)
    assert "(none)" in notice  # Completed and Failed are empty
    assert "research" in notice  # Not-started lists the pending task


# ===========================================================================
# Node: returns Command(goto=END) with termination_notice set
# ===========================================================================


@pytest.mark.asyncio
async def test_bounded_terminate_node_builds_notice_and_goes_to_end() -> None:
    """The node builds a grounded notice from the plan state and returns
    Command(goto=END) with ``termination_notice`` set (and
    ``supervisor_iterations`` +1)."""
    ctx = _make_tool_context()
    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    plan = _mixed_status_plan()
    state = _state(plan)

    result = orchestrator._bounded_terminate_node(state)

    assert result.goto == END
    notice = result.update.get("termination_notice")
    assert isinstance(notice, str) and notice
    assert "Tavily" in notice  # grounded from plan state
    # Iteration bump (matches the premature_completion_guard shape).
    assert result.update.get("supervisor_iterations") == 1


@pytest.mark.asyncio
async def test_bounded_terminate_node_handles_no_plan() -> None:
    """The node still emits a notice and terminates when there is no plan."""
    ctx = _make_tool_context()
    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)

    result = orchestrator._bounded_terminate_node(_no_plan_state())

    assert result.goto == END
    notice = result.update.get("termination_notice")
    assert isinstance(notice, str) and notice
    assert "execution limit" in notice.lower()


# ===========================================================================
# Router: both force-END paths now route to "bounded_terminate"
# ===========================================================================


def test_router_routes_to_bounded_terminate_on_max_iterations() -> None:
    """The max-iterations force-END path now routes to ``bounded_terminate``
    instead of bare END so the user receives a termination notice."""
    ctx = _make_tool_context()
    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    router = orchestrator._make_supervisor_router(["evm_analyst"])

    plan = _mixed_status_plan()
    state = _state(
        plan,
        supervisor_iterations=10,  # well past cap
        max_supervisor_iterations=5,
        messages=[HumanMessage(content="go")],
    )
    assert router(state) == "bounded_terminate"


def test_router_routes_to_bounded_terminate_on_max_replan() -> None:
    """The max-replan force-END path (inside the request_replan branch)
    now routes to ``bounded_terminate`` instead of bare END."""
    ctx = _make_tool_context()
    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    router = orchestrator._make_supervisor_router(["evm_analyst"])

    plan = _mixed_status_plan()
    state = _state(
        plan,
        supervisor_iterations=1,
        max_supervisor_iterations=10,
        replan_count=2,
        max_replan_count=2,
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "request_replan",
                        "args": {"reason": "retry"},
                        "id": "tc1",
                        "type": "tool_call",
                    }
                ],
            )
        ],
    )
    assert router(state) == "bounded_terminate"


# ===========================================================================
# agent_service delivery: termination_notice -> final assistant message
# ===========================================================================


@pytest.mark.asyncio
async def test_extract_termination_notice_populates_stream_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_extract_termination_notice`` reads ``termination_notice`` from the
    checkpoint's channel_values and sets ``state.termination_message``."""
    from app.ai import agent_service as agent_service_module
    from app.ai.graph_params import StreamState

    session_id = uuid4()
    notice = "I could not complete your request within the execution limit."
    fake_cp = MagicMock()
    fake_cp.aget = AsyncMock(
        return_value={"channel_values": {"termination_notice": notice}}
    )
    monkeypatch.setattr(agent_service_module, "shared_checkpointer", fake_cp)

    # Minimal AgentService: only the method under test touches self/args.
    service = agent_service_module.AgentService.__new__(
        agent_service_module.AgentService
    )
    state = StreamState(
        event_bus=MagicMock(),
        session_id=session_id,
        model_name=None,
        main_invocation_id="inv-1",
    )
    await service._extract_termination_notice(session_id, state)

    assert state.termination_message == notice
    fake_cp.aget.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_termination_notice_no_checkpoint_leaves_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No checkpoint -> ``termination_message`` stays ``None`` (no crash)."""
    from app.ai import agent_service as agent_service_module
    from app.ai.graph_params import StreamState

    session_id = uuid4()
    fake_cp = MagicMock()
    fake_cp.aget = AsyncMock(return_value=None)
    monkeypatch.setattr(agent_service_module, "shared_checkpointer", fake_cp)

    service = agent_service_module.AgentService.__new__(
        agent_service_module.AgentService
    )
    state = StreamState(
        event_bus=MagicMock(),
        session_id=session_id,
        model_name=None,
        main_invocation_id="inv-1",
    )
    await service._extract_termination_notice(session_id, state)

    assert state.termination_message is None


@pytest.mark.asyncio
async def test_persist_session_messages_persists_termination_as_final_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``state.termination_message`` is set, ``_persist_session_messages``
    persists it as a final assistant message (metadata marks it as a bounded-
    termination notice) and sets ``last_persisted_message_id`` so the COMPLETE
    event points at it."""
    from app.ai import agent_service as agent_service_module
    from app.ai.graph_params import StreamState

    session_id = uuid4()
    notice = "I could not complete your request within the execution limit."

    service = agent_service_module.AgentService(session=AsyncMock())
    # config_service is a cached property -> set the backing field directly.
    fake_term_msg = MagicMock()
    fake_term_msg.id = uuid4()
    fake_config = MagicMock()
    fake_config.add_message = AsyncMock(return_value=fake_term_msg)
    service._config_service = fake_config

    state = StreamState(
        event_bus=MagicMock(),
        session_id=session_id,
        model_name=None,
        main_invocation_id="inv-1",
    )
    state.termination_message = notice

    await service._persist_session_messages(state)

    # The termination notice was persisted as an assistant message.
    add_calls = service.config_service.add_message.call_args_list
    term_call = next(
        (
            c
            for c in add_calls
            if c.kwargs.get("role") == "assistant" and c.kwargs.get("content") == notice
        ),
        None,
    )
    assert term_call is not None, "termination notice was not persisted"
    assert (
        term_call.kwargs.get("message_metadata", {}).get("bounded_termination") is True
    )
    # last_persisted_message_id points at the termination message.
    assert state.last_persisted_message_id == fake_term_msg.id
