"""Protocol-agnostic execution lifecycle coordinator.

Provides :class:`ExecutionLifecycle` -- a single-server, in-memory coordinator
that tracks the lifetime of an agent execution independently of the transport
that started it (WebSocket today; REST SSE / other transports later).

Responsibilities (transport-agnostic):

- Owns the bounded ``execution_id -> _ExecutionContext`` registry that pairs a
  graceful-stop :class:`asyncio.Event`, the execution's
  :class:`AgentEventBus`, and the set of attached transport **presence
  tokens**.
- Bridges transport disconnects to graceful stop with a grace window: when the
  last token detaches, a grace-stop task is scheduled; a re-attach before the
  window elapses cancels the stop.  A live execution is never forcibly
  cancelled -- ``request_stop`` only *sets* the same stop_event the pausable
  deadline and the supervisor loop already honour.
- ``terminate`` is the single idempotent terminal-cleanup entry point that
  cancels pending ask_user prompts and removes the event bus.  The DB status
  write, ``active_execution_id`` clear, and terminal event publish STAY in
  ``AgentService``'s finalize paths, which CALL ``terminate``.

The registry eviction is **non-destructive**: on overflow it drops the OLDEST
entry and logs a warning.  It never ``.set()``s a live execution's stop_event
(the old ``AgentService._stop_events`` registry DID, which could spuriously
stop a live execution -- this fixes that bug).

Observers are **opaque hashable presence tokens** (e.g. a per-connection
``object()``).  The lifecycle does NOT deliver events through the tokens --
delivery stays the transport's own per-execution bus subscription (the
fire-and-forget ``publish`` fan-out that existed here reordered chat events
and was removed).  The tokens only represent "a transport is present" so
grace-stop / cleanup decisions can be made without holding transport state.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Hashable
from dataclasses import dataclass, field

from app.ai.execution.agent_event_bus import AgentEventBus
from app.ai.execution.runner_manager import runner_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


# Type alias for an opaque per-transport presence token.  Callers pass a single
# hashable object (e.g. ``object()``) per connection and reuse it across all
# attaches for that connection.  The token carries no methods.
ObserverToken = Hashable


@dataclass
class _ExecutionContext:
    """Internal per-execution state held by :class:`ExecutionLifecycle`."""

    stop_event: asyncio.Event
    bus: AgentEventBus
    observers: set[ObserverToken] = field(default_factory=set)
    grace_task: asyncio.Task[None] | None = None
    terminal: bool = False


class ExecutionLifecycle:
    """Process-level coordinator for agent execution lifetimes.

    Single-server deployment model: there is one event loop and one instance
    of this class (the module-level :data:`execution_lifecycle` singleton).
    No locking is required.
    """

    def __init__(self) -> None:
        self._contexts: dict[str, _ExecutionContext] = {}
        # Tokens attached before ``register`` ran land here, keyed by
        # execution_id.  ``register`` pulls them into the new context so
        # presence-tracking is robust regardless of the start/attach ordering
        # (the WS may attach before ``start_execution``'s ``register``).
        self._pending: dict[str, set[ObserverToken]] = {}

    # ------------------------------------------------------------------
    # Registry: register / attach / detach
    # ------------------------------------------------------------------

    def register(
        self,
        execution_id: str,
        stop_event: asyncio.Event,
        bus: AgentEventBus,
    ) -> None:
        """Register (or overwrite) the context for *execution_id*.

        Eviction is **non-destructive**: when the registry is at capacity the
        OLDEST entry is dropped with a warning.  It is NEVER ``.set()`` -- a
        dropped live execution simply stops being tracked; its own
        ``start_execution`` finally block still tears it down.

        Any presence tokens attached to *execution_id* BEFORE this call (held
        in ``_pending``) are pulled into the new context's observer set, so a
        transport that attached during the small window before
        ``start_execution`` registered is not lost.

        Args:
            execution_id: Unique execution identifier.
            stop_event: The graceful-stop event the supervisor / pausable
                deadline consult.  Owned by the caller (created by
                ``AgentService._register_stop_event``).
            bus: The event bus for this execution.
        """
        max_entries = settings.AI_EXECUTION_REGISTRY_MAX
        if execution_id not in self._contexts and len(self._contexts) >= max_entries:
            oldest_key = next(iter(self._contexts))
            evicted = self._contexts.pop(oldest_key, None)
            # Cancel any in-flight grace task on the evicted entry so it does
            # not later call request_stop on a context that is no longer
            # tracked (the execution keeps running, just untracked here).
            if evicted is not None and evicted.grace_task is not None:
                evicted.grace_task.cancel()
            logger.warning(
                "ExecutionLifecycle registry reached %d entries — dropped oldest "
                "(execution_id=%s); the dropped execution continues untracked",
                max_entries,
                oldest_key,
            )
        ctx = _ExecutionContext(stop_event=stop_event, bus=bus)
        # Pull in any tokens attached before register ran (attach-before-register race).
        pending = self._pending.pop(execution_id, None)
        if pending:
            ctx.observers |= pending
        self._contexts[execution_id] = ctx

    def attach(self, execution_id: str, token: ObserverToken) -> bool:
        """Attach a transport presence token to *execution_id*.

        Cancels any pending grace-stop task for this execution (a reconnect
        within the grace window should NOT stop the run).

        If *execution_id* is not yet registered (the
        ``start_execution`` task has not reached ``register`` yet) the token
        is held in ``_pending`` and ``register`` will pull it in.  In that
        case this returns ``True`` -- the transport is considered attached as
        soon as the execution registers.

        Args:
            execution_id: Execution to observe.
            token: An opaque hashable presence token (one per transport
                connection, reused across all attaches for that connection).

        Returns:
            ``True`` if the execution is alive (registered and not terminal,
            or pending registration) and the token was recorded; ``False`` if
            the execution is already terminal (the token is not recorded).
        """
        ctx = self._contexts.get(execution_id)
        if ctx is None:
            # Attach-before-register race: hold the token so ``register``
            # pulls it in.  ``detach`` / ``terminate`` also discard from
            # ``_pending`` so nothing leaks if register never runs.
            self._pending.setdefault(execution_id, set()).add(token)
            return True
        if ctx.terminal:
            return False
        # A re-attach within the grace window aborts the pending stop.
        if ctx.grace_task is not None:
            ctx.grace_task.cancel()
            ctx.grace_task = None
        ctx.observers.add(token)
        return True

    def detach(self, execution_id: str, token: ObserverToken) -> None:
        """Detach a transport presence token from *execution_id*.

        If no tokens remain AND the execution is not terminal, schedule a
        grace-stop task: after ``settings.AI_DISCONNECT_GRACE_SECONDS``, if
        STILL no tokens and not terminal, call :meth:`request_stop`
        (immediate).  The task is stored on the context so :meth:`attach` /
        :meth:`terminate` can cancel it.

        Safe to call for an unknown execution or a token that was never
        attached (also discards from ``_pending`` -- no-op if absent).
        """
        # Discard a pending token too (attach-before-register that never
        # registered, or detached during the same window).
        pending = self._pending.get(execution_id)
        if pending is not None:
            pending.discard(token)
            if not pending:
                self._pending.pop(execution_id, None)

        ctx = self._contexts.get(execution_id)
        if ctx is None:
            return
        ctx.observers.discard(token)
        if not ctx.observers and not ctx.terminal and ctx.grace_task is None:
            ctx.grace_task = asyncio.create_task(
                self._grace_stop(execution_id),
                name=f"execution-grace-stop-{execution_id}",
            )

    async def _grace_stop(self, execution_id: str) -> None:
        """Wait the grace window, then request_stop if still unobserved."""
        try:
            await asyncio.sleep(settings.AI_DISCONNECT_GRACE_SECONDS)
        except asyncio.CancelledError:
            # Re-attach or terminate cancelled us -- clean exit.
            return
        ctx = self._contexts.get(execution_id)
        if ctx is None or ctx.terminal:
            return
        if not ctx.observers:
            logger.info(
                "ExecutionLifecycle: grace window expired with no observers — "
                "requesting stop for execution %s",
                execution_id,
            )
            ctx.grace_task = None
            self.request_stop(execution_id)
        else:
            ctx.grace_task = None

    # ------------------------------------------------------------------
    # Stop signalling
    # ------------------------------------------------------------------

    def request_stop(self, execution_id: str) -> bool:
        """Signal a running execution to stop gracefully.

        Sets the context's ``stop_event`` (the pausable deadline + supervisor
        check honour it) AND cancels any pending ``ask_user`` human-wait
        futures for this execution.

        Cancelling pending asks is essential: when the supervisor (or a
        specialist) is blocked inside ``ask_user``'s
        ``await asyncio.wait_for(future, AI_ASK_USER_TIMEOUT_SECONDS)``,
        the surrounding ``astream_events`` ``__anext__`` step is suspended
        inside LangGraph's streaming machinery and the graph-level pausable
        deadline's ``wait_for`` tick does NOT reliably re-fire to consult
        ``should_stop`` (verified live: ticks stop, execution runs to the
        300s ask_user timeout instead of honoring the stop).  Cancelling
        the ask future here resolves it immediately -- ``ask_user`` catches
        ``CancelledError`` and returns a synthetic value, the supervisor
        tool call completes, and the graph-level deadline / supervisor
        stop check then finalizes the execution as ``stopped`` within ~1s.

        Does NOT cancel any task or remove any registry entry beyond the
        ask futures -- terminal teardown happens in :meth:`terminate`,
        called from the finalize paths once the run actually ends.

        Args:
            execution_id: The execution to stop.

        Returns:
            ``True`` if the execution was found and signalled, ``False`` if it
            is unknown or already terminal.
        """
        ctx = self._contexts.get(execution_id)
        if ctx is None or ctx.terminal:
            logger.warning(
                "[EXECUTION_LIFECYCLE] request_stop: unknown/terminal execution %s",
                execution_id,
            )
            return False
        ctx.stop_event.set()
        # Cancel any in-flight ask_user so a human-wait does not hold the
        # graph past the stop (see docstring).  Idempotent with terminate's
        # own ask-cancel; calling it here unblocks the graph promptly rather
        # than waiting for the ask_user internal timeout.
        cancelled_asks = self._cancel_asks(execution_id)
        logger.info(
            "[EXECUTION_LIFECYCLE] Stop signalled for execution %s "
            "(ask_user futures cancelled=%d)",
            execution_id,
            cancelled_asks,
        )
        return True

    def is_stopping(self, execution_id: str) -> bool:
        """True if *execution_id* is registered and its stop_event is set."""
        ctx = self._contexts.get(execution_id)
        if ctx is None:
            return False
        return ctx.stop_event.is_set()

    # ------------------------------------------------------------------
    # Terminal cleanup
    # ------------------------------------------------------------------

    def terminate(self, execution_id: str) -> None:
        """Idempotent terminal cleanup for *execution_id*.

        Cancels any grace task, marks the context terminal, cancels pending
        ask_user prompts, removes the event bus, and drops the context from
        the registry.  Also discards any pending tokens for *execution_id*.
        Safe to call multiple times and for an unknown execution (no-op).

        The DB status write, ``active_execution_id`` clear, and terminal event
        publish are intentionally NOT done here -- those stay in
        ``AgentService``'s finalize paths, which call this method.
        """
        # Drop any presence tokens held in the attach-before-register window.
        self._pending.pop(execution_id, None)

        ctx = self._contexts.pop(execution_id, None)
        if ctx is None:
            # Already terminated (or never registered) -- still make a
            # best-effort sweep of ask_user + bus so a stray call after a
            # registry drop does not leak either.
            self._cancel_asks(execution_id)
            return
        ctx.terminal = True
        if ctx.grace_task is not None:
            ctx.grace_task.cancel()
            ctx.grace_task = None
        self._cancel_asks(execution_id)
        runner_manager.remove_bus(execution_id)
        logger.info(
            "[EXECUTION_LIFECYCLE] Terminated execution %s (observers detached=%d)",
            execution_id,
            len(ctx.observers),
        )

    @staticmethod
    def _cancel_asks(execution_id: str) -> int:
        """Best-effort cancel of pending ask_user prompts for *execution_id*.

        Returns the number of ask_user futures cancelled (0 if none or on
        error) so callers (``request_stop``, ``terminate``) can log it.
        """
        try:
            from app.ai.tools.ask_user import cancel_asks_for_execution

            return cancel_asks_for_execution(execution_id)
        except Exception:
            logger.error(
                "[EXECUTION_LIFECYCLE] Failed to cancel ask_user prompts for %s",
                execution_id,
                exc_info=True,
            )
            return 0


# Module-level singleton (mirrors runner_manager / shared_checkpointer).
execution_lifecycle = ExecutionLifecycle()
