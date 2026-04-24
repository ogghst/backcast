# AI API Reference

**Version:** 1.0.0
**Last Updated:** 2026-03-09

---

## Overview

The Backcast  AI system provides a LangGraph-based agent for natural language interactions with project management data. This document describes all public interfaces for the AI system.

### Core Components

1. **AgentService**: Main service for agent orchestration
2. **Graph API**: LangGraph StateGraph compilation and execution
3. **Tool Layer**: @ai_tool decorator and tool registry
4. **WebSocket API**: Real-time streaming interface
5. **Monitoring**: Performance and execution tracking

### Caching Infrastructure

Compiled agent graphs, LLM clients, and tool lists are cached for performance.

| Component | Module | Purpose |
|-----------|--------|---------|
| `LLMClientCache` | `app.ai.graph_cache` | Thread-safe LLM client cache keyed by `(model_name, temperature, max_tokens, base_url_hash)` |
| `CompiledGraphCache` | `app.ai.graph_cache` | LRU cache (max 20) for compiled graphs keyed by `GraphCacheKey` |
| `GraphCacheKey` | `app.ai.graph_cache` | Frozen dataclass: `(model_name, frozenset(tool_names), execution_mode, system_prompt_hash, assistant_role_hash)` |
| `BackcastRuntimeContext` | `app.ai.graph_cache` | Per-request context for LangGraph Runtime |
| `shared_checkpointer` | `app.ai.graph_cache` | Singleton `MemorySaver` shared across all graph invocations |

Per-request context is managed via ContextVar helpers: `set_request_context()`, `clear_request_context()`, `get_request_tool_context()`, `get_request_interrupt_node()`.

---

## AgentService API

### Class: `AgentService`

Main service for AI agent conversation management.

```python
from app.ai.agent_service import AgentService
from sqlalchemy.ext.asyncio import AsyncSession

class AgentService:
    def __init__(self, session: AsyncSession) -> None:
        """Initialize agent service.

        Args:
            session: Database session for persistence
        """
```

#### Methods

##### `process_message()`

Process a user message and return the agent response.

```python
async def process_message(
    self,
    message: str,
    conversation_id: UUID,
    model_id: UUID,
    user_id: str
) -> AIChatResponse:
    """Process a message through the agent.

    Args:
        message: User message text
        conversation_id: Conversation session ID
        model_id: AI model to use
        user_id: User ID for RBAC

    Returns:
        AIChatResponse with agent response

    Raises:
        ValueError: If model or conversation not found
    """
```

**Performance:** <500ms for simple queries (p50)

##### `create_conversation()`

Create a new conversation session.

```python
async def create_conversation(
    self,
    assistant_id: UUID,
    user_id: str,
    title: str | None = None
) -> AIConversationSession:
    """Create a new conversation session.

    Args:
        assistant_id: AI assistant configuration
        user_id: User ID for RBAC
        title: Optional conversation title

    Returns:
        AIConversationSession object
    """
```

---

## Graph API

### Function: `create_graph()`

Create a LangGraph StateGraph for agent execution.

```python
from app.ai.graph import create_graph
from langchain_core.language_model import BaseChatModel

def create_graph(
    llm: BaseChatModel,
    tools: list[BaseTool]
) -> StateGraph:
    """Create LangGraph StateGraph.

    Args:
        llm: Language model for agent
        tools: List of tools to bind to LLM

    Returns:
        Compiled StateGraph ready for execution
    """
```

**Performance:** <100ms for graph compilation

### Function: `should_continue()`

Conditional edge function for routing.

```python
def should_continue(state: AgentState) -> Literal["agent", "tools", "end"]:
    """Determine next step in agent loop.

    Args:
        state: Current agent state

    Returns:
        "tools" if tool calls present
        "agent" if returning from tool
        "end" if finished
    """
```

### Function: `export_graphviz()`

Export graph structure for visualization.

```python
def export_graphviz(graph: StateGraph) -> str:
    """Export graph as DOT format.

    Args:
        graph: Compiled StateGraph

    Returns:
        DOT format string for Graphviz
    """
```

**Output:** Valid DOT format compatible with Graphviz

