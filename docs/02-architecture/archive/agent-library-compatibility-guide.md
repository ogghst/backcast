# Agent Library Compatibility Guide
>
> **Status:** SUPERSEDED — Evaluation complete. DeepAgents SDK replaced by LangGraph (bare).
 Score 10/12 compatibility, low-medium migration effort. See compatibility guide for rationale.
 **Retention reason:** API contract audit is useful for evaluating future alternatives.

> **Status:** SUPERSEDED — Evaluation complete.
 Decision: Stay with LangGraph (bare). See alternatives analysis for rationale.
Reference for evaluating AI agent orchestration libraries as replacements for the `deepagents` SDK in the Backcast codebase.

Every requirement below is derived from an audit of actual code usage — not theoretical needs.

---

## 1. Dependency Map

Backcast has exactly **one import** from the `deepagents` package:

```python
# backend/app/ai/deep_agent_orchestrator.py:13
from deepagents import create_deep_agent
```

Everything else depends on the `CompiledStateGraph` object returned by `create_deep_agent()`.

```
deepagents.create_deep_agent()           ← SINGLE IMPORT POINT
    |
    +-- deep_agent_orchestrator.py       ← Calls create_deep_agent, builds middleware & subagent dicts
    |       |
    |       +-- middleware/temporal_context.py      (extends AgentMiddleware, uses ToolCallRequest)
    |       +-- middleware/backcast_security.py     (extends AgentMiddleware, uses ToolCallRequest + contextvars)
    |       +-- subagents/__init__.py               (7 plain dict configs — zero SDK dependency)
    |
    +-- agent_service.py               ← Consumes graph.astream_events(v1) and graph.ainvoke
    |       |
    |       +-- token_buffer.py        ← Per-agent token buffering
    |       +-- ai_chat.py             ← WebSocket endpoint, sends WS messages
    |
    +-- graph.py                       ← Fallback StateGraph (no SDK dependency)
    +-- state.py                       ← AgentState TypedDict (Backcast-owned)
    +-- tools/interrupt_node.py        ← Extends langgraph ToolNode (fallback path only)
```

**Key insight:** The 7 subagent configs in `subagents/__init__.py` are plain Python dicts with zero SDK imports. The coupling comes solely from how `deep_agent_orchestrator.py` transforms those dicts into the format `create_deep_agent()` expects.

---

## 2. Required Features (Must-Haves)

### R1: Factory Function Returning CompiledStateGraph

The library must provide a factory that returns a LangGraph `CompiledStateGraph` supporting both streaming and non-streaming invocation.

```python
def create_agent(
    model: str | BaseChatModel,       # MUST accept both formats
    tools: list[BaseTool],             # LangChain BaseTool instances (may be empty [])
    system_prompt: str,                # System prompt text
    subagents: list[dict] | None,      # See R9
    middleware: list[Middleware],       # See R4
    checkpointer: Any | None,           # Always None in Backcast
) -> CompiledStateGraph
```

The returned graph MUST support:

```python
# Streaming (primary path — agent_service.py:794)
async for event in graph.astream_events(
    input={"messages": [...], "tool_call_count": 0, "next": "agent"},
    config={"recursion_limit": 25, "configurable": {"thread_id": "session-uuid"}},
    version="v1",
):
    ...

# Non-streaming (agent_service.py:495)
result = await graph.ainvoke(
    input={"messages": [...], "tool_call_count": 0, "next": "agent"},
    config={"recursion_limit": 25, "configurable": {"thread_id": "session-uuid"}},
)
```

**Evidence:** `agent_service.py` lines 495 and 794.

---

### R2: `astream_events(version="v1")` Event Protocol

The codebase consumes these event types from `agent_service.py` lines 806–1085:

