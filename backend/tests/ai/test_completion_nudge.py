"""Tests for the supervisor plan-completion nudge (FIX B).

When ALL plan steps are completed, the supervisor (on a weaker reasoning
model such as GLM-4.7) used to receive only a bare directive -- "respond
with the briefing findings, do not delegate further" -- with NO inlined
results.  It then confabulated a failure ("delegation was wrong / no such
tools") even though the specialists had succeeded.  ``_build_completion_nudge``
now inlines each completed step's ``result_summary`` and grounds the
supervisor's final answer.  These tests cover the helper directly.
"""

from __future__ import annotations

from app.ai.plan import PlanDocument, PlanStep
from app.ai.supervisor_orchestrator import _build_completion_nudge

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _completed_step(
    step_index: int,
    specialist: str,
    result_summary: str,
) -> PlanStep:
    return PlanStep(
        step_index=step_index,
        specialist=specialist,
        task_description=f"task for {specialist}",
        status="completed",
        result_summary=result_summary,
    )


# ===========================================================================
# Grounding: inlines completed summaries + anti-confabulation instructions
# ===========================================================================


def test_nudge_inlines_completed_summaries() -> None:
    """Completed steps with result_summary values appear in the nudge."""
    plan = PlanDocument(
        original_request="sviluppa la WBE di design",
        steps=[
            _completed_step(
                0,
                "project_manager",
                "8 WBE creati con successo (Design, Procurement, ...).",
            ),
            _completed_step(
                1,
                "evm_analyst",
                "CPI computed at 0.98, SPI at 1.02.",
            ),
        ],
        requires_planning=True,
    )

    nudge = _build_completion_nudge(plan, cleaned_findings="ignored fallback")

    # The actual specialist findings are inlined (the grounding source).
    assert "8 WBE creati con successo" in nudge
    assert "CPI computed at 0.98" in nudge
    # Step numbering is 1-based for human readability.
    assert "Step 1 (project_manager):" in nudge
    assert "Step 2 (evm_analyst):" in nudge


def test_nudge_states_work_already_executed_and_no_delegation() -> None:
    """The nudge tells the supervisor the work is done and not to delegate."""
    plan = PlanDocument(
        original_request="x",
        steps=[_completed_step(0, "general_purpose", "done")],
        requires_planning=True,
    )
    nudge = _build_completion_nudge(plan, cleaned_findings="done")

    assert "ALREADY executed" in nudge
    assert "Do NOT delegate further" in nudge


def test_nudge_forbids_confabulated_failure_narrative() -> None:
    """The nudge explicitly forbids claiming the work is
    missing/impossible/unavailable and forbids re-litigating delegation."""
    plan = PlanDocument(
        original_request="x",
        steps=[_completed_step(0, "general_purpose", "done")],
        requires_planning=True,
    )
    nudge = _build_completion_nudge(plan, cleaned_findings="done")

    assert "missing" in nudge
    assert "impossible" in nudge
    assert "unavailable" in nudge
    assert "re-litigate" in nudge


def test_nudge_appends_completed_findings_section_header() -> None:
    """The inlined block sits under a `## Completed findings` header."""
    plan = PlanDocument(
        original_request="x",
        steps=[_completed_step(0, "general_purpose", "done")],
        requires_planning=True,
    )
    nudge = _build_completion_nudge(plan, cleaned_findings="done")
    assert "## Completed findings" in nudge


def test_nudge_reports_total_step_count() -> None:
    plan = PlanDocument(
        original_request="x",
        steps=[
            _completed_step(0, "a", "r0"),
            _completed_step(1, "b", "r1"),
            _completed_step(2, "c", "r2"),
        ],
        requires_planning=True,
    )
    nudge = _build_completion_nudge(plan, cleaned_findings="r2")
    assert "All 3 plan steps completed." in nudge


# ===========================================================================
# Truncation bounds prompt size (mirrors the [:500] preview style)
# ===========================================================================


def test_nudge_truncates_long_summaries() -> None:
    """Each summary is truncated to the limit and marked with an ellipsis."""
    long_summary = "X" * 1500
    plan = PlanDocument(
        original_request="x",
        steps=[_completed_step(0, "general_purpose", long_summary)],
        requires_planning=True,
    )
    nudge = _build_completion_nudge(plan, cleaned_findings="")

    # The full 1500-char summary must NOT appear verbatim.
    assert long_summary not in nudge
    # The truncated body is present and marked as continued.
    assert "X" * 800 in nudge
    assert "..." in nudge


# ===========================================================================
# Fallbacks: no completed summaries -> cleaned_findings -> placeholder
# ===========================================================================


def test_nudge_falls_back_to_cleaned_findings_when_no_summaries() -> None:
    """Steps completed but with empty result_summary -> use cleaned_findings."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="general_purpose",
                task_description="t",
                status="completed",
                result_summary=None,
            )
        ],
        requires_planning=True,
    )
    nudge = _build_completion_nudge(plan, cleaned_findings="fallback findings")

    assert "fallback findings" in nudge
    assert "## Completed findings" in nudge
    # The placeholder must NOT win when cleaned_findings is present.
    assert "(no findings recorded)" not in nudge


def test_nudge_falls_back_to_placeholder_when_nothing_recorded() -> None:
    """No completed summaries AND no cleaned_findings -> placeholder, no crash."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="general_purpose",
                task_description="t",
                status="completed",
                result_summary="",
            )
        ],
        requires_planning=True,
    )
    nudge = _build_completion_nudge(plan, cleaned_findings="")

    assert "(no findings recorded)" in nudge
    assert "## Completed findings" in nudge


def test_nudge_skips_non_completed_steps() -> None:
    """Only completed steps contribute findings; pending/failed are ignored."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            _completed_step(0, "a", "result-a"),
            PlanStep(
                step_index=1,
                specialist="b",
                task_description="t",
                status="pending",
            ),
            PlanStep(
                step_index=2,
                specialist="c",
                task_description="t",
                status="failed",
                result_summary="boom",
            ),
        ],
        requires_planning=True,
    )
    nudge = _build_completion_nudge(plan, cleaned_findings="")

    assert "result-a" in nudge
    assert "Step 2" not in nudge  # pending -> not inlined
    assert "boom" not in nudge  # failed -> not inlined
