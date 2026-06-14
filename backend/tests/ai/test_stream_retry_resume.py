"""Tests for checkpoint-aware resume on the top-level stream retry.

When a transient stream error occurs, ``_process_stream_events`` retries by
re-invoking ``ctx.graph.astream_events``.  Previously the retry used the
SAME stale ``existing_briefing`` / ``ctx.resume_plan_data`` captured before
the stream started, discarding any progress made during the failed attempt
(briefing sections, completed plan steps, completed specialists) that now
lives in the LangGraph checkpoint under ``thread_id=session_id``.

The fix extracts resume state from the checkpoint, refreshes the loop-local
graph-input variables, deletes the checkpoint thread, and re-runs clean.

Test strategy:

- The pure helper ``_extract_resume_state_from_checkpoint`` is unit-tested
  directly (None / no-briefing / list-coercion / set-passthrough).
- The retry-refresh behaviour is tested at the loop level: we monkeypatch
  ``shared_checkpointer`` (target ``app.ai.agent_service.shared_checkpointer``)
  to return a checkpoint with a 2-section briefing + a plan with step 0
  completed, and monkeypatch ``ctx.graph.astream_events`` to raise a
  transient ``ConnectionResetError`` on the first call and yield nothing on
  the second.  We stub ``iter_with_pausable_deadline`` so the graph's async
  iterator is consumed directly (no real deadline / runtime context wiring),
  and stub the event handlers via a do-nothing ``StreamState``.  We then
  assert:

    (a) ``shared_checkpointer.delete_thread`` was called once with the
        session id;
    (b) the second ``astream_events`` invocation's input ``briefing_data``
        matches the checkpoint's (not the stale pre-stream one) and
        ``completed_steps`` contains the completed index.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.ai.agent_service import (
    AgentService,
    _extract_resume_state_from_checkpoint,
)
from app.ai.graph_params import StreamState

# ---------------------------------------------------------------------------
# Part A: _extract_resume_state_from_checkpoint (pure helper)
# ---------------------------------------------------------------------------


def test_extract_resume_state_none_input() -> None:
    """None checkpoint -> None."""
    assert _extract_resume_state_from_checkpoint(None) is None


def test_extract_resume_state_no_briefing() -> None:
    """Checkpoint without briefing_data in channel_values -> None."""
    checkpoint = {"channel_values": {"plan_data": {"steps": []}}}
    assert _extract_resume_state_from_checkpoint(checkpoint) is None


def test_extract_resume_state_full_checkpoint_coerces_lists() -> None:
    """Full checkpoint returns all four keys; lists coerced to sets."""
    checkpoint = {
        "channel_values": {
            "briefing_data": {"original_request": "x", "sections": [{}, {}]},
            "plan_data": {"steps": [{"step_index": 0, "status": "completed"}]},
            "completed_steps": [0, 1],
            "completed_specialists": ["evm_analyst"],
        }
    }
    resume = _extract_resume_state_from_checkpoint(checkpoint)
    assert resume is not None
    assert resume["briefing_data"]["original_request"] == "x"
    assert resume["plan_data"]["steps"][0]["status"] == "completed"
    assert resume["completed_steps"] == {0, 1}
    assert isinstance(resume["completed_steps"], set)
    assert resume["completed_specialists"] == {"evm_analyst"}
    assert isinstance(resume["completed_specialists"], set)


def test_extract_resume_state_sets_passed_through() -> None:
    """Sets in channel_values pass through as sets."""
    checkpoint = {
        "channel_values": {
            "briefing_data": {"sections": []},
            "plan_data": None,
            "completed_steps": {2, 3},
            "completed_specialists": {"a", "b"},
        }
    }
    resume = _extract_resume_state_from_checkpoint(checkpoint)
    assert resume is not None
    assert resume["completed_steps"] == {2, 3}
    assert isinstance(resume["completed_steps"], set)
    assert resume["completed_specialists"] == {"a", "b"}
    assert isinstance(resume["completed_specialists"], set)


def test_extract_resume_state_missing_completed_keys_default_empty() -> None:
    """If completed_steps / completed_specialists are absent -> empty sets."""
    checkpoint = {
        "channel_values": {
            "briefing_data": {"sections": []},
        }
    }
    resume = _extract_resume_state_from_checkpoint(checkpoint)
    assert resume is not None
    assert resume["completed_steps"] == set()
    assert resume["completed_specialists"] == set()
    assert resume["plan_data"] is None


# ---------------------------------------------------------------------------
# Part B: retry-refresh loop-level behaviour
# ---------------------------------------------------------------------------


def _make_checkpoint() -> dict[str, Any]:
    """A checkpoint with a 2-section briefing and step 0 completed."""
    return {
        "channel_values": {
            "briefing_data": {
                "original_request": "checkpoint request",
                "sections": [{"findings": "a"}, {"findings": "b"}],
                "supervisor_analysis": "",
                "task_history": [],
            },
            "plan_data": {
                "original_request": "checkpoint request",
                "steps": [
                    {"step_index": 0, "status": "completed", "specialist": "x"},
                    {"step_index": 1, "status": "pending", "specialist": "y"},
                ],
                "requires_planning": True,
            },
            "completed_steps": [0],
            "completed_specialists": ["x"],
        }
    }


@pytest.mark.asyncio
async def test_retry_refreshes_from_checkpoint_and_deletes_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On a transient stream error, the retry pulls fresh briefing/plan from
    the checkpoint, deletes the checkpoint thread, and re-invokes the graph
    with the refreshed input.
    """
    # --- Fake ctx whose graph.astream_events raises once then yields nothing
    astream_inputs: list[dict[str, Any]] = []

    async def _astream_events_raise_then_empty(
        graph_input: dict[str, Any], **_kw: Any
    ) -> Any:
        astream_inputs.append(graph_input)
        if len(astream_inputs) == 1:
            raise ConnectionResetError("transient reset")
        # Second call: empty async iterator.
        return
        yield  # pragma: no cover -- makes this an async generator

    fake_graph = MagicMock()
    fake_graph.astream_events = _astream_events_raise_then_empty

    ctx = MagicMock()
    ctx.graph = fake_graph
    ctx.session_id = UUID("12345678-1234-1234-1234-123456789012")
    ctx.resume_plan_data = {
        "original_request": "STALE pre-stream",
        "steps": [],
        "requires_planning": False,
    }
    ctx.recursion_limit = 10
    ctx.user_id = UUID("00000000-0000-0000-0000-000000000001")
    ctx.user_role = "analyst"
    ctx.project_id = None
    ctx.branch_id = None
    ctx.execution_mode = MagicMock(value="standard")
    ctx.stop_event = None

    # --- Stub iter_with_pausable_deadline to just iterate the async iterator
    async def _passthrough_iter(ait: Any, **_kw: Any) -> Any:
        async for ev in ait:
            yield ev

    monkeypatch.setattr(
        "app.ai.agent_service.iter_with_pausable_deadline", _passthrough_iter
    )

    # --- Stub log_pool_status (touches the real DB pool otherwise)
    monkeypatch.setattr("app.db.session.log_pool_status", lambda *_a, **_kw: None)

    # --- Monkeypatch shared_checkpointer in agent_service
    fake_cp = MagicMock()
    fake_cp.aget = AsyncMock(return_value=_make_checkpoint())
    fake_cp.delete_thread = MagicMock()
    monkeypatch.setattr("app.ai.agent_service.shared_checkpointer", fake_cp)

    # --- A StreamState whose handlers are no-ops + a do-nothing persist
    state = MagicMock(spec=StreamState)
    state.event_bus = MagicMock()
    state.event_bus.execution_id = "exec-x"
    state.token_buffer = {}
    state.flush_tokens = MagicMock()
    state.briefing_persisted = False

    service = MagicMock(spec=AgentService)
    service._persist_briefing_from_checkpoint = AsyncMock(return_value=True)

    # The stale pre-stream briefing.
    stale_briefing = {"original_request": "STALE pre-stream", "sections": []}

    # Bind the real implementation to the mock service so the unbound-method
    # can be called with `self=service`.
    await AgentService._process_stream_events(
        service,  # type: ignore[arg-type]
        ctx,
        state,
        history=[],
        existing_briefing=stale_briefing,
    )

    # (a) delete_thread was called once with the session id.
    assert fake_cp.delete_thread.call_count == 1
    assert fake_cp.delete_thread.call_args[0][0] == str(ctx.session_id)

    # (b) The second astream_events input used the CHECKPOINT's data.
    assert len(astream_inputs) == 2
    second_input = astream_inputs[1]
    assert second_input["briefing_data"]["original_request"] == "checkpoint request"
    assert second_input["completed_steps"] == {0}
    # And the injected completed_specialists from the checkpoint.
    assert second_input["completed_specialists"] == {"x"}
    # The stale pre-stream briefing must NOT have leaked into the retry.
    assert second_input["briefing_data"]["original_request"] != "STALE pre-stream"


