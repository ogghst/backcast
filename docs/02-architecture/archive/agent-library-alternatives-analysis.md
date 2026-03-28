# Agent Library Alternatives Analysis

>
> **Status:** SUPERSEDED — The evaluation is complete. LangGraph (bare) was selected.
 Score 10/12 compatibility, low-medium migration effort.
 See compatibility guide for rationale.
 **Retention reason:** Comparison data useful if reconsidering in 6+ months.

Evaluation of 5 candidate libraries against the Backcast compatibility guide, with forward-looking assessment for MCP server attachment and orchestration configuration.

**Date:** March 2026
>
> **Status:** SUPERSEDED — Evaluation complete.
> **Decision:** LangGraph (bare) selected. Score 10/12 compatibility.
> **Retention reason:** Comparison data useful if reconsidering in 6+ months.

---

## Candidates Evaluated

| Library | Version | GitHub Stars | License | Maintainer |
|---------|---------|-------------|---------|------------|
| **LangGraph (bare)** | 0.2+ | ~15k | MIT | LangChain |
| **OpenAI Agents SDK** | 0.13.1 | 20.3k | MIT | OpenAI |
| **Google ADK** | latest | active | Apache 2.0 | Google |
| **CrewAI** | latest | ~30k+ | MIT | CrewAI Inc |
| **Pydantic AI** | latest | active | MIT | Pydantic |

---

## 1. LangGraph (Bare — No DeepAgents SDK Wrapper)

### Compatibility with Backcast Guide

| Requirement | Status | Notes |
|------------|--------|-------|
| R1: Factory → CompiledStateGraph | **Native** | This IS LangGraph's core output |
| R2: `astream_events(v1)` protocol | **Native** | LangGraph invented this protocol |
| R3: State input format | **Native** | Direct match with `AgentState` |
| R4: Middleware `awrap_tool_call` | **Native** | `AgentMiddleware` from `langchain.agents.middleware.types` — same import Backcast already uses |
| R5: `ToolCallRequest.override()` | **Native** | From `langgraph.prebuilt.tool_node` — same import Backcast already uses |
| R6: Middleware short-circuit | **Native** | Return `ToolMessage` without calling handler |
| R7: Planning tool | **DIY** | No built-in `write_todos` — must implement custom planning tool |
| R8: Subagent delegation | **Via subgraphs** | No built-in `task` tool — must implement via LangGraph subgraphs |
| R9: Subagent config format | **DIY** | Must adapt `_build_subagent_dicts()` to create subgraph-based agents |
| R10: Subagent token streaming | **Native** | Subgraph events propagate to parent `astream_events` |
| R11: `contextvars` preservation | **Native** | Same asyncio context throughout |
| R12: Model/config acceptance | **Native** | Full control over model, prompt, config |

**Compatibility score: 10/12 required (2 DIY)**

### MCP Support

