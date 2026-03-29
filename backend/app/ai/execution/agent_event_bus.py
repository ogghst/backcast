"""In-memory publish/subscribe event bus for agent execution events.

Provides :class:`AgentEventBus` -- an asyncio-based fan-out channel that
decouples agent execution from consumers (WebSocket handlers, REST SSE
handlers, test harnesses).

Features:

- **Bounded event log**: a fixed-size circular buffer (``collections.deque``)
  retains the last *N* events for late-subscriber replay without growing
  unbounded.
- **Subscriber queues**: each subscriber receives its own
  :class:`asyncio.Queue` so that a slow consumer cannot block others.
- **Replay**: new subscribers can replay events starting from a given sequence
  number to catch up on missed events (e.g. after WebSocket reconnection).
"""

import asyncio
import collections
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # avoid circular imports; AgentEvent is only used as a type hint

from app.ai.execution.agent_event import AgentEvent

logger = logging.getLogger(__name__)

# Default maximum number of events kept in the replay buffer.
DEFAULT_MAX_LOG_SIZE: int = 1000


class AgentEventBus:
    """In-memory pub/sub event bus for a single agent execution.

    The bus maintains a bounded circular buffer of events for replay and
    delivers every published event to all registered subscriber queues.

    Args:
        execution_id: Identifier of the agent execution this bus serves.
        max_log_size: Maximum number of events retained for replay.
            Defaults to :data:`DEFAULT_MAX_LOG_SIZE`.
    """

    def __init__(
        self,
        execution_id: str,
        max_log_size: int = DEFAULT_MAX_LOG_SIZE,
    ) -> None:
        self._execution_id = execution_id
        self._log: collections.deque[AgentEvent] = collections.deque(
            maxlen=max_log_size,
        )
        self._subscribers: set[asyncio.Queue[AgentEvent]] = set()
        self._sequence: int = 0
        self._completed: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def execution_id(self) -> str:
        """Return the execution identifier this bus is bound to."""
        return self._execution_id

    @property
    def event_count(self) -> int:
        """Return the total number of events published (including evicted)."""
        return self._sequence

    @property
    def subscriber_count(self) -> int:
        """Return the number of active subscriber queues."""
        return len(self._subscribers)

    @property
    def is_completed(self) -> bool:
        """Return whether the execution has completed or errored.

        Set to ``True`` once a ``"complete"`` or ``"error"`` event is
        published.  Late subscribers can check this to decide whether
        replay is sufficient or if live subscription is still needed.
        """
        return self._completed

    def subscribe(self) -> asyncio.Queue[AgentEvent]:
        """Create and register a new subscriber queue.

        Returns:
            An :class:`asyncio.Queue` that will receive all subsequently
            published events.
        """
        queue: asyncio.Queue[AgentEvent] = asyncio.Queue()
        self._subscribers.add(queue)
        logger.debug(
            "Subscriber added to bus %s (total=%d)",
            self._execution_id,
            len(self._subscribers),
        )
        return queue

    def unsubscribe(self, queue: asyncio.Queue[AgentEvent]) -> None:
        """Remove a subscriber queue.

        Args:
            queue: The queue previously returned by :meth:`subscribe`.
        """
        self._subscribers.discard(queue)
        logger.debug(
            "Subscriber removed from bus %s (total=%d)",
            self._execution_id,
            len(self._subscribers),
        )

    def publish(self, event: AgentEvent) -> AgentEvent:
        """Publish an event to all subscribers and append to the event log.

        Assigns the next monotonically increasing sequence number and the
        bus's ``execution_id`` to the event, then fans out to every subscriber
        queue.

        Args:
            event: The event to publish. Its ``sequence`` and ``execution_id``
                fields are overwritten by the bus.

        Returns:
            The published event with assigned sequence number and
            execution_id.
        """
        self._sequence += 1
        published = AgentEvent(
            event_type=event.event_type,
            data=event.data,
            timestamp=event.timestamp,
            execution_id=self._execution_id,
            sequence=self._sequence,
        )

        self._log.append(published)

        # Mark the bus as completed when a terminal event is published.
        if published.event_type in ("complete", "error"):
            self._completed = True

        dead_queues: list[asyncio.Queue[AgentEvent]] = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(published)
            except asyncio.QueueFull:
                logger.warning(
                    "Subscriber queue full on bus %s -- dropping event %d",
                    self._execution_id,
                    published.sequence,
                )
            except Exception:
                # Queue may be closed; collect for removal.
                dead_queues.append(queue)

        for queue in dead_queues:
            self._subscribers.discard(queue)

        return published

    def replay(self, since_sequence: int = 0) -> list[AgentEvent]:
        """Replay events from the bounded log starting after *since_sequence*.

        Useful for late subscribers (e.g. WebSocket reconnection) to catch up
        on events they missed.

        Args:
            since_sequence: Return events whose sequence number is strictly
                greater than this value. Pass ``0`` to replay all buffered
                events.

        Returns:
            A list of events ordered by sequence number. May be empty if no
                buffered events match or if the events have been evicted from
                the circular buffer.
        """
        return [e for e in self._log if e.sequence > since_sequence]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the bus, clearing subscribers and the event log."""
        self._subscribers.clear()
        self._log.clear()
        logger.debug("Bus %s closed", self._execution_id)
