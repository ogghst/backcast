# Analysis: Subagent Orchestration vs Handoff Pattern

**Date:** 2026-04-26
**Scope:** AI agent delegation architecture
**Status:** Research & Analysis

---

## Executive Summary

The Backcast AI system uses a **subagent-as-tool** pattern where a main agent delegates to ephemeral, isolated subagents via a `task` tool. This analysis evaluates migrating to the **handoff pattern** (LangGraph `langgraph-swarm`), where agents transfer control to each other within a shared graph while preserving full message history.

**Recommendation:** Do NOT do a full migration. The loss of parallel execution is too significant for Backcast's cross-domain query patterns. Instead, explore a **hybrid approach** — add handoff tools for multi-turn specialist interactions while retaining the task tool for parallel cross-domain requests.

---

## Current Architecture: Subagent-as-Tool

### Flow

```
User → Main Agent → task(description, subagent_type)
                      → Spawns ephemeral subagent graph
                      → Subagent runs with [HumanMessage(description)]
                      → Returns single result via Command(update={...})
                      → Main agent synthesizes response → User
```

### Key Components

| Component | File | Role |
|-----------|------|------|
| Orchestrator | `backend/app/ai/deep_agent_orchestrator.py` | Compiles main agent + subagents with middleware |
| Task Tool | `backend/app/ai/tools/subagent_task.py` | `build_task_tool()` factory — spawns subagents |
| Subagent Definitions | `backend/app/ai/subagents/__init__.py` | 7 specialized agents |
| RBAC Tool Node | `backend/app/ai/tools/rbac_tool_node.py` | Permission-checked tool execution |
| Security Middleware | `backend/app/ai/middleware/backcast_security.py` | Risk-based security layer |
| Tool Context | `backend/app/ai/tools/types.py` | `ToolContext`, `RiskLevel`, `ExecutionMode` |

### Subagent Registry (7 Agents)

1. **project_manager** — Projects, WBEs, cost elements, cost tracking, progress entries (30+ tools)
2. **evm_analyst** — EVM calculations, performance analysis (`EVMMetricsRead` structured output)
3. **change_order_manager** — Change order workflows, impact analysis (`ImpactAnalysisResponse`)
4. **user_admin** — User and department management
5. **visualization_specialist** — Mermaid diagram generation
6. **forecast_manager** — Forecasts and schedule baselines (`ForecastRead`)
7. **general_purpose** — Fallback with all tools

### RBAC & Tool Filtering Pipeline

Tools are filtered in a layered pipeline at agent compilation time:

1. **Execution Mode Filter**: `SAFE` → LOW only, `STANDARD` → LOW+HIGH, `EXPERT` → all
2. **Assistant Role Filter**: Ceiling from assistant config (`filter_tools_by_role`)
3. **User Role Filter**: Actual user permissions (`filter_tools_by_role`)
4. **Subagent Tool Whitelist**: Each subagent has an `allowed_tools` list for domain specialization
5. **Runtime Permission Check**: `RBACToolNode` verifies permissions at execution time
6. **Risk-Based Approval**: `InterruptNode` for HIGH/CRITICAL risk operations

This is a **one-time compilation** — filtered tools are baked into each subagent's graph.

### Context Isolation

Each subagent invocation:
- Receives a fresh state with only `[HumanMessage(description)]`
- Cannot see conversation history or prior subagent results
- Returns a single result via `Command(update={...})`
- Supports structured output extraction via `_summarize_structured_output()`

---

## Proposed Architecture: Handoff Pattern

### Flow (Swarm/Peer-to-Peer)

```
User → Agent A → handoff_to_agent_B(task_description)
                    → Agent B picks up with FULL message history
                    → Agent B responds directly to user
                    → Agent B can hand off to Agent C
```

### Flow (Supervisor)

```
User → Supervisor → create_handoff_tool(agent_name="evm_analyst")
                       → EVM Analyst processes with full context
                       → Responds directly to user
                       → Control returns to supervisor
```

### LangGraph Libraries

- **`langgraph-swarm`**: Peer-to-peer handoff between agents, shared graph with `active_agent` routing
- **`langgraph-supervisor`**: Centralized supervisor routes to specialists via handoff tools

