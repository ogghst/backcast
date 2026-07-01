"""BriefingDocument.from_state recovery + get_briefing sentinel behavior.

Covers TD-113: corrupt briefing state must surface the "No briefing
available yet." sentinel to the agent, not a fabricated "(recovered)" doc.
"""

from app.ai.briefing import BriefingDocument
from app.ai.supervisor_orchestrator import _create_get_briefing_tool

# _create_get_briefing_tool returns a LangChain StructuredTool; ``.func`` is the
# underlying get_briefing(state) callable, used here to bypass InjectedState wiring.
_get_briefing = _create_get_briefing_tool().func


class TestBriefingDocumentFromState:
    def test_valid_state_not_recovered(self) -> None:
        doc = BriefingDocument.from_state({"original_request": "build a plan"})
        assert doc.is_recovered is False
        assert doc.original_request == "build a plan"

    def test_garbage_state_is_recovered(self) -> None:
        doc = BriefingDocument.from_state({"garbage": True})
        assert doc.is_recovered is True
        assert doc.original_request == "(recovered)"
        assert doc.sections == []

    def test_empty_state_is_recovered(self) -> None:
        doc = BriefingDocument.from_state({})
        assert doc.is_recovered is True


class TestGetBriefingTool:
    def test_corrupt_state_returns_sentinel(self) -> None:
        assert _get_briefing(state={"briefing_data": {"garbage": True}}) == "No briefing available yet."

    def test_empty_state_returns_sentinel(self) -> None:
        assert _get_briefing(state={}) == "No briefing available yet."

    def test_valid_state_returns_markdown(self) -> None:
        result = _get_briefing(state={"briefing_data": {"original_request": "x"}})
        assert "## Request" in result
        assert "(recovered)" not in result
