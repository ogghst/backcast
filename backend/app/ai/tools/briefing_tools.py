"""Briefing access tools for specialist agents.

Provides a ``get_briefing`` tool that specialist subagents can call to retrieve
the structured briefing document from the current supervisor orchestration.

Specialists run inside their own compiled subgraph and cannot use InjectedState
to access the parent BackcastSupervisorState.  Instead, the specialist wrapper
in SupervisorOrchestrator sets a module-level ContextVar with the briefing data
before invoking the specialist graph.  This tool reads from that ContextVar.
"""

import contextvars
import logging
from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg

from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolContext

logger = logging.getLogger(__name__)

# Module-level context variable set by the specialist wrapper before
# each specialist invocation.  Each asyncio task gets its own copy.
_current_briefing: contextvars.ContextVar[dict[str, Any] | None] = (
    contextvars.ContextVar("_current_briefing", default=None)
)


def set_briefing(briefing_data: dict[str, Any] | None) -> None:
    """Store the current briefing data for the specialist's task scope.

    Called by the specialist wrapper in ``SupervisorOrchestrator`` before
    invoking the specialist graph.

    Args:
        briefing_data: Serialized BriefingDocument dict, or None to clear.
    """
    _current_briefing.set(briefing_data)


@ai_tool(
    name="get_briefing",
    description=(
        "Get the compiled briefing with findings from all specialists. "
        "Optionally filter to a specific specialist's section."
    ),
    permissions=[],
    category="context",
    risk_level=RiskLevel.LOW,
)
async def get_briefing(
    section_name: str | None = None,
    include_delegation_notes: bool = True,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Retrieve the structured briefing for the current orchestration.

    Context: Read-only tool providing programmatic access to the briefing
    document that was injected as markdown in the HumanMessage. This tool
    returns structured data (key findings, open questions, delegation notes)
    so the specialist can reference other specialists' results precisely
    without re-calling search tools.

    Args:
        section_name: Optional specialist name to filter to a single section
            (e.g. "evm_analyst", "project_manager"). When omitted, returns
            the full briefing with all sections.
        include_delegation_notes: Whether to include delegation notes in each
            section (default True). Set to False for a shorter response.
        context: Injected tool execution context.

    Returns:
        Dictionary containing:
            - original_request: The user's original request
            - sections: List of structured section dicts, each with:
                specialist_name, findings, key_findings, open_questions,
                delegation_notes (when include_delegation_notes is True)
            - total_sections: Count of sections returned
            - error: Error message if briefing is unavailable
    """
    from app.ai.briefing import BriefingDocument

    briefing_data = _current_briefing.get()

    if not briefing_data:
        return {
            "error": "No briefing data available for this specialist invocation.",
            "total_sections": 0,
            "sections": [],
        }

    doc = BriefingDocument.from_state(briefing_data)

    sections = doc.sections
    if section_name:
        sections = [s for s in sections if s.specialist_name == section_name]

    result_sections: list[dict[str, Any]] = []
    for sec in sections:
        entry: dict[str, Any] = {
            "specialist_name": sec.specialist_name,
            "findings": sec.findings,
        }
        if sec.key_findings:
            entry["key_findings"] = sec.key_findings
        if sec.open_questions:
            entry["open_questions"] = sec.open_questions
        if include_delegation_notes and sec.delegation_notes:
            entry["delegation_notes"] = sec.delegation_notes
        if sec.task_description:
            entry["task_description"] = sec.task_description
        result_sections.append(entry)

    return {
        "original_request": doc.original_request,
        "follow_up_requests": doc.follow_up_requests,
        "sections": result_sections,
        "total_sections": len(result_sections),
    }
