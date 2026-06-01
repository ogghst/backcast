"""Type-safe enums for AI agent events and execution status."""

from enum import Enum


class AgentEventType(str, Enum):
    """Event types published by the agent during execution.

    Used in _publish() calls throughout agent_service.py and consumed
    by the frontend via WebSocket messages.
    """

    THINKING = "thinking"
    AGENT_TRANSITION = "agent_transition"
    BRIEFING_UPDATE = "briefing_update"
    PLANNING = "planning"
    SUBAGENT = "subagent"
    TOOL_CALL = "tool_call"
    SUBAGENT_RESULT = "subagent_result"
    AGENT_COMPLETE = "agent_complete"
    CONTENT_RESET = "content_reset"
    TOOL_RESULT = "tool_result"
    EXECUTION_STATUS = "execution_status"
    ASK_USER = "ask_user"
    PLAN_UPDATE = "plan_update"
    COMPLETE = "complete"
    ERROR = "error"


class ExecutionStatus(str, Enum):
    """Status values for agent execution lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    AWAITING_APPROVAL = "awaiting_approval"


# Tool names that require special handling in the event loop
TOOL_NAME_TASK = "task"
TOOL_NAME_WRITE_TODOS = "write_todos"