---

## Tool Layer API

### Decorator: `@ai_tool`

Decorator for creating LangGraph-compatible tools.

```python
from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import ToolContext

@ai_tool(
    name: str | None = None,
    description: str | None = None,
    permissions: list[str] | None = None,
    category: str | None = None
)
async def tool_function(
    param1: type,
    context: ToolContext
) -> dict[str, Any]:
    """Tool function."""
    pass
```

**Parameters:**
- `name`: Tool name (unique, defaults to function name)
- `description`: Tool description (defaults to docstring)
- `permissions`: Required permissions for RBAC
- `category`: Tool category for organization

**Returns:** Decorated function with tool metadata

### Function: `get_all_tools()`

Get all registered tools from registry.

```python
from app.ai.tools import get_all_tools

def get_all_tools() -> list[Callable]:
    """Get all registered AI tools.

    Returns:
        List of tool functions
    """
```

### Function: `get_tool_by_name()`

Get a specific tool by name.

```python
from app.ai.tools import get_tool_by_name

def get_tool_by_name(name: str) -> Callable | None:
    """Get tool by name.

    Args:
        name: Tool name

    Returns:
        Tool function or None if not found
    """
```

### Function: `create_project_tools()`

Create project-related tools.

```python
from app.ai.tools import create_project_tools

def create_project_tools() -> list[BaseTool]:
    """Create LangChain tools for project operations.

    Returns:
        List of LangChain BaseTool instances
    """
```

---

## ToolContext API

### Class: `ToolContext`

Context object injected into tool functions.

```python
from app.ai.tools.types import ToolContext
from sqlalchemy.ext.asyncio import AsyncSession

class ToolContext:
    """Context for tool execution."""

    @property
    def db_session(self) -> AsyncSession:
        """Database session for data access."""

    @property
    def user_id(self) -> str:
        """Current user ID."""

    async def check_permission(self, permission: str) -> bool:
        """Check if user has permission.

        Args:
            permission: Permission string to check

        Returns:
            True if user has permission, False otherwise
        """
```

---

## WebSocket API

### Endpoint: `/api/v1/chat/stream`

WebSocket endpoint for streaming conversations.

**Message Types:**

#### WSTokenMessage

Streaming token from LLM.

```python
class WSTokenMessage(BaseModel):
    type: Literal = "token"
    conversation_id: str
    token: str
```

#### WSToolCallMessage

Tool call initiated.

```python
class WSToolCallMessage(BaseModel):
    type: Literal = "tool_call"
    conversation_id: str
    tool_name: str
    tool_args: dict[str, Any]
```

#### WSToolResultMessage

Tool execution result.

```python
class WSToolResultMessage(BaseModel):
    type: Literal = "tool_result"
    conversation_id: str
    tool_name: str
    result: dict[str, Any]
```

#### WSErrorMessage

Error occurred.

```python
class WSErrorMessage(BaseModel):
    type: Literal = "error"
    conversation_id: str
    error: str
```

#### WSCompleteMessage

Conversation complete.

```python
class WSCompleteMessage(BaseModel):
    type: Literal = "complete"
    conversation_id: str
    message_id: str
```

**Performance:** <100ms to first token (p50)

---

## Monitoring API

### Class: `ToolExecutionMetrics`

Metrics for single tool execution.

```python
from app.ai.monitoring import ToolExecutionMetrics

@dataclass
class ToolExecutionMetrics:
    """Metrics for tool execution."""

    tool_name: str
    start_time: float
    end_time: float | None = None
    success: bool = True
    error: str | None = None

    @property
    def duration_ms(self) -> float:
        """Execution duration in milliseconds."""
```

### Context Manager: `monitor_tool_execution()`

Monitor tool execution with automatic metrics collection.

```python
from app.ai.monitoring import monitor_tool_execution

async with monitor_tool_execution(tool_name="list_projects") as metrics:
    # Tool execution here
    result = await some_operation()
    metrics.success = True
```

### Function: `log_tool_call()`

Log tool call for monitoring.

