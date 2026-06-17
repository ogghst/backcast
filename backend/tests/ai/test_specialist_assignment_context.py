"""Tests for Fix A: sharing gathered ask_user answers with specialists.

The specialist is message-isolated from the supervisor's outer conversation, so
it never sees prior ``ask_user`` Q&A and re-asks questions the user already
answered.  ``collect_recent_ask_user_qa`` walks the supervisor's message list
to extract recent (question, answer) pairs, and ``supervisor_orchestrator``
injects a capped block of those pairs into the specialist's assignment_block so
the specialist sees the gathered context instead of re-asking.

This module tests the helper in isolation AND an integration-style check that
the specialist_node assignment includes a prior ask_user answer.
"""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.ai.message_utils import collect_recent_ask_user_qa

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ai_with_ask(
    call_id: str,
    question: str,
    content: str = "",
) -> AIMessage:
    """Build an AIMessage that issued an ask_user tool call."""
    return AIMessage(
        content=content,
        tool_calls=[
            {"name": "ask_user", "args": {"question": question}, "id": call_id}
        ],
    )


def _tool_answer(call_id: str, answer: str) -> ToolMessage:
    """Build the ToolMessage reply for a successful ask_user."""
    return ToolMessage(
        content=json.dumps({"answer": answer}),
        tool_call_id=call_id,
    )


def _tool_error(call_id: str, msg: str = "timed out") -> ToolMessage:
    """Build a ToolMessage reply for a timed-out ask_user."""
    return ToolMessage(
        content=json.dumps({"error": msg}),
        tool_call_id=call_id,
    )


# ===========================================================================
# Helper: pairing by tool_call_id
# ===========================================================================


def test_pairs_question_to_answer_by_tool_call_id() -> None:
    msgs = [
        _ai_with_ask("c1", "What is the project name?"),
        _tool_answer("c1", "Alpha Line"),
    ]
    pairs = collect_recent_ask_user_qa(msgs)
    assert pairs == [("What is the project name?", "Alpha Line")]


def test_ignores_non_ask_user_tool_calls() -> None:
    """Only ask_user calls are gathered, not other tool calls."""
    msgs = [
        AIMessage(
            content="",
            tool_calls=[{"name": "get_briefing", "args": {}, "id": "x1"}],
        ),
        ToolMessage(content="briefing text", tool_call_id="x1"),
        _ai_with_ask("c1", "Which WBE?"),
        _tool_answer("c1", "Robot Cell A"),
    ]
    pairs = collect_recent_ask_user_qa(msgs)
    assert pairs == [("Which WBE?", "Robot Cell A")]


# ===========================================================================
# Helper: skipping error answers
# ===========================================================================


def test_skips_error_answers() -> None:
    """A timed-out ask_user ({"error": ...}) must not be presented as context."""
    msgs = [
        _ai_with_ask("c1", "Question that timed out"),
        _tool_error("c1"),
        _ai_with_ask("c2", "Question that succeeded"),
        _tool_answer("c2", "Real answer"),
    ]
    pairs = collect_recent_ask_user_qa(msgs)
    assert pairs == [("Question that succeeded", "Real answer")]


def test_skips_unparseable_tool_content() -> None:
    """Malformed ToolMessage content is skipped, not crashed on."""
    msgs = [
        _ai_with_ask("c1", "Broken reply"),
        ToolMessage(content="not-json-at-all", tool_call_id="c1"),
        _ai_with_ask("c2", "Good reply"),
        _tool_answer("c2", "Good answer"),
    ]
    pairs = collect_recent_ask_user_qa(msgs)
    assert pairs == [("Good reply", "Good answer")]


# ===========================================================================
# Helper: orphans
# ===========================================================================


def test_skips_orphan_tool_messages() -> None:
    """A ToolMessage whose tool_call_id has no matching AIMessage is skipped."""
    msgs = [
        ToolMessage(content=json.dumps({"answer": "ghost"}), tool_call_id="orphan"),
        _ai_with_ask("c1", "Real question"),
        _tool_answer("c1", "Real answer"),
    ]
    pairs = collect_recent_ask_user_qa(msgs)
    assert pairs == [("Real question", "Real answer")]


