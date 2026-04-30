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
    parse_structured_findings,
)


class TestBriefingSection:
    """Tests for BriefingSection data model."""

    def test_creation_with_defaults(self) -> None:
        section = BriefingSection(
            specialist_name="evm_analyst",
            task_description="Analyze EVM metrics",
            findings="CPI: 0.95, SPI: 1.05",
            tool_calls_summary=["get_evm_metrics(project_id)"],
        )
        assert section.specialist_name == "evm_analyst"
        assert section.task_description == "Analyze EVM metrics"
        assert section.findings == "CPI: 0.95, SPI: 1.05"
        assert section.structured_data is None
        assert section.supervisor_rationale is None
        assert section.key_findings is None
        assert section.open_questions is None
        assert section.delegation_notes is None
        assert section.timestamp is not None

    def test_with_structured_data(self) -> None:
        section = BriefingSection(
            specialist_name="evm_analyst",
            task_description="test",
            findings="test",
            tool_calls_summary=[],
            structured_data={"cpi": 0.95, "spi": 1.05},
        )
        assert section.structured_data is not None
        assert section.structured_data["cpi"] == 0.95
        assert section.structured_data["spi"] == 1.05

    def test_with_enhanced_fields(self) -> None:
        section = BriefingSection(
            specialist_name="evm_analyst",
            task_description="Analyze EVM",
            findings="CPI: 0.95",
            tool_calls_summary=[],
            supervisor_rationale="Need EVM analysis for project health",
            key_findings=["CPI below 1.0", "SPI above 1.0"],
            open_questions=["What is the target CPI?"],
            delegation_notes="Project PRJ-001 needs further analysis",
        )
        assert section.supervisor_rationale == "Need EVM analysis for project health"
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
        assert ta.timestamp is not None

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

    def test_to_markdown_with_metadata(self) -> None:
        doc = BriefingDocument(
            original_request="Status?",
            metadata={"project_id": "PRJ-001"},
        )
        md = doc.to_markdown()
        assert "## Context" in md
        assert "project_id: PRJ-001" in md

    def test_to_markdown_with_sections(self) -> None:
        doc = BriefingDocument(original_request="Status?")
        doc.add_section(
            BriefingSection(
                specialist_name="project_manager",
                task_description="Get project info",
                findings="Project is 45% complete",
                tool_calls_summary=["list_projects()"],
            )
        )
        md = doc.to_markdown()
        assert "## Specialist Findings" in md
        assert "### project_manager (Iteration 1)" in md
        assert "Project is 45% complete" in md
        assert "list_projects()" in md

    def test_add_section_increments_iteration(self) -> None:
        doc = BriefingDocument(original_request="test")
        assert doc.iteration == 0
        doc.add_section(
            BriefingSection(
                specialist_name="a",
                task_description="t",
                findings="f",
                tool_calls_summary=[],
            )
        )
        assert doc.iteration == 1
        doc.add_section(
            BriefingSection(
                specialist_name="b",
                task_description="t",
                findings="f",
                tool_calls_summary=[],
            )
        )
        assert doc.iteration == 2
        assert len(doc.sections) == 2

    def test_to_markdown_empty_metadata(self) -> None:
        doc = BriefingDocument(original_request="test")
        md = doc.to_markdown()
        assert "## Context" not in md

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

    def test_current_task_filtered_from_context(self) -> None:
        doc = BriefingDocument(
            original_request="test",
            metadata={
                "current_task": {"specialist": "x", "description": "y"},
                "project_id": "PRJ-001",
            },
        )
        md = doc.to_markdown()
        assert "current_task" not in md
        assert "project_id: PRJ-001" in md

    def test_section_with_enhanced_fields_rendered(self) -> None:
        doc = BriefingDocument(original_request="test")
        doc.add_section(
            BriefingSection(
                specialist_name="evm_analyst",
                task_description="Run EVM",
                findings="CPI: 0.95",
                tool_calls_summary=["calc_evm()"],
                supervisor_rationale="Need cost analysis",
                key_findings=["CPI below 1.0"],
                open_questions=["What baseline?"],
                delegation_notes="See project PRJ-001",
            )
        )
        md = doc.to_markdown()
        assert "Supervisor rationale: Need cost analysis" in md
        assert "**Key Findings:**" in md
        assert "- CPI below 1.0" in md
        assert "**Open Questions:**" in md
        assert "- What baseline?" in md
        assert "**Delegation Notes:** See project PRJ-001" in md


class TestInitializeBriefing:
    """Tests for initialize_briefing compiler function."""

    def test_creates_valid_briefing(self) -> None:
        data, task_completed = initialize_briefing("What's the status of PRJ-001?")
        assert data["original_request"] == "What's the status of PRJ-001?"
        assert data["sections"] == []
        assert task_completed is False

    def test_with_metadata(self) -> None:
        data, task_completed = initialize_briefing(
            "Status?", {"project_id": "PRJ-001", "branch": "main"}
        )
        assert data["metadata"]["project_id"] == "PRJ-001"
        assert task_completed is False

    def test_without_metadata(self) -> None:
        data, task_completed = initialize_briefing("Hello")
        assert data["metadata"] == {}
        assert task_completed is False

    def test_return_data_renders_to_markdown(self) -> None:
        data, _ = initialize_briefing("What's the status?")
        doc = BriefingDocument.model_validate(data)
        md = doc.to_markdown()
        assert "# Briefing Document" in md
        assert "What's the status?" in md


