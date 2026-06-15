"""Tests for ``app.ai.middleware.context_guard``.

Covers:

- ``_tool_aware_tail_start``: tool-call-aware tail boundary so the trim never
  splits an in-flight ``assistant tool_calls -> tool response`` pair.
- ``_repair_chain``: residual-drop WARNING observability.
- ``ContextGuardMiddleware.awrap_model_call``: the integration path that used
  to silently drop a tool response when the naive boundary split a pair.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain.agents.middleware.types import ModelRequest
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.ai import middleware as middleware_pkg  # noqa: F401  (for monkeypatch path)
from app.ai.middleware import context_guard
from app.ai.middleware.context_guard import (
    ContextGuardMiddleware,
    _repair_chain,
    _tool_aware_tail_start,
)

# Keep these imports last so the ``app.ai.middleware`` package alias above is
# unambiguous; ruff sorts them at format time.


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _ai_call(call_ids: list[str], content: str = "") -> AIMessage:
    """Build an AIMessage with the given tool_call ids (and optional content)."""
    return AIMessage(
        content=content,
        tool_calls=[{"name": "t", "args": {}, "id": cid} for cid in call_ids],
    )


def _tool(call_id: str, content: str = "result") -> ToolMessage:
    return ToolMessage(content=content, tool_call_id=call_id)


def _human(text: str = "filler") -> HumanMessage:
    return HumanMessage(content=text)


# --------------------------------------------------------------------------- #
# Part A: _tool_aware_tail_start
# --------------------------------------------------------------------------- #


def test_tail_start_backs_up_to_caller_when_split_lands_on_tool_response() -> None:
    """Naive split on a tool message backs up to its issuing assistant.

    Layout: caller (AIMessage X) at index 3, ToolMessage(X) at index 4.  With
    ``len == 9`` and ``keep == 5`` the naive start ``9 - 5 == 4`` lands on the
    tool message -> helper must back up to the caller at index 3.
    """
    msgs: list[AnyMessage] = [
        SystemMessage(content="system"),  # 0
        _human("f1"),  # 1
        _human("f2"),  # 2
        _ai_call(["X"]),  # 3 (caller)
        _tool("X"),  # 4 == naive start (9 - 5)
        _human("t1"),  # 5
        _human("t2"),  # 6
        _human("t3"),  # 7
        _human("t4"),  # 8
    ]
    assert len(msgs) == 9 and len(msgs) - 5 == 4  # setup invariant
    start = _tool_aware_tail_start(msgs, keep=5)
    assert start == 3, "split must back up to the caller at index 3"


def test_tail_start_backs_up_past_multi_response_group() -> None:
    """Multi-response group: backing up to the caller pulls in earlier responses too.

    Layout: caller (AIMessage X,Y) at index 2; ToolMessage(X) at 3;
    ToolMessage(Y) at 4.  With ``len == 8`` and ``keep == 4`` the naive start
    ``8 - 4 == 4`` lands on ToolMessage(Y) -> helper backs up to caller 2,
    pulling ToolMessage(X) into the tail as well.
    """
    msgs: list[AnyMessage] = [
        SystemMessage(content="system"),  # 0
        _human("f1"),  # 1
        _ai_call(["X", "Y"]),  # 2 (caller)
        _tool("X"),  # 3
        _tool("Y"),  # 4 == naive start (8 - 4)
        _human("t1"),  # 5
        _human("t2"),  # 6
        _human("t3"),  # 7
    ]
    assert len(msgs) == 8 and len(msgs) - 4 == 4  # setup invariant
    start = _tool_aware_tail_start(msgs, keep=4)
    assert start == 2, "split must back up to the caller (pulls in X and Y)"


def test_tail_start_caller_is_system_message_does_not_back_up_below_one() -> None:
    """Caller is messages[0] (system) -> no useful caller to pull; floor at 1.

    ToolMessage(X) at index 1; its only possible caller is the system message
    at index 0, which is excluded from the search (it survives the trim
    intact).  Naive start ``len - keep == 1``; helper must not back up below 1.
    """
    msgs: list[AnyMessage] = [
        SystemMessage(content="system"),  # 0
        _tool("X"),  # 1 == naive start (5 - 4)
        _human("t1"),  # 2
        _human("t2"),  # 3
        _human("t3"),  # 4
    ]
    assert len(msgs) == 5 and len(msgs) - 4 == 1  # setup invariant
    start = _tool_aware_tail_start(msgs, keep=4)
    assert start == 1, "must not back up below index 1 (system prompt stays)"


def test_tail_start_unchanged_when_not_on_tool_message() -> None:
    """Naive start already on a non-tool message -> returned unchanged.

    Layout: HumanMessage at index 2; naive start ``6 - 4 == 2`` lands on it.
    """
    msgs: list[AnyMessage] = [
        SystemMessage(content="system"),  # 0
        _human("f1"),  # 1
        _human("f2"),  # 2 == naive start (6 - 4)
        _human("t1"),  # 3
        _human("t2"),  # 4
        _human("t3"),  # 5
    ]
    assert len(msgs) == 6 and len(msgs) - 4 == 2  # setup invariant
    start = _tool_aware_tail_start(msgs, keep=4)
    assert start == 2


# --------------------------------------------------------------------------- #
# Part B: _repair_chain WARNING observability
# --------------------------------------------------------------------------- #


def test_repair_chain_warns_on_dropped_orphaned_tool_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An orphaned tool response is dropped AND a WARNING logs its tool_call_id."""
    msgs: list[AnyMessage] = [
        SystemMessage(content="system"),
        _human("hi"),
        _tool("ORPHAN"),  # no preceding assistant with tool_calls
        _human("bye"),
    ]
    with caplog.at_level("WARNING", logger=context_guard.logger.name):
        out = _repair_chain(msgs)
    # dropped
    assert not any(getattr(m, "tool_call_id", None) == "ORPHAN" for m in out)
    # warned
    assert any(
        "ORPHAN" in rec.getMessage() and rec.levelname == "WARNING"
        for rec in caplog.records
    ), [r.getMessage() for r in caplog.records]


