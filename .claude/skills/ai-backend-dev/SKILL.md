---
name: ai-backend-dev
description: A senior backend developer specializing in AI agent implementation. Expert in LangGraph, LangChain, WebSockets, and LangChain agent patterns. Evaluates user requests against AI architecture docs, backend coding standards, and web resources. Use for AI agent implementation, LangGraph workflows, LangChain integrations, WebSocket connections, and architectural decisions involving AI/ML backend systems.
allowed-tools: [AskUserQuestion, Read, Write, Edit, Glob, Grep, mcp__plugin_context7_context7__resolve-library-id, mcp__plugin_context7_context7__query-docs, mcp__web_reader__webReader, mcp__postgres__query, Bash]
---

# AI Backend Developer Skill

Senior backend development for AI agent systems using LangGraph, LangChain, WebSocket streaming, and LangChain agent patterns at Backcast.

## Quick Start

When working on AI backend features:

1. **Check Architecture First** - Read [`docs/02-architecture/ai-chat-developer-guide.md`](../../../../docs/02-architecture/ai-chat-developer-guide.md) for the complete reference
2. **Follow EVCS Patterns** - Use TemporalBase/TemporalService for versioned AI entities
3. **Type Safety** - MyPy strict mode, no `Any` types, explicit annotations
4. **Security First** - RBAC checks, risk-based tool filtering, approval flows

## Key Architecture Components

### AI Chat System Flow

```
WebSocket Connection (ai_chat.py)
    │
    ├─ JWT Validation (BEFORE accept)
    ├─ RBAC Check (ai-chat permission)
    │
    ├─ AgentService.chat_stream()
    │   │
    │   ├─ DeepAgentOrchestrator.create_agent()
    │   │   ├─ create_project_tools() → 66 LangChain tools
    │   │   ├─ filter_tools_by_execution_mode() → Risk filtering
    │   │   ├─ SubAgent configs (7 specialized agents)
    │   │   ├─ Middleware stack (temporal, security)
    │   │   └─ langchain_create_agent()  (LangChain native)
    │   │
    │   └─ astream_events() loop
    │       ├─ on_chat_model_stream → WSTokenMessage
    │       ├─ on_tool_start → WSToolCallMessage / WSSubagentMessage
    │       ├─ on_tool_end → WSToolResultMessage / WSSubagentResultMessage
    │       └─ on_end → WSCompleteMessage
    │
    └─ InterruptNode (approval polling)
```

### Two Execution Paths

| Path | When | Description |
|------|------|-------------|
| **LangChain Agent** (primary) | Default path (subagents enabled) | Multi-agent orchestration with `task` delegation to 7 subagents |
| **StateGraph fallback** | Subagents disabled or no valid subagent tools | Direct LangGraph `StateGraph` with agent node, tool node, conditional edges. Max 5 iterations. |

## Core Files Reference

### WebSocket & Orchestration

| File | Purpose |
|------|---------|
| `backend/app/api/routes/ai_chat.py` | WebSocket endpoint `/stream`, auth, message dispatch |
| `backend/app/ai/agent_service.py` | Main orchestration: `chat_stream()`, approval registration |
| `backend/app/ai/deep_agent_orchestrator.py` | `DeepAgentOrchestrator.create_agent()` wrapper |
| `backend/app/ai/graph.py` | `create_graph()` StateGraph fallback |
| `backend/app/ai/state.py` | `AgentState` TypedDict (messages, tool_call_count, next) |

### Subagents

| File | Purpose |
|------|---------|
| `backend/app/ai/subagents/__init__.py` | 7 subagent configs: project_manager, evm_analyst, change_order_manager, cost_controller, user_admin, visualization_specialist, forecast_manager |

### Tools