`langchain-mcp-adapters` (official LangChain package) converts MCP server tools into `BaseTool` instances that work natively with LangGraph agents. Multi-server support via `MultiServerMCPClient`:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "postgres": {"command": "uvx", "args": ["mcp-server-postgres"]},
    "filesystem": {"url": "http://localhost:8000/mcp", "transport": "http"},
})
tools = await client.get_tools()  # → list[BaseTool] — plug into create_agent()
```

**MCP maturity:** First-class. The adapters are maintained by LangChain, support stdio/SSE/streamable-HTTP transports, and produce standard `BaseTool` instances.

### Orchestration Configuration

LangGraph Platform provides:
- `langgraph.json` config files for graph definition
- LangGraph Studio for visual editing
- Deployment to LangGraph Cloud / self-hosted
- Human-in-the-loop via interrupt nodes

**Orchestration config maturity:** High. But the platform is a separate paid product from the open-source library.

### Pros
- **Zero migration** for the middleware layer — same `AgentMiddleware` and `ToolCallRequest` classes
- Already the foundation; DeepAgents was just a wrapper on top
- `langchain-mcp-adapters` is mature and directly produces `BaseTool` instances
- Full control over graph topology, state schema, event streaming
- Backcast's existing `graph.py` fallback already proves the pattern works

### Cons
- Must re-implement planning (`write_todos`) and delegation (`task`) tools
- Must build subgraph-based subagent system (no built-in `SubAgentMiddleware`)
- Steeper learning curve for complex orchestration
- No built-in evaluation tools

### Migration Effort

**Low-Medium.** The middleware classes (`temporal_context.py`, `backcast_security.py`) require zero changes. The main work is:
1. Replace `create_deep_agent()` call with custom LangGraph `StateGraph` construction
2. Build a custom `task` tool that invokes subgraphs
3. Build a custom `write_todos` tool (or use `langgraph.prebuilt.create_react_agent` with planning prompt)
4. Update `agent_service.py` event detection (or keep same tool names)

---

## 2. OpenAI Agents SDK

### Compatibility with Backcast Guide

| Requirement | Status | Notes |
|------------|--------|-------|
| R1: Factory → CompiledStateGraph | **FAIL** | Returns `Runner` result, not `CompiledStateGraph`. No `astream_events` API |
| R2: `astream_events(v1)` | **FAIL** | Uses `Runner.run_stream()` — completely different streaming API |
| R3: State input format | **FAIL** | Uses `Agent` + `Runner` pattern, not `AgentState` |
| R4: Middleware `awrap_tool_call` | **FAIL** | Uses `FunctionTool` with `on_invoke_tool`, no middleware chain |
| R5: `ToolCallRequest.override()` | **FAIL** | No equivalent — tools are plain functions |
| R6: Middleware short-circuit | **Partial** | `Guardrails` can intercept, but different pattern |
| R7: Planning tool | **N/A** | No built-in planning; agents just reason natively |
| R8: Subagent delegation | **Native** | `handoffs` and `agent-as-tool` pattern |
| R9: Subagent config format | **Different** | `Agent(name, instructions, tools, handoffs)` |
| R10: Subagent token streaming | **Different** | Each agent has own `Runner`; no shared event stream |
| R11: `contextvars` preservation | **FAIL** | Tools are plain functions; no async context chain like LangGraph |
| R12: Model/config acceptance | **Partial** | Supports `str | BaseChatModel` via LiteLLM, but OpenAI-first |

**Compatibility score: 2/12 required (10 FAIL, 2 partial)**

### MCP Support

Native MCP tool integration via `MCPToolset`:

```python
from agents import Agent
from agents.mcp import MCPToolset