| Event | Required Fields | Consumed By |
|-------|----------------|-------------|
| `on_chat_model_stream` | `data.chunk` (has `.text` or `.content`) | Token streaming to WebSocket |
| `on_tool_start` | `name`, `data.input` (dict) | Tool detection, planning, subagent routing |
| `on_tool_end` | `name`, `data.output` (ToolMessage / str / dict) | Tool result capture |
| `on_tool_error` | `name`, `data.error` | Error handling |
| `on_end` | `data.output.messages` (list[BaseMessage]) | Final state extraction |

**Special detections within `on_tool_start`:**

- `name == "write_todos"` — extracts `data.input["plan"]` and `data.input["steps"]` to send `WSPlanningMessage` (`agent_service.py:849`)
- `name == "task"` — extracts `data.input["subagent_type"]` and `data.input["description"]` to send `WSSubagentMessage` (`agent_service.py:841`)

**Special detection within `on_tool_end`:**

- `name == "task"` — extracts subagent result content, saves to DB, sends `WSSubagentResultMessage` (`agent_service.py:936`)

---

### R3: State Input Format

The graph must accept this input shape (`agent_service.py:795–799`):

```python
{
    "messages": [SystemMessage(...), HumanMessage(...)],
    "tool_call_count": 0,
    "next": "agent",
}
```

Config format:

```python
{
    "recursion_limit": int,                    # from assistant_config, default 25
    "configurable": {"thread_id": str(UUID)}   # session identifier
}
```

Backcast's `AgentState` (`state.py`):

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    tool_call_count: int
    next: Literal["agent", "tools", "end"]
```

The alternative library does not need to use this exact schema internally, but must accept this input format and produce output containing at minimum `messages: list[BaseMessage]`.

---

### R4: Middleware Interface — `awrap_tool_call`

This is the **most critical coupling point**. Both Backcast middleware classes extend `AgentMiddleware` from `langchain.agents.middleware.types` and implement only ONE method.

**Required interface:**

```python
class AgentMiddleware:
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,    # See R5
        handler: Callable,           # See R4b
    ) -> ToolMessage:
        ...
```

**R4a — `ToolCallRequest` contract** (from `langgraph.prebuilt.tool_node`):

```python
class ToolCallRequest:
    tool_call: dict    # {"name": str, "id": str, "args": dict}

    def override(self, tool_call: dict) -> ToolCallRequest:
        """Create a new request with modified tool_call."""
        ...
```

**R4b — Handler contract:**

```python
async def handler(request: ToolCallRequest) -> ToolMessage:
    """Execute the tool and return result."""
    ...
```

**How TemporalContextMiddleware uses this** (`temporal_context.py:40–93`):

1. Reads `request.tool_call["name"]` and `request.tool_call["args"]`
2. Overrides temporal args (`as_of`, `branch_name`, `branch_mode`, `project_id`)
3. Creates `new_request = request.override(tool_call=new_tool_call)`
4. Returns `await handler(new_request)` — passes through to tool execution

**How BackcastSecurityMiddleware uses this** (`backcast_security.py:73–186`):

1. Reads tool name and args
2. Checks RBAC permissions — may **short-circuit** by returning `ToolMessage(content=error, tool_call_id=id)` without calling handler
3. Checks risk level, initiates approval polling if needed
4. Sets `contextvars` with `ToolContext` and `InterruptNode`
5. Returns `await handler(request)` for allowed tools

---

### R5: Middleware Must Support Request Override

The `ToolCallRequest.override()` method is used by both middleware classes to create modified requests before passing to the handler. Without this, temporal context injection breaks.

```python
# temporal_context.py:92
new_request = request.override(tool_call=new_tool_call)
return await handler(new_request)
```

---

### R6: Middleware Must Support Short-Circuit

The security middleware must be able to return a `ToolMessage` without calling the handler (permission denied, risk blocked, approval rejected).

```python
# backcast_security.py:111
if error_message:
    return ToolMessage(content=error_message, tool_call_id=tool_id)

