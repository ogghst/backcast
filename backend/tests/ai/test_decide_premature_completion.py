"""Tests for the F1 premature-completion guard (structural backstop).

When a multi-step plan is active and the supervisor emits a TEXT-ONLY answer
(no handoff tool call) while a dispatchable plan step is still PENDING, the
graph previously terminated at the router's ``No handoff → END`` branch,
baking in a confabulated "all done" final answer (memory 19 / Scenario B).
``_decide_premature_completion`` is the pure, unit-testable decision helper
that mirrors ``_decide_nonplan_failure_action``: it either routes to a guard
node that re-prompts the supervisor, or (at the global cap) force-ends.
"""

from __future__ import annotations

from app.ai.plan import PlanDocument, PlanStep
from app.ai.supervisor_orchestrator import _decide_premature_completion

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _pending_step(step_index: int, specialist: str = "evm_analyst") -> PlanStep:
    return PlanStep(
        step_index=step_index,
        specialist=specialist,
        task_description=f"task {step_index}",
        status="pending",
    )


def _completed_step(step_index: int, specialist: str = "general_purpose") -> PlanStep:
    return PlanStep(
        step_index=step_index,
        specialist=specialist,
        task_description=f"task {step_index}",
        status="completed",
        result_summary="done",
    )


def _plan(steps: list[PlanStep], requires_planning: bool = True) -> PlanDocument:
    return PlanDocument(
        original_request="x",
        steps=steps,
        requires_planning=requires_planning,
    )


# ===========================================================================
# Fires only on text-only + dispatchable pending step
# ===========================================================================


def test_fires_on_text_only_with_pending_step() -> None:
    plan = _plan([_completed_step(0), _pending_step(1)])
    decision = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=1,
        max_iterations=5,
        premature_reprompts=0,
        max_reprompts=2,
    )
    assert decision.goto == "premature_completion_guard"
    assert decision.iterations_delta == 1
    assert decision.reprompts_delta == 1


def test_noop_when_last_msg_has_tool_calls() -> None:
    plan = _plan([_completed_step(0), _pending_step(1)])
    decision = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=False,
        supervisor_iterations=1,
        max_iterations=5,
        premature_reprompts=0,
        max_reprompts=2,
    )
    assert decision.goto == "END"


def test_noop_when_last_msg_is_tool_message_post_handoff() -> None:
    """Regression: a correct handoff returns
    ``Command(goto=agent, update={"messages": [ai_message, tool_message]})``,
    so ``messages[-1]`` becomes a ``ToolMessage`` (NOT an ``AIMessage``). The
    router/guard-node predicate ``last_msg_is_text_only`` must be ``False`` for
    a ``ToolMessage`` — a mid-flow message is NOT a final text answer — so the
    guard does NOT false-fire after every correct delegation.

    This asserts the predicate computed FROM a ``ToolMessage`` last message
    using the SAME expression the router/guard-node use, then passes that
    ``False`` to the helper and expects a no-op (END).
    """
    from langchain_core.messages import AIMessage, ToolMessage

    # Simulate the post-handoff message shape: handoff tool call + its result.
    ai_msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "handoff_to_evm_analyst", "args": {}, "id": "call_1"},
        ],
    )
    tool_msg = ToolMessage(
        content="transferring to evm_analyst",
        tool_call_id="call_1",
        name="handoff_to_evm_analyst",
    )
    messages = [ai_msg, tool_msg]
    last_msg = messages[-1]
    # The SAME predicate used by the router (L1216) and guard node (L1254).
    last_msg_is_text_only = isinstance(last_msg, AIMessage) and not bool(
        getattr(last_msg, "tool_calls", None)
    )
    assert last_msg_is_text_only is False

    plan = _plan([_completed_step(0), _pending_step(1)])
    decision = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=last_msg_is_text_only,
        supervisor_iterations=1,
        max_iterations=5,
        premature_reprompts=0,
        max_reprompts=2,
    )
    assert decision.goto == "END"


def test_noop_when_no_plan() -> None:
    decision = _decide_premature_completion(
        plan=None,
        last_msg_is_text_only=True,
        supervisor_iterations=1,
        max_iterations=5,
        premature_reprompts=0,
        max_reprompts=2,
    )
    assert decision.goto == "END"


def test_noop_when_requires_planning_false() -> None:
    plan = _plan([_completed_step(0), _pending_step(1)], requires_planning=False)
    decision = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=1,
        max_iterations=5,
        premature_reprompts=0,
        max_reprompts=2,
    )
    assert decision.goto == "END"


def test_noop_when_no_steps() -> None:
    plan = _plan([], requires_planning=True)
    decision = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=1,
        max_iterations=5,
        premature_reprompts=0,
        max_reprompts=2,
    )
    assert decision.goto == "END"


def test_noop_when_no_dispatchable_pending_step() -> None:
    """get_next_pending_step() returns None (all done OR all blocked by failed
    deps) -> fall through to END, do not guard."""
    plan = _plan([_completed_step(0), _completed_step(1)])
    decision = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=1,
        max_iterations=5,
        premature_reprompts=0,
        max_reprompts=2,
    )
    assert decision.goto == "END"