agent = Agent(
    name="Assistant",
    tools=MCPToolset({"server": "http://localhost:8000/mcp"}),
)
```

**MCP maturity:** First-class. Built-in support as of v0.8+.

### Orchestration Configuration

- **No config file format** — agents defined in Python code only
- **No visual editor** for agent topology
- **Tracing** via built-in `trace` system and OpenAI dashboard
- **Sessions** for conversation history management
- **Guardrails** for input/output validation

**Orchestration config maturity:** Low. No declarative config format.

### Pros
- 20.3k stars, fastest-growing agent framework
- Native MCP support (first-class)
- Simple, clean API — lowest learning curve
- Built-in tracing and guardrails
- Active development (v0.13.1 released March 25, 2026)

### Cons
- **Fundamentally incompatible** with Backcast's architecture — no `astream_events`, no `CompiledStateGraph`, no `AgentMiddleware`, no `ToolCallRequest`
- Vendor-leaning despite LiteLLM multi-model support
- `contextvars`-based ToolContext passing would break entirely
- Replacing the entire event streaming layer in `agent_service.py` would be a massive rewrite
- No built-in planning tool (write_todos equivalent)
- Subagent token streaming through shared event stream is not the design model

### Migration Effort

**Very High.** Essentially a rewrite of `agent_service.py`'s entire event consumption layer, both middleware classes, the WebSocket message protocol mapping, and the token buffer system. The adapter would need to translate OpenAI's `Runner` streaming to Backcast's WebSocket message types.

---

## 3. Google ADK (Agent Development Kit)

### Compatibility with Backcast Guide

| Requirement | Status | Notes |
|------------|--------|-------|
| R1: Factory → CompiledStateGraph | **FAIL** | Uses `LlmAgent` + `Runner` pattern, no `CompiledStateGraph` |
| R2: `astream_events(v1)` | **FAIL** | Uses `Runner.run_async()` — different event model |
| R3: State input format | **FAIL** | Uses ADK's own state model (event-based) |
| R4: Middleware `awrap_tool_call` | **FAIL** | Uses `Tool` callbacks with `on_invoke_tool` |
| R5: `ToolCallRequest.override()` | **FAIL** | No equivalent |
| R6: Middleware short-circuit | **Partial** | `ToolConfirmation` (HITL) available |
| R7: Planning tool | **N/A** | No built-in planning |
| R8: Subagent delegation | **Native** | `sub_agents` parameter on `LlmAgent` |
| R9: Subagent config format | **Different** | `LlmAgent(name, model, instruction, tools, sub_agents)` |
| R10: Subagent token streaming | **Different** | ADK has its own event model |
| R11: `contextvars` preservation | **Unknown** | Unclear if tool execution preserves async context |
| R12: Model/config acceptance | **Partial** | Gemini-optimized, model-agnostic but Gemini-biased |

**Compatibility score: 2/12 required (10 FAIL, 2 partial)**

### MCP Support

Native MCP tool support — ADK lists "MCP tools" as a key feature:

```python
from google.adk.tools import mcp_tool

agent = Agent(
    name="assistant",
    tools=[mcp_tool("http://localhost:8000/mcp")],
)
```

**MCP maturity:** First-class. Listed as a key feature in README.

### Orchestration Configuration

- **Agent Config** — declarative agent definition without code (YAML/JSON)
- **Built-in development UI** for testing and debugging
- **Evaluation tools** (`adk eval`) for agent assessment
- **Deploy to Cloud Run or Vertex AI Agent Engine**

**Orchestration config maturity:** High. Agent Config is a unique differentiator.

### Pros
- Agent Config (declarative agent definition) — strong match for future config needs
- Built-in evaluation and development UI
- First-class MCP support
- Apache 2.0 license (permissive)
- Google backing

### Cons
- **Fundamentally incompatible** with Backcast's LangGraph-based architecture
- Gemini-optimized — may have rough edges with OpenAI models
- No `astream_events`, no `CompiledStateGraph`, no `AgentMiddleware`
- Younger ecosystem than LangGraph
- Would require full rewrite of event consumption and middleware layers
- Google ecosystem lock-in risk (Cloud Run, Vertex AI)

### Migration Effort

**Very High.** Same fundamental issue as OpenAI SDK — completely different execution model. Would need to rewrite `agent_service.py`, both middleware classes, and the event streaming layer.

---

## 4. CrewAI

### Compatibility with Backcast Guide

| Requirement | Status | Notes |
|------------|--------|-------|
| R1: Factory → CompiledStateGraph | **FAIL** | Uses `Crew` + `Process` pattern, no `CompiledStateGraph` |
| R2: `astream_events(v1)` | **FAIL** | Uses `Crew.kickoff()` with callback-based streaming |
| R3: State input format | **FAIL** | Uses `Task` objects and `Crew` state |
| R4: Middleware `awrap_tool_call` | **FAIL** | Tools are `BaseTool` subclasses with `callback` |
| R5: `ToolCallRequest.override()` | **FAIL** | No equivalent |
| R6: Middleware short-circuit | **Partial** | Can raise exceptions in tools |
| R7: Planning tool | **N/A** | No built-in planning |
| R8: Subagent delegation | **Native** | `Agent` with delegation via `Crew` process |
| R9: Subagent config format | **Different** | `Agent(role, goal, backstory, tools)` in `Crew` |
| R10: Subagent token streaming | **Different** | CrewAI streams per-agent but not via `astream_events` |
| R11: `contextvars` preservation | **Unknown** | Tools are `BaseTool` subclasses |
| R12: Model/config acceptance | **Partial** | Model-agnostic, but specific API |

**Compatibility score: 2/12 required (10 FAIL, 2 partial)**

### MCP Support

Community contributions exist (`crewai-tools-mcp`), but no first-party MCP support:

```python
from crewai_tools_mcp import MCPServer

