"""Briefing document models for the Briefing Room orchestrator pattern.

Pure data models that accumulate specialist contributions into a structured
document. No AI framework dependencies — only Pydantic and datetime.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


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

    def add_section(self, section: BriefingSection) -> None:
        self.sections.append(section)
        self.iteration += 1

    def to_markdown(self) -> str:
        parts: list[str] = [
            "# Briefing Document",
            "",
            "## Request",
            self.original_request,
        ]

        if self.metadata:
            scope_lines = [f"- {k}: {v}" for k, v in self.metadata.items()]
            parts += ["", "## Scope", *scope_lines]

        if self.sections:
            parts += ["", "## Specialist Findings"]
            for idx, sec in enumerate(self.sections, start=1):
                tools = ", ".join(sec.tool_calls_summary)
                parts += [
                    "",
                    f"### {sec.specialist_name} (Iteration {idx})",
                    f"Task: {sec.task_description}",
                    f"Tools used: {tools}",
                    "",
                    sec.findings,
                    "",
                    "---",
                ]

        if self.task_completed:
            parts += ["", "## Status", "✅ Task Completed"]

        return "\n".join(parts)


__all__ = ["BriefingDocument", "BriefingSection"]