@pytest.mark.asyncio
async def test_retry_without_checkpoint_warns_and_keeps_locals(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When no checkpoint is found on retry, the warning fires and the retry
    uses the pre-stream state (no delete_thread call)."""
    astream_inputs: list[dict[str, Any]] = []

    async def _astream_events_raise_then_empty(
        graph_input: dict[str, Any], **_kw: Any
    ) -> Any:
        astream_inputs.append(graph_input)
        if len(astream_inputs) == 1:
            raise ConnectionResetError("transient reset")
        return
        yield  # pragma: no cover

    fake_graph = MagicMock()
    fake_graph.astream_events = _astream_events_raise_then_empty

    ctx = MagicMock()
    ctx.graph = fake_graph
    ctx.session_id = UUID("11111111-1111-1111-1111-111111111111")
    ctx.resume_plan_data = None
    ctx.recursion_limit = 10
    ctx.user_id = UUID("00000000-0000-0000-0000-000000000001")
    ctx.user_role = "analyst"
    ctx.project_id = None
    ctx.branch_id = None
    ctx.execution_mode = MagicMock(value="standard")
    ctx.stop_event = None

    async def _passthrough_iter(ait: Any, **_kw: Any) -> Any:
        async for ev in ait:
            yield ev

    monkeypatch.setattr(
        "app.ai.agent_service.iter_with_pausable_deadline", _passthrough_iter
    )
    monkeypatch.setattr("app.db.session.log_pool_status", lambda *_a, **_kw: None)

    fake_cp = MagicMock()
    fake_cp.aget = AsyncMock(return_value=None)  # no checkpoint
    fake_cp.delete_thread = MagicMock()
    monkeypatch.setattr("app.ai.agent_service.shared_checkpointer", fake_cp)

    state = MagicMock(spec=StreamState)
    state.event_bus = MagicMock()
    state.event_bus.execution_id = "exec-y"
    state.token_buffer = {}
    state.flush_tokens = MagicMock()
    state.briefing_persisted = False

    service = MagicMock(spec=AgentService)
    service._persist_briefing_from_checkpoint = AsyncMock(return_value=True)

    stale_briefing = {"original_request": "pre-stream", "sections": []}

    import logging

    with caplog.at_level(logging.WARNING):
        await AgentService._process_stream_events(
            service,  # type: ignore[arg-type]
            ctx,
            state,
            history=[],
            existing_briefing=stale_briefing,
        )

    # No checkpoint -> delete_thread NOT called.
    assert fake_cp.delete_thread.call_count == 0
    # A WARNING about no checkpoint was logged.
    assert any("no checkpoint" in rec.message.lower() for rec in caplog.records)
    # The retry used the pre-stream briefing.
    assert len(astream_inputs) == 2
    assert astream_inputs[1]["briefing_data"]["original_request"] == "pre-stream"
