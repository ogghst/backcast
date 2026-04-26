# Analysis: Subagent Orchestration vs Handoff Pattern

**Date:** 2026-04-26
**Scope:** AI agent delegation architecture
**Status:** Research & Analysis

---

## Executive Summary

The Backcast AI system uses a **subagent-as-tool** pattern where a main agent delegates to ephemeral, isolated subagents via a `task` tool. This analysis evaluates migrating to the **handoff pattern** (LangGraph `langgraph-swarm`), where agents transfer control to each other within a shared graph while preserving full message history.

**Recommendation:** Migrate to the **supervisor + handoff pattern** as the primary delegation mechanism. Context preservation is more valuable than parallel execution — typical requests are complex, multi-turn, and benefit far more from agents seeing full conversation history than from concurrent subagent launches. Parallel execution via task tool can be retained as a secondary mechanism for explicit batch-style operations, but should not be the default path.

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

## Recommended Approach: Supervisor + Handoff (Primary), Task Tool (Secondary)

### Design Rationale

Typical user requests are complex and multi-turn — users ask about a project, drill into cost elements, request EVM analysis, then follow up with forecast comparisons. The current pattern loses all accumulated context at each subagent boundary, forcing the main agent to compress and re-explain on every delegation. This is the primary pain point; parallel execution speed is secondary.

**Priority: Context preservation > Execution parallelism**

### Architecture

```
                    ┌─────────────────┐
                    │   Supervisor     │
                    │  (main router)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │ handoff      │ handoff       │ handoff
              ▼              ▼               ▼
     ┌──────────────┐ ┌───────────┐ ┌──────────────┐
     │ project_     │ │ evm_      │ │ change_order_│
     │ manager      │ │ analyst   │ │ manager      │
     └──────┬───────┘ └───────────┘ └──────────────┘
            │ handoff (any agent can hand off to any other)
            ▼
     ┌──────────────┐
     │ forecast_    │  ...
     │ manager      │
     └──────────────┘
```

### How It Works

1. **Supervisor** receives the user message and decides which specialist should handle it
2. Supervisor calls `handoff_to_<agent>(task_description)` via `Command(goto=agent_name)`
3. Specialist agent picks up with **full message history** — sees everything discussed so far
4. Specialist processes the request, can use its domain tools, respond to user directly
5. If the request spans domains, specialist hands off to another specialist (with full context)
6. After completing, control can return to supervisor for synthesis/follow-up routing
7. **Task tool retained** as a secondary path for explicit parallel batch operations

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary delegation | Handoff (supervisor pattern) | Full context continuity across turns |
| Secondary delegation | Task tool (preserved) | Optional parallel execution for batch ops |
| Agent routing | Supervisor decides + peer handoff | Supervisor for initial routing, agents can hand off to peers |
| State management | Shared graph state | All agents see full message history |
| Tool filtering | Per-agent compiled tools | Each agent gets its own filtered tool set (existing pattern) |
| Structured output | Embed in graph state via Command(update={...}) | Replace task tool extraction with state-based approach |
| Approval workflows | InterruptNode within shared graph | Same mechanism, now the active specialist handles it |

### Migration Path (Incremental)

**Phase 1 — Supervisor + Handoff Infrastructure**
- Introduce `langgraph-supervisor` or implement `create_swarm()` from `langgraph-swarm`
- Replace main agent with supervisor that has handoff tools for all 7 specialists
- Each specialist is a node in the shared graph with its own compiled tools
- Keep task tool as secondary mechanism

**Phase 2 — Migrate Specialists to Handoff Nodes**
- Convert `project_manager` and `change_order_manager` first (highest multi-turn value)
- Convert `evm_analyst` and `forecast_manager` (common follow-up chains)
- Convert `user_admin` and `visualization_specialist`

**Phase 3 — Structured Output Adaptation**
- Replace `_summarize_structured_output()` with state-based extraction
- Specialists emit structured data via `Command(update={structured_output: ...})`
- Supervisor reads structured output from shared state for synthesis

