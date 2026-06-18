"""Pure extraction helpers for LangChain message types.

Provides functions to pull final AI responses and tool output content from
LangGraph message lists, handling edge cases like DeepSeek models that
sometimes return empty final AIMessages after tool execution.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from langgraph.types import Command

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

__all__ = [
    "collect_recent_ask_user_qa",
    "estimate_tools_token_cost",
    "extract_final_ai_response",
    "extract_tool_output_content",
    "find_last_ai_reasoning_kwargs",
    "is_transient_stream_error",
    "strip_think_tags",
    "trim_tool_result_text",
]

# Maximum characters to keep from each individual tool result when building
# specialist findings.  Tool results from get_project_structure,
# get_project_analysis etc. can return 50K+ chars of nested JSON which
# inflates prompt tokens on subsequent LLM turns.
_MAX_TOOL_RESULT_CHARS = 2000


def trim_tool_result_text(text: str, max_chars: int = _MAX_TOOL_RESULT_CHARS) -> str:
    """Truncate a single tool-result string to *max_chars*, preserving a trailer.

    If the text exceeds *max_chars*, keeps the first ``max_chars`` characters
    and appends a ``... [truncated N chars total]`` marker so the LLM knows
    data was omitted.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [truncated {len(text)} chars total]"


def find_last_ai_reasoning_kwargs(messages: list[BaseMessage]) -> dict[str, Any]:
    """Find reasoning_content from the last AIMessage and return additional_kwargs.

    Returns an empty dict if no reasoning_content is found. Used by handoff
    tools to propagate DeepSeek thinking mode across synthetic messages.
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            rc = msg.additional_kwargs.get("reasoning_content")
            if rc:
                return {"additional_kwargs": {"reasoning_content": rc}}
            return {}
    return {}


def is_transient_stream_error(exc: Exception) -> bool:
    """Check if a streaming error is transient and worth retrying."""
    if isinstance(exc, (ConnectionResetError, OSError)):
        return True
    err_type = type(exc).__name__
    err_module = type(exc).__module__
    return (err_type == "ReadError" and "httpcore" in err_module) or (
        err_type == "RemoteProtocolError" and "httpx" in err_module
    )


def extract_final_ai_response(messages: list[BaseMessage]) -> str:
    """Extract the last AIMessage without tool_calls from a message list.

    Falls back to concatenating ToolMessage content if the final AIMessage
    is empty (handles DeepSeek models that sometimes return empty content
    after tool execution).

    Args:
        messages: LangChain message history from graph invocation.

    Returns:
        Extracted text content, or empty string if nothing found.
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            content = str(msg.content).strip()
            if content:
                return content

    # Fallback: concatenate tool results in original order, trimmed
    tool_parts: list[str] = []
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.content:
            tool_parts.append(trim_tool_result_text(str(msg.content)))
    if tool_parts:
        return "\n\n".join(reversed(tool_parts))
    return ""


# Default cap on how many gathered ask_user Q&A pairs are surfaced to a
# specialist's assignment.  Keeps the specialist's isolated context compact so
# it does not re-open the token-bloat regression (memory 20 / commit 58a642c2
# cut specialist prompt tokens 79%); a specialist does a focused 2-4 calls/step
# and almost never needs more than a handful of prior answers.
_DEFAULT_ASK_USER_QA_LIMIT = 6