---

## Pros of Moving to Handoff

### 1. Context Preservation

**Current problem:** Subagents receive only a `HumanMessage(description)` — the main agent must compress the entire conversation into a single description string. Complex multi-turn context (project IDs, prior calculations, user preferences) is lossy.

**Handoff benefit:** Full message history is passed between agents. The receiving agent sees everything the user and previous agents discussed. No information loss during delegation.

### 2. Reduced Token Waste

**Current problem:** Main agent must synthesize subagent results → generate summary → user reads it. If the user then asks a follow-up, the main agent re-delegates with a new description that must re-include all context.

**Handoff benefit:** Agent-to-agent transfer preserves context. Follow-up questions go directly to the specialist who already has the context. No re-explanation needed.

### 3. Simpler Delegation Code

**Current problem:** The `task` tool is a complex abstraction — `ToolRuntime`, `_EXCLUDED_STATE_KEYS`, `_validate_and_prepare_state`, structured output extraction, state isolation. ~450 lines of glue code in `subagent_task.py`.

**Handoff benefit:** `create_handoff_tool(agent_name, description)` is a ~20-line function. LangGraph handles routing, state management, and message passing natively via `Command(goto=...)`.

### 4. Direct User-Agent Interaction

**Current problem:** User talks to main agent → main agent talks to subagent → subagent returns to main agent → main agent re-summarizes to user. The specialist's expertise is filtered through a generalist.

**Handoff benefit:** Specialist agents can respond directly to the user. E.g., the EVM analyst explains metrics in its own voice without main agent reinterpretation.

### 5. Multi-Turn Specialist Conversations

**Current problem:** Each `task` invocation is stateless — the subagent has no memory of prior invocations. If the user asks "show me EVM for project X" then "what about SPI specifically?", the second call starts from scratch.

**Handoff benefit:** The EVM analyst stays active across multiple user turns. "What about SPI specifically?" is answered with full context of the prior CPI discussion.

---

## Cons of Moving to Handoff

### 1. RBAC/Tool Filtering Complexity (CRITICAL)

**Current approach:** Each subagent is compiled at creation time with a pre-filtered tool set based on execution mode, assistant role, user role, and domain whitelist. Tools are baked into each subagent graph — no runtime filtering needed.

**Handoff challenge:** In a shared graph, ALL agents share the same graph compilation. Tool filtering must happen at the **agent node level**. This is solvable (each agent node can be compiled with its own filtered tools, as the current per-subagent compilation already does), but requires careful design to ensure per-agent tool boundaries are maintained across handoffs.

### 2. Loss of Parallel Execution (SIGNIFICANT)

**Current approach:** Multiple subagents run **in parallel** via multiple `task` tool calls in a single message. Cross-domain requests (e.g., "show me project status + EVM metrics") launch `project_manager` AND `evm_analyst` concurrently.

**Handoff limitation:** Handoff is **inherently sequential** — one agent is active at a time. To handle "show me project status + EVM metrics":
- Option A: Supervisor hands off to one, then the other (2x latency)
- Option B: A combined "project_status" agent with both tool sets (bloats agent count)
- Option C: Keep a hybrid — supervisor for single-domain, task tool for cross-domain

This is the **biggest functional regression** for Backcast's use case where cross-domain queries are common (project + EVM, change order + forecast).

### 3. Structured Output Handling

**Current approach:** Subagents declare `structured_output_schema` (e.g., `EVMMetricsRead`, `ImpactAnalysisResponse`, `ForecastRead`). The task tool extracts and summarizes these via `_summarize_structured_output()`.

**Handoff challenge:** Handoff returns `Command(goto=...)` — there's no natural place to extract structured output. The specialist agent's response becomes a regular `AIMessage`. Would need either:
- Post-processing hooks to extract structured data from agent responses
- Embed structured data in conversation state via `Command(update={...})`
- Lose structured output capability

### 4. Approval Workflow Integration

**Current approach:** `InterruptNode` and `BackcastSecurityMiddleware` handle human-in-the-loop approvals for HIGH/CRITICAL risk tools. The main agent orchestrates the approval flow.

