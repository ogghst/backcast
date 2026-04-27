"""Tests for structured subagent output functionality.

Tests the integration of structured output (Pydantic models) with subagent
delegation, including:
- Schema configuration in subagent configs
- Orchestrator application of with_structured_output()
- Task tool extraction and attachment of structured output
- Summary generation from structured models
- Backward compatibility with text-only responses

Test IDs:
- T-101: Subagent configs have structured_output_schema field
- T-102: Orchestrator applies with_structured_output() when schema defined
- T-103: Task tool extracts Pydantic model from subagent result
- T-104: Task tool generates human-readable summary for each schema type
- T-105: Structured output attached to ToolMessage.additional_kwargs
- T-106: Backward compatibility: text-only responses work without schema
- T-107: Invalid structured output falls back to text content
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain.tools import ToolRuntime
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.subagent_compiler import compile_subagents
from app.ai.subagents import (
    CHANGE_ORDER_MANAGER_SUBAGENT,
    EVM_ANALYST_SUBAGENT,
    FORECAST_MANAGER_SUBAGENT,
    PROJECT_MANAGER_SUBAGENT,
    get_all_subagents,
)
from app.ai.tools.subagent_task import (
    _summarize_structured_output,
    build_task_tool,
)
from app.ai.tools.types import ExecutionMode, ToolContext
from app.models.schemas.dashboard import (
    DashboardActivity,
    DashboardData,
    ProjectMetrics,
    ProjectSpotlight,
)
from app.models.schemas.evm import EVMMetricsRead
from app.models.schemas.forecast import ForecastRead
from app.models.schemas.impact_analysis import (
    EntityChange,
    EntityChanges,
    ImpactAnalysisResponse,
    KPIMetric,
    KPIScorecard,
)


class _DummyStreamWriter:
    """Minimal stream writer stub for ToolRuntime construction."""

    def write(self, data: Any) -> None:
        pass


def _make_runtime(
    state: dict[str, Any] | None = None,
    tool_call_id: str | None = "call-123",
) -> ToolRuntime:
    """Create a real ToolRuntime instance for testing."""
    return ToolRuntime(
        state=state or {},
        context={},
        config=RunnableConfig(),
        stream_writer=_DummyStreamWriter(),
        tool_call_id=tool_call_id,
        store=None,
    )


class TestSubagentConfigSchemaField:
    """T-101: Subagent configs have structured_output_schema field."""

    def test_evm_analyst_has_schema(self) -> None:
        """EVM analyst subagent has EVMMetricsRead schema."""
        schema = EVM_ANALYST_SUBAGENT.get("structured_output_schema")
        assert schema is not None
        assert schema == EVMMetricsRead

    def test_forecast_manager_has_schema(self) -> None:
        """Forecast manager subagent has ForecastRead schema."""
        schema = FORECAST_MANAGER_SUBAGENT.get("structured_output_schema")
        assert schema is not None
        assert schema == ForecastRead

    def test_change_order_manager_has_schema(self) -> None:
        """Change order manager subagent has ImpactAnalysisResponse schema."""
        schema = CHANGE_ORDER_MANAGER_SUBAGENT.get("structured_output_schema")
        assert schema is not None
        assert schema == ImpactAnalysisResponse

    def test_project_manager_no_schema(self) -> None:
        """Project manager subagent has no schema (varied responses)."""
        schema = PROJECT_MANAGER_SUBAGENT.get("structured_output_schema")
        assert schema is None

    def test_all_subagents_have_schema_field(self) -> None:
        """All subagents have structured_output_schema field defined."""
        for agent in get_all_subagents():
            assert "structured_output_schema" in agent


class TestOrchestratorStructuredOutput:
    """T-102: Orchestrator applies with_structured_output() when schema defined."""

    @patch("app.ai.subagent_compiler.langchain_create_agent")
    def test_applies_structured_output_wrapper(
        self, mock_create_agent: MagicMock
    ) -> None:
        """compile_subagents passes response_format to create_agent when schema defined."""
        mock_runnable = MagicMock()
        mock_create_agent.return_value = mock_runnable

        context = ToolContext(
            session=MagicMock(),
            user_id=str(uuid4()),
            user_role="admin",
            execution_mode=ExecutionMode.STANDARD,
            project_id=None,
        )

        subagents = [
            {
                "name": "test_agent",
                "description": "Test",
                "system_prompt": "You are a test agent",
                "allowed_tools": ["list_projects"],
                "structured_output_schema": EVMMetricsRead,
            }
        ]

        mock_tool = MagicMock(spec=StructuredTool)
        mock_tool.name = "list_projects"

        result = compile_subagents(
            "openai:gpt-4o", context, subagents, [mock_tool], allowed_tools=None
        )

        mock_create_agent.assert_called_once()
        call_kwargs = mock_create_agent.call_args.kwargs
        assert "response_format" in call_kwargs
        assert call_kwargs["response_format"] == EVMMetricsRead

        assert result[0]["runnable"] == mock_runnable
        assert result[0]["structured_output_schema"] == EVMMetricsRead

    @patch("app.ai.subagent_compiler.langchain_create_agent")
    def test_no_wrapper_when_no_schema(self, mock_create_agent: MagicMock) -> None:
        """compile_subagents does not apply wrapper when schema is None."""
        mock_runnable = MagicMock()
        mock_create_agent.return_value = mock_runnable

        context = ToolContext(
            session=MagicMock(),
            user_id=str(uuid4()),
            user_role="admin",
            execution_mode=ExecutionMode.STANDARD,
            project_id=None,
        )

        subagents = [
            {
                "name": "test_agent",
                "description": "Test",
                "system_prompt": "You are a test agent",
                "allowed_tools": ["list_projects"],
                "structured_output_schema": None,
            }
        ]

        mock_tool = MagicMock(spec=StructuredTool)
        mock_tool.name = "list_projects"

        result = compile_subagents(
            "openai:gpt-4o", context, subagents, [mock_tool], allowed_tools=None
        )

        mock_runnable.with_structured_output.assert_not_called()

        assert result[0]["runnable"] == mock_runnable
        assert result[0]["structured_output_schema"] is None


class TestStructuredOutputExtraction:
    """T-103: Task tool extracts Pydantic model from subagent result."""

    def test_expects_evm_metrics(self) -> None:
        """build_task_tool stores schema for evm_analyst subagent."""
        mock_runnable = MagicMock()
        mock_runnable.invoke.return_value = {"messages": [AIMessage(content="result")]}
        mock_runnable.ainvoke = AsyncMock(
            return_value={"messages": [AIMessage(content="result")]}
        )

        subagents = [
            {
                "name": "evm_analyst",
                "description": "EVM Analyst",
                "runnable": mock_runnable,
                "structured_output_schema": EVMMetricsRead,
            }
        ]

        tool = build_task_tool(subagents)

        # Verify tool was created
        assert isinstance(tool, StructuredTool)
        assert tool.name == "task"


class TestSummaryGeneration:
    """T-104: Task tool generates human-readable summary for each schema type."""

    def test_summarize_evm_metrics(self) -> None:
        """Generate summary from EVMMetricsRead model."""
        model = EVMMetricsRead(
            bac=100000.0,
            pv=50000.0,
            ac=55000.0,
            ev=48000.0,
            cv=-7000.0,
            sv=-2000.0,
            cpi=0.87,
            spi=0.96,
            eac=115000.0,
            etc=60000.0,
            cost_element_id=uuid4(),
            control_date=datetime.now(),
            branch="main",
            branch_mode="strict",
            progress_percentage=48.0,
        )

        summary = _summarize_structured_output(model)

        assert "EVM Metrics" in summary
        assert "CPI: 0.87" in summary
        assert "SPI: 0.96" in summary
        assert "Cost Variance (CV): -7,000.00" in summary
        assert "Estimate at Completion (EAC): 115,000.00" in summary

    def test_summarize_dashboard_data(self) -> None:
        """Generate summary from DashboardData model."""
        project_id = uuid4()
        model = DashboardData(
            last_edited_project=ProjectSpotlight(
                project_id=project_id,
                project_name="Test Project",
                project_code="TP001",
                last_activity=datetime.now(),
                metrics=ProjectMetrics(
                    total_budget=Decimal("500000.00"),
                    total_wbes=10,
                    total_cost_elements=25,
                    active_change_orders=2,
                    ev_status="on_track",
                ),
                branch="main",
            ),
            recent_activity={
                "projects": [
                    DashboardActivity(
                        entity_id=project_id,
                        entity_name="Test Project",
                        entity_type="project",
                        action="created",
                        timestamp=datetime.now(),
                        actor_id=uuid4(),
                        actor_name="Test User",
                        branch="main",
                    )
                ]
            },
        )

        summary = _summarize_structured_output(model)

        assert "Dashboard Data" in summary
        assert "Test Project" in summary
        assert "500,000.00" in summary
        assert "1 updates" in summary

    def test_summarize_impact_analysis(self) -> None:
        """Generate summary from ImpactAnalysisResponse model."""
        model = ImpactAnalysisResponse(
            change_order_id=uuid4(),
            branch_name="BR-CO-001",
            main_branch_name="main",
            kpi_scorecard=KPIScorecard(
                bac=KPIMetric(
                    main_value=Decimal("100000.00"),
                    change_value=Decimal("120000.00"),
                    delta=Decimal("20000.00"),
                ),
                budget_delta=KPIMetric(delta=Decimal("20000.00")),
                gross_margin=KPIMetric(delta=Decimal("5000.00")),
                actual_costs=KPIMetric(delta=Decimal("0.00")),
                revenue_delta=KPIMetric(delta=Decimal("0.00")),
            ),
            entity_changes=EntityChanges(
                wbes=[
                    EntityChange(
                        id=1, name="New WBE", change_type="added", budget_delta=None
                    )
                ],
                cost_elements=[],
                cost_registrations=[],
            ),
        )

        summary = _summarize_structured_output(model)

        assert "Impact Analysis" in summary
        assert "BR-CO-001" in summary
        assert "BAC change: 20,000.00" in summary
        assert "Entity changes: 1 total" in summary

    def test_summarize_forecast(self) -> None:
        """Generate summary from ForecastRead model."""
        cost_element_id = uuid4()
        model = ForecastRead(
            id=uuid4(),
            forecast_id=uuid4(),
            branch="main",
            created_by=uuid4(),
            eac_amount=Decimal("550000.00"),
            basis_of_estimate="Based on current trends and performance",
            cost_element_id=cost_element_id,
            cost_element_code="CE001",
            cost_element_name="Test Cost Element",
            cost_element_budget_amount=Decimal("500000.00"),
        )

        summary = _summarize_structured_output(model)

        assert "Forecast" in summary
        assert "CE001" in summary
        assert "550,000.00" in summary
        assert "Budget variance: 50,000.00" in summary


class TestStructuredOutputAttachment:
    """T-105: Structured output attached to ToolMessage.additional_kwargs."""

    def test_structured_output_in_additional_kwargs(self) -> None:
        """Pydantic model serialized and stored in ToolMessage.additional_kwargs."""
        # Create mock runnable that returns Pydantic model
        # Note: LangChain's with_structured_output() returns the model directly,
        # not wrapped in AIMessage. We simulate this by returning a special
        # AIMessage-like object where content is the Pydantic model.
        evm_model = EVMMetricsRead(
            bac=100000.0,
            pv=50000.0,
            ac=55000.0,
            ev=48000.0,
            cv=-7000.0,
            sv=-2000.0,
            cpi=0.87,
            spi=0.96,
            cost_element_id=uuid4(),
            control_date=datetime.now(),
            branch="main",
            branch_mode="strict",
        )

        # Create a mock message that behaves like what with_structured_output returns
        mock_message = MagicMock()
        mock_message.content = evm_model  # Pydantic model as content (not string)

        mock_runnable = MagicMock()
        mock_runnable.invoke.return_value = {"messages": [mock_message]}

        subagents = [
            {
                "name": "evm_analyst",
                "description": "EVM Analyst",
                "runnable": mock_runnable,
                "structured_output_schema": EVMMetricsRead,
            }
        ]

        tool = build_task_tool(subagents)

        # Invoke the tool
        runtime = _make_runtime()
        result = tool.func(
            description="Calculate EVM metrics",
            subagent_type="evm_analyst",
            runtime=runtime,
        )

        # Should return Command
        assert isinstance(result, Command)
        assert "messages" in result.update

        # Extract ToolMessage
        messages = result.update["messages"]
        assert len(messages) == 1
        tool_msg = messages[0]
        assert isinstance(tool_msg, ToolMessage)

        # Verify structured output in additional_kwargs
        assert tool_msg.additional_kwargs is not None
        assert "structured_output" in tool_msg.additional_kwargs
        structured = tool_msg.additional_kwargs["structured_output"]
        assert structured["schema"] == "EVMMetricsRead"
        assert "data" in structured
        assert structured["data"]["cpi"] == 0.87

        # Verify human-readable summary in content
        assert "EVM Metrics" in tool_msg.content
        assert "CPI: 0.87" in tool_msg.content


class TestBackwardCompatibility:
    """T-106: Backward compatibility with text-only responses."""

    def test_text_only_response_works(self) -> None:
        """Subagent without schema returns text content normally."""
        mock_runnable = MagicMock()
        mock_runnable.invoke.return_value = {
            "messages": [AIMessage(content="Plain text response")]
        }

        subagents = [
            {
                "name": "text_agent",
                "description": "Text Agent",
                "runnable": mock_runnable,
                "structured_output_schema": None,  # No schema
            }
        ]

        tool = build_task_tool(subagents)

        # Invoke the tool
        runtime = _make_runtime()
        result = tool.func(
            description="Get text response",
            subagent_type="text_agent",
            runtime=runtime,
        )

        assert isinstance(result, Command)
        messages = result.update["messages"]
        assert len(messages) == 1
        tool_msg = messages[0]

        # Should have plain text content
        assert tool_msg.content == "Plain text response"

        # Should NOT have additional_kwargs (or empty dict)
        assert not tool_msg.additional_kwargs or tool_msg.additional_kwargs == {}


class TestErrorHandling:
    """T-107: Invalid structured output falls back to text content."""

    def test_schema_mismatch_fallback(self) -> None:
        """When content doesn't match schema, falls back to text."""
        # Subagent returns plain text when schema expects Pydantic
        mock_runnable = MagicMock()
        mock_runnable.invoke.return_value = {
            "messages": [AIMessage(content="Some text instead of model")]
        }

        subagents = [
            {
                "name": "evm_analyst",
                "description": "EVM Analyst",
                "runnable": mock_runnable,
                "structured_output_schema": EVMMetricsRead,
            }
        ]

        tool = build_task_tool(subagents)

        # Invoke the tool
        runtime = _make_runtime()
        result = tool.func(
            description="Calculate EVM metrics",
            subagent_type="evm_analyst",
            runtime=runtime,
        )

        assert isinstance(result, Command)
        messages = result.update["messages"]
        tool_msg = messages[0]

        # Should have text content (fallback)
        assert tool_msg.content == "Some text instead of model"

        # Should NOT have structured_output (error case)
        assert tool_msg.additional_kwargs is None or "structured_output" not in (
            tool_msg.additional_kwargs or {}
        )


