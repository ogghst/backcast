"""Caching infrastructure for the LangGraph agent system.

Provides a shared checkpointer and per-request context management through
ContextVar helpers so that middleware running inside the graph can access
request-scoped data without coupling to the graph invocation signature.

Usage:
    # At request time (before invoking a graph):
    set_request_context(ctx, interrupt_node)
    try:
        result = await graph.ainvoke(...)
    finally:
        clear_request_context()

    # Inside middleware (reads fresh context when available):
    from app.ai.graph_cache import get_request_tool_context
    ctx = get_request_tool_context() or self.context
"""

import collections.abc
import contextvars
import logging
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from langgraph.checkpoint.memory import MemorySaver

if TYPE_CHECKING:
    from app.ai.tools.interrupt_node import InterruptNode
    from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)


@dataclass
class BackcastRuntimeContext:
    """Per-request context passed via LangGraph Runtime.

    Attributes:
        user_id: Authenticated user ID.
        user_role: User role for RBAC (e.g. ``"admin"``, ``"viewer"``).
        project_id: Optional project context UUID.
        branch_id: Optional branch / change-order context UUID.
        execution_mode: AI tool execution mode string.
    """

    user_id: str
    user_role: str
    project_id: str | None = None
    branch_id: str | None = None
    execution_mode: str = "standard"


# ---------------------------------------------------------------------------
# LLM client cache
# ---------------------------------------------------------------------------

T = TypeVar("T")


class LLMClientCache:
    """Thread-safe cache for ChatOpenAI (or similar) instances.

    Avoids re-instantiating LLM clients with identical configuration across
    requests.  Instances are keyed by ``(model_name, temperature, max_tokens,
    base_url_hash)``.
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[str, float, int, str], object] = {}
        self._lock = threading.Lock()

    def get_or_create(
        self,
        key: tuple[str, float, int, str],
        factory: collections.abc.Callable[[], T],
    ) -> T:
        """Return a cached LLM client or create one via *factory*.

        Args:
            key: Tuple of ``(model_name, temperature, max_tokens,
                base_url_hash)`` uniquely identifying the client configuration.
            factory: Zero-argument callable that constructs a new client when
                the key is not present in the cache.

        Returns:
            The cached or newly created LLM client instance.
        """
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                logger.debug("LLMClientCache hit: key=%s", key)
                return cached  # type: ignore[return-value]

            logger.debug("LLMClientCache miss: key=%s", key)
            client = factory()
            self._cache[key] = client
            return client


# ---------------------------------------------------------------------------
# Shared checkpointer singleton
# ---------------------------------------------------------------------------

shared_checkpointer: MemorySaver = MemorySaver()

# ---------------------------------------------------------------------------
# Request context helpers (ContextVar)
# ---------------------------------------------------------------------------
# These are set at request time (per-WebSocket-message) and read by middleware
# that may have been constructed once and reused across many requests (cached
# graphs).  When the ContextVar is set, it takes priority over the middleware's
# own self.context / self._interrupt_node attributes.
# ---------------------------------------------------------------------------

_request_tool_context: contextvars.ContextVar["ToolContext | None"] = (
    contextvars.ContextVar("_request_tool_context", default=None)
)

_request_interrupt_node: contextvars.ContextVar["InterruptNode | None"] = (
    contextvars.ContextVar("_request_interrupt_node", default=None)
)


def set_request_context(
    tool_context: "ToolContext",
    interrupt_node: "InterruptNode | None" = None,
) -> None:
    """Set per-request context for middleware to read.

    Args:
        tool_context: The :class:`ToolContext` for the current request.
        interrupt_node: Optional :class:`InterruptNode` for human-in-the-loop
            approval workflows.
    """
    _request_tool_context.set(tool_context)
    if interrupt_node is not None:
        _request_interrupt_node.set(interrupt_node)


def clear_request_context() -> None:
    """Clear per-request context after graph invocation."""
    _request_tool_context.set(None)
    _request_interrupt_node.set(None)


def get_request_tool_context() -> "ToolContext | None":
    """Get the current request :class:`ToolContext`.

    Returns:
        The active :class:`ToolContext`, or ``None`` if none has been set.
    """
    return _request_tool_context.get()


def get_request_interrupt_node() -> "InterruptNode | None":
    """Get the current request :class:`InterruptNode`.

    Returns:
        The active :class:`InterruptNode`, or ``None`` if none has been set.
    """
    return _request_interrupt_node.get()
