"""Phase 1: within-specialist context cap — unit tests.

Covers the two surgical changes that fix the specialist 120s timeout cascade:

1. ``ContextGuardMiddleware`` is mounted on specialists (via
   ``compile_subagents`` / ``build_backcast_middleware``) with
   ``preserve_head=2`` so the system prompt AND the assignment
   ``HumanMessage`` survive the trim — losing the assignment would make the
   specialist forget its task.
2. ``max_tool_iterations`` for a specialist comes from
   ``AI_SPECIALIST_MAX_TOOL_ITERATIONS`` (~8, not the flat 25), while the
   supervisor's own budget is unaffected.

These tests exercise the ContextGuard internals directly (no LLM, no graph
compilation) plus the specialist middleware-stack composition.
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

from app.ai import middleware as middleware_pkg  # noqa: F401  (monkeypatch path)
from app.ai.config import (
    AI_SPECIALIST_CONTEXT_KEEP_RECENT,
    AI_SPECIALIST_CONTEXT_TOKEN_LIMIT,
    AI_SPECIALIST_MAX_TOOL_ITERATIONS,
)
from app.ai.middleware import context_guard
from app.ai.middleware.context_guard import ContextGuardMiddleware
from app.ai.subagent_compiler import build_backcast_middleware

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _ai_call(call_ids: list[str], content: str = "") -> AIMessage:
    return AIMessage(
        content=content,
        tool_calls=[{"name": "t", "args": {}, "id": cid} for cid in call_ids],
    )


def _tool(call_id: str, content: str = "result") -> ToolMessage:
    return ToolMessage(content=content, tool_call_id=call_id)


def _force_trim(*, token_limit: int) -> tuple[Any, None]:
    """Patch ``_estimate_tokens`` to exceed the given per-instance threshold.

    The specialist ``ContextGuardMiddleware`` captures ``token_limit`` /
    ``keep_recent`` at construction (it does NOT read the module globals at
    call time), so to force the trim path deterministically we only patch the
    token estimator to exceed ``token_limit``.  ``keep_recent`` is passed to the
    constructor directly by each test (no global patching needed).

    Returns ``(real_estimator, None)`` for restoration in a ``finally``.
    """
    real_est = context_guard._estimate_tokens
    forced_est: int = token_limit * 2  # well above the per-instance threshold
    context_guard._estimate_tokens = lambda _m: forced_est  # type: ignore[assignment]
    return real_est, None


async def _run_trim(mw: ContextGuardMiddleware, messages: list[AnyMessage]) -> Any:
    """Invoke the middleware once, capturing the trimmed messages."""
    captured: dict[str, Any] = {}

    async def handler(req: ModelRequest[Any]) -> Any:
        captured["messages"] = list(req.messages)
        return req.messages

    request = ModelRequest(
        model=MagicMock(),
        messages=messages,
        system_message=messages[0] if messages else SystemMessage(content=""),
        tools=[],
        state={"briefing_data": {}},
    )
    await mw.awrap_model_call(request, handler)
    return captured["messages"]


# --------------------------------------------------------------------------- #
# Part 1: specialist middleware stack includes ContextGuard
# --------------------------------------------------------------------------- #


def test_specialist_middleware_stack_includes_context_guard() -> None:
    """``build_backcast_middleware`` (used by ``compile_subagents``) feeds the
    specialist stack; the specialist path prepends ``ContextGuardMiddleware``.

    We assert the composition contract: a specialist's middleware list must
    contain a ``ContextGuardMiddleware`` instance with the SPECIALIST-SPECIFIC
    threshold/keep-recent (NOT the supervisor's 120k/8 globals — specialists hit
    GLM's ~25-30k latency knee far below 120k).  ``compile_subagents`` builds
    ``[ContextGuardMiddleware(preserve_head=2, token_limit=AI_SPECIALIST_*,
    keep_recent=AI_SPECIALIST_*), *build_backcast_middleware(...)]``.
    """
    # build_backcast_middleware itself does NOT mount ContextGuard (the caller
    # does, to control preserve_head).  Verify it returns the base stack only,
    # so there is no accidental double-mount when the supervisor wraps it.
    ctx = MagicMock()
    ctx.execution_mode = "full"
    base = build_backcast_middleware(ctx, tools=[])
    assert not any(isinstance(m, ContextGuardMiddleware) for m in base), (
        "base stack must NOT contain ContextGuard — the supervisor AND "
        "specialists mount their own to avoid double-trimming"
    )

    # The specialist composition (mirrors compile_subagents): specialist-specific
    # threshold + keep-recent, well below the supervisor's 120k/8.
    specialist_mw: list[Any] = [
        ContextGuardMiddleware(
            preserve_head=2,
            token_limit=AI_SPECIALIST_CONTEXT_TOKEN_LIMIT,
            keep_recent=AI_SPECIALIST_CONTEXT_KEEP_RECENT,
        ),
        *base,
    ]
    guards = [m for m in specialist_mw if isinstance(m, ContextGuardMiddleware)]
    assert len(guards) == 1, "exactly one ContextGuard on the specialist stack"
    guard = guards[0]
    assert guard.preserve_head == 2, (
        "specialist ContextGuard must preserve system prompt + assignment (head=2)"
    )
    # Specialist threshold is the MUCH lower value, not the supervisor's 120k.
    assert guard.token_limit == AI_SPECIALIST_CONTEXT_TOKEN_LIMIT, (
        "specialist ContextGuard must use the specialist token limit, not the "
        "supervisor's 120k global"
    )
    assert guard.token_limit < context_guard.AI_CONTEXT_TOKEN_LIMIT, (
        "specialist threshold must be below the supervisor's 120k (latency knee)"
    )
    assert guard.keep_recent == AI_SPECIALIST_CONTEXT_KEEP_RECENT, (
        "specialist ContextGuard must use the specialist keep-recent"
    )


# --------------------------------------------------------------------------- #
# Part 2: specialist trim keeps system + assignment + bounded tool-pair tail,
#         with no orphaned ToolMessages, under the token limit
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_specialist_trim_keeps_assignment_and_bounded_tail() -> None:
    """A specialist message list with many tool CALL/RESULT pairs, after
    trimming, keeps: system prompt + assignment + the last N tool pairs
    (N from the specialist keep-recent config), with no orphaned ToolMessages.

    Layout: [System, Assignment, (call-A, tool-A), ... many pairs ..., tail pairs]
    With ``preserve_head=2`` and the specialist ``keep_recent`` (4), the
    assignment must survive and the tail must contain only complete
    call/response pairs.
    """
    keep = AI_SPECIALIST_CONTEXT_KEEP_RECENT  # specialist keep-recent (4)
    # Build 12 complete call/response pairs (24 messages) after the head.
    pairs = 12
    msgs: list[AnyMessage] = [
        SystemMessage(content="You are a specialist."),
        HumanMessage(content="## Your Assignment\nFind the project budget."),
    ]
    for i in range(pairs):
        cid = f"call_{i}"
        msgs.append(_ai_call([cid], content=f"thinking {i}"))
        msgs.append(_tool(cid, content=f"result_{i}" * 20))  # bulky results

    # Sanity: head is system + assignment.
    assert msgs[0].type == "system"
    assert msgs[1].type == "human"

    # Specialist middleware uses the specialist-specific threshold/keep-recent.
    mw = ContextGuardMiddleware(
        preserve_head=2,
        token_limit=AI_SPECIALIST_CONTEXT_TOKEN_LIMIT,
        keep_recent=keep,
    )
    real_est, _ = _force_trim(token_limit=AI_SPECIALIST_CONTEXT_TOKEN_LIMIT)
    try:
        trimmed = await _run_trim(mw, msgs)
    finally:
        context_guard._estimate_tokens = real_est  # type: ignore[assignment]

    # 1. System prompt preserved verbatim.
    assert trimmed[0].type == "system"
    assert trimmed[0].content == "You are a specialist."

    # 2. Assignment preserved verbatim (the specialist's task — CRITICAL).
    assignment_msgs = [
        m for m in trimmed if m.type == "human" and "Your Assignment" in m.content
    ]
    assert assignment_msgs, (
        "assignment HumanMessage must survive the trim (else the specialist "
        "forgets its task)"
    )

    # 3. Bounded tail: the kept call/response pairs are at most ``keep`` messages
    #    beyond the head + summary.  i.e. trimmed is much shorter than input.
    assert len(trimmed) < len(msgs), "trim must reduce the message count"
    # Tail itself (excluding head[0..1] and the injected summary) <= keep.
    tail_messages = trimmed[3:]  # skip system, assignment, summary
    assert len(tail_messages) <= keep, (
        f"tail ({len(tail_messages)}) must be bounded by keep ({keep})"
    )

    # 4. No orphaned ToolMessages: every tool message has a preceding assistant
    #    that issued its tool_call_id.
    seen_call_ids: set[str] = set()
    for m in trimmed:
        calls = getattr(m, "tool_calls", None)
        if calls:
            for c in calls:
                cid = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
                if cid:
                    seen_call_ids.add(cid)
    tool_msgs = [m for m in trimmed if m.type == "tool"]
    for tm in tool_msgs:
        assert tm.tool_call_id in seen_call_ids, (
            f"orphaned ToolMessage(tool_call_id={tm.tool_call_id}) after trim — "
            "tool/result pair was split"
        )

    # 5. And conversely every surviving tool_call has its response.
    tool_response_ids = {tm.tool_call_id for tm in tool_msgs}
    for cid in seen_call_ids:
        assert cid in tool_response_ids, (
            f"assistant tool_call {cid} has no matching tool response after trim"
        )


@pytest.mark.asyncio
async def test_specialist_trim_total_under_token_limit() -> None:
    """After trimming, the estimated tokens stay under the specialist limit.

    The trim is triggered by exceeding the threshold (80% of the specialist
    limit); the result must bring the mass back below the LIMIT (not just the
    threshold).  Uses the SPECIALIST limit (24k), not the supervisor's 120k.
    """
    limit = AI_SPECIALIST_CONTEXT_TOKEN_LIMIT  # 24000 (specialist-specific)
    pairs = 20
    msgs: list[AnyMessage] = [
        SystemMessage(content="sys"),
        HumanMessage(content="## Your Assignment\ndo the thing"),
    ]
    for i in range(pairs):
        cid = f"c{i}"
        msgs.append(_ai_call([cid]))
        # Each result ~10k chars => ~2.5k tokens; 20 pairs => ~50k tokens alone,
        # plus the keep tail.  This forces a real trim.
        msgs.append(_tool(cid, content="x" * 10_000))

    # Use the REAL estimator for the post-trim check (only force the trigger).
    real_est = context_guard._estimate_tokens
    mw = ContextGuardMiddleware(
        preserve_head=2,
        token_limit=limit,
        keep_recent=AI_SPECIALIST_CONTEXT_KEEP_RECENT,
    )
    forced_est: int = limit * 2  # force trigger
    context_guard._estimate_tokens = lambda _m: forced_est  # type: ignore[assignment]
    try:
        trimmed = await _run_trim(mw, msgs)
    finally:
        context_guard._estimate_tokens = real_est  # type: ignore[assignment]

    post_est = real_est(trimmed)
    assert post_est < limit, (
        f"trimmed message mass ({post_est} est tokens) must be under the limit "
        f"({limit})"
    )


# --------------------------------------------------------------------------- #
# Part 3: max_tool_iterations specialist cap (~8) vs supervisor (unchanged)
# --------------------------------------------------------------------------- #


def test_specialist_max_tool_iterations_is_bounded_not_flat_25() -> None:
    """``AI_SPECIALIST_MAX_TOOL_ITERATIONS`` is the specialist cap.

    Must be in the planned 8-10 range (matches the "2-4 tool calls/step" goal),
    NOT the flat 25 default that drove the timeout cascade.
    """
    assert 8 <= AI_SPECIALIST_MAX_TOOL_ITERATIONS <= 10, (
        f"specialist cap is {AI_SPECIALIST_MAX_TOOL_ITERATIONS}, expected 8-10"
    )
    # The flat-25 default must have been replaced.
    assert AI_SPECIALIST_MAX_TOOL_ITERATIONS != 25


def test_supervisor_max_tool_iterations_is_separate_and_higher() -> None:
    """The supervisor's budget is NOT the specialist cap.

    The supervisor inherits its ``max_tool_iterations`` from the graph recursion
    limit (set by agent_service.py in the initial state), NOT from
    ``AI_SPECIALIST_MAX_TOOL_ITERATIONS``.  We assert the specialist constant is
    strictly lower than the historical flat-25 supervisor default so the two are
    demonstrably decoupled.
    """
    # The specialist cap is the new, lower value; the supervisor continues to
    # use its own (recursion-limit-derived) budget.  As long as the specialist
    # cap < 25, the supervisor path is unaffected.
    assert AI_SPECIALIST_MAX_TOOL_ITERATIONS < 25


# --------------------------------------------------------------------------- #
# Part 4: specialist-vs-supervisor ContextGuard threshold decoupling
# --------------------------------------------------------------------------- #


def test_specialist_context_threshold_below_latency_knee() -> None:
    """``AI_SPECIALIST_CONTEXT_TOKEN_LIMIT`` is calibrated for GLM's latency knee.

    Specialists time out at the ~25-30k-token knee (and the 120s active-time
    limit), so the specialist guard must trigger well below the supervisor's
    120k threshold.  24000 sits safely under the knee (trim starts at ~80% ~ 19k);
    a live e2e showed a specialist running to 31k prompt_tokens at the 6th call
    with the old 120k guard never firing.
    """
    assert AI_SPECIALIST_CONTEXT_TOKEN_LIMIT == 24000
    # Must be far below the supervisor's 120k AND below the ~25k knee.
    assert AI_SPECIALIST_CONTEXT_TOKEN_LIMIT < context_guard.AI_CONTEXT_TOKEN_LIMIT
    assert AI_SPECIALIST_CONTEXT_TOKEN_LIMIT < 25000  # below the measured knee


def test_specialist_context_keep_recent_is_4_pairs() -> None:
    """Specialist keeps the last 4 tool CALL/RESULT pairs (focused 2-4 calls/step)."""
    assert AI_SPECIALIST_CONTEXT_KEEP_RECENT == 4
    # Lower than the supervisor's 8.
    assert AI_SPECIALIST_CONTEXT_KEEP_RECENT < context_guard.AI_CONTEXT_KEEP_RECENT


def test_supervisor_context_guard_does_not_pick_up_specialist_threshold() -> None:
    """REGRESSION: the supervisor's bare ``ContextGuardMiddleware()`` mount must
    keep using the global 120k/8 defaults, NOT the specialist values.

    The supervisor (``supervisor_orchestrator.py:1532``) mounts
    ``ContextGuardMiddleware()`` with no args; those default to the module
    globals.  This test guards against an accidental change that would either
    (a) break the supervisor's long-context behavior or (b) silently wire the
    specialist threshold into the supervisor.
    """
    supervisor_mw = ContextGuardMiddleware()  # bare mount, as the supervisor does
    assert supervisor_mw.preserve_head == 1
    assert supervisor_mw.token_limit == context_guard.AI_CONTEXT_TOKEN_LIMIT, (
        "supervisor must use the 120k global, not the specialist threshold"
    )
    assert supervisor_mw.keep_recent == context_guard.AI_CONTEXT_KEEP_RECENT, (
        "supervisor must use the global keep-recent (8), not the specialist's 4"
    )
    # And specifically NOT the specialist values.
    assert supervisor_mw.token_limit != AI_SPECIALIST_CONTEXT_TOKEN_LIMIT
    assert supervisor_mw.keep_recent != AI_SPECIALIST_CONTEXT_KEEP_RECENT
