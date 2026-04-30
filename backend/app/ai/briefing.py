"""Briefing document models for the Briefing Room orchestrator pattern.

Pure data models that accumulate specialist contributions into a structured
document. No AI framework dependencies — only Pydantic.
"""

from __future__ import annotations

import re

from pydantic import BaseModel


class TaskAssignment(BaseModel):
    """A task delegation from the supervisor to a specialist."""

    specialist: str
    description: str
    rationale: str | None = None


class BriefingSection(BaseModel):
    """A single specialist's contribution to the briefing document."""

    specialist_name: str
    task_description: str
    findings: str
    supervisor_rationale: str | None = None
    key_findings: list[str] | None = None
    open_questions: list[str] | None = None
    delegation_notes: str | None = None


class BriefingDocument(BaseModel):
    """Accumulating briefing document assembled by the orchestrator.

    Each specialist contribution appends a section to ``sections``.
    """

    original_request: str
    sections: list[BriefingSection] = []
    supervisor_analysis: str | None = None
    task_history: list[TaskAssignment] = []

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

        if self.sections:
            parts += ["", "## Specialist Findings"]
            for idx, sec in enumerate(self.sections, start=1):
                section_lines = [
                    "",
                    f"### {sec.specialist_name} (Iteration {idx})",
                    f"Task: {sec.task_description}",
                ]
                if sec.supervisor_rationale:
                    section_lines.append(
                        f"Supervisor rationale: {sec.supervisor_rationale}"
                    )

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


__all__ = ["BriefingDocument", "BriefingSection", "TaskAssignment"]
