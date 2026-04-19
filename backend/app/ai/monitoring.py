"""Tool execution monitoring for LangGraph agent.

Provides execution time tracking, tool call logging, and metrics collection
for observability and debugging.
"""

import contextlib
import logging
import time
from collections import defaultdict
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionMetrics:
    """Metrics for a single tool execution.

    Attributes:
        tool_name: Name of the tool executed
        execution_time_ms: Execution time in milliseconds
        success: Whether execution succeeded
        error_message: Error message if execution failed
        timestamp: Unix timestamp of execution
    """

    tool_name: str
    execution_time_ms: float
    success: bool
    error_message: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tool_name": self.tool_name,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }


@dataclass
class MonitoringContext:
    """Context for monitoring tool executions.

    Tracks execution metrics across multiple tool calls.

    Attributes:
        executions: List of execution metrics
        total_tools_called: Total number of tool calls
        total_execution_time_ms: Total execution time across all tools
    """

    executions: list[ToolExecutionMetrics] = field(default_factory=list)
    total_tools_called: int = 0
    total_execution_time_ms: float = 0.0

    def add_execution(self, metrics: ToolExecutionMetrics) -> None:
        """Add execution metrics to the context.

        Args:
            metrics: Execution metrics to add
        """
        self.executions.append(metrics)
        self.total_tools_called += 1
        self.total_execution_time_ms += metrics.execution_time_ms

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics for all executions.

        Returns:
            Dictionary with summary statistics
        """
        if not self.executions:
            return {
                "total_tools_called": 0,
                "total_execution_time_ms": 0.0,
                "average_execution_time_ms": 0.0,
                "success_rate": 1.0,
                "tools_by_name": {},
            }

        # Group by tool name
        tools_by_name: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_time_ms": 0.0,
                "errors": 0,
            }
        )

        for execution in self.executions:
            tool_name = execution.tool_name
            tools_by_name[tool_name]["count"] += 1
            tools_by_name[tool_name]["total_time_ms"] += execution.execution_time_ms
            if not execution.success:
                tools_by_name[tool_name]["errors"] += 1

        # Calculate averages
        for _tool_name, stats in tools_by_name.items():
            stats["average_time_ms"] = stats["total_time_ms"] / stats["count"]

        # Calculate success rate
        successful_executions = sum(1 for e in self.executions if e.success)
        success_rate = successful_executions / len(self.executions)

        return {
            "total_tools_called": self.total_tools_called,
            "total_execution_time_ms": self.total_execution_time_ms,
            "average_execution_time_ms": self.total_execution_time_ms
            / self.total_tools_called,
            "success_rate": success_rate,
            "tools_by_name": dict(tools_by_name),
        }


@contextlib.contextmanager
def monitor_tool_execution(
    tool_name: str,
    context: MonitoringContext | None = None,
) -> Generator[None, None, None]:
    """Context manager for monitoring tool execution.

    Args:
        tool_name: Name of the tool being executed
        context: Optional monitoring context to record metrics

    Yields:
        None

    Examples:
        >>> monitoring_ctx = MonitoringContext()
        >>>
        >>> with monitor_tool_execution("list_projects", monitoring_ctx):
        ...     result = await list_projects(...)
        >>>
        >>> summary = monitoring_ctx.get_summary()
        >>> print(f"Called {summary['total_tools_called']} tools")

    Note:
        If context is None, execution is still timed but not recorded.
        This allows for optional monitoring without changing tool code.
    """
    start_time = time.time()
    success = True
    error_message = None

    try:
        yield
    except Exception as e:
        success = False
        error_message = str(e)
        logger.error(f"Tool {tool_name} failed: {e}")
        raise
    finally:
        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000

        # Create metrics
        metrics = ToolExecutionMetrics(
            tool_name=tool_name,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message,
        )

        # Log execution
        if success:
            logger.info(f"Tool {tool_name} executed in {execution_time_ms:.2f}ms")
        else:
            logger.warning(
                f"Tool {tool_name} failed after {execution_time_ms:.2f}ms: {error_message}"
            )

        # Record metrics if context provided
        if context is not None:
            context.add_execution(metrics)


def log_tool_call(tool_name: str, args: dict[str, Any]) -> None:
    """Log a tool call with its arguments.

    Args:
        tool_name: Name of the tool being called
        args: Arguments passed to the tool

    Examples:
        >>> log_tool_call("list_projects", {"search": "test", "limit": 10})
    """
    logger.debug(f"Tool call: {tool_name} with args: {args}")


def log_tool_result(tool_name: str, result: Any) -> None:
    """Log a tool result.

    Args:
        tool_name: Name of the tool that was called
        result: Result returned by the tool

    Examples:
        >>> log_tool_result("list_projects", {"projects": [...], "total": 5})
    """
    logger.debug(f"Tool result: {tool_name} -> {result}")
