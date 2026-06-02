"""Middleware that trims supervisor message history before context window overflow.

Unlike ``SummarizationMiddleware`` (which makes a secondary LLM call to compress
history), this guard is deterministic: it replaces older messages with the
already-compiled briefing document that accumulates specialist findings. This
avoids an extra LLM invocation and keeps the supervisor grounded in structured
findings rather than a lossy LLM summary.

Only intended for the supervisor node — specialists receive isolated message
lists built fresh on each invocation, so they never accumulate long histories.

Configuration is sourced from centralized constants in ``app.ai.config``:
- ``AI_CONTEXT_TOKEN_LIMIT`` — max estimated prompt tokens
- ``AI_CONTEXT_SUMMARY_THRESHOLD_PCT`` — percentage of limit that triggers trimming
- ``AI_CONTEXT_KEEP_RECENT`` — messages to keep unsummarized at the tail
"""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest
from langchain_core.messages import AnyMessage, HumanMessage

from app.ai.briefing import BriefingDocument
from app.ai.config import (
    AI_CONTEXT_KEEP_RECENT,
    AI_CONTEXT_SUMMARY_THRESHOLD_PCT,
    AI_CONTEXT_TOKEN_LIMIT,
)

logger = logging.getLogger(__name__)

_CHARS_PER_TOKEN = 4

#: Minimum messages required before trimming is considered.  Prevents false
#: positives on early turns where system prompt + tool schemas dominate the
#: token estimate but there is almost no conversation history to trim.
_MIN_MESSAGES_TO_TRIM = 8


def _repair_chain(messages: list[AnyMessage]) -> list[AnyMessage]:
    """Repair message chain after trimming to maintain LLM API invariants.

    The LLM API requires:
    1. Every ``tool`` message must directly follow an assistant with ``tool_calls``.
    2. Every assistant ``tool_calls`` must be followed by tool responses for
       every ``tool_call_id``.

    After trimming the middle of the message list, both invariants can break.
    This function rebuilds the chain by:
    1. Collecting all tool_call_ids present in the messages.
    2. Keeping only tool messages whose tool_call_id has a matching tool_calls entry.
    3. Keeping only tool_calls on assistant messages that have all their responses.
    4. Removing assistant messages that become empty after stripping tool_calls.
    """
    # Pass 1: collect all tool_call_ids from assistant messages with tool_calls
    assistant_call_ids: set[str] = set()
    for m in messages:
        calls = getattr(m, "tool_calls", None)
        if calls:
            for c in calls:
                cid = getattr(c, "id", None) or (
                    c.get("id") if isinstance(c, dict) else None
                )
                if cid:
                    assistant_call_ids.add(cid)

    # Pass 2: collect tool_call_ids from tool messages
    tool_msg_ids: set[str] = set()
    for m in messages:
        role = getattr(m, "type", None) or getattr(m, "role", None)
        if role == "tool":
            tid = getattr(m, "tool_call_id", None)
            if tid:
                tool_msg_ids.add(tid)

    # Pass 3: rebuild chain
    # - valid_call_ids: calls that have ALL their tool responses present
    # - valid_tool_ids: tool responses whose parent call is present
    valid_call_ids = set()
    for cid in assistant_call_ids:
        # Check this call's ID appears in tool responses
        if cid in tool_msg_ids:
            valid_call_ids.add(cid)

    valid_tool_ids = {tid for tid in tool_msg_ids if tid in assistant_call_ids}

    repaired: list[AnyMessage] = []
    for m in messages:
        role = getattr(m, "type", None) or getattr(m, "role", None)

        # Drop orphaned tool responses
        if role == "tool":
            tid = getattr(m, "tool_call_id", None)
            if tid not in valid_tool_ids:
                continue

        # For assistant messages with tool_calls, strip calls without responses
        calls = getattr(m, "tool_calls", None)
        if calls:
            import copy

            from langchain_core.messages import AIMessage

            filtered_calls = [
                c
                for c in calls
                if (
                    getattr(c, "id", None)
                    or (c.get("id") if isinstance(c, dict) else None)
                )
                in valid_call_ids
            ]
            if filtered_calls:
                # Keep the message but with only valid tool_calls
                m = copy.deepcopy(m)
                if isinstance(m, AIMessage):
                    m.tool_calls = filtered_calls
            else:
                # All tool_calls were orphaned — keep as plain assistant if it has content
                content = getattr(m, "content", None)
                if not content or (isinstance(content, str) and not content.strip()):
                    continue  # skip empty assistant messages

        repaired.append(m)

    return repaired


