"""Agent execution infrastructure.

Provides the event bus and runner registry that decouple agent execution
from WebSocket lifecycle, enabling reconnection to running agents and
REST invocation.

Public API:
    - :class:`AgentEvent` -- immutable event dataclass
    - :class:`AgentEventBus` -- in-memory pub/sub with bounded replay
    - :class:`AgentRunnerManager` -- singleton registry for execution buses
"""

from app.ai.execution.agent_event import AgentEvent
from app.ai.execution.agent_event_bus import AgentEventBus
from app.ai.execution.runner_manager import AgentRunnerManager

__all__ = [
    "AgentEvent",
    "AgentEventBus",
    "AgentRunnerManager",
]