def collect_recent_ask_user_qa(
    messages: list[BaseMessage], limit: int = _DEFAULT_ASK_USER_QA_LIMIT
) -> list[tuple[str, str]]:
    """Collect recent (question, answer) pairs from supervisor ask_user calls.

    Specialists are message-isolated from the supervisor's outer conversation,
    so without this the specialist never sees the supervisor's prior ask_user
    Q&A and re-asks questions the user already answered.  This walks the
    supervisor's message list and pairs each ``ask_user`` AIMessage tool call
    with its corresponding ``ToolMessage`` reply (matched by ``tool_call_id``).

    Pairs are EXCLUDED when:

    * the ToolMessage content is not parseable JSON,
    * the parsed dict carries an ``"error"`` key (e.g. ask_user timed out), or
    * the parsed dict has no ``"answer"`` key.

    Orphan ToolMessages (no matching AIMessage) are skipped.

    Args:
        messages: The supervisor's outer conversation messages.
        limit: Maximum number of pairs to return. The MOST RECENT ``limit``
            pairs are returned (older pairs are dropped). Defaults to 6.

    Returns:
        A list of ``(question, answer)`` strings, oldest-first, capped to
        *limit*. Empty when no usable ask_user Q&A is present.
    """
    # Index tool replies by tool_call_id for O(1) pairing.
    tool_by_call_id: dict[str, ToolMessage] = {}
    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_by_call_id[msg.tool_call_id] = msg

    pairs: list[tuple[str, str]] = []
    for msg in messages:
        if not isinstance(msg, AIMessage) or not msg.tool_calls:
            continue
        for call in msg.tool_calls:
            if call.get("name") != "ask_user":
                continue
            question = str(call.get("args", {}).get("question", "")).strip()
            if not question:
                continue
            call_id = call.get("id")
            if not isinstance(call_id, str):
                continue
            reply = tool_by_call_id.get(call_id)
            if reply is None:
                # Orphan: a ToolMessage whose AIMessage is absent/garbled.
                continue
            answer = _parse_ask_user_answer(reply.content)
            if answer is None:
                # Unparseable, error-bearing, or answer-less reply: skip.
                continue
            pairs.append((question, answer))

    if not pairs:
        return []
    # Keep the most recent ``limit`` pairs, returned oldest-first.
    return pairs[-limit:]


def _parse_ask_user_answer(content: Any) -> str | None:
    """Extract an ``answer`` string from an ask_user ToolMessage content.

    The content is a stringified dict like ``{"answer": "..."}`` on success or
    ``{"error": "..."}`` on timeout. Returns the answer string, or ``None``
    when the content is unparseable, error-bearing, or has no ``answer`` key.
    """
    if not isinstance(content, str):
        return None
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    if "error" in parsed:
        return None
    answer = parsed.get("answer")
    if not isinstance(answer, str):
        return None
    return answer


def extract_tool_output_content(tool_output: Any) -> str:
    """Extract string content from various tool output types.

    Handles ToolMessage, LangGraph Command, dict with "content" key,
    and raw strings. Returns empty string if extraction fails.

    Args:
        tool_output: Tool result from LangGraph tool node execution.

    Returns:
        Extracted text content, or empty string.
    """
    if isinstance(tool_output, ToolMessage):
        raw = tool_output.content
        return raw if isinstance(raw, str) else str(raw)
    if isinstance(tool_output, Command):
        update_dict = tool_output.update
        if isinstance(update_dict, dict):
            messages = update_dict.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if isinstance(last_msg, dict):
                    return last_msg.get("content", "")
                if hasattr(last_msg, "content"):
                    return str(last_msg.content)
                return str(last_msg)
    if isinstance(tool_output, dict) and "content" in tool_output:
        content = tool_output["content"]
        return content if isinstance(content, str) else str(content)
    if isinstance(tool_output, str):
        return tool_output
    return str(tool_output) if tool_output is not None else ""


# --- Inline <think> reasoning-tag stripping ---
#
# Some reasoning models (e.g. GLM-4.7 via api.z.ai) emit their chain-of-thought
# INLINE in the content stream wrapped in <think>...</think>, rather than in a
# separate ``reasoning_content`` field like DeepSeek. Worse, the upstream
# provider sometimes strips the OPENING tag but leaves a DANGLING ``</think>``,
# so the reasoning body runs straight into the answer with only a closing tag
# between them. ``strip_think_tags`` removes all of these shapes from a fully
# assembled message; a stateful streaming filter in the agent service handles
# the live token-by-token case.

# Balanced block: ``<think>...</think>`` (non-greedy, DOTALL so newlines match).
_BALANCED_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
# Unclosed open tag to end-of-string: ``<think>...`` with no closing tag.
_UNCLOSED_OPEN_THINK_RE = re.compile(r"<think>.*", re.DOTALL)
# Dangling close tag (no opening): matches the literal ``</think>``.
_DANGLING_CLOSE_THINK_RE = re.compile(r"</think>", re.DOTALL)


