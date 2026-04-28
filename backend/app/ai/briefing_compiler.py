"""Briefing compilation functions for the Briefing Room orchestrator.

Pure string/data manipulation — no LLM calls. Compiles specialist outputs
into a BriefingDocument that accumulates findings across iterations.
"""

from __future__ import annotations

from typing import Any

from app.ai.briefing import BriefingDocument, BriefingSection

__all__ = ["compile_specialist_output", "initialize_briefing"]


def initialize_briefing(
    user_request: str,
    metadata: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], bool]:
    doc = BriefingDocument(
        original_request=user_request,
        metadata=metadata or {},
    )
    return doc.to_markdown(), doc.model_dump(), False


def compile_specialist_output(
    briefing_data: dict[str, Any],
    specialist_name: str,
    task_description: str,
    specialist_output: str,
    tool_calls_summary: list[str],
    structured_data: dict[str, Any] | None = None,
    task_completed: bool = False,
) -> tuple[str, dict[str, Any], bool]:
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
    )
    doc.add_section(section)

    if task_completed:
        doc.task_completed = True

    return doc.to_markdown(), doc.model_dump(), task_completed
