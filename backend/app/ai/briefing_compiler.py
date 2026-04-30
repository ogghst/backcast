"""Briefing compilation functions for the Briefing Room orchestrator.

Pure string/data manipulation — no LLM calls. Compiles specialist outputs
into a BriefingDocument that accumulates findings across iterations.
"""

from __future__ import annotations

import re
from typing import Any

from app.ai.briefing import BriefingDocument, BriefingSection

__all__ = [
    "compile_specialist_output",
    "initialize_briefing",
    "parse_structured_findings",
]


def initialize_briefing(
    user_request: str,
    metadata: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    doc = BriefingDocument(
        original_request=user_request,
        metadata=metadata or {},
    )
    return doc.model_dump(), False


def compile_specialist_output(
    briefing_data: dict[str, Any],
    specialist_name: str,
    task_description: str,
    specialist_output: str,
    tool_calls_summary: list[str],
    structured_data: dict[str, Any] | None = None,
    task_completed: bool = False,
    supervisor_rationale: str | None = None,
    key_findings: list[str] | None = None,
    open_questions: list[str] | None = None,
    delegation_notes: str | None = None,
) -> tuple[dict[str, Any], bool]:
    try:
        doc = BriefingDocument.model_validate(briefing_data)
    except Exception:
        doc = BriefingDocument(original_request="(recovered)")

    section = BriefingSection(
        specialist_name=specialist_name,
        task_description=task_description,
        findings=specialist_output,
        tool_calls_summary=tool_calls_summary,
        structured_data=structured_data,
        supervisor_rationale=supervisor_rationale,
        key_findings=key_findings,
        open_questions=open_questions,
        delegation_notes=delegation_notes,
    )
    doc.add_section(section)

    if task_completed:
        doc.task_completed = True

    return doc.model_dump(), task_completed


def _extract_bullet_items(text: str) -> list[str]:
    """Extract bullet-point items from a markdown section."""
    items: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            items.append(stripped[2:].strip())
    return items


def parse_structured_findings(raw_findings: str) -> dict[str, Any]:
    """Extract structured sections from specialist output text.

    Looks for ``## Key Findings``, ``## Open Questions``, and
    ``## Delegation Notes`` markdown headers and splits the text into
    structured fields.  Returns a dict where each value is either a
    ``list[str]`` (for Key Findings / Open Questions) or a ``str``
    (for Delegation Notes), or ``None`` when the section is absent.
    """
    result: dict[str, Any] = {
        "key_findings": None,
        "open_questions": None,
        "delegation_notes": None,
    }

    sections = re.split(r"\n(?=## )", raw_findings)

    for section in sections:
        header = section.strip()
        if header.startswith("## Key Findings"):
            items = _extract_bullet_items(section)
            if items:
                result["key_findings"] = items
        elif header.startswith("## Open Questions"):
            items = _extract_bullet_items(section)
            if items:
                result["open_questions"] = items
        elif header.startswith("## Delegation Notes"):
            lines = section.split("\n", 1)
            notes = lines[1].strip() if len(lines) > 1 else ""
            if notes:
                result["delegation_notes"] = notes

    return result