| File | Purpose |
|------|---------|
| `backend/app/ai/tools/__init__.py` | `create_project_tools()` factory, `filter_tools_by_execution_mode()` |
| `backend/app/ai/tools/types.py` | `ToolContext`, `ToolMetadata`, `RiskLevel`, `ExecutionMode` |
| `backend/app/ai/tools/decorator.py` | `@ai_tool` decorator for tool registration |
| `backend/app/ai/tools/interrupt_node.py` | `InterruptNode` — approval request/response via WebSocket |
| `backend/app/ai/tools/rbac_tool_node.py` | `RBACToolNode` — permission-aware tool node |
| `backend/app/ai/tools/subagent_task.py` | `build_task_tool()`, `TASK_SYSTEM_PROMPT` — task tool for subagent delegation |
| `backend/app/ai/tools/session_manager.py` | `ToolSessionManager` — task-local DB sessions for concurrent tool execution |

### Middleware

| File | Purpose |
|------|---------|
| `backend/app/ai/middleware/backcast_security.py` | RBAC checks + risk-based approval |
| `backend/app/ai/middleware/temporal_context.py` | Injects `as_of`, `branch_name`, `branch_mode`, `project_id` |

### Streaming

| File | Purpose |
|------|---------|
| `backend/app/ai/token_buffer.py` | `TokenBuffer`, `TokenBufferManager` — batched token sending to reduce WS overhead |

## Implementation Patterns

### Creating a New AI Tool

```python
from app.ai.tools.types import ToolContext, ai_tool, RiskLevel

@ai_tool(
    permissions=["project:read"],
    risk_level=RiskLevel.LOW,
    category="projects",
)
async def get_project_summary(
    context: InjectedToolArg[ToolContext],
    project_id: UUID,
) -> dict[str, Any]:
    """Get project summary including EVM metrics.

    Context: Used by evm_analyst subagent for quick project overview.

    Args:
        context: Injected tool context (session, user, permissions)
        project_id: Project to summarize

    Returns:
        Dict with project name, status, CPI, SPI, variance
    """
    # Access DB via context.session
    # Check permissions via context.check_permission()
    # Use context.branch_id for temporal queries
    ...
```

### Creating a New Subagent

Edit `backend/app/ai/subagents/__init__.py`:

```python
NEW_SUBAGENT: dict[str, Any] = {
    "name": "analytics_specialist",
    "description": "Advanced analytics and reporting",
    "system_prompt": """You are an analytics specialist...
    Focus on data analysis and trend detection.""",
    "allowed_tools": [
        "calculate_evm_metrics",
        "analyze_cost_variance",
        "get_project_kpis",
        # Add tool names
    ],
}
```

Then register in `ALL_SUBAGENTS` and update main agent delegation prompt.

### WebSocket Message Types

Server → Client messages are defined in `backend/app/models/schemas/ai.py`:

- `WSTokenMessage` — Streaming token from LLM
- `WSTokenBatchMessage` — Batched tokens via TokenBufferManager (reduces WS overhead)
- `WSPlanningMessage` — LangChain agent creating a plan
- `WSSubagentMessage` — Delegating to subagent
- `WSToolCallMessage` — Tool execution starting
- `WSSubagentResultMessage` — Subagent completed
- `WSAgentCompleteMessage` — Agent stream completed visually (completion indicator)
- `WSContentResetMessage` — Clear streaming buffer for new main agent bubble
- `WSApprovalRequestMessage` — Approval required
- `WSPollingHeartbeatMessage` — Approval polling heartbeat
- `WSCompleteMessage` — Stream complete
- `WSErrorMessage` — Error occurred

### Risk-Based Tool Filtering

```python
from app.ai.tools.types import RiskLevel, ExecutionMode, filter_tools_by_execution_mode

# Tool filtering pipeline
tools = create_project_tools(context)
tools = filter_tools_by_execution_mode(
    tools,
    execution_mode  # "safe", "standard", or "expert"
)
```

