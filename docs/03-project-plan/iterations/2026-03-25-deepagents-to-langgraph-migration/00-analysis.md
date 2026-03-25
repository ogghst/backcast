# Analysis: Migrate from DeepAgents SDK to Bare LangGraph

**Date:** 2026-03-25
**Scope:** Replace `from deepagents import create_deep_agent` with custom LangGraph construction while preserving 100% of existing middleware, event streaming, and token buffering infrastructure.

---

## 1. Current Architecture

### 1.1 Dependency Chain

```
deepagents.create_deep_agent()                    [SINGLE IMPORT - line 13 of deep_agent_orchestrator.py]
  |
  +-- langchain.agents.create_agent()              [langchain.agents.factory.create_agent - 1859 lines]
  |     |
  |     +-- Builds StateGraph with model node, ToolNode, middleware nodes
  |     +-- Chains wrap_model_call / awrap_model_call handlers
  |     +-- Chains wrap_tool_call / awrap_tool_call handlers
  |     +-- Adds before_agent, before_model, after_model, after_agent middleware nodes
  |     +-- Returns CompiledStateGraph
  |
  +-- deepagents.graph.create_deep_agent()         [303 lines]
        |
        +-- Adds TodoListMiddleware, SubAgentMiddleware, FilesystemMiddleware, etc.
        +-- Creates general-purpose subagent
        +-- Processes user subagents with full middleware stack
        +-- Calls langchain.agents.create_agent() with assembled middleware
        +-- Returns graph.with_config({"recursion_limit": 1000})
```

### 1.2 What DeepAgents Actually Does for Backcast

