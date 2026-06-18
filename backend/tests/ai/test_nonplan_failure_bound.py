"""Tests for Fix C: bounding the non-plan failure/timeout loop.

In PURE non-plan mode (no active step AND no active plan), a failed/timed-out
specialist could previously be re-dispatched by the supervisor until
``max_supervisor_iterations`` (~5x120s timeouts).  This adds a dedicated
``specialist_failure_counts`` state field and force-ends the graph on the 2nd
CONSECUTIVE failure of the SAME specialist, guaranteeing termination.

The decision is factored into a small pure helper,
``_decide_nonplan_failure_action``, so it is unit-testable without spinning up
the whole graph.  The helper returns a dataclass describing whether to
continue (goto supervisor) or terminate (goto END), the message to inject, and
the failure-count update.
"""

from __future__ import annotations

from app.ai.supervisor_orchestrator import _decide_nonplan_failure_action

# ===========================================================================
# 1st non-plan failure -> guidance injected, goto supervisor, count=1
# ===========================================================================


def test_first_failure_goes_to_supervisor() -> None:
    decision = _decide_nonplan_failure_action(
        specialist_name="project_manager",
        failure_counts={},
        error_message="invocation exceeded 120s of active time",
    )
    assert decision.goto == "supervisor"
    assert decision.failure_counts_update == {"project_manager": 1}
    assert decision.message is not None
    # Guidance must tell the supervisor NOT to immediately re-dispatch.
    assert "do NOT" in decision.message or "not" in decision.message.lower()


def test_first_failure_informs_user_of_failure() -> None:
    decision = _decide_nonplan_failure_action(
        specialist_name="evm_analyst",
        failure_counts={},
        error_message="connection reset",
    )
    assert decision.message is not None
    assert "failed" in decision.message.lower() or "error" in decision.message.lower()


# ===========================================================================
# 2nd non-plan failure of SAME specialist -> goto=END with user-facing message
# ===========================================================================


def test_second_failure_of_same_specialist_terminates() -> None:
    decision = _decide_nonplan_failure_action(
        specialist_name="project_manager",
        failure_counts={"project_manager": 1},
        error_message="invocation exceeded 120s of active time",
    )
    # GUARANTEED termination: goto END, not supervisor.
    assert decision.goto == "END"
    assert decision.failure_counts_update == {"project_manager": 2}
    # A user-facing final message is present.
    assert decision.message is not None
    assert "project_manager" in decision.message
    # It must tell the user something went wrong and how to proceed.
    assert "retry" in decision.message.lower() or "rephrase" in decision.message.lower()


def test_second_failure_terminates_even_at_higher_counts() -> None:
    """If the count somehow already exceeds 1, still terminate."""
    decision = _decide_nonplan_failure_action(
        specialist_name="forecast_manager",
        failure_counts={"forecast_manager": 5},
        error_message="timeout",
    )
    assert decision.goto == "END"


# ===========================================================================
# Different specialist -> independent count
# ===========================================================================


def test_different_specialist_count_is_independent() -> None:
    """project_manager having failed twice does not trip evm_analyst."""
    decision = _decide_nonplan_failure_action(
        specialist_name="evm_analyst",
        failure_counts={"project_manager": 2},
        error_message="timeout",
    )
    # evm_analyst is on its FIRST failure -> continue, not terminate.
    assert decision.goto == "supervisor"
    assert decision.failure_counts_update == {"evm_analyst": 1}


def test_failure_counts_keyed_by_specialist_name_only() -> None:
    """The count is per-specialist (name), NOT per-(specialist, step) like the
    plan-mode dispatch counter."""
    decision = _decide_nonplan_failure_action(
        specialist_name="project_manager",
        failure_counts={"project_manager": 1},
        error_message="timeout",
    )
    # The update key is the bare specialist name.
    assert "project_manager" in decision.failure_counts_update
    assert "|" not in next(iter(decision.failure_counts_update.keys()))


# ===========================================================================
# Edge: empty error message
# ===========================================================================


def test_empty_error_message_still_terminates_on_second_failure() -> None:
    decision = _decide_nonplan_failure_action(
        specialist_name="project_manager",
        failure_counts={"project_manager": 1},
        error_message="",
    )
    assert decision.goto == "END"
    assert decision.message is not None
