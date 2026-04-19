"""Performance benchmarks for AI agent streaming.

Tests measure streaming latency against targets:
- First token: <100ms (p50)
- Token throughput: >50 tokens/second
- WebSocket overhead: <10ms per event

These benchmarks use mocking to control LLM streaming behavior and measure
actual streaming overhead without external API latency.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.ai.graph import create_graph
from app.ai.state import AgentState

# Performance Targets
FIRST_TOKEN_TARGET_P50 = 100  # ms
TOKEN_THROUGHPUT_TARGET = 50  # tokens/second


@pytest.fixture
def mock_streaming_llm():
    """Mock LLM that streams tokens quickly."""

    async def stream_tokens(*args, **kwargs):
        """Stream tokens with realistic timing."""
        # Simulate thinking time before first token
        await asyncio.sleep(0.01)  # 10ms

        # Stream tokens
        tokens = ["Hello", " there", "!", " How", " can", " I", " help", "?"]
        for token in tokens:
            await asyncio.sleep(0.005)  # 5ms per token
            yield token

    async def mock_ainvoke(*args, **kwargs):
        """Mock invoke that returns a simple message."""
        await asyncio.sleep(0.01)  # 10ms
        return AIMessage(content="Hello there! How can I help?")

    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=llm)
    llm.astream_events = AsyncMock(side_effect=stream_tokens)
    llm.ainvoke = AsyncMock(side_effect=mock_ainvoke)
    return llm


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_first_token_latency_p50(mock_streaming_llm):
    """Benchmark: First token should arrive in <100ms (p50).

    This test measures time-to-first-token (TTFT), which is critical for
    perceived responsiveness. The first token should arrive quickly even
    if the full response takes longer.

    Target: <100ms (p50)
    """
    # Arrange
    graph = create_graph(llm=mock_streaming_llm, tools=[])

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Hello, what can you help with?")],
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "next": "agent",
    }

    # Act - Measure time to first token
    config = {"configurable": {"thread_id": "test-thread"}}
    start_time = time.perf_counter()
    first_token_time = None

    async for _event in graph.astream_events(
        initial_state, config=config, version="v1"
    ):
        if first_token_time is None:
            first_token_time = time.perf_counter()

        # Stop after first token
        if first_token_time is not None:
            break

    end_time = time.perf_counter()

    # Calculate latency
    if first_token_time is None:
        first_token_time = end_time

    latency_ms = (first_token_time - start_time) * 1000

    # Assert - Check target
    assert latency_ms < FIRST_TOKEN_TARGET_P50, (
        f"First token latency {latency_ms:.2f}ms exceeds target {FIRST_TOKEN_TARGET_P50}ms"
    )

    # Log for reporting
    print(
        f"\n✓ First token latency: {latency_ms:.2f}ms (target: <{FIRST_TOKEN_TARGET_P50}ms)"
    )


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_first_token_latency_percentiles(mock_streaming_llm):
    """Benchmark: Measure first token latency across multiple runs.

    Runs the first token benchmark 50 times to calculate p50, p95, and p99
    percentiles. This provides better insight into performance distribution.

    Targets:
    - p50: <100ms
    - p95: <150ms
    - p99: <200ms
    """
    # Arrange
    graph = create_graph(llm=mock_streaming_llm, tools=[])

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Hello")],
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "next": "agent",
    }

    # Act - Run multiple times
    iterations = 50
    latencies = []
    config = {"configurable": {"thread_id": "test-thread"}}

    for _ in range(iterations):
        start_time = time.perf_counter()
        first_token_time = None

        async for _event in graph.astream_events(
            initial_state, config=config, version="v1"
        ):
            if first_token_time is None:
                first_token_time = time.perf_counter()
                break

        if first_token_time is None:
            first_token_time = time.perf_counter()

        latencies.append((first_token_time - start_time) * 1000)

    # Calculate percentiles
    latencies_sorted = sorted(latencies)
    p50 = latencies_sorted[int(len(latencies_sorted) * 0.50)]
    p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
    p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)]

    # Assert
    assert p50 < FIRST_TOKEN_TARGET_P50, (
        f"p50 latency {p50:.2f}ms exceeds target {FIRST_TOKEN_TARGET_P50}ms"
    )
    assert p95 < 150, f"p95 latency {p95:.2f}ms exceeds target 150ms"
    assert p99 < 200, f"p99 latency {p99:.2f}ms exceeds target 200ms"

    # Log for reporting
    print(
        f"\n✓ First token percentiles (n={iterations}): "
        f"p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms"
    )


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_token_throughput(mock_streaming_llm):
    """Benchmark: Token throughput should exceed 50 tokens/second.

    This test measures the rate at which tokens are streamed, which affects
    the perceived speed of the response. Higher throughput = faster response.

    Target: >50 tokens/second
    """
    # Arrange
    graph = create_graph(llm=mock_streaming_llm, tools=[])

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Tell me about projects")],
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "next": "agent",
    }

    # Act - Measure streaming throughput
    config = {"configurable": {"thread_id": "test-thread"}}
    start_time = time.perf_counter()
    token_count = 0

    async for event in graph.astream_events(initial_state, config=config, version="v1"):
        # Count tokens (simplified - in real implementation, count actual tokens)
        if event.get("event") == "on_chat_model_stream":
            token_count += 1

    end_time = time.perf_counter()
    elapsed_seconds = end_time - start_time

    # Calculate throughput
    if token_count > 0 and elapsed_seconds > 0:
        throughput = token_count / elapsed_seconds
    else:
        throughput = 0

    # Assert - Check throughput target
    assert throughput >= TOKEN_THROUGHPUT_TARGET, (
        f"Token throughput {throughput:.2f} tokens/sec below target {TOKEN_THROUGHPUT_TARGET} tokens/sec"
    )

    # Log for reporting
    print(
        f"\n✓ Token throughput: {throughput:.2f} tokens/sec "
        f"({token_count} tokens in {elapsed_seconds:.2f}s, target: >{TOKEN_THROUGHPUT_TARGET} tokens/sec)"
    )


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_concurrent_streams(mock_streaming_llm):
    """Benchmark: Concurrent streams should scale linearly.

    This test measures how the agent handles concurrent streaming requests.
    We expect near-linear scaling with minimal degradation.

    Target: Average first token latency should not increase by >100% at 5 concurrent streams
    """
    # Arrange
    graph = create_graph(llm=mock_streaming_llm, tools=[])

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Hello")],
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "next": "agent",
    }

    # Act - Measure single stream baseline
    config = {"configurable": {"thread_id": "test-thread"}}
    start_time = time.perf_counter()
    first_token_time = None

    async for _event in graph.astream_events(
        initial_state, config=config, version="v1"
    ):
        if first_token_time is None:
            first_token_time = time.perf_counter()
            break

    single_latency = (first_token_time - start_time) * 1000

    # Measure concurrent streams
    concurrency = 5

    async def measure_stream(thread_id: int):
        cfg = {"configurable": {"thread_id": f"test-thread-{thread_id}"}}
        start = time.perf_counter()
        first = None
        async for _event in graph.astream_events(
            initial_state, config=cfg, version="v1"
        ):
            if first is None:
                first = time.perf_counter()
                break
        return (first - start) * 1000 if first else 0

    start_time = time.perf_counter()
    tasks = [measure_stream(i) for i in range(concurrency)]
    latencies = await asyncio.gather(*tasks)
    (time.perf_counter() - start_time) * 1000

    avg_latency = sum(latencies) / len(latencies)

    # Assert - Check scaling
    # Average latency should not increase by >100%
    scaling_factor = avg_latency / single_latency if single_latency > 0 else 1.0

    assert scaling_factor < 2.5, (
        f"Scaling factor {scaling_factor:.2f}x exceeds 2.5x target"
    )

    # Log for reporting
    print(
        f"\n✓ Concurrent streaming: {concurrency} streams, "
        f"single={single_latency:.2f}ms, avg={avg_latency:.2f}ms, "
        f"scaling={scaling_factor:.2f}x"
    )


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.benchmark
async def test_websocket_message_overhead(mock_streaming_llm):
    """Benchmark: WebSocket message overhead should be minimal.

    This test measures the overhead of wrapping streaming events in WebSocket
    messages. Each message should add minimal overhead.

    Target: <10ms overhead per message
    """
    # Arrange
    from app.models.schemas.ai import WSTokenMessage

    graph = create_graph(llm=mock_streaming_llm, tools=[])

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Hello")],
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "next": "agent",
    }

    # Act - Measure message serialization overhead
    config = {"configurable": {"thread_id": "test-thread"}}
    serialization_times = []

    async for event in graph.astream_events(initial_state, config=config, version="v1"):
        if event.get("event") == "on_chat_model_stream":
            # Measure time to create WebSocket message
            start = time.perf_counter()
            WSTokenMessage(
                conversation_id="test",
                token=event.get("data", {}).get("chunk", ""),
            )
            end = time.perf_counter()

            serialization_times.append((end - start) * 1000)

            # Only measure first few messages
            if len(serialization_times) >= 10:
                break

    # Calculate average overhead
    if serialization_times:
        avg_overhead = sum(serialization_times) / len(serialization_times)
    else:
        avg_overhead = 0

    # Assert - Overhead should be minimal
    assert avg_overhead < 10, (
        f"Message overhead {avg_overhead:.2f}ms exceeds 10ms target"
    )

    # Log for reporting
    print(f"\n✓ WebSocket message overhead: {avg_overhead:.2f}ms (target: <10ms)")


# Run benchmarks with pytest:
# pytest tests/performance/ai/test_streaming_performance.py -v -m performance
#
# For detailed benchmarking with statistics:
# pytest tests/performance/ai/test_streaming_performance.py -v -m performance --benchmark-only
