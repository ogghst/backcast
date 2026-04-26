"""Configuration dataclasses for AI agent creation."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for creating a Deep Agent via DeepAgentOrchestrator.

    Encapsulates the parameters passed to ``create_agent`` so callers build
    a single config object instead of passing many keyword arguments.

    Attributes:
        allowed_tools: Optional list of tool names to include (filters all tools).
        subagents: Optional subagent configurations (uses defaults if None and enabled).
        checkpointer: Optional shared checkpointer for graph state persistence.
        context_schema: Optional context schema for StateGraph construction.
        assistant_role: Optional RBAC role for the assistant (e.g. "ai-viewer").
        user_role: Optional per-user RBAC role for tool visibility filtering.
    """

    allowed_tools: list[str] | None = None
    subagents: list[dict[str, Any]] | None = None
    checkpointer: Any | None = None
    context_schema: type | None = None
    assistant_role: str | None = None
    user_role: str | None = None
    use_supervisor: bool = False


__all__ = ["AgentConfig"]