**Handoff challenge:** If a specialist agent triggers an approval request, the handoff graph must route the interrupt back to the user, then return to the **same specialist** after approval. LangGraph's interrupt mechanism works within a single graph, so this is technically possible but requires more careful wiring than the current centralized approach.

### 5. Graph Complexity and Debugging

**Current approach:** Simple graph — main agent node → tools node → loop. Subagents are black-box tool calls with clear start/end boundaries.

**Handoff challenge:** The graph becomes a multi-node state machine with routing logic, `active_agent` tracking, and conditional edges. Debugging "which agent handled what" requires tracing through graph transitions rather than reading tool call results.

### 6. Migration Effort

The current system is ~500 lines of well-tested orchestration code across:
- `deep_agent_orchestrator.py` (414 lines)
- `subagent_task.py` (453 lines)
- `subagents/__init__.py` (321 lines)
- Related middleware, security, and event bus code

Full migration would require:
- Rewriting the orchestrator to use `create_swarm()` or `create_supervisor()`
- Adapting all 7 subagent definitions to handoff format
- Rewriting the task tool as handoff tools
- Updating the event bus system (agent events, subagent events)
- Updating the WebSocket streaming layer
- Re-testing all agent interaction patterns

---

## Hybrid Approach (Recommended)

Rather than a full migration, use a **selective hybrid** that adds handoff capabilities while preserving parallel execution:

### Pattern Selection by Scenario

| Scenario | Pattern | Rationale |
|----------|---------|-----------|
| Single-domain follow-up questions | Handoff | Context preservation matters most |
| Cross-domain parallel requests | Task tool | Parallelism matters most |
| Multi-turn specialist conversations | Handoff | Avoid re-explaining context |
| One-shot structured output (EVM, forecasts) | Task tool | Structured extraction is clean |
| Change order approval workflows | Handoff | Multi-turn interaction is core to the flow |

### Implementation Sketch

1. Replace the main agent with a **supervisor** that has BOTH handoff tools AND the task tool
2. Handoff tools for agents that benefit from multi-turn context:
   - `change_order_manager` — approval workflows are inherently multi-turn
   - `project_manager` — common follow-up queries about project structures
3. Task tool retained for agents that benefit from parallel execution:
   - `evm_analyst` + `forecast_manager` — commonly invoked together
   - `visualization_specialist` — one-shot diagram generation
4. General-purpose agent remains as a handoff fallback

### Why This Works

- **No parallelism loss**: Cross-domain queries still use `task` tool for concurrent execution
- **Context continuity gained**: Multi-turn specialist interactions use handoff for full history
- **Structured output preserved**: One-shot agents continue using the existing extraction pipeline
- **Incremental adoption**: Can be introduced agent-by-agent without a big-bang migration
- **RBAC maintained**: Each agent is still compiled with its own filtered tools, regardless of pattern

---

## Summary Matrix

| Criterion | Subagent-as-Tool (Current) | Handoff (Full) | Hybrid |
|-----------|---------------------------|----------------|--------|
| Context preservation | Lossy (description-only) | Full message history | Best of both |
| Parallel execution | Native | Not supported | Selective |
| Structured output | Built-in extraction | Needs workaround | Preserved |
| RBAC/tool filtering | Per-subagent compilation | Per-node compilation | Same as current |
| Approval workflows | Main agent manages | Needs careful wiring | Both patterns |
| Code complexity | ~500 lines orchestration | ~100 lines (library) | ~300 lines |
| Migration effort | — | High | Medium |
| Debugging | Simple (tool call tracing) | Complex (graph routing) | Moderate |
| Token efficiency | Re-explains context on follow-up | No re-explanation | Best of both |

---

## Research Sources

- LangGraph Swarm library: `langgraph-swarm` on PyPI / GitHub
- LangGraph Supervisor library: `langgraph-supervisor` on PyPI / GitHub
- LangGraph docs: Multi-agent concepts, handoff patterns, swarm architecture
- Current codebase: `backend/app/ai/` directory analysis
