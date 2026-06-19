"""Regression guard for ``app.ai.middleware.sequential_tool_calls``.

Pins the two behaviors that make tool execution serial:

- ``awrap_model_call`` sets ``parallel_tool_calls=False`` (emission control).
- ``awrap_tool_call`` holds a single shared ``asyncio.Lock`` so concurrent tool
  calls from one assistant message execute one at a time (execution control).

The lock test is the key guard: it FAILS if the lock is removed or made
per-call (no shared serialization), and passes today.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest
from langchain.agents.middleware.types import ModelRequest, ToolCallRequest

from app.ai.middleware.sequential_tool_calls import SequentialToolCallsMiddleware

# Tolerance for scheduler jitter when comparing monotonic timestamps (seconds).
_JITTER = 0.005


def _tool_call_request() -> ToolCallRequest:
    """Minimal ``ToolCallRequest`` (the lock middleware never inspects it)."""
    return ToolCallRequest(
        tool_call={"name": "demo", "args": {}, "id": "call_1", "type": "tool_call"},
        tool=None,
        state={},
        runtime=None,  # type: ignore[arg-type]
    )


def test_middleware_has_shared_asyncio_lock() -> None:
    """A single ``asyncio.Lock`` exists on the instance (not per-call)."""
    mw = SequentialToolCallsMiddleware()
    assert isinstance(mw._lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_awrap_model_call_sets_parallel_tool_calls_false() -> None:
    """``awrap_model_call`` injects ``parallel_tool_calls=False`` before the model runs."""
    mw = SequentialToolCallsMiddleware()

    request = ModelRequest(
        model=object(),  # type: ignore[arg-type]
        messages=[],
        tools=[],
    )

    async def handler(req: ModelRequest[Any]) -> Any:
        return req.model_settings

    await mw.awrap_model_call(request, handler)

    # The load-bearing behavior is the side effect on model_settings before the
    # handler runs (emission control). The handler return type is opaque
    # (ModelResponse | Any), so we assert on the mutated request, not the return.
    assert request.model_settings["parallel_tool_calls"] is False


@pytest.mark.asyncio
async def test_awrap_tool_call_serializes_concurrent_invocations() -> None:
    """Two concurrent ``awrap_tool_call`` invocations must NOT overlap in time.

    With the shared lock, the second call's start lands at or after the first
    call's end. If the lock were removed (or made per-call), both calls would
    run concurrently and their windows would overlap -> this assertion fails.
    """
    mw = SequentialToolCallsMiddleware()

    windows: list[tuple[float, float]] = []

    async def handler(_req: ToolCallRequest) -> Any:
        start = time.monotonic()
        await asyncio.sleep(0.03)  # long enough to detect overlap robustly
        end = time.monotonic()
        windows.append((start, end))
        return None

    await asyncio.gather(
        mw.awrap_tool_call(_tool_call_request(), handler),
        mw.awrap_tool_call(_tool_call_request(), handler),
    )

    assert len(windows) == 2
    (start_a, end_a), (start_b, end_b) = sorted(windows)
    # Second call must start no earlier than the first call's end (within jitter).
    assert start_b >= end_a - _JITTER, (
        f"tool calls overlapped: [{start_a:.4f},{end_a:.4f}) "
        f"vs [{start_b:.4f},{end_b:.4f})"
    )
