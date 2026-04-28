"""Tests for briefing document models and briefing compiler.

Tests the data layer (BriefingSection, BriefingDocument) and the compiler
functions (initialize_briefing, compile_specialist_output) which are pure
data manipulation with no LLM calls.
"""

from __future__ import annotations

from app.ai.briefing import BriefingDocument, BriefingSection
from app.ai.briefing_compiler import compile_specialist_output, initialize_briefing


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
        assert "## Scope" in md
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
        assert "## Scope" not in md


class TestInitializeBriefing:
    """Tests for initialize_briefing compiler function."""

    def test_creates_valid_briefing(self) -> None:
        md, data, task_completed = initialize_briefing("What's the status of PRJ-001?")
        assert "# Briefing Document" in md
        assert "What's the status of PRJ-001?" in md
        assert "## Request" in md
        assert data["original_request"] == "What's the status of PRJ-001?"
        assert data["sections"] == []
        assert task_completed is False

    def test_with_metadata(self) -> None:
        md, data, task_completed = initialize_briefing(
            "Status?", {"project_id": "PRJ-001", "branch": "main"}
        )
        assert "project_id: PRJ-001" in md
        assert data["metadata"]["project_id"] == "PRJ-001"
        assert task_completed is False

    def test_without_metadata(self) -> None:
        md, data, task_completed = initialize_briefing("Hello")
        assert "## Scope" not in md
        assert data["metadata"] == {}
        assert task_completed is False


class TestCompileSpecialistOutput:
    """Tests for compile_specialist_output compiler function."""

    def test_appends_section(self) -> None:
        _, initial_data, _ = initialize_briefing("Status?")
        md, data, task_completed = compile_specialist_output(
            briefing_data=initial_data,
            specialist_name="project_manager",
            task_description="Get project info",
            specialist_output="Project is 45% complete",
            tool_calls_summary=["list_projects()"],
        )
        assert "project_manager" in md
        assert "Project is 45% complete" in md
        assert len(data["sections"]) == 1
        assert data["iteration"] == 1
        assert task_completed is False

    def test_preserves_existing_sections(self) -> None:
        _, data, _ = initialize_briefing("Status?")
        _, data, _ = compile_specialist_output(
            briefing_data=data,
            specialist_name="a",
            task_description="t1",
            specialist_output="Finding 1",
            tool_calls_summary=[],
        )
        md, data, _ = compile_specialist_output(
            briefing_data=data,
            specialist_name="b",
            task_description="t2",
            specialist_output="Finding 2",
            tool_calls_summary=["tool_x()"],
        )
        assert len(data["sections"]) == 2
        assert data["iteration"] == 2
        assert "Finding 1" in md
        assert "Finding 2" in md

    def test_with_structured_data(self) -> None:
        _, data, _ = initialize_briefing("EVM?")
        _, data, _ = compile_specialist_output(
            briefing_data=data,
            specialist_name="evm_analyst",
            task_description="Calculate EVM",
            specialist_output="CPI: 0.95",
            tool_calls_summary=["calculate_evm()"],
            structured_data={"cpi": 0.95, "spi": 1.05},
        )
        assert data["sections"][0]["structured_data"]["cpi"] == 0.95

    def test_handles_empty_briefing_data(self) -> None:
        md, data, task_completed = compile_specialist_output(
            briefing_data={},
            specialist_name="test",
            task_description="test task",
            specialist_output="test output",
            tool_calls_summary=[],
        )
        assert "test output" in md
        assert data["original_request"] == "(recovered)"
        assert task_completed is False
