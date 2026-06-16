"""Configuration dataclasses for AI agent creation."""

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.config import settings

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


# ---------------------------------------------------------------------------
# System-level runtime settings (NOT configurable via UI / DB).
# Controlled via environment variables (backend/.env) for deployment tuning.
# Sourced from the pydantic ``Settings`` singleton so .env is honored; re-exported
# here under stable names for all existing ``from app.ai.config import ...`` callers.
# ---------------------------------------------------------------------------

#: Maximum estimated prompt-token count before context summarization kicks in.
AI_CONTEXT_TOKEN_LIMIT: int = settings.AI_CONTEXT_TOKEN_LIMIT

#: Percentage (0-100) of the token limit at which summarization triggers.
AI_CONTEXT_SUMMARY_THRESHOLD_PCT: int = settings.AI_CONTEXT_SUMMARY_THRESHOLD_PCT

#: Number of recent messages to keep unsummarized at the head of context.
AI_CONTEXT_KEEP_RECENT: int = settings.AI_CONTEXT_KEEP_RECENT

#: When a multi-step plan exists, strip ALL domain tools from the supervisor
#: and force delegation via handoff tools only.
AI_DELEGATION_ENFORCED: bool = settings.AI_DELEGATION_ENFORCED

#: When true, enforce sequential tool execution (one tool call at a time).
#: Prevents DB pool exhaustion and race conditions from concurrent tool calls.
#: Set to false to allow parallel tool execution.
AI_SEQUENTIAL_TOOL_CALLS: bool = settings.AI_SEQUENTIAL_TOOL_CALLS

#: Hard cap on tool calls within a single specialist invocation.  Bounded low
#: because a specialist does a focused 2-4 calls/step; the flat 25 default drove
#: the 120s timeout cascade.  The supervisor's own budget is separate (it uses
#: the graph recursion_limit via the initial state set by agent_service).
AI_SPECIALIST_MAX_TOOL_ITERATIONS: int = settings.AI_SPECIALIST_MAX_TOOL_ITERATIONS

#: Specialist-specific ContextGuard token limit.  Much lower than the supervisor's
#: ``AI_CONTEXT_TOKEN_LIMIT`` (120k) because specialists hit GLM's ~25-30k-token
#: latency knee (and the 120s active-time limit) far below the supervisor threshold.
#: A live e2e showed a specialist running away to 31k prompt_tokens at the 6th
#: tool call; 24k sits safely under the knee (trim starts at ~80% ~ 19k).
AI_SPECIALIST_CONTEXT_TOKEN_LIMIT: int = settings.AI_SPECIALIST_CONTEXT_TOKEN_LIMIT

#: Specialist-specific ContextGuard keep-recent (tool CALL/RESULT pairs kept
#: verbatim; older summarized).  Lower than the supervisor's 8 because a
#: specialist does a focused 2-4 calls/step.
AI_SPECIALIST_CONTEXT_KEEP_RECENT: int = settings.AI_SPECIALIST_CONTEXT_KEEP_RECENT

#: Tool-category prefix used to identify MCP tools from external servers.
AI_MCP_TOOL_CATEGORY_PREFIX: str = settings.AI_MCP_TOOL_CATEGORY_PREFIX


#: Default page size for AI tool list/find operations (env-configurable).
AI_TOOLS_DEFAULT_PAGE_SIZE: int = settings.AI_TOOLS_DEFAULT_PAGE_SIZE

__all__ = [
    "AgentConfig",
    "OrchestratorMode",
    "AI_CONTEXT_TOKEN_LIMIT",
    "AI_CONTEXT_SUMMARY_THRESHOLD_PCT",
    "AI_CONTEXT_KEEP_RECENT",
    "AI_DELEGATION_ENFORCED",
    "AI_SEQUENTIAL_TOOL_CALLS",
    "AI_SPECIALIST_MAX_TOOL_ITERATIONS",
    "AI_SPECIALIST_CONTEXT_TOKEN_LIMIT",
    "AI_SPECIALIST_CONTEXT_KEEP_RECENT",
    "AI_MCP_TOOL_CATEGORY_PREFIX",
    "AI_TOOLS_DEFAULT_PAGE_SIZE",
]
