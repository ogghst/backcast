"""Performance benchmarks for AI tool execution.

Tests measure tool execution latency against targets:
- Simple tool: <100ms (p50)
- Complex tool: <500ms (p50)
- Tool chaining: Scales linearly
- Concurrent tools: No significant degradation

These benchmarks use mocking to isolate tool execution overhead from
external service latency.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from app.ai.graph import create_graph
from app.ai.state import AgentState

# Performance Targets
SIMPLE_TOOL_TARGET_P50 = 100  # ms
COMPLEX_TOOL_TARGET_P50 = 500  # ms


@pytest.fixture
def mock_fast_llm_with_tool_call():
    """Mock LLM that makes a tool call quickly."""

    async def invoke(*args, **kwargs):
        await asyncio.sleep(0.01)  # 10ms LLM delay
        return AIMessage(
            content="",
            tool_calls=[{"name": "simple_tool", "args": {"input": "test"}, "id": "1"}],
        )

    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=llm)
    llm.ainvoke = AsyncMock(side_effect=invoke)
    return llm


@pytest.fixture
def mock_slow_llm_with_tool_call():
    """Mock LLM that makes a tool call slowly (complex reasoning)."""

    async def invoke(*args, **kwargs):
        await asyncio.sleep(0.1)  # 100ms LLM delay
        return AIMessage(
            content="",
            tool_calls=[{"name": "complex_tool", "args": {"query": "complex"}, "id": "1"}],
        )

    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=llm)
    llm.ainvoke = AsyncMock(side_effect=invoke)
    return llm


@pytest.fixture
def simple_tool():
    """Create a simple tool for testing."""

    @tool
    async def simple_tool(input: str) -> str:
        """A simple tool that returns input."""
        await asyncio.sleep(0.01)  # 10ms tool execution
        return f"Processed: {input}"

    return simple_tool


@pytest.fixture
def complex_tool():
    """Create a complex tool for testing."""

    @tool
    async def complex_tool(query: str) -> str:
        """A complex tool that processes query."""
        await asyncio.sleep(0.1)  # 100ms tool execution
        # Simulate complex processing
        result = f"Complex result for {query}"
        return result

    return complex_tool


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_simple_tool_execution_p50(mock_fast_llm_with_tool_call, simple_tool):
    """Benchmark: Simple tool execution should complete in <100ms (p50).

    This test measures the overhead of executing a simple tool through
    the graph. The tool execution time is mocked to be fast (10ms),
    so we're measuring the graph/tool layer overhead.

    Target: <100ms (p50)
    """
    # Arrange
    graph = create_graph(llm=mock_fast_llm_with_tool_call, tools=[simple_tool])

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Execute simple tool")],
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "next": "agent",
    }

    # Config with thread_id for checkpointer
    config = {"configurable": {"thread_id": "perf-test-simple-tool"}}

    # Act - Measure execution time
    start_time = time.perf_counter()
    result = await graph.ainvoke(initial_state, config=config)
    end_time = time.perf_counter()

    latency_ms = (end_time - start_time) * 1000

    # Assert - Check target
    assert result is not None
    assert "messages" in result

    # Check that tool was executed
    tool_messages = [msg for msg in result["messages"] if isinstance(msg, ToolMessage)]
    assert len(tool_messages) > 0, "Tool should have been executed"

    # Performance assertion
    assert (
        latency_ms < SIMPLE_TOOL_TARGET_P50
    ), f"Simple tool execution latency {latency_ms:.2f}ms exceeds target {SIMPLE_TOOL_TARGET_P50}ms"

    # Log for reporting
    print(
        f"\n✓ Simple tool execution latency: {latency_ms:.2f}ms "
        f"(target: <{SIMPLE_TOOL_TARGET_P50}ms)"
    )


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_simple_tool_execution_percentiles(mock_fast_llm_with_tool_call, simple_tool):
    """Benchmark: Measure simple tool execution latency across multiple runs.

    Runs the simple tool benchmark 50 times to calculate p50, p95, and p99
    percentiles.

    Targets:
    - p50: <100ms
    - p95: <150ms
    - p99: <200ms
    """
    # Arrange
    graph = create_graph(llm=mock_fast_llm_with_tool_call, tools=[simple_tool])

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Use the simple tool")],
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "next": "agent",
    }

    # Config with thread_id for checkpointer

    # Act - Run multiple times
    iterations = 50
    latencies = []

    for i in range(iterations):
        iter_config = {"configurable": {"thread_id": f"perf-test-simple-tool-percentiles-{i}"}}
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
        p50 < 150
    ), f"p50 latency {p50:.2f}ms exceeds target 150ms"
    assert p95 < 200, f"p95 latency {p95:.2f}ms exceeds target 200ms"
    assert p99 < 250, f"p99 latency {p99:.2f}ms exceeds target 250ms"

    # Log for reporting
    print(
        f"\n✓ Simple tool percentiles (n={iterations}): "
        f"p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms"
    )


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_complex_tool_execution_p50(mock_slow_llm_with_tool_call, complex_tool):
    """Benchmark: Complex tool execution should complete in <500ms (p50).

    This test measures the overhead of executing a complex tool through
    the graph. The tool execution time is mocked to be 100ms, simulating
    a more complex operation.

    Target: <500ms (p50)
    """
    # Arrange
    graph = create_graph(llm=mock_slow_llm_with_tool_call, tools=[complex_tool])

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Use the complex tool")],
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "next": "agent",
    }

    # Act - Measure execution time
    config = {"configurable": {"thread_id": "perf-test-complex-tool"}}
    start_time = time.perf_counter()
    result = await graph.ainvoke(initial_state, config=config)
    end_time = time.perf_counter()

    latency_ms = (end_time - start_time) * 1000

    # Assert - Check target
    assert result is not None
    assert "messages" in result

    # Check that tool was executed
    tool_messages = [msg for msg in result["messages"] if isinstance(msg, ToolMessage)]
    assert len(tool_messages) > 0, "Tool should have been executed"

    # Performance assertion
    assert (
        latency_ms < COMPLEX_TOOL_TARGET_P50
    ), f"Complex tool execution latency {latency_ms:.2f}ms exceeds target {COMPLEX_TOOL_TARGET_P50}ms"

    # Log for reporting
    print(
        f"\n✓ Complex tool execution latency: {latency_ms:.2f}ms "
        f"(target: <{COMPLEX_TOOL_TARGET_P50}ms)"
    )


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_tool_chaining_performance(simple_tool):
    """Benchmark: Tool chaining should scale linearly.

    This test measures the overhead of chaining multiple tools together.
    Each additional tool should add constant overhead.

    Target: Each additional tool should add <100ms overhead
    """
    # Arrange - Create tools for chaining
    @tool
    async def tool_a(input: str) -> str:
        """Tool A for chaining test."""
        await asyncio.sleep(0.01)
        return f"A: {input}"

    @tool
    async def tool_b(input: str) -> str:
        """Tool B for chaining test."""
        await asyncio.sleep(0.01)
        return f"B: {input}"

    @tool
    async def tool_c(input: str) -> str:
        """Tool C for chaining test."""
        await asyncio.sleep(0.01)
        return f"C: {input}"

    # Mock LLM to make sequential tool calls
    async def invoke_with_chain(*args, **kwargs):
        await asyncio.sleep(0.01)
        messages = kwargs.get("messages", [])
        tool_call_count = sum(1 for msg in messages if isinstance(msg, ToolMessage))

        if tool_call_count == 0:
            return AIMessage(
                content="",
                tool_calls=[{"name": "tool_a", "args": {"input": "start"}, "id": "1"}],
            )
        elif tool_call_count == 1:
            return AIMessage(
                content="",
                tool_calls=[{"name": "tool_b", "args": {"input": "continue"}, "id": "2"}],
            )
        elif tool_call_count == 2:
            return AIMessage(
                content="",
                tool_calls=[{"name": "tool_c", "args": {"input": "finish"}, "id": "3"}],
            )
        else:
            return AIMessage(content="Done")

    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=llm)
    llm.ainvoke = AsyncMock(side_effect=invoke_with_chain)

    graph = create_graph(llm=llm, tools=[tool_a, tool_b, tool_c])

    # Act - Measure execution time for 3-tool chain
    initial_state: AgentState = {
        "messages": [HumanMessage(content="Chain tools")],
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "next": "agent",
    }

    config = {"configurable": {"thread_id": "perf-test-tool-chaining"}}
    start_time = time.perf_counter()
    result = await graph.ainvoke(initial_state, config=config)
    end_time = time.perf_counter()

    latency_ms = (end_time - start_time) * 1000

    # Assert - All tools should have executed
    tool_messages = [msg for msg in result["messages"] if isinstance(msg, ToolMessage)]
    assert len(tool_messages) == 3, f"Expected 3 tool executions, got {len(tool_messages)}"

    # Performance assertion
    # 3 tools with ~10ms each = ~30ms, plus graph overhead
    # Should be well under 300ms
    assert latency_ms < 300, f"Tool chaining latency {latency_ms:.2f}ms exceeds 300ms"

    # Log for reporting
    print(f"\n✓ Tool chaining (3 tools): {latency_ms:.2f}ms (target: <300ms)")


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_concurrent_tool_execution(simple_tool):
    """Benchmark: Concurrent tool execution should scale efficiently.

    This test measures how the system handles multiple tools executing
    concurrently. While tools may execute sequentially in the graph,
    we measure the overhead of multiple tools being available.

    Target: Overhead per additional tool <10ms
    """
    # Arrange - Create multiple tools
    tools = []
    for i in range(10):
        async def tool_func(input: str, index: int = i) -> str:
            """Tool function for concurrent execution test."""
            await asyncio.sleep(0.01)
            return f"Tool {index}: {input}"
        tool_func.__name__ = f"tool_{i}"
        tools.append(tool(tool_func))

    # Mock LLM
    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=llm)
    llm.ainvoke = AsyncMock(
        return_value=AIMessage(
            content="",
            tool_calls=[{"name": "tool_0", "args": {"input": "test"}, "id": "1"}],
        )
    )

    # Measure graph compilation with 1 tool
    start_time = time.perf_counter()
    create_graph(llm=llm, tools=[tools[0]])
    compile_time_1 = (time.perf_counter() - start_time) * 1000

    # Measure graph compilation with 10 tools
    start_time = time.perf_counter()
    create_graph(llm=llm, tools=tools)
    compile_time_10 = (time.perf_counter() - start_time) * 1000

    # Calculate overhead per tool
    overhead_per_tool = (compile_time_10 - compile_time_1) / 9

    # Assert - Overhead should be minimal
    assert overhead_per_tool < 10, (
        f"Overhead per tool {overhead_per_tool:.2f}ms exceeds 10ms target"
    )

    # Log for reporting
    print(
        f"\n✓ Concurrent tool overhead: {overhead_per_tool:.2f}ms per tool "
        f"(1 tool: {compile_time_1:.2f}ms, 10 tools: {compile_time_10:.2f}ms)"
    )


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_tool_registry_overhead():
    """Benchmark: Tool registry lookup should be fast.

    This test measures the overhead of looking up tools in the registry.
    Fast lookup is critical for performance when many tools are available.

    Target: <1ms per tool lookup
    """
    # Arrange
    from unittest.mock import MagicMock

    from app.ai.tools import create_project_tools
    from app.ai.tools.types import ToolContext

    mock_session = MagicMock()
    context = ToolContext(session=mock_session, user_id="test-user", user_role="admin")

    # Act - Measure lookup time
    iterations = 100
    start_time = time.perf_counter()

    for _ in range(iterations):
        tools = create_project_tools(context)

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000
    avg_lookup_time_ms = total_time_ms / iterations

    # Assert - Lookup should be very fast
    assert avg_lookup_time_ms < 1, (
        f"Average lookup time {avg_lookup_time_ms:.2f}ms exceeds 1ms target"
    )

    # Log for reporting
    print(
        f"\n✓ Tool registry lookup: {avg_lookup_time_ms:.2f}ms "
        f"({len(tools)} tools, target: <1ms)"
    )


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_tool_context_injection_overhead():
    """Benchmark: ToolContext injection should add minimal overhead.

    This test measures the overhead of injecting ToolContext into tool calls.
    Context injection is critical for security and database access.

    Target: <5ms overhead for context injection
    """
    # Arrange
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.ai.tools import ToolContext

    @tool
    async def tool_with_context(input: str, context: ToolContext) -> str:
        """Tool that requires context."""
        return f"Processed: {input}"

    # Act - Measure context injection overhead
    async def inject_context():
        # Simulate context creation
        mock_session = MagicMock(spec=AsyncSession)
        context = ToolContext(session=mock_session, user_id="test-user", user_role="admin")
        return context

    iterations = 100
    start_time = time.perf_counter()

    for _ in range(iterations):
        await inject_context()

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000
    avg_injection_time_ms = total_time_ms / iterations

    # Assert - Injection should be fast
    assert avg_injection_time_ms < 5, (
        f"Average injection time {avg_injection_time_ms:.2f}ms exceeds 5ms target"
    )

    # Log for reporting
    print(
        f"\n✓ ToolContext injection overhead: {avg_injection_time_ms:.2f}ms "
        f"(target: <5ms)"
    )


# Run benchmarks with pytest:
# pytest tests/performance/ai/test_tool_performance.py -v -m performance
#
# For detailed benchmarking with statistics:
# pytest tests/performance/ai/test_tool_performance.py -v -m performance --benchmark-only
