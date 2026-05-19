"""Grouped parameter objects for agent graph creation and execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

if TYPE_CHECKING:
    from fastapi import WebSocket
    from langchain_deepseek import ChatDeepSeek
    from langchain_openai import ChatOpenAI

    from app.ai.execution.agent_event_bus import AgentEventBus
    from app.ai.tools.types import ToolContext
    from app.models.domain.ai import AIAssistantConfig

from app.ai.tools.types import ExecutionMode


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