**Phase 4 — Event Bus & Streaming Updates**
- Update `AgentEventBus` to emit handoff events (agent_enter, agent_exit)
- Update WebSocket streaming to show which agent is active
- Update frontend chat to display agent transitions

### RBAC & Security Considerations

The existing security layer maps well to the handoff pattern:

- **Per-agent tool compilation** (current) works identically — each agent node gets its own filtered tool set based on execution mode, roles, and domain whitelist
- **BackcastSecurityMiddleware** applies per-agent — same middleware stack, just running within the shared graph
- **InterruptNode** for approvals — the active specialist triggers interrupts, user approves, specialist continues
- **Risk levels** unchanged — LOW/HIGH/CRITICAL filtering per agent as today
- **No new attack surface** — handoff doesn't bypass any existing security layers

### What Changes from Current System

| Aspect | Current | After Migration |
|--------|---------|-----------------|
| Context at delegation | Description string only | Full message history |
| Follow-up questions | Re-delegate from scratch | Specialist continues with context |
| Cross-domain queries | Parallel subagents | Sequential handoff (slower but richer) |
| Main agent role | Synthesizer of subagent results | Router + optional synthesis |
| Structured output | Task tool extraction | State-based in graph |
| Debugging | Tool call tracing | Graph transition tracing |
| Code surface | ~500 lines custom orchestration | ~150 lines (library-driven) |

---

## Summary Matrix

| Criterion | Subagent-as-Tool (Current) | Handoff (Full) | Recommended |
|-----------|---------------------------|----------------|-------------|
| Context preservation | Lossy (description-only) | Full message history | Full message history |
| Parallel execution | Native | Not supported | Retained as secondary |
| Structured output | Built-in extraction | Needs workaround | State-based extraction |
| RBAC/tool filtering | Per-subagent compilation | Per-node compilation | Same as current |
| Approval workflows | Main agent manages | Needs careful wiring | Per-specialist interrupts |
| Code complexity | ~500 lines orchestration | ~100 lines (library) | ~150 lines |
| Migration effort | — | High | Medium (incremental) |
| Debugging | Simple (tool call tracing) | Complex (graph routing) | Moderate |
| Token efficiency | Re-explains context on follow-up | No re-explanation | No re-explanation |


---

## Alternative Architectures from Anthropic

Anthropic's "Building Effective AI Agents" article (December 2024) defines 6 agentic patterns, each progressively more autonomous. These patterns are framework-agnostic and provide a useful lens for evaluating Backcast's architecture.

### Anthropic's Core Principle

> "Start with simple prompts, optimize with evaluation, add multi-step agentic systems only when simpler solutions fall short."

### Pattern 1: Prompt Chaining

```
LLM Call → Output → LLM Call → Output → ...
```

Each LLM call uses the previous one's output as input. Simple, deterministic pipeline.

**Applicability to Backcast:** Low. Backcast's requests are interactive and user-driven, not linear pipelines. However, internal tool pipelines (e.g., "fetch project → calculate EVM → generate summary") could use this for deterministic sub-flows within a specialist agent.

### Pattern 2: Routing

```
User Input → Classifier → Route to specialized handler
```

Classify input, then route to the appropriate specialized prompt/agent. No delegation, no multi-agent — just conditional logic.

**Applicability to Backcast:** This is what the **supervisor in the recommended approach** does at its simplest level. A router classifies the request domain and sends it to the right specialist. The difference is that Backcast needs multi-turn conversations after routing, not just single-shot handling.

**Key insight:** The supervisor+handoff pattern is essentially "routing with context persistence." Pure routing loses follow-up capability.

### Pattern 3: Parallelization

```
User Input → [LLM Call A] + [LLM Call B] + [LLM Call C] → Aggregate
```

Multiple LLM calls run concurrently, results are aggregated.

**Applicability to Backcast:** This is what the **current subagent-as-tool pattern** does well. Cross-domain queries ("show me project status + EVM metrics") launch multiple subagents in parallel. The analysis recommends retaining this as a secondary mechanism, not the primary path.

### Pattern 4: Orchestrator-Workers

