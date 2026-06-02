"""Briefing compilation functions for the Briefing Room orchestrator.

Pure string/data manipulation — no LLM calls.  Compiles specialist outputs
into a BriefingDocument that accumulates findings across iterations.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.ai.briefing import BriefingDocument, BriefingSection

# Structured section headers — used by parse_and_clean() and _SCOPE_BOUNDARY
# in supervisor_orchestrator.py. Keep in sync.
SECTION_KEY_FINDINGS = "## Key Findings"
SECTION_OPEN_QUESTIONS = "## Open Questions"
SECTION_DELEGATION_NOTES = "## Delegation Notes"

__all__ = [
    "compile_specialist_output",
    "initialize_briefing",
    "parse_and_clean",
]


def initialize_briefing(user_request: str) -> BriefingDocument:
    return BriefingDocument(original_request=user_request)


def _extract_bullet_items(text: str) -> list[str]:
    items: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            items.append(stripped[2:].strip())
    return items


def parse_and_clean(raw_findings: str) -> tuple[str, dict[str, Any]]:
    """Parse structured sections from specialist output and strip them.

    Supports two formats:
    1. Structured JSON (SpecialistOutput) — preferred
    2. Plain text with ## Key Findings / ## Open Questions / ## Delegation Notes sections

    Returns ``(cleaned_findings, parsed)`` where ``parsed`` has keys
    ``key_findings``, ``open_questions``, ``delegation_notes`` (each ``None``
    or ``list[str]``/``str``).
    """
    parsed: dict[str, Any] = {
        "key_findings": None,
        "open_questions": None,
        "delegation_notes": None,
    }

    # --- Try structured JSON first ---
    text = raw_findings.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        first_newline = text.index("\n") if "\n" in text else len(text)
        text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[: -len("```")]
        text = text.strip()

    try:
        data = json.loads(text)
        if isinstance(data, dict) and "summary" in data:
            parsed = {
                "key_findings": data.get("key_findings") or None,
                "open_questions": data.get("open_questions") or None,
                "delegation_notes": data.get("delegation_notes") or None,
            }
            cleaned = data.get("summary", "")
            return cleaned, parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # --- Fallback: regex-based section extraction (existing logic) ---
    non_structured: list[str] = []

    sections = re.split(r"\n(?=## )", raw_findings)

    for section in sections:
        header = section.strip()
        if header.startswith(SECTION_KEY_FINDINGS):
            items = _extract_bullet_items(section)
            if items:
                parsed["key_findings"] = items
        elif header.startswith(SECTION_OPEN_QUESTIONS):
            items = _extract_bullet_items(section)
            if items:
                parsed["open_questions"] = items
        elif header.startswith(SECTION_DELEGATION_NOTES):
            lines = section.split("\n", 1)
            notes = lines[1].strip() if len(lines) > 1 else ""
            if notes:
                parsed["delegation_notes"] = notes
        else:
            non_structured.append(section)

    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(non_structured)).strip()
    return cleaned, parsed


def compile_specialist_output(
    briefing_data: dict[str, Any],
    specialist_name: str,
    task_description: str,
    specialist_output: str,
    supervisor_rationale: str | None = None,
    parsed_findings: dict[str, Any] | None = None,
    step_index: int | None = None,
) -> dict[str, Any]:
    doc = BriefingDocument.from_state(briefing_data)

    section = BriefingSection(
        specialist_name=specialist_name,
        task_description=task_description,
        findings=specialist_output,
        supervisor_rationale=supervisor_rationale,
        step_index=step_index,
        **(parsed_findings or {}),
    )
    doc.sections.append(section)

    return doc.model_dump()