# backcast_security.py:142
return ToolMessage(content=error_content, tool_call_id=tool_id)
```

---

### R7: Planning Tool (`write_todos`)

The codebase detects `tool_name == "write_todos"` in `on_tool_start` events (`agent_service.py:849`) to display planning progress to the user.

**Required from the library:**
- Provide a planning tool (or allow Backcast to register its own)
- The tool's `on_tool_start` event must have `data.input` containing:
  - `"plan"`: `str` — plan description
  - `"steps"`: `list` — individual step items

The `write_todos` tool is treated as an "external tool" by Backcast's security middleware — it passes through without Backcast-specific permission checks (`backcast_security.py:215–217`).

---

### R8: Subagent Delegation Tool (`task`)

The codebase detects `tool_name == "task"` in both `on_tool_start` and `on_tool_end` events (`agent_service.py:841, 936`).

**Required delegation tool contract:**
- Accepts `subagent_type: str` — which subagent to invoke
- Accepts `description: str` — task instructions for the subagent
- `on_tool_start` event has `data.input` with both fields
- `on_tool_end` event has `data.output` with the subagent's response text
- Subagent tokens stream through the **same** `astream_events` stream as the main agent

When subagents are enabled, the main agent receives an **empty** tools list (`deep_agent_orchestrator.py:131`). Its only tool is the delegation tool. All domain tools live on subagents.

---

### R9: Subagent Configuration Format

The orchestrator builds subagent dicts in this shape (`deep_agent_orchestrator.py:262–268`):

```python
{
    "name": str,                      # e.g., "project_manager", "evm_analyst"
    "description": str,               # LLM-readable description for routing decisions
    "system_prompt": str,             # Instructions for the subagent
    "tools": list[BaseTool],          # Filtered tool instances for this subagent
    "middleware": list[AgentMiddleware],  # Shared middleware stack (Temporal + Security)
}
```

7 subagents are defined in `subagents/__init__.py`:

| Subagent | Purpose | Tools |
|----------|---------|-------|
| `project_manager` | Project & WBE CRUD | 9 tools |
| `evm_analyst` | EVM metrics & performance | 8 tools |
| `change_order_manager` | Change order workflows | 8 tools |
| `cost_controller` | Cost elements & schedules | 12 tools |
| `user_admin` | User & department management | 9 tools |
| `visualization_specialist` | Diagram generation | 1 tool |
| `forecast_manager` | Forecasts & cost tracking | 16 tools |

Each subagent receives the **same** middleware stack as the main agent (TemporalContextMiddleware + BackcastSecurityMiddleware).

---

### R10: Subagent Token Streaming Through Parent

Subagent tokens must appear in the same `astream_events` stream as the main agent. The frontend distinguishes tokens by tracking `current_subagent_name` (set on `on_tool_start` for `"task"`) and routing `on_chat_model_stream` tokens accordingly.

If the alternative library streams subagent events in a separate stream, the frontend will not display subagent output in real-time.

---

### R11: `contextvars` Preservation

The security middleware passes non-serializable context via `contextvars` (`backcast_security.py:31–38, 149–150`):

```python
_current_context.set(self.context)          # ToolContext with AsyncSession
_current_interrupt_node.set(self._interrupt_node)
```

Tools retrieve these during execution via `get_context()` and `get_interrupt_node()`.

**Implication:** Tool execution must run in the same asyncio context as the middleware's `awrap_tool_call`. If the library spawns tools in separate threads, processes, or cancels the async context, `contextvars` will be lost and every tool call will fail with "Tool context not provided".

---

### R12: Model & Configuration Acceptance

The library must accept:

- **Model:** `str` (e.g., `"openai:gpt-4o"`) or `BaseChatModel` instance (e.g., `ChatOpenAI`). Backcast passes a `ChatOpenAI` instance directly.
- **System prompt:** `str`
- **Checkpointer:** `None` (Backcast never passes a checkpointer — session state is managed in the database)

---

## 3. Features from DeepAgents NOT Used

These features exist in the SDK but are never used by Backcast. An alternative library does **not** need to provide them.

| DeepAgents Feature | Used? | Notes |
|--------------------|-------|-------|
| `awrap_model_call` hook | No | Backcast middleware only uses `awrap_tool_call` |
| `before_agent` / `after_agent` hooks | No | |
| `before_model` / `after_model` hooks | No | |
| `wrap_tool_call` (sync) | No | Only async variant used |
| `wrap_model_call` (sync) | No | Only async variant used |
| `checkpointer` | No | Always `None` |
| `context_schema` | Passed but not meaningful | Actual injection happens in custom middleware |
| `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep` tools | No | SDK built-in file tools |
| `execute` (shell) tool | No | |
| `MemoryMiddleware` | No | |
| `FilesystemMiddleware` | No | |
| `SkillsMiddleware` | No | |
| `SummarizationMiddleware` | No | |
| `PatchToolCallsMiddleware` | No | |
| `AnthropicPromptCachingMiddleware` | No | |
| `HumanInTheLoopMiddleware` | No | Backcast has its own approval system |
| `CompiledSubAgent` (pre-compiled runnable) | No | Backcast uses `SubAgent` dicts only |
| `interrupt_on` parameter | No | |
| `store` / `BaseStore` | No | |
| `backend` / `BackendProtocol` | No | |
| `skills` / `memory` parameters | No | |
| `response_format` | No | |
| `cache` / `BaseCache` | No | |
| `debug` / `name` parameters | No | |

---

## 4. Optional Features (Should-Haves)

| # | Feature | Why It Matters |
|---|---------|---------------|
| S1 | Configurable planning tool name | `"write_todos"` is hardcoded in `agent_service.py:849`. A configurable name reduces coupling. |
| S2 | Configurable delegation tool name | `"task"` is hardcoded in `agent_service.py:841`. A configurable name reduces coupling. |
| S3 | `awrap_model_call` hook | The SDK's own `SubAgentMiddleware` uses this to inject system prompt instructions about available subagents. If replacing the SDK, this mechanism must still work (or the library must handle subagent prompt injection differently). |
| S4 | No `getattr(m, "tools", [])` from middleware | The SDK collects tools from middleware instances. `BackcastSecurityMiddleware` works around this with `_security_tools`. A library that doesn't collect tools from middleware avoids this workaround. |
| S5 | Graceful fallback coexistence | The codebase has a fallback path in `graph.py` that creates a plain `StateGraph`. The alternative library should not prevent this fallback from coexisting. |
| S6 | Documented/stable middleware base class | `langchain.agents.middleware.types.AgentMiddleware` is not part of LangChain's core stable API. A library with its own well-documented middleware interface would reduce fragility. |

---

## 5. Exact API Contracts

### 5.1 Factory Function

```python
def create_agent(
    model: str | BaseChatModel,
    tools: list[BaseTool],
    system_prompt: str,
    subagents: list[dict] | None = None,
    context_schema: dict | None = None,
    middleware: list[AgentMiddleware] = [],
    checkpointer: Any = None,
) -> CompiledStateGraph:
    """Returns a LangGraph CompiledStateGraph."""
