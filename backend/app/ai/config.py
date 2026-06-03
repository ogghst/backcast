"""Configuration dataclasses for AI agent creation."""

import logging
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class OrchestratorMode(StrEnum):
    """Available agent orchestration strategies."""

    SUPERVISOR = "supervisor"


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for creating an agent graph.

    Encapsulates the parameters passed to orchestrator ``create_*`` methods
    so callers build a single config object instead of many keyword arguments.

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


def get_specialist_tools(
    specialist_name: str,
    defaults: list[str] | None,
) -> list[str] | None:
    """Resolve tool list for a specialist from env var override or defaults.

    Reads the ``AI_TOOLS_{SPECIALIST_NAME}`` environment variable (uppercased,
    non-alphanumeric characters replaced with underscores).  If set, the
    comma-separated value is parsed into a list:

    - ``""`` (empty) → ``None`` (no tools)
    - ``"*"`` → ``["*"]`` (wildcard / all tools)
    - ``"tool_a,tool_b"`` → ``["tool_a", "tool_b"]``

    Falls back to *defaults* when the env var is not set.

    Args:
        specialist_name: The subagent identifier (e.g. ``"project_manager"``).
        defaults: Hardcoded tool list used when no env override exists.

    Returns:
        Tool list, ``["*"]`` for wildcard, or ``None`` for no tools.
    """
    env_key = (
        "AI_TOOLS_"
        + "".join(c if c.isalnum() else "_" for c in specialist_name).upper()
    )
    env_value = os.environ.get(env_key)

    if env_value is None:
        return defaults

    env_value = env_value.strip()
    if not env_value:
        logger.info(
            "Tools for %s overridden via %s: no tools (empty)", specialist_name, env_key
        )
        return None

    tools = [t.strip() for t in env_value.split(",") if t.strip()]
    logger.info(
        "Tools for %s overridden via %s: %d tools", specialist_name, env_key, len(tools)
    )
    return tools


# ---------------------------------------------------------------------------
# System-level runtime settings (NOT configurable via UI / DB).
# Controlled via environment variables for deployment tuning.
# ---------------------------------------------------------------------------

#: Maximum estimated prompt-token count before context summarization kicks in.
AI_CONTEXT_TOKEN_LIMIT: int = int(os.environ.get("AI_CONTEXT_TOKEN_LIMIT", "120000"))

#: Percentage (0-100) of the token limit at which summarization triggers.
AI_CONTEXT_SUMMARY_THRESHOLD_PCT: int = int(
    os.environ.get("AI_CONTEXT_SUMMARY_THRESHOLD_PCT", "80")
)

#: Number of recent messages to keep unsummarized at the head of context.
AI_CONTEXT_KEEP_RECENT: int = int(os.environ.get("AI_CONTEXT_KEEP_RECENT", "8"))

#: When a multi-step plan exists, strip ALL domain tools from the supervisor
#: and force delegation via handoff tools only.
AI_DELEGATION_ENFORCED: bool = os.environ.get(
    "AI_DELEGATION_ENFORCED", "true"
).lower() in (
    "true",
    "1",
    "yes",
)

#: When true, enforce sequential tool execution (one tool call at a time).
#: Prevents DB pool exhaustion and race conditions from concurrent tool calls.
#: Set to false to allow parallel tool execution.
AI_SEQUENTIAL_TOOL_CALLS: bool = os.environ.get(
    "AI_SEQUENTIAL_TOOL_CALLS", "true"
).lower() in (
    "true",
    "1",
    "yes",
)

#: Tool-category prefix used to identify MCP tools from external servers.
AI_MCP_TOOL_CATEGORY_PREFIX: str = os.environ.get("AI_MCP_TOOL_CATEGORY_PREFIX", "mcp:")


#: Default page size for AI tool list/find operations (env-configurable).
AI_TOOLS_DEFAULT_PAGE_SIZE: int = int(
    os.environ.get("AI_TOOLS_DEFAULT_PAGE_SIZE", "50")
)

__all__ = [
    "AgentConfig",
    "OrchestratorMode",
    "get_specialist_tools",
    "AI_CONTEXT_TOKEN_LIMIT",
    "AI_CONTEXT_SUMMARY_THRESHOLD_PCT",
    "AI_CONTEXT_KEEP_RECENT",
    "AI_DELEGATION_ENFORCED",
    "AI_SEQUENTIAL_TOOL_CALLS",
    "AI_MCP_TOOL_CATEGORY_PREFIX",
    "AI_TOOLS_DEFAULT_PAGE_SIZE",
]
