"""Ask-user tool for interactive clarification during agent execution.

Allows the supervisor and specialists to ask the user clarification
questions via the AI chat. Uses the AgentEventBus to publish an ASK_USER
event and awaits a response via an asyncio.Future keyed by ask_id.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import uuid4

from langchain_core.tools import InjectedToolArg
from pydantic import BeforeValidator

from app.ai.execution.agent_event import AgentEvent
from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import RiskLevel, ToolContext
from app.core.config import settings

logger = logging.getLogger(__name__)


def _coerce_options_list(v: Any) -> Any:
    """Coerce a JSON-encoded string into a list for the ``options`` parameter.

    Some LLMs (e.g. glm-4.7) pass ``options`` as a JSON string like
    ``'["Assembly Station 1", "Robot Cell A"]'`` instead of a proper list.
    This validator handles that case transparently.
    """
    if v is None or isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return v


# Module-level registry for in-flight ask_user requests.
# Key: ask_id (str), Value: (future, execution_id) tuple.
_pending_asks: dict[str, tuple[asyncio.Future[str], str]] = {}

# execution_ids currently BLOCKED awaiting a human answer. The specialist
# step-timeout watchdog reads this (via ``is_awaiting_user``) to PAUSE its
# deadline while a specialist is legitimately waiting on ask_user, so a slow
# human does not get the specialist killed mid-clarification.
_awaiting_user: set[str] = set()


def mark_awaiting_user(execution_id: str) -> None:
    """Mark *execution_id* as currently blocked awaiting a human answer.

    Called by :func:`ask_user` immediately before awaiting the response
    future. The specialist step-timeout watchdog consults
    :func:`is_awaiting_user` to pause its active-work clock while a human is
    being asked.
    """
    _awaiting_user.add(execution_id)


def clear_awaiting_user(execution_id: str) -> None:
    """Clear the awaiting-user flag for *execution_id* (idempotent)."""
    _awaiting_user.discard(execution_id)


def is_awaiting_user(execution_id: str) -> bool:
    """True if *execution_id* is currently blocked awaiting a human answer."""
    return execution_id in _awaiting_user


def resolve_ask_user_response(ask_id: str, answer: str) -> None:
    """Resolve a pending ask_user Future with the user's answer.

    Called from the WebSocket message handler in ai_chat.py when an
    ``ask_user_response`` message is received.

    Args:
        ask_id: The unique identifier of the ask request.
        answer: The user's response text.
    """
    entry = _pending_asks.get(ask_id)
    if entry is None:
        logger.warning("resolve_ask_user_response: no pending ask for id=%s", ask_id)
        return
    future, _ = entry
    if future.done():
        logger.warning("resolve_ask_user_response: ask_id=%s already resolved", ask_id)
        return
    future.set_result(answer)
    logger.info("ask_user response resolved: ask_id=%s", ask_id)


def cleanup_ask(ask_id: str) -> None:
    """Remove a completed or cancelled ask from the registry.

    Args:
        ask_id: The unique identifier of the ask request.
    """
    _pending_asks.pop(ask_id, None)


def cancel_asks_for_execution(execution_id: str) -> int:
    """Cancel all pending ask_user futures for a given execution.

    Called when an execution is stopped (user request or WS disconnect).

    Args:
        execution_id: The execution ID to cancel asks for.

    Returns:
        Number of futures cancelled.
    """
    cancelled = 0
    for ask_id, (future, eid) in list(_pending_asks.items()):
        if eid == execution_id:
            if not future.done():
                future.cancel()
                cancelled += 1
            cleanup_ask(ask_id)
    return cancelled


def is_ask_user_pending() -> bool:
    """True if any ask_user request is currently awaiting a human response.

    Used by the specialist step-timeout to PAUSE its deadline while a
    specialist is legitimately blocked on a human response.  Note this is
    a global predicate (any in-flight ask) -- conservative for this
    single-conversation-per-process server: it errs toward waiting rather
    than wrongly killing a specialist mid-clarification.
    """
    return any(not fut.done() for fut, _ in _pending_asks.values())


@ai_tool(
    name="ask_user",
    description=(
        "Ask the user a clarifying question and BLOCK until they answer. This "
        "is the ONLY sanctioned way to put a question to the user — never ask "
        "a question as plain text in your reply. Call this whenever you would "
        "otherwise write 'which?', 'do you want…?', or 'what should I use "
        "for…?'. When the set of possible answers is small and known, pass "
        "them as `options` so the user answers with one click instead of "
        'typing (e.g. options=["Robot Cell A","Assembly Station 1"]). Use '
        "`why` for one line of context. Prefer this over guessing or stalling "
        "— one precise question unblocks the whole task."
    ),
    permissions=[],
    category="interaction",
    risk_level=RiskLevel.LOW,
)
async def ask_user(
    question: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # type: ignore[assignment]
    *,
    why: str | None = None,
    options: Annotated[list[str] | None, BeforeValidator(_coerce_options_list)] = None,
    timeout_seconds: float = float(settings.AI_ASK_USER_TIMEOUT_SECONDS),
) -> dict[str, Any]:
    """Ask the user a clarification question and wait for a response.

    Publishes an ``ask_user`` event to the event bus. The frontend renders
    the question and sends back an ``ask_user_response`` message via
    WebSocket. The tool blocks until the response arrives or the timeout
    expires.

    Args:
        question: The question to present to the user.
        context: Injected tool execution context (provides event_bus).
        why: Optional explanation of why this question is being asked.
        options: Optional list of suggested answers the user can choose from.
        timeout_seconds: Maximum seconds to wait for a response (default 300).

    Returns:
        Dictionary with ``answer`` (the user's response) on success, or
        ``error`` if the request timed out or the event bus is unavailable.
    """
    if context is None or context._event_bus is None:
        return {"error": "Cannot ask user: no event bus available in this context"}

    ask_id = str(uuid4())
    execution_id = context._event_bus.execution_id

    # Create a Future that will be resolved by resolve_ask_user_response().
    loop = asyncio.get_running_loop()
    future: asyncio.Future[str] = loop.create_future()
    _pending_asks[ask_id] = (future, execution_id)

    expires_at = datetime.now(UTC) + timedelta(seconds=timeout_seconds)

    # Build the event payload via the typed WS schema so the frontend gets a
    # stable shape: type, question, ask_id, plus optional context/options,
    # and expires_at + timeout_seconds for a countdown.
    from app.models.schemas.ai import WSAskUserMessage

    event_data = WSAskUserMessage(
        type="ask_user",
        question=question,
        ask_id=ask_id,
        context=why,
        options=options,
        expires_at=expires_at,
        timeout_seconds=int(timeout_seconds),
    ).model_dump(mode="json", exclude_none=True)

    # Publish to the event bus so the frontend receives it.
    context._event_bus.publish(
        AgentEvent(
            event_type="ask_user",
            data=event_data,
            timestamp=datetime.now(UTC),
        )
    )
    logger.info("ask_user published: ask_id=%s, question=%.80s", ask_id, question)

    try:
        # Mark this execution as awaiting a human so the specialist
        # step-timeout PAUSES its active-work clock while we block.
        mark_awaiting_user(execution_id)
        answer = await asyncio.wait_for(future, timeout=timeout_seconds)
        return {"answer": answer}
    except TimeoutError:
        logger.warning(
            "ask_user timed out: ask_id=%s after %.0fs", ask_id, timeout_seconds
        )
        return {"error": f"User did not respond within {timeout_seconds:.0f} seconds"}
    finally:
        clear_awaiting_user(execution_id)
        cleanup_ask(ask_id)
