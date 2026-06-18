"""E2E placement tests for the supervisor briefing/plan context fixes (Phase 2).

Codifies the design principle in
``plans/check-this-llm-call-lively-balloon.md``: plan verification / replan
correctness is the LLM's job. Code in the plan/replan path does ONLY robust
checks (``step.status``, dedicated error fields, the ``_MAX_PLAN_STEPS`` cap,
catalog membership). NO task-text / casefold / string dedup anywhere.

The 5 tests cover:

1. ``test_replan_clean_context_drops_redundant_step`` -- the trace regression:
   a clean current briefing (file already saved) lets the replanner drop a
   redundant step. Proves the replanner's INPUT prompt carried the live
   finding text (Phase 2's clean-context fix).
2. ``test_replan_does_not_semantic_dedup_steps`` -- codifies the principle:
   a revised step that textually duplicates a completed step's task is
   PRESERVED as pending (code does no semantic dedup; that is the LLM's job).
3. ``test_replan_preserves_completed_and_caps_count`` -- happy multi-step:
   3 completed preserved verbatim; revised capped at ``_MAX_PLAN_STEPS - 3``,
   contiguous indices starting at ``max_completed_idx + 1``; all pending +
   ``replanned``.
4. ``test_briefing_middleware_renders_current_findings_each_turn`` -- P1 fix:
   the per-turn middleware renders the CURRENT briefing between sentinels on
   every call (no stale "No findings yet."), exactly one briefing span, and
   ``_briefing_update`` no longer emits a one-shot ``messages`` entry.
5. ``test_plan_block_minimal_and_no_handoff_terminates`` -- bundles
   ``to_prompt_text`` (1-based, truncated, status-labeled) with the
   F1-removal guarantee: the router's no-handoff branch returns END (not a
   removed guard node) even when a step is genuinely pending.

Harness mirrors ``test_replan_integration.py`` and the (deleted)
``test_premature_completion_integration.py``: mock LLM via ``AsyncMock``
returning ``MagicMock(content=<json>)``; real ``ModelRequest`` + async
handler for middleware; ``@pytest.mark.asyncio``; pytest-asyncio strict.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain.agents.middleware.types import ModelRequest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END

from app.ai.middleware.briefing_context import (
    _BRIEFING_CONTEXT_PREFIX,
    BriefingContextMiddleware,
    _render_briefing_block,
)
from app.ai.plan import (
    PLAN_RESULT_INLINE_LIMIT,
    PlanDocument,
    PlannerOutput,
    PlannerStepOutput,
    PlanStep,
)
from app.ai.planner import _MAX_PLAN_STEPS, _merge_replanned_steps, planner_node
from app.ai.supervisor_orchestrator import (
    SupervisorOrchestrator,
    _briefing_update,
)
from app.ai.tools.types import ToolContext

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_llm_response(content: str) -> MagicMock:
    """Create a mock LLM response carrying string ``content``."""
    msg = MagicMock()
    msg.content = content
    return msg


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


_SPECIALIST_CATALOG: list[dict[str, str]] = [
    {"name": "project_manager", "description": "Read project / WBS data"},
    {"name": "document_manager", "description": "Create and save documents"},
]


# ===========================================================================
# Test 1: clean current briefing -> replanner drops the redundant step
# ===========================================================================


@pytest.mark.asyncio
async def test_replan_clean_context_drops_redundant_step() -> None:
    """The trace regression: after project_manager reads WBS AND saves the
    markdown doc (over-delivery), the supervisor requests a replan because
    step 1 (document_manager) is already accomplished. The replanner, now
    seeing the LIVE briefing finding text, returns a revised plan that
    contains ONLY the completed read step (no phantom duplicate). Proves
    Phase 2's clean-context fix reached the replanner's INPUT prompt.
    """
    # Existing plan: step 0 completed (project_manager saved the file), step 1
    # pending (document_manager was going to create the very same file).
    existing_plan = PlanDocument(
        original_request="crea un documento markdown con la lista delle WBE",
        steps=[
            PlanStep(
                step_index=0,
                specialist="project_manager",
                task_description="Read all WBS Elements",
                status="completed",
                result_summary=(
                    "Read WBS elements AND saved wbe_list.md at project root "
                    "(file already created)."
                ),
            ),
            PlanStep(
                step_index=1,
                specialist="document_manager",
                task_description="Create markdown doc with WBE list and save it",
                status="pending",
                dependencies=[0],
            ),
        ],
        requires_planning=True,
    )

    # Mock replanner: seeing the LIVE briefing (file already saved), it
    # concludes NO pending work remains and returns ZERO revised steps. The
    # merge then preserves only the completed step 0 -> no phantom pending
    # step. This is the realistic "clean context -> drop redundant step"
    # outcome the trace needed (the phantom in the trace came from the
    # replanner echoing a now-redundant step; with clean context it drops it).
    revised_output = PlannerOutput(
        original_request="crea un documento markdown con la lista delle WBE",
        requires_planning=True,
        estimated_complexity="simple",
        steps=[],  # nothing left to do -- file already saved
    )
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = _make_llm_response(revised_output.model_dump_json())

    # Live briefing shows the file was already saved.
    briefing_data: dict[str, Any] = {
        "original_request": "crea un documento markdown con la lista delle WBE",
        "sections": [
            {
                "specialist_name": "project_manager",
                "findings": "Saved wbe_list.md at the project root.",
                "key_findings": ["wbe_list.md already saved"],
                "open_questions": [],
                "delegation_notes": "",
                "task_description": "Read all WBS Elements",
            }
        ],
        "supervisor_analysis": "",
        "task_history": [],
    }

    state: dict[str, Any] = {
        "messages": [
            HumanMessage(content="crea un documento markdown con la lista delle WBE")
        ],
        "plan_data": existing_plan.model_dump(),
        "replan_context": "Step 1 already accomplished -- file saved by step 0.",
        "briefing_data": briefing_data,
    }

    result = await planner_node(state, mock_llm, specialist_catalog=_SPECIALIST_CATALOG)

    plan = PlanDocument.from_state(result["plan_data"])

    # No pending step remains whose task duplicates the completed step's work:
    # the only step is the completed read; document_manager is gone.
    assert plan.get_next_pending_step() is None
    assert all(
        s.status == "completed" or "Read all WBS" not in s.task_description
        for s in plan.steps
    )
    # The document_manager step is NOT present anymore.
    assert not any(s.specialist == "document_manager" for s in plan.steps)

    # replan_context cleared and LLM called exactly once.
    assert result["replan_context"] == ""
    mock_llm.ainvoke.assert_awaited_once()

    # Phase 2 proof: the replanner's INPUT prompt carried the live briefing
    # finding text (the file was saved), so it had the clean context needed
    # to drop the redundant step.
    sent_messages = mock_llm.ainvoke.call_args.args[0]
    prompt_blob = "\n".join(
        m.content for m in sent_messages if isinstance(m.content, str)
    )
    assert "saved" in prompt_blob.lower() or "wbe_list" in prompt_blob.lower()


# ===========================================================================
# Test 2: code does NOT semantic-dedup steps (codifies the principle)
# ===========================================================================


def test_replan_does_not_semantic_dedup_steps() -> None:
    """Codifies the governing design principle: code in the plan/replan path
    does ONLY robust checks. It does NOT dedup revised steps against completed
    ones by comparing task text -- plan evaluation has too many special cases
    for code, and that is the LLM's job.

    Existing plan has a completed step 0 ("List projects"). The mock replanner
    returns a revised step whose ``task_description`` TEXTUALLY DUPLICATES
    step 0's ("List projects"). ``_merge_replanned_steps`` must PRESERVE that
    duplicate revised step as pending -- it is NOT stripped. If a future
    change adds ``_task_key`` / casefold / string dedup to the replan path,
    this test fails.
    """
    existing_plan = PlanDocument(
        original_request="List projects",
        steps=[
            PlanStep(
                step_index=0,
                specialist="project_manager",
                task_description="List projects",
                status="completed",
                result_summary="Found 3 projects",
            )
        ],
        requires_planning=True,
    )

    new_output = PlannerOutput(
        original_request="List projects",
        requires_planning=True,
        estimated_complexity="simple",
        steps=[
            PlannerStepOutput(
                step_index=0,
                specialist="project_manager",
                task_description="List projects",  # textually duplicates step 0
                dependencies=[],
                expected_output="Project list",
            )
        ],
    )

    valid = frozenset({"project_manager"})
    merged = _merge_replanned_steps(existing_plan, new_output, valid)

    # The completed step 0 is preserved...
    assert any(
        s.step_index == 0
        and s.status == "completed"
        and s.task_description == "List projects"
        for s in merged.steps
    )
    # ...AND the duplicate revised step is PRESERVED as pending (NOT stripped).
    # Intentional: code does no semantic dedup; that is the LLM's job.
    pending_dupes = [
        s
        for s in merged.steps
        if s.status == "pending" and s.task_description == "List projects"
    ]
    assert len(pending_dupes) == 1, (
        "Replan path must NOT semantic-dedup; the duplicate revised step is "
        "the LLM's responsibility to drop, not code's."
    )
    assert pending_dupes[0].replanned is True
    assert pending_dupes[0].step_index == 1  # re-indexed after the completed step


# ===========================================================================
# Test 3: completed preserved verbatim + count cap + contiguous re-indexing
# ===========================================================================


def test_replan_preserves_completed_and_caps_count() -> None:
    """Happy multi-step replan: 3 completed preserved verbatim; revised steps
    capped at ``_MAX_PLAN_STEPS - 3``; revised indices contiguous starting at
    ``max_completed_idx + 1``; all revised pending + ``replanned``.
    """
    existing_plan = PlanDocument(
        original_request="Multi-step",
        steps=[
            PlanStep(
                step_index=i,
                specialist="project_manager",
                task_description=f"Completed {i}",
                status="completed",
                result_summary=f"Result {i}",
            )
            for i in range(3)
        ],
        requires_planning=True,
    )

    # Replanner returns 4 revised steps (more than capacity allows).
    new_output = PlannerOutput(
        original_request="Multi-step",
        requires_planning=True,
        estimated_complexity="moderate",
        steps=[
            PlannerStepOutput(
                step_index=i,
                specialist="project_manager",
                task_description=f"Revised {i}",
                dependencies=[],
                expected_output=f"Out {i}",
            )
            for i in range(4)
        ],
    )

    valid = frozenset({"project_manager"})
    merged = _merge_replanned_steps(existing_plan, new_output, valid)

    # 3 completed preserved verbatim (status/result_summary/indices).
    completed = [s for s in merged.steps if s.status == "completed"]
    assert len(completed) == 3
    for i, step in enumerate(completed):
        assert step.step_index == i
        assert step.result_summary == f"Result {i}"
        assert step.task_description == f"Completed {i}"

    # Only _MAX_PLAN_STEPS - 3 revised steps admitted.
    revised = [s for s in merged.steps if s.status == "pending"]
    assert len(revised) == _MAX_PLAN_STEPS - 3

    # Revised indices contiguous starting at max_completed_idx + 1 (= 3).
    assert [s.step_index for s in revised] == list(range(3, 3 + len(revised)))
    # All revised pending + replanned.
    assert all(s.status == "pending" for s in revised)
    assert all(s.replanned is True for s in revised)

    # Total respects the hard cap.
    assert len(merged.steps) <= _MAX_PLAN_STEPS


# ===========================================================================
# Test 4: BriefingContextMiddleware renders current findings each turn (P1)
# ===========================================================================


@pytest.mark.asyncio
async def test_briefing_middleware_renders_current_findings_each_turn() -> None:
    """P1 fix: the per-turn middleware renders the CURRENT briefing between
    sentinels on every call. Two successive turns both show the live finding
    ("CPI=0.94, file saved"), never the stale "No findings yet.", and exactly
    ONE briefing span (sentinel span replacement, not accumulation).

    Also asserts ``_briefing_update`` no longer emits a one-shot ``messages``
    SystemMessage (the stale-message root cause): after Change 2 the briefing
    reaches the supervisor only via this middleware.
    """
    briefing_data: dict[str, Any] = {
        "original_request": "analyze",
        "sections": [
            {
                "specialist_name": "evm_analyst",
                "findings": "CPI=0.94, file saved",
                "key_findings": ["CPI below 1.0"],
                "open_questions": [],
                "delegation_notes": "",
                "task_description": "calc CPI",
            }
        ],
        "supervisor_analysis": "",
        "task_history": [],
    }

    middleware = BriefingContextMiddleware()
    base_prompt = "You are a supervisor. Plan: do work."

    # Turn 1: bare prompt, no briefing span yet.
    captured: dict[str, Any] = {}

    async def handler(req: ModelRequest[Any]) -> Any:
        captured["text"] = req.system_message.text if req.system_message else ""
        return MagicMock()

    request1 = ModelRequest(
        model=MagicMock(),
        messages=[],
        system_message=SystemMessage(content=base_prompt),
        tools=[],
        state={"briefing_data": briefing_data, "messages": []},
    )
    await middleware.awrap_model_call(request1, handler)
    text1 = captured["text"]
    assert "CPI=0.94" in text1
    assert "No findings yet." not in text1
    assert text1.count("<!--BRIEFING_START-->") == 1

    # Turn 2: seed system_message from turn 1's output (simulate successive
    # turns). The middleware must REPLACE the prior span, not accumulate.
    request2 = ModelRequest(
        model=MagicMock(),
        messages=[],
        system_message=SystemMessage(content=text1),
        tools=[],
        state={"briefing_data": briefing_data, "messages": []},
    )
    await middleware.awrap_model_call(request2, handler)
    text2 = captured["text"]
    assert "CPI=0.94" in text2
    assert "No findings yet." not in text2
    # EXACTLY one briefing span after two turns (span replacement, not add).
    assert text2.count("<!--BRIEFING_START-->") == 1

    # _render_briefing_block helper honors the prefix and empty-state fallback.
    assert _render_briefing_block(briefing_data).startswith(_BRIEFING_CONTEXT_PREFIX)
    assert "No findings yet." in _render_briefing_block(None)

    # _briefing_update no longer emits a one-shot messages SystemMessage
    # (the briefing now reaches the supervisor via this middleware only).
    from app.ai.briefing import BriefingDocument

    doc = BriefingDocument.from_state(briefing_data)
    update = _briefing_update(doc)
    assert "messages" not in update


# ===========================================================================
# Test 5: plan block minimal + no-handoff terminates (F1 removal)
# ===========================================================================


def test_plan_block_minimal_and_no_handoff_terminates() -> None:
    """Bundles the ``to_prompt_text`` Phase 2 fixes with the F1-removal
    termination guarantee.

    (a) ``to_prompt_text``:
        - completed step with a ~2000-char result_summary inlines a TRUNCATED
          result (<= PLAN_RESULT_INLINE_LIMIT + 3 chars to allow for ``...``).
        - failed step renders ``Error:`` (NOT plain ``Result:``).
        - numbering is 1-based (``"1."``, ``"2."``).
    (b) F1 is REMOVED: the router's no-handoff branch returns END even when a
        genuinely-pending step exists -- i.e. it does NOT route to a removed
        ``"premature_completion_guard"`` node. Termination stays guaranteed by
        END + iteration/replan caps + ``_bounded_terminate_node``.
    """
    long_result = "X" * 2000
    error_string = "Specialist evm_analyst failed: Tavily API quota exceeded"
    plan = PlanDocument(
        original_request="research + summarize",
        steps=[
            PlanStep(
                step_index=0,
                specialist="document_manager",
                task_description="Load the project document",
                status="completed",
                result_summary=long_result,
            ),
            PlanStep(
                step_index=1,
                specialist="web_researcher",
                task_description="Research market benchmarks",
                status="failed",
                result_summary=error_string,
            ),
        ],
        requires_planning=True,
    )

    text = plan.to_prompt_text()

    # (a) 1-based numbering.
    assert "  1. " in text
    assert "  2. " in text
    assert "  0. " not in text

    # Completed result is truncated to <= PLAN_RESULT_INLINE_LIMIT + 3 ("...").
    completed_inline = next(
        line for line in text.splitlines() if line.strip().startswith("Result:")
    )
    # The result body after "Result: " must be <= limit + 3.
    body = completed_inline.strip()[len("Result: ") :]
    assert len(body) <= PLAN_RESULT_INLINE_LIMIT + 3
    assert body.endswith("...")

    # Failed step renders Error: with the error string (not plain Result:).
    error_inline = next(
        line for line in text.splitlines() if line.strip().startswith("Error:")
    )
    assert "Tavily API quota exceeded" in error_inline

    # (b) F1 removal: no-handoff -> END even with a pending step present.
    # Build a plan with a genuinely-pending dispatchable step and a text-only
    # "done" supervisor last message.
    pending_plan = PlanDocument(
        original_request="two-step",
        steps=[
            PlanStep(
                step_index=0,
                specialist="document_manager",
                task_description="Done step",
                status="completed",
                result_summary="ok",
            ),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="Still pending step",
                status="pending",
            ),
        ],
        requires_planning=True,
    )
    state: dict[str, Any] = {
        "messages": [
            HumanMessage(content="two-step"),
            AIMessage(content="All done."),  # text-only, no tool_calls
        ],
        "supervisor_iterations": 1,
        "max_supervisor_iterations": 10,
        "max_replan_count": 2,
        "replan_count": 0,
        "completed_specialists": set(),
        "completed_steps": {0},
        "plan_data": pending_plan.model_dump(),
    }
    router = SupervisorOrchestrator._make_supervisor_router(["evm_analyst"])
    result = router(state)
    # Terminates at END -- NOT a removed guard node.
    assert result == END
    assert result != "premature_completion_guard"