| Mode | LOW (read) | HIGH (write) | CRITICAL (delete) | Approval? |
|------|------------|--------------|-------------------|-----------|
| `safe` | yes | no | no | N/A |
| `standard` | yes | yes (approval) | no (blocked) | Yes, for HIGH only |
| `expert` | yes | yes | yes | No |

### Approval Flow Implementation

```python
from app.ai.tools.interrupt_node import InterruptNode

# In middleware or tool node
if risk_level >= RiskLevel.HIGH and execution_mode == "standard":
    # Triggers approval request to client
    # Polls for response up to 60 seconds
    result = await interrupt_node(
        tool_name=tool_name,
        tool_args=tool_args,
        risk_level=risk_level,
        context=context,
        session_id=session_id,
    )
```

## Security Model

### Three-Tier Security

```
Tier 1: JWT Authentication
    ↓ (ai_chat.py - before websocket.accept)
Tier 2: RBAC Permission Checking (per-tool)
    ↓ (BackcastSecurityMiddleware._check_tool_permission)
Tier 3: Risk-Based Execution Modes
    ↓ (filter_tools_by_execution_mode + approval workflow)
```

### Temporal Context Injection

Security measure — LLM cannot override temporal parameters:

```python
# Middleware injection (middleware/temporal_context.py)
# LLM might request: {"as_of": "2025-01-01", "project_id": "other-id"}
# Middleware overrides to: {"as_of": "2024-06-01", "project_id": "locked-id"}
```

Injected parameters: `as_of`, `branch_name`, `branch_mode`, `project_id`.

## Backend Coding Standards (AI-Specific)

### Type Safety

```python
# Bad
async def process_data(data: Any) -> Any:
    return data

# Good
from typing import TypeAlias
ProcessResult: TypeAlias = dict[str, str | int | float]

async def process_data(data: ToolInput) -> ProcessResult:
    return {"status": "ok", "count": 1}
```

### Docstrings for AI Tools

```python
async def calculate_evm_metrics(
    project_id: UUID,
    as_of: datetime,
    branch: str = "main",
) -> dict[str, Decimal]:
    """Calculate EVM metrics for a project.

    Context: Core EVM calculation used by evm_analyst subagent
    and dashboard reporting. Computes CPI, SPI, CV, SV.

    Args:
        project_id: Project to calculate metrics for
        as_of: Timestamp for bitemporal query (historical data)
        branch: Version control branch (default: "main")

    Returns:
        Dict with keys: cpi, spi, cv, sv, bac, ev, pv, ac

    Raises:
        ValueError: Project not found or no valid data at as_of
    """
```

### Async/Await Patterns

```python
# Bad - Missing await
result = session.execute(stmt)

# Good
result = await session.execute(stmt)

# Bad - Fire-and-forget without error handling
asyncio.create_task(background_work())

# Good - Proper error handling
task = asyncio.create_task(background_work())
task.add_done_callback(lambda t: t.exception())
```

## Common Pitfalls

### WebSocket Connection Management

```python
# Bad - No auth check before accept
@app.websocket("/stream")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()  # Too late!

# Good - Auth before accept
@app.websocket("/stream")
async def chat_stream(
    websocket: WebSocket,
    token: str = Query(...),
):
    user = await validate_token(token)
    if not user:
        await websocket.close(code=1008)
        return
    await websocket.accept()
```

### Tool Context Usage

```python
# Bad - Not using injected context
@ai_tool()
async def list_projects() -> list[Project]:
    async with get_session() as session:
        return await session.execute(...)

# Good - Using injected ToolContext
@ai_tool()
async def list_projects(
    context: InjectedToolArg[ToolContext],
) -> list[dict]:
    # context.session, context.user_id, context.branch_id
    # context.check_permission() already validated
    ...
```

### Subagent Result Handling

Handled inline in `agent_service.py:_consume_stream()` within the `on_tool_end` event handler, not via middleware.

