"""Tests for briefing document models and briefing compiler.

Tests the data layer (BriefingSection, BriefingDocument) and the compiler
functions (initialize_briefing, compile_specialist_output) which are pure
data manipulation with no LLM calls.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool

from app.ai.briefing import BriefingDocument, BriefingSection, TaskAssignment
from app.ai.briefing_compiler import (
    compile_specialist_output,
    initialize_briefing,
    parse_and_clean,
)


class TestBriefingSection:
    """Tests for BriefingSection data model."""

    def test_creation_with_defaults(self) -> None:
        section = BriefingSection(
            specialist_name="evm_analyst",
            findings="CPI: 0.95, SPI: 1.05",
        )
        assert section.specialist_name == "evm_analyst"
        assert section.findings == "CPI: 0.95, SPI: 1.05"
        assert section.key_findings is None
        assert section.open_questions is None
        assert section.delegation_notes is None

    def test_with_enhanced_fields(self) -> None:
        section = BriefingSection(
            specialist_name="evm_analyst",
            findings="CPI: 0.95",
            key_findings=["CPI below 1.0", "SPI above 1.0"],
            open_questions=["What is the target CPI?"],
            delegation_notes="Project PRJ-001 needs further analysis",
        )
        assert section.key_findings == ["CPI below 1.0", "SPI above 1.0"]
        assert section.open_questions == ["What is the target CPI?"]
        assert section.delegation_notes == "Project PRJ-001 needs further analysis"


class TestTaskAssignment:
    """Tests for TaskAssignment model."""

    def test_creation_with_defaults(self) -> None:
        ta = TaskAssignment(specialist="evm_analyst", description="Run EVM calc")
        assert ta.specialist == "evm_analyst"
        assert ta.description == "Run EVM calc"
        assert ta.rationale is None

    def test_with_rationale(self) -> None:
        ta = TaskAssignment(
            specialist="project_manager",
            description="Get project details",
            rationale="Need project context for EVM analysis",
        )
        assert ta.rationale == "Need project context for EVM analysis"


class TestBriefingDocument:
    """Tests for BriefingDocument data model and markdown rendering."""

    def test_to_markdown_empty(self) -> None:
        doc = BriefingDocument(original_request="What is the status?")
        md = doc.to_markdown()
        assert "# Briefing Document" in md
        assert "## Request" in md
        assert "What is the status?" in md
        assert "## Specialist Findings" not in md

    def test_to_markdown_with_sections(self) -> None:
        doc = BriefingDocument(original_request="Status?")
        doc.sections.append(
            BriefingSection(
                specialist_name="project_manager",
                findings="Project is 45% complete",
            )
        )
        md = doc.to_markdown()
        assert "## Specialist Findings" in md
        assert "### project_manager (Iteration 1)" in md
        assert "Project is 45% complete" in md

    def test_sections_append(self) -> None:
        doc = BriefingDocument(original_request="test")
        doc.sections.append(BriefingSection(specialist_name="a", findings="f"))
        assert len(doc.sections) == 1
        doc.sections.append(BriefingSection(specialist_name="b", findings="f"))
        assert len(doc.sections) == 2

    def test_supervisor_analysis_rendered(self) -> None:
        doc = BriefingDocument(
            original_request="Status of PRJ-001?",
            supervisor_analysis="User wants project health check. Need EVM + schedule.",
        )
        md = doc.to_markdown()
        assert "## Supervisor Analysis" in md
        assert "User wants project health check" in md

    def test_task_history_rendered(self) -> None:
        doc = BriefingDocument(original_request="test")
        doc.add_task_assignment(
            TaskAssignment(
                specialist="evm_analyst",
                description="Run EVM calculations",
                rationale="User asked about project health",
            )
        )
        md = doc.to_markdown()
        assert "## Task History" in md
        assert "**evm_analyst**: Run EVM calculations" in md
        assert "Rationale: User asked about project health" in md

    def test_section_with_enhanced_fields_rendered(self) -> None:
        doc = BriefingDocument(original_request="test")
        doc.sections.append(
            BriefingSection(
                specialist_name="evm_analyst",
                findings="CPI: 0.95",
                key_findings=["CPI below 1.0"],
                open_questions=["What baseline?"],
                delegation_notes="See project PRJ-001",
            )
        )
        md = doc.to_markdown()
        assert "**Key Findings:**" in md
        assert "- CPI below 1.0" in md
        assert "**Open Questions:**" in md
        assert "- What baseline?" in md
        assert "**Delegation Notes:** See project PRJ-001" in md

    def test_from_state_recovered(self) -> None:
        doc = BriefingDocument.from_state({})
        assert doc.original_request == "(recovered)"
        assert doc.sections == []

    def test_from_state_valid(self) -> None:
        original = BriefingDocument(original_request="test")
        doc = BriefingDocument.from_state(original.model_dump())
        assert doc.original_request == "test"


class TestInitializeBriefing:
    """Tests for initialize_briefing compiler function."""

    def test_creates_valid_briefing(self) -> None:
        doc = initialize_briefing("What's the status of PRJ-001?")
        assert doc.original_request == "What's the status of PRJ-001?"
        assert doc.sections == []

    def test_return_renders_to_markdown(self) -> None:
        doc = initialize_briefing("What's the status?")
        md = doc.to_markdown()
        assert "# Briefing Document" in md
        assert "What's the status?" in md


class TestCompileSpecialistOutput:
    """Tests for compile_specialist_output compiler function."""

    def test_appends_section(self) -> None:
        doc = initialize_briefing("Status?")
        data = compile_specialist_output(
            briefing_data=doc.model_dump(),
            specialist_name="project_manager",
            task_description="Get project info",
            specialist_output="Project is 45% complete",
        )
        assert len(data["sections"]) == 1
        assert data["sections"][0]["specialist_name"] == "project_manager"
        assert data["sections"][0]["findings"] == "Project is 45% complete"

    def test_preserves_existing_sections(self) -> None:
        doc = initialize_briefing("Status?")
        data = doc.model_dump()
        data = compile_specialist_output(
            briefing_data=data,
            specialist_name="a",
            task_description="t1",
            specialist_output="Finding 1",
        )
        data = compile_specialist_output(
            briefing_data=data,
            specialist_name="b",
            task_description="t2",
            specialist_output="Finding 2",
        )
        assert len(data["sections"]) == 2
        assert data["sections"][0]["findings"] == "Finding 1"
        assert data["sections"][1]["findings"] == "Finding 2"

    def test_handles_empty_briefing_data(self) -> None:
        data = compile_specialist_output(
            briefing_data={},
            specialist_name="test",
            task_description="test task",
            specialist_output="test output",
        )
        assert data["original_request"] == "(recovered)"
        assert data["sections"][0]["findings"] == "test output"

    def test_with_parsed_findings(self) -> None:
        doc = initialize_briefing("Test?")
        data = compile_specialist_output(
            briefing_data=doc.model_dump(),
            specialist_name="evm_analyst",
            task_description="Run EVM",
            specialist_output="CPI: 0.95",
            supervisor_rationale="Cost analysis needed",
            parsed_findings={
                "key_findings": ["CPI below threshold"],
                "open_questions": ["Which baseline?"],
                "delegation_notes": "Project PRJ-001",
            },
        )
        section = data["sections"][0]
        assert section["key_findings"] == ["CPI below threshold"]
        assert section["open_questions"] == ["Which baseline?"]
        assert section["delegation_notes"] == "Project PRJ-001"


class TestParseAndClean:
    """Tests for parse_and_clean single-pass parser."""

    def test_extracts_key_findings(self) -> None:
        raw = "Some analysis text\n\n## Key Findings\n- CPI is 0.95\n- SPI is 1.05\n"
        cleaned, parsed = parse_and_clean(raw)
        assert parsed["key_findings"] == ["CPI is 0.95", "SPI is 1.05"]
        assert parsed["open_questions"] is None
        assert parsed["delegation_notes"] is None
        assert "## Key Findings" not in cleaned
        assert "Some analysis text" in cleaned

    def test_extracts_open_questions(self) -> None:
        raw = "## Open Questions\n- What baseline?\n- Which version?\n"
        cleaned, parsed = parse_and_clean(raw)
        assert parsed["open_questions"] == ["What baseline?", "Which version?"]

    def test_extracts_delegation_notes(self) -> None:
        raw = "## Delegation Notes\nProject PRJ-001 needs scheduling review.\n"
        cleaned, parsed = parse_and_clean(raw)
        assert parsed["delegation_notes"] == "Project PRJ-001 needs scheduling review."

    def test_extracts_all_sections(self) -> None:
        raw = (
            "Analysis here\n\n"
            "## Key Findings\n"
            "- Finding A\n\n"
            "## Open Questions\n"
            "- Question B\n\n"
            "## Delegation Notes\n"
            "Some notes here\n"
        )
        cleaned, parsed = parse_and_clean(raw)
        assert parsed["key_findings"] == ["Finding A"]
        assert parsed["open_questions"] == ["Question B"]
        assert parsed["delegation_notes"] == "Some notes here"
        assert "Analysis here" in cleaned
        assert "## Key Findings" not in cleaned
        assert "## Open Questions" not in cleaned
        assert "## Delegation Notes" not in cleaned

    def test_returns_none_when_no_headers(self) -> None:
        cleaned, parsed = parse_and_clean("Just plain text, no headers here.")
        assert parsed["key_findings"] is None
        assert parsed["open_questions"] is None
        assert parsed["delegation_notes"] is None
        assert cleaned == "Just plain text, no headers here."

    def test_uses_asterisk_bullets(self) -> None:
        raw = "## Key Findings\n* Finding with asterisk\n"
        cleaned, parsed = parse_and_clean(raw)
        assert parsed["key_findings"] == ["Finding with asterisk"]

    def test_empty_section_returns_none(self) -> None:
        raw = "## Key Findings\n\n## Open Questions\n- Q1\n"
        cleaned, parsed = parse_and_clean(raw)
        assert parsed["key_findings"] is None
        assert parsed["open_questions"] == ["Q1"]


class TestGetBriefingTool:
    """Tests for _create_get_briefing_tool fallback behavior."""

    @staticmethod
    def _make_tool() -> BaseTool:
        from app.ai.supervisor_orchestrator import _create_get_briefing_tool

        return _create_get_briefing_tool()

    def test_empty_briefing_data(self) -> None:
        tool = self._make_tool()
        result = tool.func(state={"briefing_data": {}})
        assert result == "No briefing available yet."

        result = tool.func(state={})
        assert result == "No briefing available yet."

    def test_valid_briefing_data(self) -> None:
        tool = self._make_tool()
        doc = initialize_briefing("What's the status of PRJ-001?")
        result = tool.func(state={"briefing_data": doc.model_dump()})
        assert "# Briefing Document" in result
        assert "What's the status of PRJ-001?" in result
