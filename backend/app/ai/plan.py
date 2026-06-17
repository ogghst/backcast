"""Plan document models for the planner node.

Defines the structured decomposition of a user request into ordered steps,
each assigned to a specialist. Pure Pydantic — no AI framework dependencies.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

StepStatus = Literal["pending", "in_progress", "completed", "skipped", "failed"]

VALID_SPECIALISTS: frozenset[str] = frozenset({"general_purpose"})


class PlanStep(BaseModel):
    """A single atomic step within a plan.

    Each step targets one specialist with a focused task description.
    Dependencies reference other step indices that must complete first.

    ``replanned`` is True for steps introduced or revised by a replan
    (set in ``_merge_replanned_steps``); completed steps carried over from
    the original plan stay False. The flag flows to the UI via PLAN_UPDATE
    so replanned steps can be visually distinguished.
    """

    step_index: int
    specialist: str
    task_description: str
    dependencies: list[int] = []
    input_from_dependencies: str | None = None
    expected_output: str = ""
    status: StepStatus = "pending"
    result_summary: str | None = None
    # Resolved-identity channel (F2): concrete identifiers created/resolved by
    # the specialist (created-entity code/name + resolved project). Foregrounded
    # by ``_build_completion_nudge`` as RESOLVED FACTS so the supervisor's final
    # answer cites them instead of re-deriving/re-disambiguating identities.
    delegation_notes: str | None = None
    replanned: bool = False


class PlannerStepOutput(BaseModel):
    """Single step in the planner's structured LLM output."""

    step_index: int = Field(description="Sequential step index starting from 0")
    specialist: str = Field(description="Specialist name from the available list")
    task_description: str = Field(
        description="Focused, actionable description of what this step should do"
    )
    dependencies: list[int] = Field(
        default=[], description="Indices of steps that must complete first"
    )
    expected_output: str = Field(
        default="", description="What this step should produce"
    )


class PlannerOutput(BaseModel):
    """Structured output schema for the planner LLM call."""

    original_request: str = Field(description="The user's request verbatim")
    requires_planning: bool = Field(
        description="True if multi-step execution is needed"
    )
    estimated_complexity: Literal["simple", "moderate", "complex"] = Field(
        description="Assessment of request complexity"
    )
    steps: list[PlannerStepOutput] = Field(
        description="Ordered list of execution steps"
    )


