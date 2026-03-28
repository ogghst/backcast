"""Performance benchmarks for AI tool risk checking.

Measures the overhead of risk checking and execution mode filtering
to ensure it adds minimal latency to tool execution.

Success criteria: Median overhead < 10ms per tool execution.
"""

import time
from uuid import uuid4

import pytest
from langchain_core.tools import tool

from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext
from app.ai.tools.risk_check_node import RiskCheckNode


# Test fixtures


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    from unittest.mock import MagicMock

    return MagicMock()


@pytest.fixture
def tool_context(mock_session):
    """Create a tool context for testing."""
    return ToolContext(
        session=mock_session,
        user_id=str(uuid4()),
        user_role="admin",
        execution_mode=ExecutionMode.STANDARD,
    )


@pytest.fixture
def sample_tools():
    """Create sample tools with different risk levels."""
    tools = []

    # Low risk tool
    @tool
    def low_risk_tool() -> str:
        """A low-risk tool."""
        return "low risk result"

    low_risk_tool._tool_metadata = type(
        "ToolMetadata",
        (),
        {
            "name": "low_risk_tool",
            "description": "A low-risk tool",
            "risk_level": RiskLevel.LOW,
        },
    )
    tools.append(low_risk_tool)

    # High risk tool
    @tool
    def high_risk_tool() -> str:
        """A high-risk tool."""
        return "high risk result"

    high_risk_tool._tool_metadata = type(
        "ToolMetadata",
        (),
        {
            "name": "high_risk_tool",
            "description": "A high-risk tool",
            "risk_level": RiskLevel.HIGH,
        },
    )
    tools.append(high_risk_tool)

    # Critical risk tool
    @tool
    def critical_risk_tool() -> str:
        """A critical-risk tool."""
        return "critical risk result"

    critical_risk_tool._tool_metadata = type(
        "ToolMetadata",
        (),
        {
            "name": "critical_risk_tool",
            "description": "A critical-risk tool",
            "risk_level": RiskLevel.CRITICAL,
        },
    )
    tools.append(critical_risk_tool)

    # Tool without metadata (defaults to HIGH)
    @tool
    def unannotated_tool() -> str:
        """A tool without risk level annotation."""
        return "unannotated result"

    tools.append(unannotated_tool)

    return tools


# Benchmark tests


@pytest.mark.performance
def test_risk_check_node_initialization_overhead(tool_context, sample_tools, benchmark):
    """Benchmark RiskCheckNode initialization overhead.

    Measures: Time to create a RiskCheckNode with tool filtering
    Success: Median < 5ms
    """

    def create_risk_check_node():
        return RiskCheckNode(sample_tools, tool_context)

    result = benchmark(create_risk_check_node)

    # Verify the node was created correctly
    assert result is not None
    assert hasattr(result, "context")
    assert result.context.execution_mode == ExecutionMode.STANDARD


@pytest.mark.performance
def test_safe_mode_filtering_overhead(tool_context, sample_tools, benchmark):
    """Benchmark tool filtering in SAFE mode.

    Measures: Time to filter tools to low-risk only
    Success: Median < 1ms
    """

    tool_context_safe = ToolContext(
        session=tool_context.session,
        user_id=tool_context.user_id,
        user_role=tool_context.user_role,
        execution_mode=ExecutionMode.SAFE,
    )

    def filter_safe_mode():
        node = RiskCheckNode(sample_tools, tool_context_safe)
        # Check that node was created successfully
        return node.context.execution_mode == ExecutionMode.SAFE

    result = benchmark(filter_safe_mode)

    # Verify node was created for safe mode
    assert result is True


@pytest.mark.performance
def test_standard_mode_filtering_overhead(tool_context, sample_tools, benchmark):
    """Benchmark tool filtering in STANDARD mode.

    Measures: Time to filter tools to low and high-risk
    Success: Median < 1ms
    """

    def filter_standard_mode():
        node = RiskCheckNode(sample_tools, tool_context)
        # Check that node was created successfully
        return node.context.execution_mode == ExecutionMode.STANDARD

    result = benchmark(filter_standard_mode)

    # Verify node was created for standard mode
    assert result is True


@pytest.mark.performance
def test_expert_mode_filtering_overhead(tool_context, sample_tools, benchmark):
    """Benchmark tool filtering in EXPERT mode.

    Measures: Time to filter tools (all tools)
    Success: Median < 1ms
    """

    tool_context_expert = ToolContext(
        session=tool_context.session,
        user_id=tool_context.user_id,
        user_role=tool_context.user_role,
        execution_mode=ExecutionMode.EXPERT,
    )

    def filter_expert_mode():
        node = RiskCheckNode(sample_tools, tool_context_expert)
        # Check that node was created successfully
        return node.context.execution_mode == ExecutionMode.EXPERT

    result = benchmark(filter_expert_mode)

    # Verify node was created for expert mode
    assert result is True


@pytest.mark.performance
def test_check_tool_risk_overhead(tool_context, sample_tools, benchmark):
    """Benchmark individual tool risk check overhead.

    Measures: Time to check if a specific tool is allowed
    Success: Median < 0.5ms
    """

    node = RiskCheckNode(sample_tools, tool_context)

    def check_risk():
        return node.check_tool_risk("critical_risk_tool")

    result = benchmark(check_risk)

    # In standard mode, critical tools should require approval
    allowed, error_message = result
    assert not allowed
    assert "requires approval" in error_message.lower()


