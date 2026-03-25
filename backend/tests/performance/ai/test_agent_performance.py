"""Performance benchmarks for AI agent invocation.

Tests measure agent invocation latency against targets:
- Simple query: <500ms (p50)
- Complex query: <1000ms (p50)
- Concurrent requests: Scales linearly

These benchmarks use mocking to control LLM response time and measure
actual graph execution overhead without external API latency.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.ai.graph import create_graph
from app.ai.state import AgentState

# Performance Targets
SIMPLE_QUERY_TARGET_P50 = 500  # ms
COMPLEX_QUERY_TARGET_P50 = 1000  # ms


@pytest.fixture
def mock_fast_llm():
    """Mock LLM that responds quickly (simulating fast API response)."""
    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=llm)
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="Quick response"))
    return llm


@pytest.fixture
def mock_slow_llm():
    """Mock LLM that responds slowly (simulating complex reasoning)."""
    async def slow_invoke(*args, **kwargs):
        await asyncio.sleep(0.1)  # 100ms delay
        return AIMessage(content="Detailed response after thinking")

    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=llm)
    llm.ainvoke = AsyncMock(side_effect=slow_invoke)
    return llm


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_simple_query_latency_p50(mock_fast_llm):
    """Benchmark: Simple query should complete in <500ms (p50).

    This test measures the overhead of graph execution for a simple query
    that doesn't require tool calling. The LLM response is mocked to be
    instantaneous, so we're measuring pure graph execution time.

    Target: <500ms (p50)
    """
    # Arrange
    graph = create_graph(llm=mock_fast_llm, tools=[])

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Hello, what can you help with?")],
        "tool_call_count": 0,
        "next": "agent",
    }

    # Config with thread_id for checkpointer
    config = {"configurable": {"thread_id": "perf-test-simple-query"}}

    # Act - Measure execution time
    start_time = time.perf_counter()
    result = await graph.ainvoke(initial_state, config=config)
    end_time = time.perf_counter()

    latency_ms = (end_time - start_time) * 1000

    # Assert - Check target
    assert result is not None
    assert "messages" in result
    assert len(result["messages"]) == 2  # Initial + response

    # Performance assertion
    assert (
        latency_ms < SIMPLE_QUERY_TARGET_P50
    ), f"Simple query latency {latency_ms:.2f}ms exceeds target {SIMPLE_QUERY_TARGET_P50}ms"

    # Log for reporting
    print(f"\n✓ Simple query latency: {latency_ms:.2f}ms (target: <{SIMPLE_QUERY_TARGET_P50}ms)")


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_simple_query_latency_percentiles(mock_fast_llm):
    """Benchmark: Measure simple query latency across multiple runs.

    Runs the simple query benchmark 50 times to calculate p50, p95, and p99
    percentiles. This provides better insight into performance distribution
    than a single run.

    Targets:
    - p50: <500ms
    - p95: <750ms
    - p99: <1000ms
    """
    # Arrange
    graph = create_graph(llm=mock_fast_llm, tools=[])

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Hello")],
        "tool_call_count": 0,
        "next": "agent",
    }

    # Config with thread_id for checkpointer

    # Act - Run multiple times
    iterations = 50
    latencies = []

    for i in range(iterations):
        # Use unique thread_id for each iteration to avoid state conflicts
        iter_config = {"configurable": {"thread_id": f"perf-test-percentiles-{i}"}}
        start_time = time.perf_counter()
        await graph.ainvoke(initial_state, config=iter_config)
        end_time = time.perf_counter()
        latencies.append((end_time - start_time) * 1000)

    # Calculate percentiles
    latencies_sorted = sorted(latencies)
    p50 = latencies_sorted[int(len(latencies_sorted) * 0.50)]
    p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
    p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)]

    # Assert
    assert (
        p50 < SIMPLE_QUERY_TARGET_P50
    ), f"p50 latency {p50:.2f}ms exceeds target {SIMPLE_QUERY_TARGET_P50}ms"
    assert p95 < 750, f"p95 latency {p95:.2f}ms exceeds target 750ms"
    assert p99 < 1000, f"p99 latency {p99:.2f}ms exceeds target 1000ms"

    # Log for reporting
    print(
        f"\n✓ Simple query percentiles (n={iterations}): "
        f"p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms"
    )


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_complex_query_latency_p50(mock_slow_llm):
    """Benchmark: Complex query should complete in <1000ms (p50).

    This test measures graph execution for a query that requires tool calling.
    The LLM response is mocked to take 100ms, simulating complex reasoning.

    Target: <1000ms (p50)
    """
    # Arrange - Create a mock tool
    from langchain_core.tools import tool

    @tool
    async def mock_search(query: str) -> str:
        """Mock search tool."""
        await asyncio.sleep(0.05)  # 50ms tool execution
        return f"Results for {query}"

    mock_slow_llm.bind_tools = MagicMock(return_value=mock_slow_llm)

    # Mock LLM to make a tool call
    async def invoke_with_tool(*args, **kwargs):
        await asyncio.sleep(0.1)
        return AIMessage(
            content="",
            tool_calls=[{"name": "mock_search", "args": {"query": "test"}, "id": "1"}],
        )

    mock_slow_llm.ainvoke = AsyncMock(side_effect=invoke_with_tool)

    graph = create_graph(llm=mock_slow_llm, tools=[mock_search])

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Search for project data")],
        "tool_call_count": 0,
        "next": "agent",
    }

    # Config with thread_id for checkpointer
    config = {"configurable": {"thread_id": "perf-test-complex-query"}}

    # Act - Measure execution time
    start_time = time.perf_counter()
    result = await graph.ainvoke(initial_state, config=config)
    end_time = time.perf_counter()

    latency_ms = (end_time - start_time) * 1000

    # Assert
    assert result is not None
    assert "messages" in result

    # Performance assertion
    assert (
        latency_ms < COMPLEX_QUERY_TARGET_P50
    ), f"Complex query latency {latency_ms:.2f}ms exceeds target {COMPLEX_QUERY_TARGET_P50}ms"

    # Log for reporting
    print(
        f"\n✓ Complex query latency: {latency_ms:.2f}ms (target: <{COMPLEX_QUERY_TARGET_P50}ms)"
    )


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_concurrent_requests_scaling(mock_fast_llm):
    """Benchmark: Concurrent requests should scale linearly.

    This test measures how the agent handles concurrent requests.
    We expect near-linear scaling up to a reasonable concurrency level.

    Target: Average latency should not increase by >50% at 10 concurrent requests
    """
    # Arrange
    graph = create_graph(llm=mock_fast_llm, tools=[])

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Hello")],
        "tool_call_count": 0,
        "next": "agent",
    }

    # Config with thread_id for checkpointer
    config = {"configurable": {"thread_id": "perf-test-concurrent"}}

    # Act - Measure single request baseline
    start_time = time.perf_counter()
    await graph.ainvoke(initial_state, config=config)
    single_latency = (time.perf_counter() - start_time) * 1000

    # Measure concurrent requests
    concurrency = 10
    start_time = time.perf_counter()

    tasks = [
        graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": f"perf-test-concurrent-{i}"}}
        )
        for i in range(concurrency)
    ]
    await asyncio.gather(*tasks)

    total_time = (time.perf_counter() - start_time) * 1000
    avg_latency = total_time / concurrency

    # Assert - Check scaling
    # Average latency should not increase by >50%
    scaling_factor = avg_latency / single_latency

    assert (
        scaling_factor < 1.5
    ), f"Scaling factor {scaling_factor:.2f}x exceeds 1.5x target"

    # Log for reporting
    print(
        f"\n✓ Concurrent scaling: {concurrency} requests, "
        f"single={single_latency:.2f}ms, avg={avg_latency:.2f}ms, "
        f"scaling={scaling_factor:.2f}x"
    )


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_memory_usage_simple_query(mock_fast_llm):
    """Benchmark: Measure memory usage for simple query.

    This test ensures memory usage remains reasonable for simple queries.
    While not a strict performance target, excessive memory usage indicates
    potential issues with state management or graph structure.
    """
    import tracemalloc

    # Arrange
    graph = create_graph(llm=mock_fast_llm, tools=[])

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Hello")],
        "tool_call_count": 0,
        "next": "agent",
    }

    # Config with thread_id for checkpointer
    config = {"configurable": {"thread_id": "perf-test-memory"}}

    # Act - Measure memory usage
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    await graph.ainvoke(initial_state, config=config)

    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # Calculate memory difference
    top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
    total_kb = sum(stat.size_diff for stat in top_stats) / 1024

    # Assert - Memory usage should be reasonable (<10MB for simple query)
    assert total_kb < 10000, f"Memory usage {total_kb:.2f}KB exceeds 10MB target"

    # Log for reporting
    print(f"\n✓ Memory usage for simple query: {total_kb:.2f}KB")


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_graph_compilation_overhead(mock_fast_llm):
    """Benchmark: Measure graph compilation overhead.

    Graph compilation should be fast enough to allow frequent recompilation
    if needed (e.g., when tools change). This test measures compilation time.

    Target: <100ms for graph compilation
    """
    # Act - Measure compilation time
    start_time = time.perf_counter()
    create_graph(llm=mock_fast_llm, tools=[])
    compilation_time = (time.perf_counter() - start_time) * 1000

    # Assert - Compilation should be fast
    assert compilation_time < 100, f"Compilation time {compilation_time:.2f}ms exceeds 100ms target"

    # Log for reporting
    print(f"\n✓ Graph compilation overhead: {compilation_time:.2f}ms (target: <100ms)")


# Run benchmarks with pytest:
# pytest tests/performance/ai/test_agent_performance.py -v -m performance
#
# For detailed benchmarking with statistics:
# pytest tests/performance/ai/test_agent_performance.py -v -m performance --benchmark-only