Backcast passes these to `create_deep_agent()`:
- `model`: A `BaseChatModel` instance (already resolved, NOT a string)
- `tools`: Empty list `[]` when subagents enabled, or filtered tool list when disabled
- `system_prompt`: String (Backcast's custom prompt + delegation instructions)
- `subagents`: List of 7 dicts `{name, description, system_prompt, tools, middleware}`
- `context_schema`: Dict (unused by middleware - actual injection is in custom middleware)
- `middleware`: `[TemporalContextMiddleware, BackcastSecurityMiddleware]`
- `checkpointer`: Always `None`

DeepAgents then:
1. Adds `TodoListMiddleware`, `FilesystemMiddleware`, `SubAgentMiddleware`, `SummarizationMiddleware`, `AnthropicPromptCachingMiddleware`, `PatchToolCallsMiddleware` to the stack
2. Creates a general-purpose subagent with all those middlewares
3. Processes each user subagent by prepending the same middleware stack
4. Calls `langchain.agents.create_agent()` with the full middleware chain
5. Sets `recursion_limit=1000` and returns the compiled graph

### 1.3 What Backcast Actually Uses vs. What DeepAgents Provides

**USED by Backcast:**
- `AgentMiddleware` base class and `awrap_tool_call` hook (via TemporalContextMiddleware, BackcastSecurityMiddleware)
- `ToolCallRequest` with `.override()` method
- `CompiledStateGraph` with `.astream_events(version="v1")` and `.ainvoke()`
- `SubAgentMiddleware` providing the `task` tool (with `ToolRuntime` for `state` access)
- `TodoListMiddleware` providing the `write_todos` tool
- `SubAgentMiddleware.awrap_model_call` injecting subagent system prompt instructions
- `astream_events` event types: `on_chat_model_stream`, `on_tool_start`, `on_tool_end`, `on_tool_error`, `on_end`

**NOT USED by Backcast (confirmed by code analysis):**
- `MemoryMiddleware`, `FilesystemMiddleware`, `SummarizationMiddleware`
- `AnthropicPromptCachingMiddleware`, `PatchToolCallsMiddleware`, `SkillsMiddleware`
- `HumanInTheLoopMiddleware`, `InterruptOnConfig`, `interrupt_on`
- `backend` / `StateBackend`, `store` / `BaseStore`
- `skills`, `memory`, `response_format`, `debug`, `name`, `cache`
- `awrap_model_call` hook on Backcast's own middleware (only SubAgentMiddleware uses it)
- `before_agent`, `after_agent`, `before_model`, `after_model` hooks
- `CompiledSubAgent` (pre-compiled runnable pattern)
- `checkpointer` (always None)
- `context_schema` (passed but middleware ignores it)

### 1.4 Key Insight: The Real Coupling

The coupling is NOT to `deepagents` itself. It is to `langchain.agents.create_agent()` which deepagents wraps. Specifically:

1. **`AgentMiddleware`** and **`ToolCallRequest`** come from `langchain.agents.middleware.types` - NOT from deepagents
2. **`create_agent()`** comes from `langchain.agents.factory` - NOT from deepagents
3. The `task` tool is built by `SubAgentMiddleware._build_task_tool()` which uses `StructuredTool.from_function()` with `ToolRuntime` - a LangChain feature
4. The `write_todos` tool comes from `langchain.agents.middleware.TodoListMiddleware`

**This means we can replace `create_deep_agent()` with a direct call to `langchain.agents.create_agent()` plus custom middleware, WITHOUT losing any of the middleware infrastructure.**

---

## 2. Migration Options

### Option A: Use `langchain.agents.create_agent()` Directly (Recommended)

Replace `create_deep_agent()` with `create_agent()` from `langchain.agents`, assembling only the middleware Backcast needs.

**Pros:**
- `AgentMiddleware`, `ToolCallRequest`, middleware chaining - ALL preserved (same imports)
- `astream_events`, `CompiledStateGraph` - same runtime
- Only need to build: custom `task` tool (subagent delegation), custom `write_todos` tool (or include TodoListMiddleware)
- Minimal code changes - single file (`deep_agent_orchestrator.py`)

**Cons:**
- Depends on `langchain.agents.create_agent()` which is part of the `langchain` package (already installed)
- Must implement subagent routing logic (currently in `SubAgentMiddleware._build_task_tool()`)
- Must decide: keep `TodoListMiddleware` or implement custom planning

**Estimated changes:**
- `deep_agent_orchestrator.py`: Replace `create_deep_agent()` call with `create_agent()` + custom task tool (~150 lines changed)
- New file `backend/app/ai/tools/subagent_task.py`: Custom task tool (~100 lines)
- No changes to middleware, agent_service, frontend, or tests (except test imports)

### Option B: Build Raw LangGraph StateGraph (Full DIY)

Build the entire StateGraph from scratch using `langgraph.graph.StateGraph`, `langgraph.prebuilt.ToolNode`, etc.

**Pros:**
- Full control, no dependency on `langchain.agents.create_agent()`
- Simpler graph (no middleware nodes Backcast doesn't use)

**Cons:**
- Must reimplement middleware chaining logic (~200 lines from `factory.py`)
- Must reimplement `ToolCallRequest` handling, tool call wrapping, model call wrapping
- Higher risk of subtle differences in event stream behavior
- The `ToolNode` from `langgraph.prebuilt` already supports `wrap_tool_call`/`awrap_tool_call` parameters, but the composition logic would need to be hand-written

**Estimated changes:**
- `deep_agent_orchestrator.py`: Complete rewrite (~300 lines)
- New file for middleware chaining (~200 lines)
- Higher regression risk

### Option C: Use `langchain.agents.create_agent()` + Keep `SubAgentMiddleware`

Import `SubAgentMiddleware` from deepagents but build the main agent directly.

**Pros:**
- Least code changes
- SubAgentMiddleware handles task tool, subagent routing, and prompt injection

**Cons:**
- Still depends on `deepagents` package (partial dependency)
- SubAgentMiddleware adds unwanted `awrap_model_call` hook that injects `TASK_SYSTEM_PROMPT` into every model call (this is currently desired behavior)
- Still pulls in `TodoListMiddleware` dependency through deepagents

**Estimated changes:**
- `deep_agent_orchestrator.py`: Replace `create_deep_agent()` call (~50 lines changed)

### Decision: Option A (Direct `langchain.agents.create_agent()`)

Rationale:
- Removes the `deepagents` dependency entirely
- Preserves 100% of the middleware infrastructure (same imports, same classes)
- `langchain.agents.create_agent()` is already installed (it's a dependency of deepagents)
- The custom task tool can be built using the same `StructuredTool.from_function()` + `ToolRuntime` pattern
- Lowest risk of behavioral changes in event streaming

---

## 3. Detailed Impact Analysis

### 3.1 Files That Change

| File | Change Type | Lines Affected |
|------|------------|---------------|
| `backend/app/ai/deep_agent_orchestrator.py` | **Major rewrite** | Import, `create_agent()` method, `_build_subagent_dicts()` |
| `backend/app/ai/tools/subagent_task.py` | **New file** | ~120 lines - custom task tool with ToolRuntime |
| `backend/app/ai/tools/planning.py` | **New file** (optional) | ~60 lines - custom write_todos tool, or just import TodoListMiddleware |

### 3.2 Files That Do NOT Change

| File | Reason |
|------|--------|
| `backend/app/ai/middleware/temporal_context.py` | Same `AgentMiddleware` import from `langchain.agents.middleware.types` |
| `backend/app/ai/middleware/backcast_security.py` | Same imports, same behavior |
| `backend/app/ai/agent_service.py` | Consumes `astream_events(v1)` - no change needed |
| `backend/app/ai/state.py` | Backcast-owned `AgentState` TypedDict - unchanged |
| `backend/app/ai/graph.py` | Fallback path - unchanged |
| `backend/app/ai/subagents/__init__.py` | Plain dicts - unchanged |
| `backend/app/ai/token_buffer.py` | Independent of agent construction |
| `backend/app/api/routes/ai_chat.py` | WebSocket protocol - unchanged |
| `frontend/src/features/ai/chat/` | WebSocket message protocol - unchanged |

### 3.3 Import Changes

```python
# BEFORE:
from deepagents import create_deep_agent

# AFTER:
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from app.ai.tools.subagent_task import build_task_tool
```

### 3.4 What Must Be Replicated

#### 3.4.1 The `task` Tool (Subagent Delegation)

The SDK's `_build_task_tool()` in `subagents.py` (lines 374-471) creates a `StructuredTool` that:
1. Accepts `description: str` and `subagent_type: str` parameters
2. Uses `ToolRuntime` to access `runtime.state` and `runtime.tool_call_id`
3. Looks up the subagent by `subagent_type` in a dict of compiled runnables
4. Invokes the subagent with `subagent.ainvoke({"messages": [HumanMessage(content=description)]})`
5. Returns a `Command(update={"messages": [ToolMessage(...)]})` with the final message

Key detail: The subagent is invoked via `ainvoke()` (synchronous within the tool call). This means subagent tokens DO NOT stream through the parent's `astream_events` during the tool call. However, the compatibility guide states "Subagent tokens stream through parent astream_events" (R10). This works because when the subagent graph is invoked as part of the parent's ToolNode execution, LangGraph's event propagation mechanism causes the subagent's internal events to bubble up to the parent's `astream_events` stream.

**For the migration**: We must use the same `ToolRuntime` pattern to ensure subagent state access and `Command` return work identically.

#### 3.4.2 The `write_todos` Tool (Planning)

The SDK's `TodoListMiddleware` provides this. Options:
1. **Import `TodoListMiddleware`** from `langchain.agents.middleware` directly (simplest)
2. **Build a custom planning tool** that emits the same event structure

Recommendation: Import `TodoListMiddleware` directly. It's part of `langchain` and works with `create_agent()`. The `agent_service.py` detects `tool_name == "write_todos"` and reads `data.input["plan"]` and `data.input["steps"]`.

#### 3.4.3 Subagent Prompt Injection

The SDK's `SubAgentMiddleware.awrap_model_call()` injects `TASK_SYSTEM_PROMPT` + available subagent descriptions into every model call. This tells the LLM about the `task` tool and available subagents.

For the migration: Either:
1. Include this instruction text in the main agent's `system_prompt` (simplest, and Backcast already appends delegation instructions at line 161-167)
2. Create a lightweight middleware with only `awrap_model_call` to inject the prompt

Recommendation: Include in system_prompt. Backcast already adds delegation instructions. We just need to add the `TASK_SYSTEM_PROMPT` content (the "when to use / when not to use" guidance).

#### 3.4.4 Subagent Construction

The SDK builds each subagent via `create_agent()` with its own middleware stack (TodoListMiddleware, FilesystemMiddleware, SummarizationMiddleware, etc.). For Backcast, we only need:
- The subagent's model, system_prompt, tools
- Backcast's custom middleware (TemporalContextMiddleware, BackcastSecurityMiddleware)

We do NOT need: FilesystemMiddleware, SummarizationMiddleware, AnthropicPromptCachingMiddleware, PatchToolCallsMiddleware, TodoListMiddleware (subagents don't plan).

#### 3.4.5 `recursion_limit` and Metadata

The SDK sets `recursion_limit=1000` via `.with_config()`. Backcast's `agent_service.py` sets its own `recursion_limit` from assistant config (default 25). The `.with_config()` values are OVERRIDDEN by per-invoke config, so the SDK's 1000 is not actually used.

For the migration: Set `recursion_limit` via `.with_config()` or let `agent_service.py` handle it (which it already does).

### 3.5 Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Event stream format changes | **Low** | Same `create_agent()` runtime, same `astream_events` protocol |
| Subagent token streaming breaks | **Medium** | Must use same `ToolRuntime` pattern and subgraph invocation |
| Middleware chaining order changes | **Low** | `create_agent()` handles composition identically |
| `write_todos` event format changes | **Low** | Import same `TodoListMiddleware`, same tool name and args |
| `task` tool event format changes | **Low** | Build custom tool with same name, same args (`subagent_type`, `description`) |
| `Command` return from task tool breaks | **Medium** | Must test that `Command(update=...)` works in `create_agent()` ToolNode |
| BackcastSecurityMiddleware `getattr` workaround breaks | **Low** | `create_agent()` still collects tools from `getattr(m, "tools", [])` but BackcastSecurityMiddleware uses `_security_tools` (private attr), which is NOT collected. Same behavior. |
| `contextvars` preservation | **Low** | Same async context, same tool execution path |
| `ToolCallRequest` interface changes | **None** | Same import from `langgraph.prebuilt.tool_node` |

### 3.6 What `langchain.agents.create_agent()` Provides That We Need

Reviewing `factory.py` (1859 lines), `create_agent()`:
1. Resolves model strings to instances (Backcast passes instances - no-op)
2. Converts system_prompt to SystemMessage (Backcast passes strings - works)
3. Collects middleware tools via `getattr(m, "tools", [])` - BackcastSecurityMiddleware uses `_security_tools` (safe)
4. Chains `awrap_tool_call` handlers into composed wrapper - handles both Backcast middlewares
5. Creates `ToolNode(tools=available_tools, awrap_tool_call=composed_wrapper)` - exactly what we need
6. Chains `awrap_model_call` handlers - only SubAgentMiddleware uses this (if we import it)
7. Builds StateGraph with model node, tools node, middleware nodes
8. Adds conditional edges for tool routing
9. Compiles and returns `CompiledStateGraph`

**All of this is what Backcast needs.** No need to reimplement.

---

## 4. Open Questions

1. **Do we need `TodoListMiddleware` for the main agent?** The `write_todos` tool is detected in `agent_service.py` to send `WSPlanningMessage`. If we remove it, the frontend won't show planning progress. Recommendation: Keep it.

2. **Do subagents need `TodoListMiddleware`?** Currently, subagents in the SDK get their own `TodoListMiddleware`. But `agent_service.py` only detects `write_todos` on the main agent (it tracks `current_subagent_name` and routes events). Subagent `write_todos` calls would not be specially handled. Recommendation: Subagents do NOT need `TodoListMiddleware`.

3. **Should we keep the `general-purpose` subagent?** The SDK adds one by default. Backcast's `enable_subagents=True` means only Backcast's 7 domain subagents are used. The `general-purpose` subagent is NOT in Backcast's subagent list. Recommendation: Do NOT add it.

4. **Can we use `StructuredTool.from_function()` with `ToolRuntime`?** Yes, this is the same pattern the SDK uses. `ToolRuntime` is available from `langchain.tools`.

5. **Does `create_agent()` from `langchain.agents` work with `Command` returns from tools?** Yes - the `ToolNode` in `create_agent()` handles `Command` returns (line 924: `ToolNode(tools=..., awrap_tool_call=...)`). The task tool returns `Command(update={"messages": [ToolMessage(...)]})`.

---

## 5. Success Criteria

1. `from deepagents import create_deep_agent` is removed from the codebase
2. `deepagents` is removed from `pyproject.toml` dependencies
3. Both middleware classes (`TemporalContextMiddleware`, `BackcastSecurityMiddleware`) require zero code changes
4. `agent_service.py` event detection (`write_todos`, `task`) works identically
5. WebSocket message protocol is unchanged (frontend requires zero changes)
6. `astream_events(version="v1")` produces the same event types and structure
7. Subagent tokens stream through parent's event stream
8. `contextvars`-based `ToolContext` passing works identically
9. All existing tests pass (with updated imports)
10. `recursion_limit` is properly configurable via `agent_service.py`

---

## 6. Estimated Effort

- **deep_agent_orchestrator.py rewrite**: ~150 lines (replace `create_deep_agent` call, update imports, adapt subagent construction)
- **New `subagent_task.py`**: ~120 lines (build_task_tool function)
- **Test updates**: ~50 lines (update imports, add task tool tests)
- **pyproject.toml**: Remove `deepagents` dependency
- **Total**: ~320 lines of new/changed code across 4 files
- **Risk**: Low-Medium (same runtime, same protocol, same middleware)