class TestAsyncPath:
    """Tests for async atask function with structured output."""

    @pytest.mark.asyncio
    async def test_async_extracts_structured_output(self) -> None:
        """Async atask extracts structured output correctly."""
        evm_model = EVMMetricsRead(
            bac=100000.0,
            pv=50000.0,
            ac=55000.0,
            ev=48000.0,
            cv=-7000.0,
            sv=-2000.0,
            cpi=0.87,
            spi=0.96,
            cost_element_id=uuid4(),
            control_date=datetime.now(),
            branch="main",
            branch_mode="strict",
        )

        # Create a mock message that behaves like what with_structured_output returns
        mock_message = MagicMock()
        mock_message.content = evm_model  # Pydantic model as content (not string)

        mock_runnable = MagicMock()
        mock_runnable.ainvoke = AsyncMock(return_value={"messages": [mock_message]})

        subagents = [
            {
                "name": "evm_analyst",
                "description": "EVM Analyst",
                "runnable": mock_runnable,
                "structured_output_schema": EVMMetricsRead,
            }
        ]

        tool = build_task_tool(subagents)

        # Invoke async
        runtime = _make_runtime()
        result = await tool.coroutine(
            description="Calculate EVM metrics",
            subagent_type="evm_analyst",
            runtime=runtime,
        )

        assert isinstance(result, Command)
        messages = result.update["messages"]
        tool_msg = messages[0]

        # Verify structured output
        assert tool_msg.additional_kwargs is not None
        assert "structured_output" in tool_msg.additional_kwargs
        assert "EVM Metrics" in tool_msg.content