agent = Agent(
    role="Analyst",
    tools=[MCPServer(server_url="http://localhost:8000/mcp")],
)
```

**MCP maturity:** Low. Third-party adapter only, not first-party.

### Orchestration Configuration

- `Crew` class with `Agent`, `Task`, `Process` definitions in Python
- **No declarative config format** (no YAML/JSON agent config)
- **No visual editor**
- **Memory** system for cross-run context
- **Sequential and hierarchical** process patterns

**Orchestration config maturity:** Low. Code-only definition.

### Pros
- 30k+ stars — most popular agent framework by stars
- Intuitive "team of specialists" mental model
- Simple API — lowest learning curve for multi-agent
- Built-in memory system
- Model-agnostic

### Cons
- **Fundamentally incompatible** with Backcast's LangGraph architecture
- No `astream_events`, no `CompiledStateGraph`, no `AgentMiddleware`
- CrewAI's "crew" paradigm doesn't match Backcast's subagent delegation model
- No first-party MCP support
- Production readiness concerns at scale
- Limited streaming control — can't hook into individual token events

### Migration Effort

**Very High.** Same fundamental issue — completely different execution and event model.

---

## 5. Pydantic AI

### Compatibility with Backcast Guide

| Requirement | Status | Notes |
|------------|--------|-------|
| R1: Factory → CompiledStateGraph | **FAIL** | Uses `Agent` + dependency injection, no `CompiledStateGraph` |
| R2: `astream_events(v1)` | **FAIL** | Uses `agent.run_stream()` — different streaming model |
| R3: State input format | **FAIL** | Uses Pydantic model-based messages |
| R4: Middleware `awrap_tool_call` | **FAIL** | Uses `Tool` decorator with `run` function |
| R5: `ToolCallRequest.override()` | **FAIL** | No equivalent |
| R6: Middleware short-circuit | **Partial** | Can raise `ModelRetry` |
| R7: Planning tool | **N/A** | No built-in planning |
| R8: Subagent delegation | **Native** | `agent.as_tool()` pattern |
| R9: Subagent config format | **Different** | `Agent(name, instructions, tools)` with DI |
| R10: Subagent token streaming | **Different** | Each agent has own stream |
| R11: `contextvars` preservation | **Unknown** | Uses dependency injection, not contextvars |
| R12: Model/config acceptance | **Partial** | Model-agnostic via providers |

**Compatibility score: 2/12 required (10 FAIL, 2 partial)**

### MCP Support

No built-in MCP support. Would need custom adapter:

```python
# No official integration — would need to:
# 1. Connect to MCP server via mcp Python SDK
# 2. Convert MCP tools to Pydantic AI Tool objects
```

**MCP maturity:** None. No first-party or mature third-party adapter.

### Orchestration Configuration

- **Code-only** — agents defined in Python
- **Dependency injection** for context management
- **No declarative config** or visual editor
- **Structured output** by default (Pydantic's strength)
- **Type safety** — Pydantic models for all I/O

**Orchestration config maturity:** Low. Code-only, but excellent type safety.

### Pros
- Best-in-class type safety (Pydantic foundation)
- Clean dependency injection model
- Model-agnostic
- Excellent structured output
- Growing community (Pydantic ecosystem)

### Cons
- **Fundamentally incompatible** with Backcast's LangGraph architecture
- No `astream_events`, no `CompiledStateGraph`, no `AgentMiddleware`
- No MCP support
- Newer, smaller ecosystem
- Would require full rewrite of event consumption and middleware

### Migration Effort

**Very High.** Same fundamental issue as all non-LangGraph frameworks.

---

## Comparative Summary

### Backcast Compatibility (Required Features)

| Library | Score | Migration |
|---------|-------|----------|
| **LangGraph (bare)** | 10/12 | **Low-Medium** |
| OpenAI Agents SDK | 2/12 | Very High |
| Google ADK | 2/12 | Very High |
| CrewAI | 2/12 | Very High |
| Pydantic AI | 2/12 | Very High |

### MCP Support

| Library | Maturity | Notes |
|---------|----------|-------|
| **LangGraph** | **First-class** | `langchain-mcp-adapters` — produces `BaseTool` instances |
| **OpenAI Agents SDK** | **First-class** | Built-in `MCPToolset` |
| **Google ADK** | **First-class** | Listed as key feature |
| CrewAI | Third-party | `crewai-tools-mcp` community adapter |
| Pydantic AI | None | No adapter available |

### Orchestration Configuration

| Library | Declarative Config | Visual Editor | Evaluation |
|---------|-----------------|-------------|-----------|
| **LangGraph Platform** | `langgraph.json` | LangGraph Studio | Via LangSmith |
| **Google ADK** | Agent Config (YAML) | Built-in Dev UI | Built-in `adk eval` |
| OpenAI Agents SDK | No | No | Built-in tracing |
| CrewAI | No | No | No |
| Pydantic AI | No | No | No |

### Future-Readiness (MCP + Orchestration Config)

| Library | MCP | Config | Assessment |
|---------|-----|-------|-----------|
| **LangGraph** | Excellent | Good | Best fit. `langchain-mcp-adapters` is mature. LangGraph Platform provides config and deployment. |
| **OpenAI Agents SDK** | Excellent | Poor | Strong MCP but no config story. Would need to build config management. |
| **Google ADK** | Excellent | Excellent | Best MCP + config combo on paper. But fundamentally incompatible with Backcast. |
| CrewAI | Poor | Poor | Weak on both fronts. |
| Pydantic AI | None | Poor | Weakest on future needs. |

---

## Recommendation

### Primary Path: LangGraph (Bare)

**Rationale:** LangGraph is already the foundation. DeepAgents was a thin wrapper. Going bare eliminates the wrapper while keeping 100% compatibility with the existing middleware, event streaming, and state management.

**What changes:**
- Replace `create_deep_agent()` call with custom `StateGraph` construction in `deep_agent_orchestrator.py`
- Build a custom `task` tool using LangGraph subgraphs (the `CompiledSubAgent` pattern already exists in the SDK)
- Build a custom planning tool (or use a system prompt that structures planning into todo items)
- Add `langchain-mcp-adapters` for MCP server tool integration

**What stays the same:**
- Both middleware classes (zero changes)
- `ToolCallRequest` and `request.override()` (same LangGraph API)
- `astream_events(version="v1")` protocol
- `AgentState` TypedDict
- Token buffer system
- WebSocket message protocol
- `contextvars`-based ToolContext passing

**Estimated migration:** Replace `deep_agent_orchestrator.py` internals (~200 lines) and add planning/delegation tool definitions (~100-150 lines). No changes to middleware, event handling, or frontend.

### Secondary Consideration: Hybrid Approach

If you want to explore non-LangGraph frameworks for future projects while keeping Backcast on LangGraph, consider:

- **OpenAI Agents SDK** for simpler agent projects where you don't need the full Backcast security stack
- **Google ADK** if Gemini becomes a first-class model option and you want Agent Config

Both can coexist as separate agent endpoints alongside the LangGraph-based main chat system.

---

## Key Takeaway

The compatibility guide's most critical finding is that Backcast's architecture is deeply tied to **LangGraph's runtime** (`CompiledStateGraph`, `astream_events`, `ToolCallRequest`, `AgentMiddleware`). Only LangGraph satisfies these contracts natively. Every other framework would require a complete rewrite of the event streaming, middleware, and token buffering layers.

For MCP and orchestration configuration — both are well-served by the LangGraph ecosystem (`langchain-mcp-adapters` and LangGraph Platform).
