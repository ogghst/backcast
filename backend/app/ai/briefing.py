"""Briefing document models for the Briefing Room orchestrator pattern.

Pure data models that accumulate specialist contributions into a structured
document. No AI framework dependencies — only Pydantic.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TaskAssignment(BaseModel):
    """A task delegation from the supervisor to a specialist."""

    specialist: str
    description: str
    rationale: str | None = None


class BriefingSection(BaseModel):
    """A single specialist's contribution to the briefing document."""

    specialist_name: str
    findings: str
    task_description: str | None = None
    supervisor_rationale: str | None = None
    key_findings: list[str] | None = None
    open_questions: list[str] | None = None
    delegation_notes: str | None = None
    step_index: int | None = None


class BriefingDocument(BaseModel):
    """Accumulating briefing document assembled by the orchestrator.

    Each specialist contribution appends a section to ``sections``.
    """

    original_request: str
    sections: list[BriefingSection] = []
    supervisor_analysis: str | None = None
    task_history: list[TaskAssignment] = []
    plan: list[dict[str, Any]] | None = None

    @classmethod
    def from_state(cls, briefing_data: dict[str, Any]) -> BriefingDocument:
        """Reconstruct from state dict with consistent fallback."""
        try:
            return cls.model_validate(briefing_data)
        except Exception:
            return cls(original_request="(recovered)")

    def add_task_assignment(self, assignment: TaskAssignment) -> None:
        self.task_history.append(assignment)

    def to_markdown(self) -> str:
        parts: list[str] = [
            "# Briefing Document",
            "",
            "## Request",
            self.original_request,
        ]

        if self.supervisor_analysis:
            parts += ["", "## Supervisor Analysis", self.supervisor_analysis]

        if self.task_history:
            parts += ["", "## Task History"]
            for idx, task in enumerate(self.task_history, start=1):
                parts.append(f"{idx}. **{task.specialist}**: {task.description}")
                if task.rationale:
                    parts.append(f"   - Rationale: {task.rationale}")

        if self.plan:
            parts += ["", "## Execution Plan"]
            for step_idx, step in enumerate(self.plan, start=1):
                specialist = step.get("specialist", "unknown")
                task_desc = step.get("task_description", "")
                status = step.get("status", "pending")
                parts.append(f"Step {step_idx}: [{specialist}] {task_desc} — {status}")

        if self.sections:
            parts += ["", "## Specialist Findings"]
            for idx, sec in enumerate(self.sections, start=1):
                header = sec.specialist_name
                if sec.step_index is not None:
                    header += f" (Step {sec.step_index})"
                else:
                    header += f" (Iteration {idx})"
                section_lines = [
                    "",
                    f"### {header}",
                ]

                # Findings are already cleaned of structured sections at input time
                # (in briefing_compiler.py), so we can render directly
                if sec.findings:
                    section_lines += [
                        "",
                        sec.findings,
                    ]
                if sec.key_findings:
                    section_lines += ["", "**Key Findings:**"]
                    for kf in sec.key_findings:
                        section_lines.append(f"- {kf}")
                if sec.open_questions:
                    section_lines += ["", "**Open Questions:**"]
                    for q in sec.open_questions:
                        section_lines.append(f"- {q}")
                if sec.delegation_notes:
                    section_lines += [
                        "",
                        f"**Delegation Notes:** {sec.delegation_notes}",
                    ]
                section_lines += ["", "---"]
                parts += section_lines

        return "\n".join(parts)

    def to_scoped_markdown(self, relevant_step_indices: set[int] | None = None) -> str:
        """Render a filtered briefing for a plan-step specialist.

        When *relevant_step_indices* is ``None``, falls back to the full
        :meth:`to_markdown` output.  When provided, only includes:

        - Request header (minimal domain context)
        - Supervisor analysis
        - Task history
        - Specialist findings whose ``step_index`` is in *relevant_step_indices*

        The execution plan section is **omitted** — the specialist only sees
        its own assignment block, not the full plan.
        """
        if relevant_step_indices is None:
            return self.to_markdown()

        parts: list[str] = [
            "# Briefing Document",
            "",
            "## Request",
            self.original_request,
        ]

        if self.supervisor_analysis:
            parts += ["", "## Supervisor Analysis", self.supervisor_analysis]

        if self.task_history:
            parts += ["", "## Task History"]
            for idx, task in enumerate(self.task_history, start=1):
                parts.append(f"{idx}. **{task.specialist}**: {task.description}")
                if task.rationale:
                    parts.append(f"   - Rationale: {task.rationale}")

        # Omit Execution Plan — specialist sees only its assignment block

        if self.sections:
            filtered = [
                sec
                for sec in self.sections
                if sec.step_index is None or sec.step_index in relevant_step_indices
            ]
            if filtered:
                parts += ["", "## Specialist Findings"]
                for sec in filtered:
                    header = sec.specialist_name
                    if sec.step_index is not None:
                        header += f" (Step {sec.step_index})"
                    else:
                        header += " (Step ?)"
                    section_lines = ["", f"### {header}"]
                    if sec.findings:
                        section_lines += ["", sec.findings]
                    if sec.key_findings:
                        section_lines += ["", "**Key Findings:**"]
                        for kf in sec.key_findings:
                            section_lines.append(f"- {kf}")
                    if sec.open_questions:
                        section_lines += ["", "**Open Questions:**"]
                        for q in sec.open_questions:
                            section_lines.append(f"- {q}")
                    if sec.delegation_notes:
                        section_lines += [
                            "",
                            f"**Delegation Notes:** {sec.delegation_notes}",
                        ]
                    section_lines += ["", "---"]
                    parts += section_lines

        return "\n".join(parts)


__all__ = ["BriefingDocument", "BriefingSection", "TaskAssignment"]