def _estimate_tokens(messages: list[AnyMessage]) -> int:
    """Rough token estimate of conversation content (excluding system prompt).

    Skips the first message (system prompt) because it is always present and
    does not grow across turns.  Including it caused massive over-estimates
    on the first turn of a new session where tool schemas inflate the system
    message to tens of thousands of characters.
    """
    total_chars = 0
    for m in messages[1:]:  # skip system prompt
        content = m.content if isinstance(m.content, str) else str(m.content)
        total_chars += len(content)
    return total_chars // _CHARS_PER_TOKEN


def _build_summary_message(briefing_data: dict[str, Any]) -> HumanMessage:
    """Build a compact context summary from the briefing document.

    Returns a ``HumanMessage`` so it occupies the mid-conversation slot
    naturally — the supervisor treats it as a user-provided context block.
    """
    doc = BriefingDocument.from_state(briefing_data)
    md = doc.to_markdown()
    if not md.strip():
        md = "(No briefing findings yet.)"
    content = f"[Context Summary - older messages summarized]\n{md}"
    return HumanMessage(content=content)


class ContextGuardMiddleware(AgentMiddleware):
    """Trim supervisor message history when estimated tokens approach the limit.

    Before each model call:
    1. Estimate token count from message content lengths.
    2. If tokens exceed ``AI_CONTEXT_SUMMARY_THRESHOLD_PCT``% of
       ``AI_CONTEXT_TOKEN_LIMIT``, trim older messages:
       - Keep the first message (system prompt).
       - Keep the last ``AI_CONTEXT_KEEP_RECENT`` messages for continuity.
       - Replace everything in between with a single briefing-document summary.
    3. Log the trimming decision for observability.

    This middleware is intentionally cheap (no LLM calls) because the briefing
    document already serves as a structured summary of all specialist work.
    """

    async def awrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Any,
    ) -> Any:
        messages = request.messages
        if not messages:
            return await handler(request)

        est = _estimate_tokens(messages)
        threshold = AI_CONTEXT_TOKEN_LIMIT * AI_CONTEXT_SUMMARY_THRESHOLD_PCT // 100

        if est <= threshold:
            return await handler(request)

        # Not enough messages to meaningfully trim — avoids false positives
        # on early turns where token estimate is dominated by tool schemas.
        if len(messages) < _MIN_MESSAGES_TO_TRIM:
            logger.info(
                "Context guard: est %d tokens > %d threshold, "
                "too few messages to trim (%d < %d)",
                est,
                threshold,
                len(messages),
                _MIN_MESSAGES_TO_TRIM,
            )
            return await handler(request)

        if len(messages) <= AI_CONTEXT_KEEP_RECENT + 1:
            logger.info(
                "Context guard: est %d tokens > %d threshold, "
                "too few messages to trim (%d)",
                est,
                threshold,
                len(messages),
            )
            return await handler(request)

        # Build briefing summary from graph state.
        briefing_data: dict[str, Any] = {}
        state = dict(request.state) if request.state else {}
        raw_briefing = state.get("briefing_data")
        if isinstance(raw_briefing, dict):
            briefing_data = raw_briefing

        summary_msg = _build_summary_message(briefing_data)
        first_msg = messages[0]
        tail = messages[-AI_CONTEXT_KEEP_RECENT:]
        removed = len(messages) - 1 - AI_CONTEXT_KEEP_RECENT

        # Ensure message-chain integrity: tool responses must follow
        # assistant messages with tool_calls.  If the trim boundary
        # splits a tool_calls → tool pair, drop the orphaned tool msgs.
        trimmed = [first_msg, summary_msg, *tail]
        trimmed = _repair_chain(trimmed)

        logger.info(
            "Context guard: est %d tokens > %d threshold, trimmed %d msgs",
            est,
            threshold,
            removed,
        )

        return await handler(request.override(messages=trimmed))


__all__ = ["ContextGuardMiddleware"]
