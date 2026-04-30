"""Briefing document models for the Briefing Room orchestrator pattern.

Pure data models that accumulate specialist contributions into a structured
document. No AI framework dependencies — only Pydantic and datetime.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TaskAssignment(BaseModel):
    """A task delegation from the supervisor to a specialist."""

    specialist: str
    description: str
    rationale: str | None = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)  # noqa: UP017
    )


class BriefingSection(BaseModel):
    """A single specialist's contribution to the briefing document."""

    specialist_name: str
    task_description: str
    findings: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)  # noqa: UP017
    )
    tool_calls_summary: list[str]
    structured_data: dict[str, Any] | None = None
    supervisor_rationale: str | None = None
    key_findings: list[str] | None = None
    open_questions: list[str] | None = None
    delegation_notes: str | None = None


class BriefingDocument(BaseModel):
    """Accumulating briefing document assembled by the orchestrator.

    Each specialist contribution appends a section and increments the
    iteration counter.
    """

    original_request: str
    sections: list[BriefingSection] = []
    metadata: dict[str, Any] = {}
    iteration: int = 0
    task_completed: bool = False
    supervisor_analysis: str | None = None
    task_history: list[TaskAssignment] = []

    def add_section(self, section: BriefingSection) -> None:
        self.sections.append(section)
        self.iteration += 1

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

        display_metadata = {
            k: v for k, v in self.metadata.items() if k != "current_task"
        }
        if display_metadata:
            scope_lines = [f"- {k}: {v}" for k, v in display_metadata.items()]
            parts += ["", "## Context", *scope_lines]

        if self.sections:
            parts += ["", "## Specialist Findings"]
            for idx, sec in enumerate(self.sections, start=1):
                tools = ", ".join(sec.tool_calls_summary)
                section_lines = [
                    "",
                    f"### {sec.specialist_name} (Iteration {idx})",
                    f"Task: {sec.task_description}",
                ]
                if sec.supervisor_rationale:
                    section_lines.append(
                        f"Supervisor rationale: {sec.supervisor_rationale}"
                    )
                section_lines += [
                    f"Tools used: {tools}",
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

        if self.task_completed:
            parts += ["", "## Status", "Task Completed"]

        return "\n".join(parts)


__all__ = ["BriefingDocument", "BriefingSection", "TaskAssignment"]