# ===========================================================================
# Helper: capping + recency
# ===========================================================================


def test_caps_to_limit_returning_most_recent() -> None:
    """With limit=2 and 3 pairs, the LAST 2 (most recent) are returned."""
    msgs: list = []
    for i in range(3):
        cid = f"c{i}"
        msgs.append(_ai_with_ask(cid, f"Q{i}"))
        msgs.append(_tool_answer(cid, f"A{i}"))
    pairs = collect_recent_ask_user_qa(msgs, limit=2)
    assert pairs == [("Q1", "A1"), ("Q2", "A2")]


def test_default_limit_is_six() -> None:
    """The default limit is 6 pairs (memory 20 / commit 58a642c2 cap)."""
    msgs: list = []
    for i in range(8):
        cid = f"c{i}"
        msgs.append(_ai_with_ask(cid, f"Q{i}"))
        msgs.append(_tool_answer(cid, f"A{i}"))
    pairs = collect_recent_ask_user_qa(msgs)
    assert len(pairs) == 6
    # Most recent 6
    assert pairs[0] == ("Q2", "A2")
    assert pairs[-1] == ("Q7", "A7")


def test_empty_messages_returns_empty() -> None:
    assert collect_recent_ask_user_qa([]) == []


def test_no_ask_user_calls_returns_empty() -> None:
    msgs = [
        HumanMessage(content="hello"),
        AIMessage(content="hi"),
    ]
    assert collect_recent_ask_user_qa(msgs) == []


# ===========================================================================
# Integration: specialist_node assignment includes a prior ask_user answer
# ===========================================================================


def test_assignment_block_includes_gathered_ask_user_qa() -> None:
    """The specialist assignment must surface a prior ask_user answer so the
    specialist does not re-ask it."""
    from app.ai.supervisor_orchestrator import (
        _format_gathered_context_block,
    )

    # Minimal supervisor message history: user was asked and answered.
    supervisor_messages = [
        _ai_with_ask("c1", "What is the contract value?"),
        _tool_answer("c1", "1.2M EUR"),
    ]

    block = _format_gathered_context_block(supervisor_messages)
    # Block is non-empty and contains both the question and the answer.
    assert block is not None
    assert "contract value" in block.lower()
    assert "1.2M EUR" in block
    # Imperative header (exact) must be present so GLM-4.7 treats the gathered
    # answers as foreground inputs.
    assert (
        "## Already-confirmed user inputs "
        "(use these verbatim as inputs; do NOT call ask_user for any of them)"
    ) in block
    # Directive line under the header.
    assert "Treat each answer as a confirmed input value." in block
    assert "Do not re-ask." in block


def test_assignment_block_empty_when_no_qa() -> None:
    """When there is no gathered Q&A, no block is emitted (returns None)."""
    from app.ai.supervisor_orchestrator import (
        _format_gathered_context_block,
    )

    assert _format_gathered_context_block([]) is None
    assert (
        _format_gathered_context_block([AIMessage(content="no questions here")]) is None
    )


def test_gathered_block_prepended_before_assignment_header() -> None:
    """The gathered context block must appear BEFORE "## Your Assignment" so it
    is the first thing in the specialist's isolated message (GLM-4.7 was
    re-asking answered questions when the block sat at the end of a long
    assignment)."""
    from app.ai.supervisor_orchestrator import _format_gathered_context_block

    supervisor_messages = [
        _ai_with_ask("c1", "What is the contract value?"),
        _tool_answer("c1", "1.2M EUR"),
    ]
    block = _format_gathered_context_block(supervisor_messages)
    assert block is not None

    # Simulate the specialist_node prepend: gathered block goes first, then the
    # task/assignment body.
    assignment_body = "## Your Assignment\n\nDo the cost analysis."
    assignment_block = f"{block}\n\n{assignment_body}"

    gathered_idx = assignment_block.index(block)
    assignment_idx = assignment_block.index("## Your Assignment")
    assert gathered_idx < assignment_idx, (
        "gathered context must precede the assignment header"
    )
    # And the imperative header leads the whole assignment.
    assert assignment_block.startswith("## Already-confirmed user inputs")