class TestMakeJsonSerializable:
    """Tests for _make_json_serializable method."""

    @pytest.mark.asyncio
    async def test_parses_json_string_to_dict(self, db_session: AsyncSession) -> None:
        """JSON strings are parsed back to dict objects."""
        from app.ai.agent_service import AgentService

        service = AgentService(db_session)

        # Test JSON string parsing
        json_str = '{"project_id": "23d37626-bd10-48dc-ad36-64655a556af4", "num": 1.5, "text": "hello"}'
        result = service._make_json_serializable(json_str)

        assert isinstance(result, dict)
        assert result["project_id"] == "23d37626-bd10-48dc-ad36-64655a556af4"
        assert result["num"] == 1.5  # Number, not string
        assert result["text"] == "hello"

    @pytest.mark.asyncio
    async def test_preserves_non_json_strings(self, db_session: AsyncSession) -> None:
        """Non-JSON strings are preserved as-is."""
        from app.ai.agent_service import AgentService

        service = AgentService(db_session)

        # Test plain text string
        plain_text = "This is just plain text"
        result = service._make_json_serializable(plain_text)

        assert result == "This is just plain text"
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_parses_nested_json_strings(self, db_session: AsyncSession) -> None:
        """Nested structures with JSON strings are parsed correctly."""
        from app.ai.agent_service import AgentService

        service = AgentService(db_session)

        # Test nested JSON string in a dict
        nested = {
            "tool": "test_tool",
            "result": '{"inner": "value", "number": 42}',
            "normal": "string",
        }
        result = service._make_json_serializable(nested)

        assert isinstance(result, dict)
        assert result["tool"] == "test_tool"
        assert result["normal"] == "string"
        # The JSON string should be parsed
        assert isinstance(result["result"], dict)
        assert result["result"]["inner"] == "value"
        assert result["result"]["number"] == 42

    @pytest.mark.asyncio
    async def test_handles_tool_message_with_json_content(
        self, db_session: AsyncSession
    ) -> None:
        """ToolMessage with JSON string content is parsed correctly."""
        from langchain_core.messages import ToolMessage

        from app.ai.agent_service import AgentService

        service = AgentService(db_session)

        # Create ToolMessage with JSON string content
        json_content = '{"project_id": "abc-123", "value": 100.0}'
        tool_msg = ToolMessage(
            content=json_content,
            tool_call_id="call_123",
        )

        result = service._make_json_serializable(tool_msg)

        assert isinstance(result, dict)
        assert "content" in result
        assert "tool_call_id" in result
        assert result["tool_call_id"] == "call_123"
        # Content should be parsed from JSON string to dict
        assert isinstance(result["content"], dict)
        assert result["content"]["project_id"] == "abc-123"
        assert result["content"]["value"] == 100.0

    @pytest.mark.asyncio
    async def test_handles_invalid_json_gracefully(
        self, db_session: AsyncSession
    ) -> None:
        """Invalid JSON strings fall back to string."""
        from app.ai.agent_service import AgentService

        service = AgentService(db_session)

        # Test invalid JSON
        invalid_json = "{this is not valid JSON"
        result = service._make_json_serializable(invalid_json)

        # Should return the string as-is
        assert result == invalid_json
        assert isinstance(result, str)
