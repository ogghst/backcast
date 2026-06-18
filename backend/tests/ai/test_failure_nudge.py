"""Tests for the supervisor plan-failure nudge (issue #2).

When a specialist step FAILS during a plan-driven chat, the supervisor
historically received a weak directive ("continue delegating the next
pending step, or respond with the findings so far") that said nothing about
informing the user of the failure or quoting the actual error.  On weaker
reasoning models (e.g. GLM-4.7) it then answered with a stale "awaiting
results" message and left the failure visible only in the side planning
panel (e2e session 97be79d4).  ``_build_failure_nudge`` now forces a
grounded failure report and distinguishes "pending steps remain" from
"plan ended in failure".  These tests cover the helper directly.
"""

from __future__ import annotations

from app.ai.plan import PlanDocument, PlanStep
from app.ai.supervisor_orchestrator import _build_failure_nudge

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _step(
    step_index: int,
    specialist: str,
    status: str,
    *,
    result_summary: str | None = None,
    dependencies: list[int] | None = None,
) -> PlanStep:
    return PlanStep(
        step_index=step_index,
        specialist=specialist,
        task_description=f"task for {specialist}",
        status=status,
        result_summary=result_summary,
        dependencies=dependencies or [],
    )


def _timeout_error() -> str:
    return "invocation exceeded 120s of active time"


# ===========================================================================
# No-pending-steps case (plan ended in failure): must report + forbid
# ===========================================================================


def test_no_pending_inlines_error_message() -> None:
    """The actual error string must appear verbatim in the nudge."""
    plan = PlanDocument(
        original_request="sviluppa la WBE di design",
        steps=[
            _step(0, "project_manager", "failed", result_summary=None),
        ],
        requires_planning=True,
    )
    nudge = _build_failure_nudge(plan, "project_manager", _timeout_error())

    assert _timeout_error() in nudge


def test_no_pending_must_inform_user_and_forbid_success() -> None:
    """No-pending nudge forces informing the user and forbids claiming
    success / awaiting-results / missing-tools."""
    plan = PlanDocument(
        original_request="x",
        steps=[_step(0, "project_manager", "failed")],
        requires_planning=True,
    )
    nudge = _build_failure_nudge(plan, "project_manager", _timeout_error())

    # Must direct the supervisor to inform the user now.
    assert "MUST now respond to the user" in nudge
    assert "FAILED" in nudge
    # Explicit prohibitions.
    assert "Do NOT claim success" in nudge
    # Catches the Italian stale answer from the e2e.
    assert "Attendo i risultati" in nudge
    assert "awaiting results" in nudge
    assert "missing" in nudge
    assert "unavailable" in nudge
    assert "Do NOT delegate further" in nudge


def test_no_pending_inlines_completed_step_summaries() -> None:
    """When other steps completed before the failure, their summaries are
    inlined so the supervisor can report partial progress."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            _step(
                0,
                "project_manager",
                "completed",
                result_summary="8 WBE creati con successo.",
            ),
            _step(1, "evm_analyst", "failed"),
        ],
        requires_planning=True,
    )
    nudge = _build_failure_nudge(plan, "evm_analyst", _timeout_error())

    assert "## Completed before the failure" in nudge
    assert "8 WBE creati con successo" in nudge
    assert "Step 1 (project_manager):" in nudge


def test_no_pending_placeholder_when_nothing_accomplished() -> None:
    """No completed steps -> the placeholder is shown, no crash."""
    plan = PlanDocument(
        original_request="x",
        steps=[_step(0, "project_manager", "failed")],
        requires_planning=True,
    )
    nudge = _build_failure_nudge(plan, "project_manager", _timeout_error())

    assert "## Completed before the failure" in nudge
    assert "(nothing)" in nudge


# ===========================================================================
# Pending-steps-remain case: inform user AND continue/replan
# ===========================================================================


def test_pending_steps_informs_user_and_continues() -> None:
    """When pending steps remain, the nudge must (1) tell the user about the
    failure AND (2) allow delegating the next pending step / replan."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            _step(0, "project_manager", "failed"),
            _step(1, "evm_analyst", "pending"),
        ],
        requires_planning=True,
    )
    nudge = _build_failure_nudge(plan, "project_manager", _timeout_error())

    assert _timeout_error() in nudge
    # Must instruct informing the user first.
    assert "briefly inform the user" in nudge
    assert "FAILED" in nudge
    # Must allow continuing to the next pending step.
    assert "delegate the next pending step" in nudge
    # The next pending step's index (1-based) and specialist are named so the
    # supervisor knows what to delegate.  Emitted lowercase mid-sentence.
    assert "step 2 (evm_analyst)" in nudge
    assert "request_replan" in nudge
    # Must forbid claiming the failed step succeeded.
    assert "Do NOT claim this step succeeded" in nudge


def test_pending_steps_does_not_promise_delegation_when_zero_pending() -> None:
    """Regression for the old bug: the nudge must NEVER tell the supervisor
    to 'continue delegating the next pending step' when zero pending steps
    remain -- that branch is the no-pending branch and must hard-direct an
    immediate failure report instead."""
    plan = PlanDocument(
        original_request="x",
        steps=[_step(0, "project_manager", "failed")],
        requires_planning=True,
    )
    nudge = _build_failure_nudge(plan, "project_manager", _timeout_error())

    assert "Continue delegating the next pending step" not in nudge
    assert "delegate the next pending step" not in nudge


# ===========================================================================
# Robustness: empty / None error message
# ===========================================================================


def test_empty_error_message_does_not_crash() -> None:
    """An empty/None error must not crash; a placeholder is substituted."""
    plan = PlanDocument(
        original_request="x",
        steps=[_step(0, "project_manager", "failed")],
        requires_planning=True,
    )
    nudge_empty = _build_failure_nudge(plan, "project_manager", "")
    nudge_none = _build_failure_nudge(plan, "project_manager", "")

    assert "(no error detail recorded)" in nudge_empty
    assert "(no error detail recorded)" in nudge_none
    assert "FAILED" in nudge_empty


# ===========================================================================
# Truncation mirrors the completion nudge bound
# ===========================================================================


def test_completed_summary_truncated_in_no_pending_case() -> None:
    """A long completed summary is truncated in the no-pending branch."""
    long_summary = "Y" * 1500
    plan = PlanDocument(
        original_request="x",
        steps=[
            _step(0, "project_manager", "completed", result_summary=long_summary),
            _step(1, "evm_analyst", "failed"),
        ],
        requires_planning=True,
    )
    nudge = _build_failure_nudge(plan, "evm_analyst", _timeout_error())

    assert long_summary not in nudge
    assert "Y" * 800 in nudge
    assert "..." in nudge