def test_repair_chain_warns_on_dropped_assistant_with_orphaned_tool_calls(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An assistant whose tool_calls are all orphaned AND content empty is dropped + warned."""
    msgs: list[AnyMessage] = [
        SystemMessage(content="system"),
        _human("hi"),
        _ai_call(["NO_RESP"]),  # empty content, response missing -> dropped
        _human("bye"),
    ]
    with caplog.at_level("WARNING", logger=context_guard.logger.name):
        out = _repair_chain(msgs)
    # dropped (no AIMessage with that call id)
    assert not any(
        getattr(m, "tool_calls", None)
        and any(
            (c.get("id") if isinstance(c, dict) else getattr(c, "id", None))
            == "NO_RESP"
            for c in m.tool_calls
        )
        for m in out
    )
    # warned with the dropped id
    assert any(
        "NO_RESP" in rec.getMessage() and rec.levelname == "WARNING"
        for rec in caplog.records
    ), [r.getMessage() for r in caplog.records]


def test_repair_chain_no_warning_on_clean_chain(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An intact call/response pair emits no WARNING (guards against log spam)."""
    msgs: list[AnyMessage] = [
        SystemMessage(content="system"),
        _ai_call(["OK"]),
        _tool("OK"),
        _human("thanks"),
    ]
    with caplog.at_level("WARNING", logger=context_guard.logger.name):
        _repair_chain(msgs)
    assert not [rec for rec in caplog.records if rec.levelname == "WARNING"], [
        r.getMessage() for r in caplog.records
    ]


# --------------------------------------------------------------------------- #
# Integration: ContextGuardMiddleware awrap_model_call
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_middleware_trim_preserves_tool_call_response_pair() -> None:
    """The bug: naive trim splits AIMessage(tool_calls=[X]) -> ToolMessage(X).

    After the fix, BOTH the assistant (with call X) and the tool response
    survive in the trimmed result.
    """
    keep = context_guard.AI_CONTEXT_KEEP_RECENT  # 8
    # Build a list long enough to trim where naive split lands on the tool msg.
    msgs: list[AnyMessage] = [
        SystemMessage(content="system"),
        *(_human() for _ in range(keep)),  # filler before the caller
        _ai_call(["X"]),  # caller just before the naive split
        _tool("X"),  # response at the naive split (len - keep)
        *(_human() for _ in range(keep - 1)),  # tail fillers
    ]
    # naive start = len - keep should equal the index of the ToolMessage("X").
    naive_start = len(msgs) - keep
    assert getattr(msgs[naive_start], "type", None) == "tool", "test setup invariant"

    # Force the trim path regardless of token estimate.
    monkeypatched_threshold = context_guard.AI_CONTEXT_TOKEN_LIMIT
    monkeypatched_est: int = monkeypatched_threshold * 2  # well above threshold

    captured: dict[str, Any] = {}

    async def handler(req: ModelRequest[Any]) -> Any:
        captured["messages"] = list(req.messages)
        return req.messages

    request = ModelRequest(
        model=MagicMock(),
        messages=msgs,
        system_message=SystemMessage(content="system"),
        tools=[],
        state={"briefing_data": {}},
    )

    mw = ContextGuardMiddleware()

    # Patch the token estimator used inside the module to force trimming.
    original_est = context_guard._estimate_tokens
    context_guard._estimate_tokens = lambda _m: monkeypatched_est  # type: ignore[assignment]
    try:
        await mw.awrap_model_call(request, handler)
    finally:
        context_guard._estimate_tokens = original_est  # type: ignore[assignment]

    trimmed = captured["messages"]

    # The assistant carrying tool_call X must survive.
    assert any(
        getattr(m, "tool_calls", None)
        and any(
            (c.get("id") if isinstance(c, dict) else getattr(c, "id", None)) == "X"
            for c in m.tool_calls
        )
        for m in trimmed
    ), "assistant with tool_call X must survive the trim"

    # The tool response X must survive.
    assert any(getattr(m, "tool_call_id", None) == "X" for m in trimmed), (
        "tool response X must survive the trim (the actual bug being fixed)"
    )