class TestCompileSpecialistOutput:
    """Tests for compile_specialist_output compiler function."""

    def test_appends_section(self) -> None:
        initial_data, _ = initialize_briefing("Status?")
        data, task_completed = compile_specialist_output(
            briefing_data=initial_data,
            specialist_name="project_manager",
            task_description="Get project info",
            specialist_output="Project is 45% complete",
            tool_calls_summary=["list_projects()"],
        )
        assert len(data["sections"]) == 1
        assert data["sections"][0]["specialist_name"] == "project_manager"
        assert data["sections"][0]["findings"] == "Project is 45% complete"
        assert data["iteration"] == 1
        assert task_completed is False

    def test_preserves_existing_sections(self) -> None:
        data, _ = initialize_briefing("Status?")
        data, _ = compile_specialist_output(
            briefing_data=data,
            specialist_name="a",
            task_description="t1",
            specialist_output="Finding 1",
            tool_calls_summary=[],
        )
        data, _ = compile_specialist_output(
            briefing_data=data,
            specialist_name="b",
            task_description="t2",
            specialist_output="Finding 2",
            tool_calls_summary=["tool_x()"],
        )
        assert len(data["sections"]) == 2
        assert data["iteration"] == 2
        assert data["sections"][0]["findings"] == "Finding 1"
        assert data["sections"][1]["findings"] == "Finding 2"

    def test_with_structured_data(self) -> None:
        data, _ = initialize_briefing("EVM?")
        data, _ = compile_specialist_output(
            briefing_data=data,
            specialist_name="evm_analyst",
            task_description="Calculate EVM",
            specialist_output="CPI: 0.95",
            tool_calls_summary=["calculate_evm()"],
            structured_data={"cpi": 0.95, "spi": 1.05},
        )
        assert data["sections"][0]["structured_data"]["cpi"] == 0.95

    def test_handles_empty_briefing_data(self) -> None:
        data, task_completed = compile_specialist_output(
            briefing_data={},
            specialist_name="test",
            task_description="test task",
            specialist_output="test output",
            tool_calls_summary=[],
        )
        assert data["original_request"] == "(recovered)"
        assert data["sections"][0]["findings"] == "test output"
        assert task_completed is False

    def test_with_enhanced_fields(self) -> None:
        data, _ = initialize_briefing("Test?")
        data, _ = compile_specialist_output(
            briefing_data=data,
            specialist_name="evm_analyst",
            task_description="Run EVM",
            specialist_output="CPI: 0.95",
            tool_calls_summary=[],
            supervisor_rationale="Cost analysis needed",
            key_findings=["CPI below threshold"],
            open_questions=["Which baseline?"],
            delegation_notes="Project PRJ-001",
        )
        section = data["sections"][0]
        assert section["supervisor_rationale"] == "Cost analysis needed"
        assert section["key_findings"] == ["CPI below threshold"]
        assert section["open_questions"] == ["Which baseline?"]
        assert section["delegation_notes"] == "Project PRJ-001"


class TestParseStructuredFindings:
    """Tests for parse_structured_findings deterministic parser."""

    def test_extracts_key_findings(self) -> None:
        raw = "Some analysis text\n\n## Key Findings\n- CPI is 0.95\n- SPI is 1.05\n"
        result = parse_structured_findings(raw)
        assert result["key_findings"] == ["CPI is 0.95", "SPI is 1.05"]
        assert result["open_questions"] is None
        assert result["delegation_notes"] is None

    def test_extracts_open_questions(self) -> None:
        raw = "## Open Questions\n- What baseline?\n- Which version?\n"
        result = parse_structured_findings(raw)
        assert result["open_questions"] == ["What baseline?", "Which version?"]

    def test_extracts_delegation_notes(self) -> None:
        raw = "## Delegation Notes\nProject PRJ-001 needs scheduling review.\n"
        result = parse_structured_findings(raw)
        assert result["delegation_notes"] == "Project PRJ-001 needs scheduling review."

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
        result = parse_structured_findings(raw)
        assert result["key_findings"] == ["Finding A"]
        assert result["open_questions"] == ["Question B"]
        assert result["delegation_notes"] == "Some notes here"

    def test_returns_none_when_no_headers(self) -> None:
        result = parse_structured_findings("Just plain text, no headers here.")
        assert result["key_findings"] is None
        assert result["open_questions"] is None
        assert result["delegation_notes"] is None

    def test_uses_asterisk_bullets(self) -> None:
        raw = "## Key Findings\n* Finding with asterisk\n"
        result = parse_structured_findings(raw)
        assert result["key_findings"] == ["Finding with asterisk"]

    def test_empty_section_returns_none(self) -> None:
        raw = "## Key Findings\n\n## Open Questions\n- Q1\n"
        result = parse_structured_findings(raw)
        assert result["key_findings"] is None
        assert result["open_questions"] == ["Q1"]


class TestGetBriefingTool:
    """Tests for _create_get_briefing_tool fallback behavior."""

    @staticmethod
    def _make_tool() -> BaseTool:
        from app.ai.supervisor_orchestrator import _create_get_briefing_tool

        return _create_get_briefing_tool()

    def test_empty_briefing_data(self) -> None:
        tool = self._make_tool()
        # Empty dict for briefing_data
        result = tool.func(state={"briefing_data": {}})
        assert result == "No briefing available yet."

        # Missing briefing_data key entirely
        result = tool.func(state={})
        assert result == "No briefing available yet."

    def test_malformed_briefing_data(self) -> None:
        tool = self._make_tool()
        result = tool.func(
            state={"briefing_data": {"original_request": 123, "sections": "not_a_list"}}
        )
        assert result == "No briefing available yet."

    def test_valid_briefing_data(self) -> None:
        tool = self._make_tool()
        data, _ = initialize_briefing("What's the status of PRJ-001?")
        result = tool.func(state={"briefing_data": data})
        assert "# Briefing Document" in result
        assert "What's the status of PRJ-001?" in result
