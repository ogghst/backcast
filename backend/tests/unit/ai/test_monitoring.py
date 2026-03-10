"""Unit tests for tool execution monitoring."""

import pytest

from app.ai.monitoring import (
    MonitoringContext,
    ToolExecutionMetrics,
    log_tool_call,
    log_tool_result,
    monitor_tool_execution,
)


class TestToolExecutionMetrics:
    """Test suite for ToolExecutionMetrics dataclass."""

    def test_metrics_initialization(self) -> None:
        """Test that metrics can be initialized with required fields."""
        metrics = ToolExecutionMetrics(
            tool_name="test_tool",
            execution_time_ms=100.0,
            success=True,
        )

        assert metrics.tool_name == "test_tool"
        assert metrics.execution_time_ms == 100.0
        assert metrics.success is True
        assert metrics.error_message is None
        assert metrics.timestamp > 0

    def test_metrics_to_dict(self) -> None:
        """Test that metrics can be converted to dictionary."""
        metrics = ToolExecutionMetrics(
            tool_name="test_tool",
            execution_time_ms=100.0,
            success=True,
            error_message="Test error",
        )

        result = metrics.to_dict()

        assert result["tool_name"] == "test_tool"
        assert result["execution_time_ms"] == 100.0
        assert result["success"] is True
        assert result["error_message"] == "Test error"
        assert "timestamp" in result


class TestMonitoringContext:
    """Test suite for MonitoringContext."""

    def test_context_initialization(self) -> None:
        """Test that context initializes with empty state."""
        context = MonitoringContext()

        assert context.executions == []
        assert context.total_tools_called == 0
        assert context.total_execution_time_ms == 0.0

    def test_add_execution_increments_counters(self) -> None:
        """Test that add_execution updates counters correctly."""
        context = MonitoringContext()

        metrics = ToolExecutionMetrics(
            tool_name="test_tool",
            execution_time_ms=100.0,
            success=True,
        )

        context.add_execution(metrics)

        assert len(context.executions) == 1
        assert context.total_tools_called == 1
        assert context.total_execution_time_ms == 100.0

    def test_add_execution_multiple(self) -> None:
        """Test that multiple executions are tracked correctly."""
        context = MonitoringContext()

        # Add multiple executions
        for i in range(3):
            metrics = ToolExecutionMetrics(
                tool_name=f"tool_{i}",
                execution_time_ms=float(i * 100),
                success=True,
            )
            context.add_execution(metrics)

        assert len(context.executions) == 3
        assert context.total_tools_called == 3
        assert context.total_execution_time_ms == 300.0  # 0 + 100 + 200

    def test_get_summary_empty(self) -> None:
        """Test that summary returns zeros for empty context."""
        context = MonitoringContext()

        summary = context.get_summary()

        assert summary["total_tools_called"] == 0
        assert summary["total_execution_time_ms"] == 0.0
        assert summary["average_execution_time_ms"] == 0.0
        assert summary["success_rate"] == 1.0
        assert summary["tools_by_name"] == {}

    def test_get_summary_with_executions(self) -> None:
        """Test that summary calculates statistics correctly."""
        context = MonitoringContext()

        # Add some executions
        context.add_execution(
            ToolExecutionMetrics(
                tool_name="tool_a",
                execution_time_ms=100.0,
                success=True,
            )
        )
        context.add_execution(
            ToolExecutionMetrics(
                tool_name="tool_a",
                execution_time_ms=200.0,
                success=True,
            )
        )
        context.add_execution(
            ToolExecutionMetrics(
                tool_name="tool_b",
                execution_time_ms=150.0,
                success=False,
                error_message="Test error",
            )
        )

        summary = context.get_summary()

        assert summary["total_tools_called"] == 3
        assert summary["total_execution_time_ms"] == 450.0
        assert summary["average_execution_time_ms"] == 150.0
        assert summary["success_rate"] == 2 / 3  # 2 out of 3 succeeded

        # Check tools_by_name
        assert "tool_a" in summary["tools_by_name"]
        assert "tool_b" in summary["tools_by_name"]
        assert summary["tools_by_name"]["tool_a"]["count"] == 2
        assert summary["tools_by_name"]["tool_a"]["average_time_ms"] == 150.0
        assert summary["tools_by_name"]["tool_a"]["errors"] == 0
        assert summary["tools_by_name"]["tool_b"]["count"] == 1
        assert summary["tools_by_name"]["tool_b"]["errors"] == 1


class TestMonitorToolExecution:
    """Test suite for monitor_tool_execution context manager."""

    def test_monitor_successful_execution(self) -> None:
        """Test that successful execution is tracked correctly."""
        context = MonitoringContext()

        with monitor_tool_execution("test_tool", context):
            pass  # Do nothing (successful execution)

        assert len(context.executions) == 1
        assert context.executions[0].tool_name == "test_tool"
        assert context.executions[0].success is True
        assert context.executions[0].error_message is None
        assert context.executions[0].execution_time_ms >= 0

    def test_monitor_failed_execution(self) -> None:
        """Test that failed execution is tracked correctly."""
        context = MonitoringContext()

        with pytest.raises(ValueError, match="Test error"):
            with monitor_tool_execution("test_tool", context):
                raise ValueError("Test error")

        assert len(context.executions) == 1
        assert context.executions[0].tool_name == "test_tool"
        assert context.executions[0].success is False
        assert "Test error" in context.executions[0].error_message
        assert context.executions[0].execution_time_ms >= 0

    def test_monitor_without_context(self) -> None:
        """Test that monitoring works without context (no recording)."""
        # Should not crash
        with monitor_tool_execution("test_tool", context=None):
            pass

    def test_execution_time_is_measured(self) -> None:
        """Test that execution time is measured accurately."""
        context = MonitoringContext()

        import time

        with monitor_tool_execution("test_tool", context):
            time.sleep(0.01)  # Sleep for 10ms

        # Should be approximately 10ms (allow for some variance)
        assert context.executions[0].execution_time_ms >= 8.0

    def test_monitor_tracks_multiple_tools(self) -> None:
        """Test that multiple tool executions are tracked."""
        context = MonitoringContext()

        with monitor_tool_execution("tool_a", context):
            pass

        with monitor_tool_execution("tool_b", context):
            pass

        with monitor_tool_execution("tool_a", context):
            pass

        assert context.total_tools_called == 3
        assert len(context.executions) == 3


class TestLoggingFunctions:
    """Test suite for logging functions."""

    def test_log_tool_call_no_crash(self) -> None:
        """Test that log_tool_call doesn't crash."""
        # This test just verifies the logging function works without errors
        # The actual logging is tested by integration tests
        log_tool_call("test_tool", {"arg1": "value1", "arg2": 42})
        # If we get here without exception, the test passes

    def test_log_tool_result_no_crash(self) -> None:
        """Test that log_tool_result doesn't crash."""
        # This test just verifies the logging function works without errors
        # The actual logging is tested by integration tests
        log_tool_result("test_tool", {"result": "success"})
        # If we get here without exception, the test passes