def test_noop_when_pending_step_blocked_by_failed_dependency() -> None:
    """A pending step whose dependency FAILED is not dispatchable
    (get_next_pending_step excludes it via are_dependencies_met). No guard."""
    plan = _plan(
        [
            PlanStep(
                step_index=0,
                specialist="a",
                task_description="t",
                status="failed",
            ),
            PlanStep(
                step_index=1,
                specialist="b",
                task_description="t",
                status="pending",
                dependencies=[0],
            ),
        ]
    )
    assert plan.get_next_pending_step() is None
    decision = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=1,
        max_iterations=5,
        premature_reprompts=0,
        max_reprompts=2,
    )
    assert decision.goto == "END"


# ===========================================================================
# Global cap: premature_reprompts >= max_reprompts -> END
# ===========================================================================


def test_ends_at_global_reprompt_cap() -> None:
    plan = _plan([_completed_step(0), _pending_step(1)])
    decision = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=2,
        max_iterations=5,
        premature_reprompts=2,
        max_reprompts=2,
    )
    assert decision.goto == "END"
    # Clean intentional message, not a re-prompt.
    assert decision.reprompts_delta == 0


def test_global_cap_accumulates_across_distinct_steps() -> None:
    """Two DIFFERENT steps confabulated in sequence. 1st -> guard (reprompts
    0->1). 2nd -> guard (1->2). 3rd -> cap (2 >= 2) -> END."""
    # Step 1 confabulated:
    plan = _plan([_completed_step(0), _pending_step(1), _pending_step(2)])
    d1 = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=1,
        max_iterations=8,
        premature_reprompts=0,
        max_reprompts=2,
    )
    assert d1.goto == "premature_completion_guard"
    # Simulate step 1 then completed, step 2 confabulated:
    plan2 = _plan([_completed_step(0), _completed_step(1), _pending_step(2)])
    d2 = _decide_premature_completion(
        plan=plan2,
        last_msg_is_text_only=True,
        supervisor_iterations=2,
        max_iterations=8,
        premature_reprompts=1,
        max_reprompts=2,
    )
    assert d2.goto == "premature_completion_guard"
    # 3rd confabulation hits the GLOBAL cap -> END:
    plan3 = _plan([_completed_step(0), _completed_step(1), _pending_step(2)])
    d3 = _decide_premature_completion(
        plan=plan3,
        last_msg_is_text_only=True,
        supervisor_iterations=3,
        max_iterations=8,
        premature_reprompts=2,
        max_reprompts=2,
    )
    assert d3.goto == "END"


# ===========================================================================
# Message discipline: no re-render, one offending step, contrastive refutation
# ===========================================================================


def test_message_does_not_rerender_plan() -> None:
    """PlanAwareToolMiddleware already injects the plan + NEXT ACTION every
    turn; the correction must NOT re-render the plan (status markers / NEXT
    ACTION) — only the contrastive delta."""
    plan = _plan(
        [
            _completed_step(0),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="register 800 EUR cost event",
                status="pending",
            ),
        ]
    )
    decision = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=1,
        max_iterations=5,
        premature_reprompts=0,
        max_reprompts=2,
    )
    msg = decision.message
    assert msg is not None
    # No plan re-render markers.
    assert "[pending]" not in msg
    assert "[completed]" not in msg
    assert "## Execution Plan" not in msg
    assert "NEXT ACTION" not in msg


def test_message_leads_with_contrastive_refutation() -> None:
    plan = _plan(
        [
            _completed_step(0),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="register 800 EUR cost event",
                status="pending",
            ),
        ]
    )
    decision = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=1,
        max_iterations=5,
        premature_reprompts=0,
        max_reprompts=2,
    )
    msg = decision.message
    assert msg is not None
    assert "FALSE" in msg
    assert "Do NOT report a pending step as done" in msg


def test_message_cites_exactly_one_offending_step() -> None:
    plan = _plan(
        [
            _completed_step(0),
            _completed_step(1),
            PlanStep(
                step_index=2,
                specialist="accountant",
                task_description="register 800 EUR cost",
                status="pending",
            ),
        ]
    )
    decision = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=1,
        max_iterations=5,
        premature_reprompts=0,
        max_reprompts=2,
    )
    msg = decision.message
    assert msg is not None
    # Exactly one offending step cited (step 3 of 3, 1-based).
    assert "step 3/3" in msg
    assert "accountant" in msg
    assert "register 800 EUR cost" in msg
    assert "handoff_to_accountant" in msg
    # The completed steps (1, 2) are NOT enumerated.
    assert "step 1/" not in msg
    assert "step 2/" not in msg


def test_end_message_is_clean_intentional() -> None:
    plan = _plan([_completed_step(0), _pending_step(1)])
    decision = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=2,
        max_iterations=5,
        premature_reprompts=2,
        max_reprompts=2,
    )
    assert decision.goto == "END"
    # The END-path message must exist (clean intentional text).
    assert decision.message is not None
