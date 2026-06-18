"""Tests for PlanStep.delegation_notes plumbing (F2 resolved-identity channel).

``delegation_notes`` is the field designed to carry concrete resolved
identifiers (created-entity code/name + resolved project) from the
specialist into the plan.  ``mark_step_completed`` now accepts and stores it
so ``_build_completion_nudge`` can foreground RESOLVED FACTS.
"""

from __future__ import annotations

from app.ai.plan import PlanDocument, PlanStep


def test_mark_step_completed_stores_delegation_notes() -> None:
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="project_manager",
                task_description="create the WBE",
                status="pending",
            ),
        ],
        requires_planning=True,
    )
    plan.mark_step_completed(
        0,
        "WBE creata.",
        delegation_notes="Created WBE DESIGN-001 on project QAE001 (id=42).",
    )
    step = plan.get_step(0)
    assert step is not None
    assert step.status == "completed"
    assert step.result_summary == "WBE creata."
    assert step.delegation_notes == "Created WBE DESIGN-001 on project QAE001 (id=42)."


def test_mark_step_completed_delegation_notes_optional() -> None:
    """Backward-compatible: delegation_notes defaults to None when omitted."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="a",
                task_description="t",
                status="pending",
            ),
        ],
        requires_planning=True,
    )
    plan.mark_step_completed(0, "done")
    step = plan.get_step(0)
    assert step is not None
    assert step.result_summary == "done"
    assert step.delegation_notes is None


def test_planstep_delegation_notes_defaults_none() -> None:
    step = PlanStep(step_index=0, specialist="a", task_description="t")
    assert step.delegation_notes is None


def test_mark_step_completed_preserves_delegation_notes_through_roundtrip() -> None:
    """delegation_notes survives model_dump() -> from_state() (state sharing)."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="a",
                task_description="t",
                status="pending",
            ),
        ],
        requires_planning=True,
    )
    plan.mark_step_completed(0, "summary", delegation_notes="notes-xyz")
    restored = PlanDocument.from_state(plan.model_dump())
    step = restored.get_step(0)
    assert step is not None
    assert step.delegation_notes == "notes-xyz"
