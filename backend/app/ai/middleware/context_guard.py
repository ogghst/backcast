"""Middleware that trims message history before context window overflow.

Unlike ``SummarizationMiddleware`` (which makes a secondary LLM call to compress
history), this guard is deterministic: it replaces older messages with the
already-compiled briefing document that accumulates specialist findings. This
avoids an extra LLM invocation and keeps the agent grounded in structured
findings rather than a lossy LLM summary.

Mounted on BOTH the supervisor and specialists:

- **Supervisor** (``SupervisorOrchestrator._build_middleware``): long-running,
  accumulates specialist findings across many turns. ``preserve_head=1`` keeps
  only the system prompt above the summary.
- **Specialist** (``compile_subagents``): message-isolated per invocation, but
  its own ReAct loop appends every tool CALL/RESULT pair up to
  ``max_tool_iterations``. ``preserve_head=2`` keeps the system prompt AND the
  initial assignment ``HumanMessage`` (the specialist's task) above the summary
  — losing the assignment would make the specialist forget what it was asked.

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
                # Observability: a residual split (or any future edge case)
                # dropped a tool response.  Cheap — only when actually dropping.
                logger.warning(
                    "Context guard _repair_chain: dropped orphaned tool message "
                    "tool_call_id=%s",
                    tid,
                )
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
                    # Observability: an assistant was dropped because every one
                    # of its tool_calls was orphaned and it had no content.
                    dropped_ids = [
                        getattr(c, "id", None)
                        or (c.get("id") if isinstance(c, dict) else None)
                        for c in calls
                    ]
                    logger.warning(
                        "Context guard _repair_chain: dropped assistant with "
                        "orphaned tool_calls (ids=%s)",
                        dropped_ids,
                    )
                    continue  # skip empty assistant messages

        repaired.append(m)

    return repaired


def _is_tool_message(m: AnyMessage) -> bool:
    """True if ``m`` is a tool response message."""
    role = getattr(m, "type", None) or getattr(m, "role", None)
    return role == "tool"


def _find_caller_index(messages: list[AnyMessage], tool_idx: int) -> int:
    """Return the index of the assistant whose ``tool_calls`` issued the tool
    message at ``tool_idx``, or ``-1`` if not found in the range ``[1, tool_idx)``.

    ``messages[0]`` (system prompt) is deliberately excluded — it survives the
    trim intact, so a tool response whose only caller is the system message has
    no caller worth pulling into the tail.
    """
    tid = getattr(messages[tool_idx], "tool_call_id", None)
    if not tid:
        return -1
    for idx in range(tool_idx - 1, 0, -1):  # stop before messages[0]
        calls = getattr(messages[idx], "tool_calls", None)
        if not calls:
            continue
        for c in calls:
            cid = getattr(c, "id", None) or (
                c.get("id") if isinstance(c, dict) else None
            )
            if cid == tid:
                return idx
    return -1


def _tool_aware_tail_start(
    messages: list[AnyMessage],
    keep: int,
    floor: int = 1,
) -> int:
    """Return the start index for the tail so it never begins inside a
    tool-response group whose issuing assistant would be dropped.

    If the naive start ``len(messages) - keep`` lands on a ``tool`` message,
    back the split up to its issuing assistant so the call/response pair stays
    intact (instead of being orphaned and dropped by ``_repair_chain``).

    ``floor`` is the minimum index the split may take — messages ``[0, floor)``
    are preserved verbatim above the summary.  For the supervisor ``floor=1``
    (only the system prompt); for a specialist ``floor=2`` (system prompt + the
    assignment ``HumanMessage``).
    """
    n = len(messages)
    s = max(floor, n - keep)
    while s < n and _is_tool_message(messages[s]):
        caller_idx = _find_caller_index(messages, s)
        if floor <= caller_idx < s:
            s = caller_idx
            continue  # messages[s] is now an assistant -> loop exits next pass
        break  # caller is below floor (survives trim) or not found -> _repair_chain
    return s


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
    """Trim message history when estimated tokens approach the limit.

    Before each model call:
    1. Estimate token count from message content lengths.
    2. If tokens exceed ``AI_CONTEXT_SUMMARY_THRESHOLD_PCT``% of
       ``AI_CONTEXT_TOKEN_LIMIT``, trim older messages:
       - Keep the first ``preserve_head`` messages verbatim (system prompt,
         and for specialists also the assignment ``HumanMessage``).
       - Keep the last ``AI_CONTEXT_KEEP_RECENT`` messages for continuity.
       - Replace everything in between with a single briefing-document summary.
    3. Log the trimming decision for observability.

    This middleware is intentionally cheap (no LLM calls) because the briefing
    document already serves as a structured summary of all agent work.

    Args:
        preserve_head: Number of leading messages preserved verbatim above the
            summary.  ``1`` for the supervisor (system prompt only); ``2`` for
            specialists (system prompt + assignment task).
        token_limit: Max estimated prompt tokens before trimming triggers (the
            threshold is ``AI_CONTEXT_SUMMARY_THRESHOLD_PCT``% of this).  Defaults
            to the supervisor-calibrated ``AI_CONTEXT_TOKEN_LIMIT`` (120k) so the
            supervisor's behavior is byte-identical.  Specialists pass their own,
            much lower ``AI_SPECIALIST_CONTEXT_TOKEN_LIMIT`` because they hit GLM's
            ~25-30k-token latency knee far below 120k.
        keep_recent: Number of recent messages kept unsummarized at the tail.
            Defaults to ``AI_CONTEXT_KEEP_RECENT`` (the supervisor's 8).
            Specialists pass ``AI_SPECIALIST_CONTEXT_KEEP_RECENT`` (4).
    """

    def __init__(
        self,
        *,
        preserve_head: int = 1,
        token_limit: int | None = None,
        keep_recent: int | None = None,
    ) -> None:
        self.preserve_head = max(1, preserve_head)
        # ``None`` -> fall back to the module globals (supervisor defaults) so
        # the supervisor's bare ``ContextGuardMiddleware()`` mount is unchanged.
        self.token_limit = (
            token_limit if token_limit is not None else AI_CONTEXT_TOKEN_LIMIT
        )
        self.keep_recent = (
            keep_recent if keep_recent is not None else AI_CONTEXT_KEEP_RECENT
        )

    async def awrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Any,
    ) -> Any:
        messages = request.messages
        if not messages:
            return await handler(request)

        est = _estimate_tokens(messages)
        threshold = self.token_limit * AI_CONTEXT_SUMMARY_THRESHOLD_PCT // 100

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

        if len(messages) <= self.keep_recent + self.preserve_head:
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
        head = list(messages[: self.preserve_head])
        split = _tool_aware_tail_start(
            messages, self.keep_recent, floor=self.preserve_head
        )
        tail = messages[split:]
        removed = split - self.preserve_head  # messages dropped between head and tail

        # Ensure message-chain integrity: tool responses must follow
        # assistant messages with tool_calls.  ``_tool_aware_tail_start`` avoids
        # splitting a pair at the boundary; ``_repair_chain`` repairs any
        # residual orphan and WARNs when it has to drop.
        trimmed = [*head, summary_msg, *tail]
        trimmed = _repair_chain(trimmed)

        logger.info(
            "Context guard: est %d tokens > %d threshold, trimmed %d msgs "
            "(preserve_head=%d)",
            est,
            threshold,
            removed,
            self.preserve_head,
        )

        return await handler(request.override(messages=trimmed))


__all__ = ["ContextGuardMiddleware"]
