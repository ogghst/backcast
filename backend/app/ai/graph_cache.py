"""Caching infrastructure for the LangGraph agent system.

Provides thread-safe caches for compiled agent graphs, LLM clients, and a shared
checkpointer so that the expensive harness construction (LLM client, 45+ tools,
main graph, subagent graphs, middleware) is reused across requests instead of
rebuilt on every user prompt.

Per-request context (ToolContext, InterruptNode) is managed through ContextVar
helpers so that middleware running inside the graph can access request-scoped
data without coupling to the graph invocation signature.

Usage:
    # At request time (before invoking a cached graph):
    set_request_context(ctx, interrupt_node)
    try:
        result = await cached_graph.ainvoke(...)
    finally:
        clear_request_context()

    # Inside middleware (reads fresh context when available):
    from app.ai.graph_cache import get_request_tool_context
    ctx = get_request_tool_context() or self.context
"""

import collections
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

# ---------------------------------------------------------------------------
# Cache key dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraphCacheKey:
    """Immutable cache key for a compiled agent graph.

    Attributes:
        model_name: LLM model identifier (e.g. ``"gpt-4o"``).
        allowed_tools: Frozen set of tool names enabled for this graph.
        execution_mode: Execution mode string (``"safe"``, ``"standard"``,
            ``"expert"``).
        system_prompt_hash: SHA-256 hex digest of the system prompt template.
    """

    model_name: str
    allowed_tools: frozenset[str]
    execution_mode: str
    system_prompt_hash: str


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
# Compiled graph cache (LRU)
# ---------------------------------------------------------------------------


class CompiledGraphCache:
    """Thread-safe LRU cache for compiled LangGraph agent graphs.

    Uses :class:`collections.OrderedDict` for O(1) LRU eviction.  Maximum
    capacity defaults to 20 entries.
    """

    DEFAULT_MAX_SIZE: int = 20

    def __init__(self, max_size: int = DEFAULT_MAX_SIZE) -> None:
        self._cache: collections.OrderedDict[GraphCacheKey, object] = (
            collections.OrderedDict()
        )
        self._max_size = max_size
        self._lock = threading.Lock()

    def get(self, key: GraphCacheKey) -> object | None:
        """Retrieve a compiled graph by *key*.

        On a hit the entry is moved to the end of the ordering so it becomes
        the most-recently-used.

        Args:
            key: Cache key to look up.

        Returns:
            The compiled graph, or ``None`` if not present.
        """
        with self._lock:
            graph = self._cache.get(key)
            if graph is None:
                logger.info("CompiledGraphCache miss: key=%s", key)
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            logger.info("CompiledGraphCache hit: key=%s", key)
            return graph

    def put(self, key: GraphCacheKey, graph: object) -> None:
        """Store a compiled graph under *key*, evicting LRU if necessary.

        Args:
            key: Cache key.
            graph: Compiled LangGraph graph to cache.
        """
        with self._lock:
            if key in self._cache:
                # Already present -- move to end and update value.
                self._cache.move_to_end(key)
                self._cache[key] = graph
                return

            if len(self._cache) >= self._max_size:
                evicted_key, _ = self._cache.popitem(last=False)
                logger.info(
                    "CompiledGraphCache LRU eviction: evicted=%s, size=%d",
                    evicted_key,
                    len(self._cache),
                )

            self._cache[key] = graph
            # Move to end so it is the most-recently-used.
            self._cache.move_to_end(key)


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