```
User Input → Orchestrator → [Worker A] + [Worker B] → Synthesize
```

An orchestrator LLM breaks down a task, delegates to workers, and synthesizes results. Workers can be LLM calls or tool calls.

**Applicability to Backcast:** This is the **closest match to the current architecture.** The main agent is the orchestrator, subagents are workers. The problem: context isolation between orchestrator and workers causes information loss on follow-ups.

**Key difference from recommended approach:** Orchestrator-workers implies the orchestrator always synthesizes. The handoff pattern allows specialists to respond directly to the user, then hand off to other specialists — no mandatory synthesis layer.

### Pattern 5: Evaluator-Optimizer

```
LLM Output → Evaluator → Feedback → LLM retries → ...
```

One LLM generates, another evaluates, loops until quality threshold met.

**Applicability to Backcast:** Moderate potential for specific use cases:
- EVM analysis quality checks (validate calculations before presenting)
- Change order impact analysis (cross-check impact assessment)
- Not needed as a primary architecture, but could improve reliability of specialist outputs

### Pattern 6: Autonomous Agent

```
User Input → Agent → [Plan → Execute → Observe → Loop] → Done
```

Full autonomy: the agent plans, executes tools, observes results, and loops until the task is complete.

**Applicability to Backcast:** Each specialist agent already operates in this mode internally (tool call loop). The question is about **inter-agent** architecture, not intra-agent behavior. This pattern is already in use within each subagent/specialist.

### Anthropic's Agent SDK Pattern

The Claude Agent SDK (`claude-agent-sdk-python`) uses a **subagent-as-tool** pattern identical to Backcast's current approach:

- Main agent defines `agents` dict with `AgentDefinition` per specialist
- Each specialist has `description`, `prompt`, `tools`, and optional `model` override
- Delegation happens via a built-in `Task` tool
- Subagents run with isolated context
- `parent_tool_use_id` tracks subagent execution in streaming

**This confirms that Anthropic's SDK validates the current pattern for isolation-focused use cases.** However, Backcast's multi-turn, cross-domain conversation needs go beyond what the SDK's subagent pattern optimizes for.

### Mapping to Backcast's Options

| Anthropic Pattern | Current Backcast Equivalent | Recommended Approach Equivalent |
|---|---|---|
| Prompt Chaining | Not used | Internal tool pipelines within specialists |
| Routing | Main agent prompt-based routing | Supervisor initial routing |
| Parallelization | `task` tool with multiple subagents | Retained as secondary mechanism |
| Orchestrator-Workers | Full current architecture | Supervisor replaces orchestrator synthesis |
| Evaluator-Optimizer | Not used | Optional: post-processing quality checks |
| Autonomous Agent | Each subagent internally | Each specialist internally (unchanged) |
| SDK Subagent-as-Tool | Exact match | Retained for batch parallel operations |

### Key Takeaway from Anthropic's Research

Anthropic's patterns reinforce that **no single pattern is universally best.** The right architecture depends on the specific workflow:

- For **single-domain, multi-turn conversations** (most Backcast use cases): Routing + context persistence (supervisor+handoff) is optimal
- For **cross-domain batch queries** ("analyze all projects + generate reports"): Parallelization (current `task` tool) is optimal
- For **quality-critical outputs** (EVM calculations, impact analysis): Evaluator-optimizer could add a validation layer

The recommended hybrid approach (supervisor+handoff primary, task tool secondary) maps naturally to Anthropic's pattern taxonomy: **Routing** for initial delegation, **context persistence** for multi-turn continuity, **Parallelization** retained for batch operations.

---

## Research Sources

- Anthropic Engineering Blog: "Building Effective AI Agents" (December 2024)
- Claude Agent SDK (`claude-agent-sdk-python`): AgentDefinition, subagent patterns
- LangGraph Swarm library: `langgraph-swarm` on PyPI / GitHub
- LangGraph Supervisor library: `langgraph-supervisor` on PyPI / GitHub
- LangGraph docs: Multi-agent concepts, handoff patterns, swarm architecture
- Current codebase: `backend/app/ai/` directory analysis
