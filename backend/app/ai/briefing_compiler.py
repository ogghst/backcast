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
) -> dict[str, Any]:
    doc = BriefingDocument(original_request=user_request)
    return doc.model_dump()


def _strip_structured_sections(raw_findings: str) -> str:
    """Remove structured sections from specialist output before storing.

    Since key_findings, open_questions, and delegation_notes are parsed
    and stored separately, we remove them from the raw findings to avoid
    duplication in the final markdown render.
    """
    sections_to_remove = ["## Delegation Notes", "## Open Questions", "## Key Findings"]
    cleaned = raw_findings
    for section_header in sections_to_remove:
        # Match from header to next section or end
        pattern = rf"\n?{section_header}.*?(?=\n## |$)"
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL)
    # Clean up extra blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def compile_specialist_output(
    briefing_data: dict[str, Any],
    specialist_name: str,
    task_description: str,
    specialist_output: str,
    supervisor_rationale: str | None = None,
    key_findings: list[str] | None = None,
    open_questions: list[str] | None = None,
    delegation_notes: str | None = None,
) -> dict[str, Any]:
    try:
        doc = BriefingDocument.model_validate(briefing_data)
    except Exception:
        doc = BriefingDocument(original_request="(recovered)")

    # Strip structured sections from raw output to avoid duplication
    # (they are stored separately in key_findings, open_questions, delegation_notes)
    cleaned_findings = _strip_structured_sections(specialist_output)

    section = BriefingSection(
        specialist_name=specialist_name,
        task_description=task_description,
        findings=cleaned_findings,
        supervisor_rationale=supervisor_rationale,
        key_findings=key_findings,
        open_questions=open_questions,
        delegation_notes=delegation_notes,
    )
    doc.sections.append(section)

    return doc.model_dump()


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
