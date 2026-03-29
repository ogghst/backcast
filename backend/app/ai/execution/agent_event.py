"""Agent event data structure for the execution event bus.

Provides the :class:`AgentEvent` immutable dataclass that represents a single
event produced by an agent execution (token batch, tool call, approval request,
completion, error, etc.).

Events are published to :class:`AgentEventBus` and consumed by subscribers
(WebSocket handlers, REST SSE handlers, test harnesses).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class AgentEvent:
    """Immutable event emitted during agent execution.

    Attributes:
        event_type: Categorises the event (e.g. ``"token_batch"``,
            ``"tool_call"``, ``"tool_result"``, ``"approval_request"``,
            ``"complete"``, ``"error"``).
        data: Payload dictionary carrying event-specific information.
        timestamp: UTC datetime when the event was created.
        execution_id: Optional identifier of the agent execution that produced
            this event.
        sequence: Monotonically increasing sequence number assigned by the
            :class:`AgentEventBus` at publication time.
    """

    event_type: str
    data: dict[str, object] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    execution_id: str | None = None
    sequence: int = 0