```

### 5.2 Middleware Interface (minimum)

```python
class AgentMiddleware:
    """Minimum interface required by Backcast.

    Backcast only uses awrap_tool_call. All other hooks are unused.
    """

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage]],
    ) -> ToolMessage:
        """
        Intercept tool calls.

        - Can modify request via request.override(tool_call=modified)
        - Can short-circuit by returning ToolMessage without calling handler
        - Must preserve contextvars across handler invocation
        """
        ...
```

### 5.3 ToolCallRequest

```python
class ToolCallRequest:
    tool_call: dict    # {"name": str, "id": str, "args": dict}

    def override(self, tool_call: dict) -> ToolCallRequest:
        """Create new request with modified tool_call."""
        ...
```

### 5.4 Subagent Config Dict

```python
subagent_config = {
    "name": str,                           # Unique identifier (e.g., "evm_analyst")
    "description": str,                    # LLM-readable description for routing
    "system_prompt": str,                  # Instructions for this subagent
    "tools": list[BaseTool],               # Tools available to this subagent
    "middleware": list[AgentMiddleware],    # Middleware applied to this subagent
}
```

### 5.5 Event Stream Messages

```python
# Token streaming
{"event": "on_chat_model_stream", "data": {"chunk": AIMessageChunk}}
# chunk must have .text or .content attribute