def strip_think_tags(text: str) -> str:
    """Remove inline ``<think>...</think>`` reasoning from a complete message.

    Handles every shape that leaks out of reasoning models:

    - **Balanced**: ``<think>reasoning</think>answer`` -> ``answer``
    - **Unclosed open**: ``prefix<think>reasoning to end`` -> ``prefix``
      (the model opened a think block and never closed it -- drop the tail)
    - **Dangling close** (the main bug shape, no opening tag): the provider
      strips ``<think>`` but leaves ``</think>``, so reasoning runs straight
      into the answer. ``reasoning body</think>real answer`` -> ``real answer``
      (everything up to and including the FIRST ``</think>`` is removed).
    - **Multiple balanced blocks**: all are removed.
    - **No tags**: the text is returned byte-identical (after a strip()).

    Conservative on ambiguity: when a dangling close has no matching open,
    reasoning always PRECEDES the answer, so stripping up to the first
    ``</think>`` is correct. Multiple dangling closes are handled by removing
    only up to the first one (any text after the first ``</think>`` is the
    answer; a second ``</think>`` in the answer is treated literally and left
    alone).

    Cheap no-op when neither tag is present: returns ``text.strip()``.

    Args:
        text: Fully assembled assistant message content.

    Returns:
        The message with reasoning blocks removed, leading/trailing
        whitespace stripped.
    """
    # Fast path: nothing to do when neither tag appears. Avoids running three
    # regexes over normal markdown/tables on the hot persistence path.
    if "<think>" not in text and "</think>" not in text:
        return text.strip()

    # 1. Remove all balanced ``<think>...</think>`` blocks first.
    cleaned = _BALANCED_THINK_RE.sub("", text)

    # 2. Dangling close: a ``</think>`` with no preceding ``<think>`` left
    #    (the provider stripped the opening tag). Remove everything from the
    #    START of the string through the FIRST ``</think>`` -- reasoning
    #    always precedes the answer, so this is the safe cut.
    if "</think>" in cleaned and "<think>" not in cleaned:
        first_close = _DANGLING_CLOSE_THINK_RE.search(cleaned)
        assert first_close is not None  # ``"</think>" in cleaned`` above
        cleaned = cleaned[first_close.end() :]

    # 3. Unclosed open: a ``<think>`` with no closing tag remains -- the model
    #    opened reasoning and ran to the end. Drop from the tag to end-of-string.
    if "<think>" in cleaned and "</think>" not in cleaned:
        cleaned = _UNCLOSED_OPEN_THINK_RE.sub("", cleaned)

    return cleaned.strip()


def estimate_tools_token_cost(tools: list[BaseTool]) -> int:
    """Estimate the prompt-token cost of a list of bound tool definitions.

    Sums ``len(json.dumps(convert_to_openai_tool(t))) // 4`` over the tools,
    i.e. the standard ~4-chars-per-token heuristic applied to the OpenAI-style
    tool JSON schema that LangChain sends on every LLM call (no provider
    caching for tools). This is the per-call, roughly-constant "tool-def"
    term that -- together with the growing accumulated tool-result history --
    dominates specialist prompt size and thus latency.

    Pure and side-effect free; never raises (a tool that fails conversion is
    skipped and counted as 0). Returns 0 for an empty list.

    Args:
        tools: LangChain ``BaseTool`` instances (e.g. a specialist's
            ``allowed_tools`` roster or the supervisor's ``direct_tools``).

    Returns:
        Estimated token cost of the tool-definition payload.
    """
    total = 0
    for tool in tools:
        try:
            schema = convert_to_openai_tool(tool)
            total += len(json.dumps(schema, default=str)) // 4
        except Exception:  # noqa: BLE001 -- diagnostics helper, never raise
            # A misbehaving tool should not poison the estimate; skip it.
            continue
    return total