class PlanDocument(BaseModel):
    """Structured execution plan produced by the planner node.

    If ``requires_planning`` is False the plan represents a single-step
    fallback that routes directly to the most appropriate specialist.
    """

    original_request: str
    steps: list[PlanStep] = []
    estimated_complexity: Literal["simple", "moderate", "complex"] = "simple"
    requires_planning: bool = False
    specialist_catalog: list[dict[str, Any]] | None = None

    # ------------------------------------------------------------------
    # Reconstruction
    # ------------------------------------------------------------------

    @classmethod
    def from_state(cls, data: dict[str, Any]) -> PlanDocument:
        """Reconstruct from a state dict with consistent fallback."""
        try:
            return cls.model_validate(data)
        except Exception:
            return cls(original_request="(recovered)")

    # ------------------------------------------------------------------
    # Step accessors
    # ------------------------------------------------------------------

    def get_step(self, step_index: int) -> PlanStep | None:
        """Return the step matching *step_index*, or ``None``."""
        for step in self.steps:
            if step.step_index == step_index:
                return step
        return None

    def get_next_pending_step(self) -> PlanStep | None:
        """Return the first pending step whose dependencies are met."""
        for step in self.steps:
            if step.status == "pending" and self.are_dependencies_met(step.step_index):
                return step
        return None

    def get_first_incomplete_step_index(self) -> int | None:
        """Return the step_index of the first non-completed/non-skipped step.

        Used to determine where to resume a stopped execution.
        Returns ``None`` when all steps are completed or skipped.
        """
        for step in self.steps:
            if step.status not in ("completed", "skipped"):
                return step.step_index
        return None

    def completed_step_indices(self) -> set[int]:
        """Return step indices for steps that are completed or skipped."""
        return {
            s.step_index for s in self.steps if s.status in ("completed", "skipped")
        }

    # ------------------------------------------------------------------
    # Step mutations
    # ------------------------------------------------------------------

    def mark_step_completed(
        self,
        step_index: int,
        result_summary: str,
        delegation_notes: str | None = None,
    ) -> None:
        """Mark a step as completed with a result summary.

        Args:
            step_index: The step to mark completed.
            result_summary: The specialist's summary of what was accomplished.
            delegation_notes: Optional resolved-identity notes (created-entity
                code/name + resolved project) sourced from the specialist's
                ``SpecialistOutput.delegation_notes``. Foregrounded by the
                completion nudge as RESOLVED FACTS (F2).
        """
        step = self.get_step(step_index)
        if step is not None:
            step.status = "completed"
            step.result_summary = result_summary
            if delegation_notes is not None:
                step.delegation_notes = delegation_notes

    def mark_step_failed(self, step_index: int, error: str) -> None:
        """Mark a step as failed with an error description."""
        step = self.get_step(step_index)
        if step is not None:
            step.status = "failed"
            step.result_summary = error

    # ------------------------------------------------------------------
    # Dependency helpers
    # ------------------------------------------------------------------

    def are_dependencies_met(self, step_index: int) -> bool:
        """Check whether all dependencies of a step are completed."""
        step = self.get_step(step_index)
        if step is None:
            return False
        for dep_idx in step.dependencies:
            dep = self.get_step(dep_idx)
            if dep is None or dep.status != "completed":
                return False
        return True

    def blocked_step_indices(self) -> list[int]:
        """Pending steps permanently blocked because a dependency FAILED.

        A pending step whose dependency is merely ``pending``/``in_progress``
        is NOT blocked (it may yet become dispatchable). Only a ``failed``
        dependency permanently blocks it.
        """
        failed = {s.step_index for s in self.steps if s.status == "failed"}
        return [
            s.step_index
            for s in self.steps
            if s.status == "pending" and any(d in failed for d in s.dependencies)
        ]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_specialists(self, available: list[str]) -> list[str]:
        """Return specialist names in this plan not present in *available*."""
        available_set = set(available)
        invalid: list[str] = []
        seen: set[str] = set()
        for step in self.steps:
            if step.specialist not in available_set and step.specialist not in seen:
                invalid.append(step.specialist)
                seen.add(step.specialist)
        return invalid

    # ------------------------------------------------------------------
    # Prompt serialization
    # ------------------------------------------------------------------

    def to_prompt_text(self) -> str:
        """Compact text representation for injection into supervisor context."""
        lines: list[str] = [
            "## Execution Plan",
            f"Request: {self.original_request}",
            f"Complexity: {self.estimated_complexity}",
            f"Steps: {len(self.steps)}",
        ]

        for step in self.steps:
            status_marker = {
                "pending": "[pending]",
                "in_progress": "[in progress]",
                "completed": "[completed]",
                "skipped": "[skipped]",
                "failed": "[failed]",
            }.get(step.status, "[unknown]")

            dep_str = f" (depends on {step.dependencies})" if step.dependencies else ""
            lines.append(
                f"  {step.step_index}. {status_marker} "
                f"{step.specialist}: {step.task_description}{dep_str}"
            )

            if step.input_from_dependencies:
                lines.append(f"     Input: {step.input_from_dependencies}")

            if step.result_summary:
                lines.append(f"     Result: {step.result_summary}")

        return "\n".join(lines)


__all__ = [
    "PlanDocument",
    "PlanStep",
    "PlannerOutput",
    "PlannerStepOutput",
    "StepStatus",
    "VALID_SPECIALISTS",
]