# Tool start
{"event": "on_tool_start", "name": "tool_name", "data": {"input": {...}}}

# Tool end
{"event": "on_tool_end", "name": "tool_name", "data": {"output": ToolMessage | str | dict}}

# Tool error
{"event": "on_tool_error", "name": "tool_name", "data": {"error": Exception | str}}

# Stream complete
{"event": "on_end", "data": {"output": {"messages": list[BaseMessage]}}}
```

### 5.6 Tool Metadata (Backcast-side)

Tools declare metadata via the `@ai_tool` decorator. The security middleware reads this to enforce permissions and risk levels:

```python
@ai_tool(
    name="create_project",
    permissions=["project:write"],
    risk_level=RiskLevel.HIGH,
    category="projects",
)
async def create_project(context: InjectedToolArg[ToolContext], ...) -> dict:
    ...
```

The alternative library does not need to understand this decorator, but its middleware must be able to access `tool._tool_metadata` (or equivalent) to read `permissions` and `risk_level`.

---

## 6. Tight Couplings Requiring Refactoring

| # | Coupling | Location | Impact if Changed |
|---|----------|----------|-------------------|
| C1 | `langchain.agents.middleware.types.AgentMiddleware` base class | `temporal_context.py:19`, `backcast_security.py:19` | Both middleware classes must be adapted if new library has a different base |
| C2 | `langgraph.prebuilt.tool_node.ToolCallRequest` | `temporal_context.py:14`, `backcast_security.py:21` | Both middleware classes import this; must adapt if different request object |
| C3 | Hardcoded `"write_todos"` | `agent_service.py:849` | Update if planning tool has a different name |
| C4 | Hardcoded `"task"` | `agent_service.py:841, 936` | Update if delegation tool has a different name |
| C5 | `getattr(m, "tools", [])` tool collection | SDK internals | `BackcastSecurityMiddleware` uses `_security_tools` workaround; adjust if new library has different collection mechanism |
| C6 | `contextvars` for `ToolContext` / `InterruptNode` passing | `backcast_security.py:31–38` | Breaks if tools run in separate context (different thread, process, or cancelled task) |
| C7 | `InterruptNode` extends `langgraph.prebuilt.ToolNode` | `interrupt_node.py` | Only used in fallback path currently; no impact on Deep Agent path |

---

## 7. Compatibility Checklist

### Required

- [ ] Factory function returns `CompiledStateGraph` (or LangGraph-runnable equivalent)
- [ ] Returned graph supports `.astream_events(input, config, version="v1")`
- [ ] Returned graph supports `.ainvoke(input, config)`
- [ ] Accepts `list[BaseTool]` for tool binding (including empty list)
- [ ] Accepts `str | BaseChatModel` for model
- [ ] Accepts `system_prompt: str`
- [ ] Supports `checkpointer=None` (no built-in state persistence)
- [ ] Middleware with `awrap_tool_call(request, handler) -> ToolMessage` hook
- [ ] `ToolCallRequest`-like object with `.tool_call` dict and `.override()` method
- [ ] Middleware can short-circuit (return `ToolMessage` without calling handler)
- [ ] Provides planning tool (`write_todos` or equivalent with configurable name)
- [ ] Provides subagent delegation tool (`task` or equivalent with configurable name)
- [ ] Subagent config accepts `{name, description, system_prompt, tools, middleware}` dicts
- [ ] Subagent tokens stream through the parent's `astream_events` stream
- [ ] Subagent state is isolated from main agent
- [ ] Tool execution runs in same async context as middleware (preserves `contextvars`)
- [ ] Supports `recursion_limit` via config

### Optional

- [ ] Configurable planning tool name
- [ ] Configurable delegation tool name
- [ ] `awrap_model_call` middleware hook (for prompt injection)
- [ ] Does not collect tools from middleware via `getattr`
- [ ] Graceful fallback coexistence with plain `StateGraph`
- [ ] Documented/stable middleware base class

---

## 8. Migration Strategy

### Adapter Layer (single change point)

Create an adapter in `deep_agent_orchestrator.py` that translates Backcast's parameters to the new library's API. This isolates the migration to one file:

```python
# deep_agent_orchestrator.py
# Before:
from deepagents import create_deep_agent