```python
from app.ai.monitoring import log_tool_call

def log_tool_call(
    tool_name: str,
    context: ToolContext,
    **kwargs: Any
) -> None:
    """Log tool call.

    Args:
        tool_name: Name of tool being called
        context: Tool context
        **kwargs: Tool arguments
    """
```

### Function: `log_tool_result()`

Log tool result for monitoring.

```python
from app.ai.monitoring import log_tool_result

def log_tool_result(
    tool_name: str,
    result: dict[str, Any],
    execution_time_ms: float
) -> None:
    """Log tool result.

    Args:
        tool_name: Name of tool
        result: Tool execution result
        execution_time_ms: Execution time in milliseconds
    """
```

---

## State API

### Type: `AgentState`

Agent state for LangGraph.

```python
from typing import Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

class AgentState(TypedDict):
    """State for LangGraph agent."""

    messages: Annotated[list[BaseMessage], add_messages]
    tool_call_count: int
    next: str
```

**Fields:**
- `messages`: Conversation messages (appends with add_messages)
- `tool_call_count`: Number of tool iterations
- `next`: Next step in agent flow

---

## Performance Characteristics

### Latency Targets

| Operation | Target (p50) | Target (p95) |
|-----------|-------------|-------------|
| Agent invocation | <500ms | <750ms |
| Streaming first token | <100ms | <150ms |
| Simple tool execution | <100ms | <150ms |
| Complex tool execution | <500ms | <750ms |
| Graph compilation | <100ms | <150ms |

### Throughput Targets

| Operation | Target |
|-----------|--------|
| Token streaming | >50 tokens/second |
| Concurrent requests | Linear scaling to 10x |
| Tool registry lookup | <1ms |

### Resource Usage

| Operation | Memory Target |
|-----------|---------------|
| Simple query | <10MB |
| Graph compilation | <50MB |
| Tool execution | <5MB per tool |

---

## Security Model

### Tool-Level RBAC

Tools enforce permissions via `@ai_tool` decorator:

```python
@ai_tool(permissions=["project-read"])
async def list_projects(context: ToolContext):
    # Permission checked before execution
    pass
```

### Permission Checking

1. Decorator checks `context.check_permission()` for each permission
2. All permissions must be granted (AND logic)
3. Permission denied → error response, tool not executed
4. Service layer also checks permissions (defense in depth)

### Context Isolation

- `context.user_id` is injected by system (not user-provided)
- Tools cannot accept `user_id` as parameter
- All operations scoped to current user

---

## Error Handling

### Tool Errors

Tools return error responses:

```python
{
    "error": "Permission denied: project-read required"
}
```

### Agent Errors

Agent errors are logged and returned:

```python
{
    "error": "Model not found",
    "details": "Model ID 123 not found in database"
}
```

### WebSocket Errors

Errors sent as WSErrorMessage:

```python
{
    "type": "error",
    "conversation_id": "...",
    "error": "Database connection failed"
}
```

---

## Migration Notes

### From Custom Loop to LangGraph

**Before:**
```python
# Custom loop
while True:
    response = await llm.agenerate(messages)
    if response.tool_calls:
        for tool_call in response.tool_calls:
            result = await execute_tool(tool_call)
        messages.append(result)
    else:
        break
```

**After:**
```python
# LangGraph
graph = create_graph(llm=llm, tools=tools)
result = await graph.ainvoke(initial_state)
```

### Tool Migration

**Before:**
```python
def list_projects(search: str) -> dict:
    # Custom tool
    pass
```

**After:**
```python
@ai_tool(permissions=["project-read"])
async def list_projects(search: str, context: ToolContext) -> dict:
    # Wrap service method
    service = ProjectService(context.db_session)
    return await service.get_projects(search=search)
```

---

## References

- [Tool Development Guide](/home/nicola/dev/backcast_evs/docs/02-architecture/ai/tool-development-guide.md)
- [Troubleshooting Guide](/home/nicola/dev/backcast_evs/docs/02-architecture/ai/troubleshooting.md)
- [ADR 009: LangGraph Rewrite](/home/nicola/dev/backcast_evs/docs/02-architecture/decisions/009-langgraph-rewrite.md)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

---

**Last Updated:** 2026-03-09
**API Version:** 1.0.0