```python
# In agent_service.py _consume_stream(), on_tool_end handler:
# 1. Extract subagent content from ToolMessage/Command/dict
# 2. Track in subagent_messages_by_main_invocation for ordered DB persistence
# 3. Send WSSubagentResultMessage to client (Activity Panel)
# 4. Flush subagent token buffer
# 5. Send WSAgentCompleteMessage (completion indicator)
# 6. Send WSContentResetMessage (clear streaming buffer)
# 7. Generate new main_invocation_id for next main agent bubble
```

## Quality Gates

Before completion, ensure:

- [ ] MyPy strict mode passes (`uv run mypy app/ai --strict`)
- [ ] Ruff linting passes (`uv run ruff check app/ai`)
- [ ] All tests pass (`uv run pytest tests/ai/ -v`)
- [ ] Test coverage ≥80%
- [ ] Docstrings on all public methods and tools
- [ ] WebSocket protocol messages follow schemas in `models/schemas/ai.py`
- [ ] Tool permissions declared in `@ai_tool` decorator
- [ ] Risk levels assigned to all tools
- [ ] Approval flow tested for HIGH tools (CRITICAL blocked in standard mode)

## Troubleshooting

### Log Markers

Search `backend/logs/app.log` for:

| Marker | Location | Meaning |
|--------|----------|---------|
| `WebSocket chat connection established` | `ai_chat.py` | Auth successful |
| `[AGENT_CREATION_START]` | `deep_agent_orchestrator.py` | Agent creation |
| `[TOOL_FILTERING]` | `deep_agent_orchestrator.py` | Tool filtering |
| `APPROVAL_REQUEST_SENT:` | `interrupt_node.py` | Approval pending |
| `[APPROVAL_GRANTED]` / `[APPROVAL_TIMEOUT]` | `backcast_security.py` | Approval result |
| `[SUBAGENT_DELEGATION]` | `agent_service.py` | Subagent called |

### Connection Closes with Code 1008

Check:
1. JWT token valid and not expired
2. Token subject contains valid user email
3. User exists in database
4. User's role has `ai-chat` permission

### Tools Not Available

Check:
1. `assistant_config.allowed_tools` whitelist includes tool
2. `execution_mode` compatible with tool `risk_level`
3. Subagent mode: main agent has NO direct tools

### Database Queries for Debugging

```sql
-- Recent AI chat sessions
SELECT id, user_id, title, project_id, created_at
FROM ai_conversation_sessions
ORDER BY created_at DESC LIMIT 20;

-- Session messages with tool calls
SELECT id, role, content,
       tool_calls IS NOT NULL as has_tool_calls
FROM ai_conversation_messages
WHERE session_id = '<uuid>'
ORDER BY created_at;

-- Active assistant configs
SELECT id, name, model_id, is_active,
       array_length(allowed_tools, 1) as tool_count
FROM ai_assistant_configs
WHERE is_active = true;
```

## External Resources

Use Context7 MCP for up-to-date library documentation:

- **LangChain**: Resolve `/langchain-ai/langchain` then query docs
- **LangGraph**: Resolve `/langchain-ai/langgraph` then query docs
- **FastAPI**: Resolve `/tiangolo/fastapi` then query docs

Use webReader MCP for current documentation:
- URL fetch for library docs and examples

## Out of Scope

This skill does NOT:

- Handle frontend React components (use frontend-developer agent)
- Create database migrations (use Alembic directly)
- Implement business logic outside AI/agent scope
- Manage infrastructure/deployment

## Related Documentation

- [AI Chat Developer Guide](../../../../docs/02-architecture/ai-chat-developer-guide.md) — Complete system reference
- [Backend Coding Standards](../../../../docs/02-architecture/backend/coding-standards.md) — General standards
- [AI Tools Migration Guide](../../../../docs/02-architecture/ai-tools-migration-guide.md) — Tool migration patterns
- [AI Execution Modes](../../../../docs/05-user-guide/ai-execution-modes.md) — User-facing execution modes