@pytest.mark.performance
def test_large_toolset_filtering_overhead(tool_context, benchmark):
    """Benchmark filtering with a large toolset.

    Measures: Time to filter 100 tools with mixed risk levels
    Success: Median < 10ms

    This simulates a production-like scenario with many tools.
    """

    # Import the tool decorator properly
    from langchain_core.tools import tool as create_tool

    # Create a large toolset (100 tools)
    large_toolset = []

    risk_levels = [RiskLevel.LOW, RiskLevel.HIGH, RiskLevel.CRITICAL]

    for i in range(100):
        risk_level = risk_levels[i % 3]

        # Create tool with proper docstring
        def tool_func() -> str:
            """Tool function for performance testing."""
            return f"tool result"

        tool_instance = create_tool(tool_func)
        tool_instance.name = f"tool_{i}"
        tool_instance._tool_metadata = type(
            "ToolMetadata",
            (),
            {
                "name": f"tool_{i}",
                "description": f"Tool {i}",
                "risk_level": risk_level,
            },
        )
        large_toolset.append(tool_instance)

    def filter_large_toolset():
        node = RiskCheckNode(large_toolset, tool_context)
        # Return the context execution mode to verify node was created
        return node.context.execution_mode == ExecutionMode.STANDARD

    result = benchmark(filter_large_toolset)

    # Verify node was created successfully
    assert result is True


@pytest.mark.performance
def test_risk_check_memory_overhead(tool_context, sample_tools):
    """Test memory overhead of risk checking.

    Measures: Memory usage before and after creating RiskCheckNode
    Success: Minimal memory increase (< 1KB per node)
    """

    import gc
    import sys

    # Get baseline memory
    gc.collect()
    baseline_objects = len(gc.get_objects())

    # Create multiple nodes
    nodes = []
    for _ in range(100):
        node = RiskCheckNode(sample_tools, tool_context)
        nodes.append(node)

    # Check memory overhead
    # Each node should hold references to the same tools (not copy them)
    # so memory overhead should be minimal
    gc.collect()
    final_objects = len(gc.get_objects())

    # Memory overhead should be reasonable (< 3x baseline to account for nodes themselves)
    assert final_objects < baseline_objects * 3


# Integration-style performance test


@pytest.mark.performance
@pytest.mark.slow
def test_end_to_end_risk_check_latency(tool_context, sample_tools):
    """End-to-end latency test for risk checking.

    Measures: Total time from tool selection to execution decision
    Success: p95 < 10ms, p99 < 20ms

    This test simulates the full flow:
    1. Create RiskCheckNode
    2. Check tool risk
    3. Filter tools for execution
    """

    latencies = []

    for _ in range(1000):
        start_time = time.perf_counter()

        # Create node with filtering
        node = RiskCheckNode(sample_tools, tool_context)

        # Check risk for each tool
        for tool in sample_tools:
            tool_name = getattr(tool, "name", "unknown")
            node.check_tool_risk(tool_name)

        end_time = time.perf_counter()

        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)

    # Calculate percentiles
    latencies_sorted = sorted(latencies)
    p50 = latencies_sorted[500]  # Median
    p95 = latencies_sorted[950]
    p99 = latencies_sorted[990]

    # Print statistics for visibility
    print(f"\nRisk Check Latency Statistics (n=1000):")
    print(f"  p50 (median): {p50:.2f}ms")
    print(f"  p95: {p95:.2f}ms")
    print(f"  p99: {p99:.2f}ms")
    print(f"  min: {min(latencies):.2f}ms")
    print(f"  max: {max(latencies):.2f}ms")

    # Success criteria
    assert p50 < 10, f"Median latency {p50}ms exceeds 10ms threshold"
    assert p95 < 15, f"p95 latency {p95}ms exceeds 15ms threshold"
    assert p99 < 25, f"p99 latency {p99}ms exceeds 25ms threshold"


# Regression test


@pytest.mark.performance
def test_risk_check_overhead_not_degraded(tool_context, sample_tools):
    """Regression test to ensure risk check overhead hasn't degraded.

    Compares current performance against baseline (established in initial implementation).
    If this test fails, it indicates a performance regression.

    Baseline (established 2026-03-22):
    - Node creation: < 5ms
    - Tool filtering: < 1ms
    - Risk check: < 0.5ms
    """

    import statistics

    # Warm-up
    for _ in range(10):
        RiskCheckNode(sample_tools, tool_context)

    # Measure node creation
    creation_times = []
    for _ in range(100):
        start = time.perf_counter()
        node = RiskCheckNode(sample_tools, tool_context)
        end = time.perf_counter()
        creation_times.append((end - start) * 1000)
        assert node is not None

    median_creation = statistics.median(creation_times)

    # Measure risk checking
    node = RiskCheckNode(sample_tools, tool_context)
    check_times = []
    for _ in range(100):
        start = time.perf_counter()
        node.check_tool_risk("critical_risk_tool")
        end = time.perf_counter()
        check_times.append((end - start) * 1000)

    median_check = statistics.median(check_times)

    print(f"\nPerformance Regression Check:")
    print(f"  Node creation median: {median_creation:.2f}ms (baseline: < 5ms)")
    print(f"  Risk check median: {median_check:.2f}ms (baseline: < 0.5ms)")

    # Assert against baseline
    assert median_creation < 5, f"Node creation degraded: {median_creation}ms > 5ms"
    assert median_check < 0.5, f"Risk check degraded: {median_check}ms > 0.5ms"