# After:
from new_library import create_agent as _create_agent

def create_agent(...):
    # Translate Backcast params to new library format
    ...
```

### Middleware Adaptation (hardest part)

The two middleware classes depend on `AgentMiddleware` and `ToolCallRequest`. Options:

1. **If the new library provides compatible interfaces** — minimal changes, just change the import
2. **If interfaces differ** — create a thin adapter wrapping the new library's middleware interface
3. **If no middleware support** — implement tool interception at the `ToolNode` level (similar to the existing `RBACToolNode` fallback)

### Event Stream Detection

Update hardcoded tool names in `agent_service.py` if the new library uses different names for planning and delegation:

```python
# agent_service.py:849 — update if planning tool name changes
if tool_name == "write_todos":

# agent_service.py:841 — update if delegation tool name changes
if tool_name == "task":
```

### Subagent Configs (no changes)

The 7 subagent configs in `subagents/__init__.py` are plain Python dicts. Only `_build_subagent_dicts()` in the orchestrator needs adaptation to match the new library's expected format.

### Fallback Path (keep as safety net)

`graph.py` (`create_graph()`) creates a plain `StateGraph` without any SDK dependency. Keep this path intact as a fallback and for non-subagent use cases.

---

## 9. Key Files Reference

### Backcast Files

| File | Role in SDK Integration |
|------|----------------------|
| `backend/app/ai/deep_agent_orchestrator.py` | Single import point; builds middleware & subagent dicts; adapter layer |
| `backend/app/ai/agent_service.py` | Consumes `graph.astream_events(v1)`; event detection (write_todos, task) |
| `backend/app/ai/middleware/backcast_security.py` | RBAC + risk checking + approval polling; depends on AgentMiddleware + ToolCallRequest |
| `backend/app/ai/middleware/temporal_context.py` | Injects temporal params into tool args; depends on AgentMiddleware + ToolCallRequest |
| `backend/app/ai/subagents/__init__.py` | 7 subagent config dicts (pure data, zero SDK dependency) |
| `backend/app/ai/state.py` | `AgentState` TypedDict (Backcast-owned) |
| `backend/app/ai/graph.py` | Fallback `StateGraph` (no SDK dependency) |
| `backend/app/ai/tools/interrupt_node.py` | Approval flow; extends `langgraph.ToolNode` (fallback path only) |
| `backend/app/ai/tools/types.py` | `ToolContext`, `RiskLevel`, `ExecutionMode` |
| `backend/app/ai/token_buffer.py` | Per-agent token buffering |
| `backend/app/ai/tools/__init__.py` | `create_project_tools()`, `filter_tools_by_execution_mode()` |
| `backend/app/api/routes/ai_chat.py` | WebSocket endpoint; dispatches messages |

### SDK Files (for reference)

| File | Content |
|------|---------|
| `backend/.venv/.../deepagents/__init__.py` | Exports: `create_deep_agent`, `SubAgent`, `SubAgentMiddleware` |
| `backend/.venv/.../deepagents/graph.py` | `create_deep_agent()` implementation — builds middleware stack, creates subagents |
| `backend/.venv/.../deepagents/middleware/subagents.py` | `SubAgentMiddleware`, `SubAgent` TypedDict, `_build_task_tool()` |
| `backend/.venv/.../langchain/agents/middleware/types.py` | `AgentMiddleware` base class, `ToolCallRequest`, `ModelRequest` |
