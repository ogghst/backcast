"""Singleton registry for agent execution event buses.

Provides :class:`AgentRunnerManager` -- a process-level registry that maps
execution identifiers to their :class:`AgentEventBus` instances. The registry
enables WebSocket handlers and REST endpoints to locate a running execution's
event bus by execution ID so they can subscribe and receive live events.

Usage::

    from app.ai.execution.runner_manager import runner_manager

    bus = runner_manager.create_bus("exec-123")
    # ... agent publishes events to bus ...

    # From a WebSocket handler on another connection:
    bus = runner_manager.get_bus("exec-123")
    if bus is not None:
        queue = bus.subscribe()
        # forward events to WebSocket
"""

import logging

from app.ai.execution.agent_event_bus import AgentEventBus

logger = logging.getLogger(__name__)


class AgentRunnerManager:
    """Process-level registry mapping execution IDs to event buses.

    Thread-safety is not required because the deployment model is
    single-process with a single asyncio event loop.
    """

    def __init__(self) -> None:
        self._buses: dict[str, AgentEventBus] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def active_execution_count(self) -> int:
        """Return the number of currently tracked executions."""
        return len(self._buses)

    def create_bus(self, execution_id: str) -> AgentEventBus:
        """Create and register a new event bus for *execution_id*.

        Args:
            execution_id: Unique identifier for the agent execution.

        Returns:
            The newly created :class:`AgentEventBus`.

        Raises:
            ValueError: If a bus already exists for *execution_id*.
        """
        if execution_id in self._buses:
            raise ValueError(
                f"Event bus already exists for execution {execution_id}"
            )

        bus = AgentEventBus(execution_id=execution_id)
        self._buses[execution_id] = bus
        logger.info(
            "Created event bus for execution %s (active=%d)",
            execution_id,
            len(self._buses),
        )
        return bus

    def get_bus(self, execution_id: str) -> AgentEventBus | None:
        """Look up the event bus for *execution_id*.

        Args:
            execution_id: Execution identifier to look up.

        Returns:
            The :class:`AgentEventBus` if the execution is tracked, or
            ``None`` if not found.
        """
        return self._buses.get(execution_id)

    def remove_bus(self, execution_id: str) -> None:
        """Remove and close the event bus for *execution_id*.

        Safe to call even if no bus exists for the given ID.

        Args:
            execution_id: Execution identifier to remove.
        """
        bus = self._buses.pop(execution_id, None)
        if bus is not None:
            bus.close()
            logger.info(
                "Removed event bus for execution %s (active=%d)",
                execution_id,
                len(self._buses),
            )
        else:
            logger.debug(
                "No event bus to remove for execution %s", execution_id
            )


# Module-level singleton (same pattern as shared_checkpointer in graph_cache).
runner_manager = AgentRunnerManager()
