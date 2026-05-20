"""Grouped parameter objects for agent graph creation and execution."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

if TYPE_CHECKING:
    from fastapi import WebSocket
    from langchain_deepseek import ChatDeepSeek
    from langchain_openai import ChatOpenAI

    from app.ai.execution.agent_event_bus import AgentEventBus
    from app.ai.tools.types import ToolContext
    from app.models.domain.ai import AIAssistantConfig

from app.ai.event_types import AgentEventType
from app.ai.tools.types import ExecutionMode

_logger = logging.getLogger(__name__)


@dataclass
class GraphCreationParams:
    """Parameters for _create_deep_agent_graph."""

    llm: ChatOpenAI | ChatDeepSeek
    tool_context: ToolContext
    assistant_config: AIAssistantConfig
    session_id: UUID | None = None
    enable_subagents: bool = True
    provider_type: str | None = None
    model_name: str | None = None
    available_tools: list[Any] | None = None
    event_bus: AgentEventBus | None = None
    user_role: str = "guest"
    websocket: WebSocket | None = None


@dataclass
class GraphExecutionParams:
    """Parameters for _run_agent_graph."""

    message: str
    assistant_config: AIAssistantConfig
    session_id: UUID
    user_id: UUID
    event_bus: AgentEventBus
    project_id: UUID | None = None
    branch_id: UUID | None = None
    as_of: datetime | None = None
    branch_name: str | None = None
    branch_mode: Literal["merged", "isolated"] | None = None
    execution_mode: ExecutionMode = field(default=ExecutionMode.STANDARD)
    context: dict[str, Any] | None = None


@dataclass
class GraphContext:
    """Prepared resources for agent graph execution.

    Returned by ``_prepare_graph_execution`` and passed to stream processing
    and persistence methods.
    """

    history: list[Any]  # list[BaseMessage]
    llm: Any  # ChatOpenAI | ChatDeepSeek
    graph: Any  # CompiledStateGraph
    tool_context: Any  # ToolContext
    available_tools: list[Any]
    model_name: str | None
    recursion_limit: int
    user_role: str
    interrupt_node: Any | None  # InterruptNode | None
    session_id: UUID
    event_bus: Any  # AgentEventBus
    project_id: UUID | None
    branch_id: UUID | None
    user_id: UUID
    as_of: datetime | None
    branch_name: str | None
    branch_mode: Literal["merged", "isolated"] | None
    execution_mode: ExecutionMode
    assistant_config: Any  # AIAssistantConfig


@dataclass
class StreamState:
    """Mutable state for a single agent graph execution stream.

    Groups all tracking variables that were previously scattered across the
    ``_run_agent_graph`` method body, and provides event-publishing helper
    methods that replace the closures formerly defined inline.
    """

    # Fixed context
    event_bus: Any  # AgentEventBus
    session_id: UUID
    model_name: str | None
    main_invocation_id: str

    # Tool/content tracking
    all_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    all_tool_results: list[dict[str, Any]] = field(default_factory=list)
    main_agent_segments: dict[str, list[str]] = field(default_factory=dict)
    reasoning_content_value: str | None = None
    subagent_messages: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    # Step tracking
    current_step: int = 0
    estimated_total_steps: int | None = None
    stream_start_time: float = field(default_factory=time.time)
    total_output_chars: int = 0
    tool_calls_count: int = 0

    # Agent/invocation tracking
    current_subagent_name: str | None = None
    current_invocation_id: str | None = None
    task_initiating_main_invocation_id: str | None = None
    last_entered_agent: str | None = None

    # Timing
    llm_call_start: float | None = None
    llm_call_count: int = 0
    tool_call_start: float | None = None

    # Token buffering
    token_accumulator: Any = None  # TokenUsageAccumulator -- initialised in __post_init__
    token_buffer: dict[str, list[str]] = field(default_factory=dict)

    # Status
    graph_error: Exception | None = None
    briefing_persisted: bool = False

    def __post_init__(self) -> None:
        from app.ai.token_estimator import TokenUsageAccumulator

        if self.token_accumulator is None:
            self.token_accumulator = TokenUsageAccumulator()

    # -- Event helpers (replace closures) --

    def publish(
        self, event_type: str | AgentEventType, data: dict[str, Any]
    ) -> None:
        """Publish an event to the event bus."""
        from app.ai.execution.agent_event import AgentEvent

        self.event_bus.publish(
            AgentEvent(
                event_type=event_type,
                data=data,
                timestamp=datetime.now(UTC),
            )
        )

    def flush_tokens(self, invocation_id: str | None) -> None:
        """Flush accumulated tokens for *invocation_id* to the event bus."""
        if invocation_id is None:
            return
        buffered = self.token_buffer.pop(invocation_id, [])
        if not buffered:
            return
        self.publish(
            "token_batch",
            {
                "type": "token_batch",  # wire-level only -- not in AgentEventType
                "tokens": "".join(buffered),
                "session_id": str(self.session_id),
                "source": "subagent" if self.current_subagent_name else "main",
                "subagent_name": self.current_subagent_name,
                "invocation_id": invocation_id,
            },
        )

    def publish_briefing_update(
        self,
        chain_output: Any,
        chain_name: str,
        *,
        log_label: str | None = None,
    ) -> None:
        """Extract briefing data from a chain output and publish a briefing_update event."""
        from app.ai.briefing import BriefingDocument
        from app.models.schemas.ai import WSBriefingMessage

        if not isinstance(chain_output, dict) or "briefing_data" not in chain_output:
            return
        briefing_data = chain_output.get("briefing_data") or {}
        try:
            briefing_md = BriefingDocument.model_validate(briefing_data).to_markdown()
        except Exception:
            return
        if not briefing_md:
            return
        completed = chain_output.get("completed_specialists", set())
        completed_list = sorted(completed) if isinstance(completed, set) else []
        self.publish(
            AgentEventType.BRIEFING_UPDATE,
            WSBriefingMessage(
                type=AgentEventType.BRIEFING_UPDATE,
                briefing=briefing_md,
                specialist_name=chain_name,
                completed_specialists=completed_list,
            ).model_dump(mode="json"),
        )
        if log_label:
            _logger.info(
                "[%s] name=%s | sections=%d | completed=%s",
                log_label,
                chain_name,
                len(briefing_data.get("sections", [])),
                completed_list,
            )
