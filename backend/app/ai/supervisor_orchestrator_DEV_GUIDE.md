# Supervisor Agent Graph — Developer Guide

> **Core file:** `backend/app/ai/supervisor_orchestrator.py` (~836 lines)
> **Key collaborators:** `planner.py`, `handoff_tools.py`, `briefing.py`, `briefing_compiler.py`, `subagent_compiler.py`, `db_loader.py`, `plan.py`, `supervisor_state.py`, `middleware/context_guard.py`, `middleware/plan_aware_tools.py`

This guide covers the supervisor graph: node topology, state flow, briefing pattern, plan-driven delegation, specialist isolation, middleware, and error handling. Intended for debugging graph execution and cleaning up the code.

---

## Table of Contents

1. [Graph Topology](#1-graph-topology)
2. [State Schema](#2-state-schema-backcastsupervisorstate)
3. [Compilation Pipeline](#3-compilation-pipeline-createsupervisorgraph)
4. [Node Reference](#4-node-reference)
5. [Routing Logic](#5-routing-logic-the-router)
6. [Briefing Pattern](#6-briefing-pattern)
7. [Plan-Driven Execution](#7-plan-driven-execution)
8. [Specialist Isolation](#8-specialist-isolation)
9. [Middleware Stack](#9-middleware-stack)
10. [Specialist Loading & Compilation](#10-specialist-loading--compilation)
11. [Error & Retry Flow](#11-error--retry-flow)
12. [Fallback Graph](#12-fallback-graph)
13. [Non-Standard Patterns & Improvement Points](#13-non-standard-patterns--improvement-points)

---

## 1. Graph Topology

```
START
  │
  ▼
initialize_briefing ─── seeds BriefingDocument from user request
  │
  ▼
planner ─── single LLM call → PlanDocument (simple or multi-step)
  │
  ▼
supervisor ─── LLM with handoff tools + optional direct tools
  │
  ├── handoff_to_X called? ──► specialist_X (wrapper node)
  │                                 │
  │                    Command(goto="supervisor")
  │                    Command(goto=END)
  │                                 │
  ◄─────────────────────────────────┘
  │
  ├── no handoff / max iterations ──► END
  │
  ▼
 END
```

**Wire-up** (`supervisor_orchestrator.py` L438–448):
```
START → initialize_briefing → planner → supervisor
supervisor ─conditional─→ specialist_1 | specialist_2 | ... | END
specialist nodes return Command(goto=...) explicitly — no static edge back
```

The graph is compiled as `"backcast_supervisor"` (L452).

---

## 2. State Schema (`BackcastSupervisorState`)

Defined in `supervisor_state.py`. TypedDict with reducer annotations:

| Field | Type / Reducer | Purpose |
|---|---|---|
| `messages` | `list[BaseMessage]` — `operator.add` | Outer conversation only (user + supervisor). **Not shared with specialists.** |
| `active_agent` | `str` | Currently active specialist name (for event routing) |
| `tool_call_count` | `int` — `operator.add` | Accumulated across all agents |
| `max_tool_iterations` | `int` | Hard cap on tool calls |
| `briefing_data` | `dict[str, Any]` | Serialized `BriefingDocument` — **single source of truth** for all specialist findings |
| `supervisor_iterations` | `int` — `operator.add` | Completed supervisor→specialist cycles |
| `max_supervisor_iterations` | `int` | Hard cap on supervisor loops (default 3, raised for multi-step plans) |
| `completed_specialists` | `set[str]` — `operator.or_` | Union-accumulated set of finished specialist names |
| `plan_data` | `dict[str, Any]` | Serialized `PlanDocument` when plan-execute mode is active |
| `completed_steps` | `set[int]` — `operator.or_` | Indices of completed plan steps |
| `current_step_index` | `int` | Zero-based index of executing step, `-1` when between steps |

**Key insight:** `operator.add` and `operator.or_` reducers mean nodes return **deltas** that get merged into the state, not full state replacements.

---

## 3. Compilation Pipeline (`create_supervisor_graph`)

Called from `agent_service.py:_create_deep_agent_graph()` (L999). Steps in `supervisor_orchestrator.py`:

| Step | Lines | What happens |
|---|---|---|
| 1. Tool filtering | L252 | `filter_tools_for_context()` — applies execution-mode + RBAC filtering |
| 2. Load specialists | L255–280 | `load_specialists_from_db()` (cached 5min TTL) → `compile_subagents()` |
| 3. Build supervisor tools | L291–307 | `get_briefing` + `handoff_to_*` + optional direct tools |
| 4. Build supervisor prompt | L310–339 | Base prompt + specialist section + delegation enforcement + direct-tools/handoff suffix |
| 5. Create supervisor agent | L341–349 | `langchain_create_agent()` with tools, middleware, `_BriefingSupervisorState` |
| 6. Create specialist wrappers | L353–355 | One `_create_specialist_wrapper()` per specialist |
| 7. Build graph nodes | L360–432 | `initialize_briefing_node`, `planner_node_fn`, `supervisor`, specialist nodes |
| 8. Wire edges | L438–448 | `START→init→planner→supervisor`, conditional from supervisor to specialists |
| 9. Compile | L450–458 | `parent.compile(checkpointer, name="backcast_supervisor")` |

### Specialist Filtering Before Compilation

`delegation_config.allowed_specialists` on the assistant config (L265–272) restricts which specialists are available:
```python
allowed = self.main_assistant_config.delegation_config.get("allowed_specialists")
if allowed is not None:
    subagent_configs = [s for s in subagent_configs if s.get("name") in allowed]
```

### Direct Tools

When `delegation_config.direct_tools` is set, the supervisor gets those tools directly (L296–307) — it can use them without delegating. This modifies the prompt suffix (L329–339).

---

## 4. Node Reference

### 4a. `initialize_briefing` (L361–387)

**Purpose:** Seed the `BriefingDocument` from the user request.

```
1. Scan messages in reverse for latest HumanMessage
2. If briefing_data already exists in state → reuse and update original_request
3. Otherwise → initialize_briefing(user_request) creates a fresh BriefingDocument
4. Return _briefing_update(doc) which sets:
   - briefing_data (serialized doc)
   - supervisor_iterations = 0
   - max_supervisor_iterations = 3
   - completed_specialists = set()
   - messages = [SystemMessage with briefing markdown]
   - completed_steps = set()
   - current_step_index = -1
   - plan_data (if existing)
```

### 4b. `planner` (L389–427)

**Purpose:** Single LLM call → `PlanDocument`. Delegates to `planner_node()` from `planner.py`.

```
1. Extract user request from messages
2. Build planner prompt with specialist catalog
3. LLM call via structured output (json_mode) → PlannerOutput
4. Validate specialist names, convert to PlanDocument
5. Emit PLAN_UPDATE event
6. Return {"plan_data": plan.model_dump()}
```

On failure: falls back to single-step `general_purpose` plan.

See `planner.py` for details — the planner uses `json_mode` specifically because `function_calling` mode conflicts with the DeepSeek `tool_choice` monkey-patch (planner.py L266–271).

### 4c. `supervisor` (L341–349)

Created via `langchain_create_agent()` — not a plain function node but a **compiled agent subgraph**. The supervisor is itself an agent with its own internal `agent↔tools` loop.

**Tools available:**
- `get_briefing` — reads `briefing_data` from state
- `handoff_to_{specialist}` — one per specialist, returns `Command(goto=specialist)`
- Optional direct tools from `delegation_config.direct_tools`

**Middleware:** `[ContextGuardMiddleware, PlanAwareToolMiddleware, ...base_middleware]`

The supervisor's LLM never sees specialist message history — it sees the briefing document injected as context by `ContextGuardMiddleware`.

### 4d. `specialist_{name}` (L546–804)

Each is a **wrapper node** that isolates the specialist subgraph from the parent state. See [§8](#8-specialist-isolation).

---

## 5. Routing Logic (The Router)

`_make_supervisor_router()` (L460–544) creates a closure that routes from the supervisor node.

### Decision Tree

```
1. Check iteration cap
   ├── iterations >= max_iterations → END (L499)
   │   (max_iterations raised to len(plan.steps)+1 when multi-step plan)
   │
2. Check last message for handoff tool calls
   ├── No tool_calls → END (L542)
   │
   ├── tool_call starts with "handoff_to_"
   │   ├── Extract slug, resolve to specialist name via slug_map
   │   ├── Specialist already in completed_specialists AND no plan → END (L531)
   │   └── Specialist in specialist_set → return specialist_name (L534)
   │
   └── No matching handoff → END
```

### Slug Resolution

Specialist names are slugified (`_slugify()`) to create valid tool names. The router maintains a `slug_map` to reverse the slug back to the original specialist name. Slug collisions are logged as warnings (L476–480).

### Plan-Aware Iteration Cap

When a multi-step plan exists, `max_iterations` is raised to `len(plan.steps) + 1` (L495–497) so the supervisor can delegate all steps. Without this, the default cap of 3 would prematurely terminate.

### Re-Dispatch Guard

Non-plan mode: if a specialist is in `completed_specialists`, re-dispatching to it forces END (L525–531). In plan mode, re-dispatch is allowed because different plan steps may target the same specialist.

---

## 6. Briefing Pattern

The briefing document is the **sole communication channel** between specialists and the supervisor. Specialists never see each other's message history.

### Data Flow

```
User message
  │
  ▼
initialize_briefing → BriefingDocument(original_request=user_msg)
  │
  ▼
supervisor reads briefing via get_briefing tool → decides to hand off
  │
  ▼
handoff_to_X tool → records TaskAssignment in briefing.task_history
  │
  ▼
specialist_X wrapper:
  - Reads briefing_data from state
  - Builds isolated HumanMessage with assignment block
  - Invokes specialist subgraph
  - Compiles output via compile_specialist_output()
  - Appends BriefingSection to briefing.sections
  │
  ▼
supervisor reads updated briefing → delegates next step or ends
```

### BriefingDocument Structure (`briefing.py`)

```
BriefingDocument
├── original_request: str          # User's message
├── sections: list[BriefingSection] # Specialist contributions (appended)
├── supervisor_analysis: str       # Supervisor's analysis (optional)
├── task_history: list[TaskAssignment]  # Delegation record
└── plan: list[dict]               # Execution plan (optional)
```

Each `BriefingSection`:
```
BriefingSection
├── specialist_name: str
├── findings: str                  # Specialist's main output
├── task_description: str          # What was asked
├── supervisor_rationale: str      # Why this specialist was chosen
├── key_findings: list[str]        # Extracted by parse_and_clean()
├── open_questions: list[str]
├── delegation_notes: str
└── step_index: int                # Plan step (if plan-driven)
```

### Output Parsing (`briefing_compiler.py`)

`parse_and_clean()` (L41–105) extracts structured sections from specialist output:
1. Try JSON parse first (expects `{"summary": ..., "key_findings": [...]}`)
2. Fallback: regex split on `## ` headers, extract bullet items
3. Returns `(cleaned_findings, parsed_metadata)`

`compile_specialist_output()` (L108–129) creates a `BriefingSection` and appends it to the document.

---

## 7. Plan-Driven Execution

### PlanDocument Structure (`plan.py`)

```
PlanDocument
├── original_request: str
├── steps: list[PlanStep]
├── estimated_complexity: "simple" | "moderate" | "complex"
├── requires_planning: bool
└── specialist_catalog: list[dict] | None

PlanStep
├── step_index: int
├── specialist: str
├── task_description: str
├── dependencies: list[int]         # Step indices
├── expected_output: str
├── status: "pending" | "in_progress" | "completed" | "failed" | "skipped"
└── result_summary: str | None
```

### Execution Flow

```
planner_node
  → PlanDocument with steps
  → PLAN_UPDATE event emitted

supervisor (iteration 1)
  → reads plan_data from state
  → PlanAwareToolMiddleware strips non-delegation tools
  → calls handoff_to_X with step_index
  → specialist wrapper picks up active_step via step matching

specialist_X wrapper:
  → finds first pending step matching specialist_name
  → checks are_dependencies_met()
  → marks step "in_progress"
  → builds assignment block with step context + dependency results
  → invokes specialist subgraph
  → marks step "completed" or "failed"
  → injects plan progress SystemMessage for supervisor
  → emits PLAN_UPDATE
  → Command(goto="supervisor")

supervisor (iteration N)
  → reads updated plan_data
  → delegates next pending step
  → if all steps done → final response
```

### Step Matching (specialist wrapper, L568–576)

```python
for step in active_plan.steps:
    if (step.specialist == specialist_name
        and step.status == "pending"
        and step.step_index not in completed_step_indices
        and active_plan.are_dependencies_met(step.step_index)):
        active_step = step
        break
```

Matches by specialist name + pending status + unmet dependency check. First match wins.

### Plan Completion Message (L784–800)

After a step completes, the wrapper injects a `SystemMessage` into the state telling the supervisor what happened and what's next. If all steps are done, it tells the supervisor to respond to the user.

---

## 8. Specialist Isolation

Each specialist runs in a **completely isolated message context**. The wrapper node (`_create_specialist_wrapper`, L546–804):

1. **Does NOT pass parent messages** — constructs fresh messages with just the assignment block
2. **Reads** `briefing_data` from parent state to build context
3. **Invokes** the specialist subgraph independently
4. **Compiles** results back into `briefing_data`
5. **Returns** `Command(update={...}, goto="supervisor")` — state deltas only

### Assignment Block Construction (L622–660)

**With plan step:**
```
## Your Assignment (Plan Step 2/5)

Calculate EVM metrics for project ACME-001

**Expected output:** EVM summary with CPI, SPI, and variance analysis
**Context from previous steps:** Step 0 result: ...
- Step 0 result: Project ACME-001 has 12 WBS elements...
**User's original request:** Analyze ACME-001 performance
```

**Without plan step (briefing mode):**
```
## Your Assignment

Execute specialist task from briefing

**Supervisor's rationale:** Need EVM analysis for cost tracking
**User's original request:** How is the project doing?
```

### Briefing Exposure to Specialist

`set_briefing(briefing_data_raw)` (L666) makes the briefing available to the specialist's `get_briefing` tool via a module-level function — **not** via state injection. This is a non-standard pattern (see [§13](#13-non-standard-patterns--improvement-points)).

---

## 9. Middleware Stack

### Supervisor Middleware (L806–815)

```python
[
    ContextGuardMiddleware(),    # Trims message history using briefing
    PlanAwareToolMiddleware(),   # Strips non-delegation tools when plan active
    SequentialToolCallsMiddleware(),  # (if AI_SEQUENTIAL_TOOL_CALLS)
    TemporalContextMiddleware(context),  # Injects temporal context
    BackcastSecurityMiddleware(context, tools, interrupt_node=None),
]
```

### ContextGuardMiddleware (`middleware/context_guard.py`)

**Before each supervisor LLM call:**
1. Estimate tokens from message content lengths (÷4 chars/token, skip system prompt)
2. If tokens > `AI_CONTEXT_SUMMARY_THRESHOLD_PCT`% of `AI_CONTEXT_TOKEN_LIMIT`:
   - Keep system prompt + last `AI_CONTEXT_KEEP_RECENT` messages
   - Replace everything in between with `BriefingDocument.to_markdown()` as a HumanMessage
   - Repair message chain integrity (tool responses must follow tool_calls)

Key invariant: requires `_MIN_MESSAGES_TO_TRIM = 8` before trimming to avoid false positives where tool schemas dominate the token estimate.

### PlanAwareToolMiddleware (`middleware/plan_aware_tools.py`)

**When a multi-step plan is active** (`requires_planning=True` and steps exist):

1. **Pre-filter:** Strip all tools except `get_briefing` and `handoff_to_*`
2. **Prompt injection:** Append `_PLAN_DELEGATION_SUFFIX` — strong instruction to delegate only
3. **Post-filter:** Strip any tool_calls for disallowed tools that the LLM hallucinated

This is a defense-in-depth: even if the LLM ignores instructions, it literally cannot call domain tools because they're removed from the tool list.

### Specialist Middleware (`subagent_compiler.py:build_backcast_middleware`)

```python
[
    SequentialToolCallsMiddleware(),  # (if AI_SEQUENTIAL_TOOL_CALLS)
    TemporalContextMiddleware(context),
    BackcastSecurityMiddleware(context, tools, interrupt_node=None),
]
```

Specialists do NOT get `ContextGuardMiddleware` (they receive fresh short messages each time) or `PlanAwareToolMiddleware` (they don't delegate).

---

## 10. Specialist Loading & Compilation

### Loading from DB (`subagents/db_loader.py`)

```
AIAssistantConfig rows
  WHERE agent_type='specialist' AND is_active=True
  → cached 5min TTL (module-level _cache, _cache_ts)
  → converted to dicts via assistant_config_to_specialist_dict()
```

Each specialist dict:
```python
{
    "name": "evm_analyst",
    "description": "...",
    "presentation_prompt": "...",  # shown in specialist catalog
    "system_prompt": "...",        # injected as specialist system prompt
    "allowed_tools": ["get_project", "get_wbs_elements", ...],
    "structured_output_schema": SpecialistOutput,  # Pydantic class (resolved from FQCN string)
}
```

### Compilation (`subagent_compiler.py:compile_subagents`)

Tool filtering convention:
- `allowed_tools = None` → no tools (specialist has no regular tool access)
- `allowed_tools = ["*"]` → all available tools (catch-all / fallback)
- `allowed_tools = ["t1", "t2"]` → only listed tools

Each specialist is compiled via `langchain_create_agent()` with its own tool set and middleware. When `AI_SEQUENTIAL_TOOL_CALLS` is true, `SequentialToolCallsMiddleware` enforces sequential tool behavior via native v1 public API: it injects `parallel_tool_calls=False` into `model_settings` (emission control) and holds a shared `asyncio.Lock` in `awrap_tool_call` so that even if the model emits multiple calls in one AIMessage, they execute one at a time (execution serialization).

---

## 11. Error & Retry Flow

### Specialist Retry (within wrapper, L683–734)

```python
max_retries = settings.AI_SPECIALIST_MAX_RETRIES
for _attempt in range(max_retries + 1):
    try:
        result = await specialist_graph.ainvoke(...)
        break
    except Exception as exc:
        if is_transient_stream_error(exc) and _attempt < max_retries:
            await asyncio.sleep(2.0)  # hardcoded 2s retry delay
            continue
        # Non-transient or max retries:
        # → mark plan step as failed
        # → compile error into briefing
        # → emit PLAN_UPDATE
        # → Command(goto="supervisor") with error update
```

**Key behavior:** Failed specialists are NOT added to `completed_specialists`, so the supervisor can retry them.

### Planner Failure (`planner.py` L294–296)

On any error, falls back to a single-step `general_purpose` plan — never crashes the graph.

### Router Iteration Guard (L499–504)

If `supervisor_iterations >= max_iterations`, the router forces `END` regardless of pending steps. This prevents infinite delegation loops.

### Handoff Tool — No Error Path

The handoff tools (`handoff_tools.py`) don't have try/except. If `BriefingDocument.from_state()` or `doc.add_task_assignment()` fails, the exception propagates into the LangGraph tool node, which emits an `on_tool_error` event and the graph continues.

---

## 12. Fallback Graph

When no specialists can be compiled (L284–288), `_build_fallback_graph()` (L817–832) creates a simple agent with direct tool access — no briefing, no handoff tools. Security remains middleware-only (`BackcastSecurityMiddleware` + `TemporalContextMiddleware`).

```python
langchain_create_agent(
    model=self.model,
    tools=all_tools,
    system_prompt=base_prompt,
    middleware=self._build_middleware(all_tools),
    ...
)
```

---

## 13. Non-Standard Patterns & Improvement Points

### 🔴 Briefing Exposure via Module-Level Function

**Location:** `supervisor_orchestrator.py` L666 + `tools/briefing_tools.py`

```python
set_briefing(briefing_data_raw if briefing_data_raw else None)
```

`set_briefing()` stores data in a module-level `ContextVar`. The specialist's `get_briefing` tool reads from that `ContextVar`. This is not LangGraph's state-sharing mechanism — it's a side channel that bypasses the graph state. If two specialists run concurrently (which they shouldn't, but the pattern doesn't prevent it), they'd share the same context var.

**Improvement:** Pass briefing data through the specialist subgraph's state or via `BackcastRuntimeContext` instead of a module-level side channel.

### 🔴 `completed_specialists` Set Uses `operator.or_` Reducer

**Location:** `supervisor_state.py` L58

```python
completed_specialists: Annotated[set[str], operator.or_]
```

This union-accumulates across all graph cycles. The wrapper adds `{specialist_name}` (L762). But the router reads the set to block re-dispatch (L525). If a specialist completes, then the same specialist is re-invoked in plan mode, the `or_` reducer doesn't replace — it only grows. The early-exit guard at L583 handles this, but the interaction between the set reducer and the per-step re-dispatch is subtle.

### 🟡 Hardcoded Retry Delay

**Location:** `supervisor_orchestrator.py` L704

```python
await asyncio.sleep(2.0)  # hardcoded 2s retry delay
```

Should be configurable (same issue as `agent_service.py` retry delays).

### 🟡 Slug Collision Silently Logged

**Location:** `supervisor_orchestrator.py` L476–480

When two specialist names slugify to the same string, only a warning is logged. The second overwrites the first in `slug_map`, so one specialist becomes unreachable.

**Improvement:** Raise an error or deduplicate slug names with a suffix.

### 🟡 `_briefing_update` Doesn't Preserve `max_tool_iterations`

**Location:** `supervisor_orchestrator.py` L127–149

The `_briefing_update` helper returned by `initialize_briefing_node` sets `supervisor_iterations`, `max_supervisor_iterations`, `completed_specialists`, etc. but does **not** set or preserve `max_tool_iterations`. This value must be set by the caller via the initial graph input state.

### 🟡 Specialist Skipping Logic Asymmetric

**Location:** `subagent_compiler.py` L165–169

Specialists with no matching tools after filtering are silently skipped:
```python
if not subagent_tools:
    logger.warning("%s '%s' has no tools after filtering — skipping", label, name)
    continue
```
But a specialist with `allowed_tools = None` intentionally gets no tools. The check treats this the same as a filtered-out specialist, which may mask configuration errors.

### 🟡 `PlanAwareToolMiddleware` Prompt Injection Not Idempotent

**Location:** `middleware/plan_aware_tools.py` L173

```python
if _PLAN_DELEGATION_SUFFIX.strip() not in current_prompt:
    new_prompt = current_prompt + _PLAN_DELEGATION_SUFFIX
```

The check uses string containment, which works but is fragile. If the system prompt happens to contain the same text, the suffix won't be added. This is a minor concern but worth noting.

### 🟡 `db_loader.py` Module-Level Mutable Cache

**Location:** `subagents/db_loader.py` L24–26

```python
_cache: list[dict[str, Any]] | None = None
_cache_ts: float = 0.0
_CACHE_TTL = 300.0
```

Module-level mutable globals with no size limit. The cache is invalidated by `invalidate_cache()` which resets to `None`. Under normal operation this is fine (specialist list is small), but there's no eviction mechanism if TTL expires — it just reloads.

### 🟢 Minor: `_BriefingSupervisorState` Redundancy

**Location:** `supervisor_orchestrator.py` L152–162

```python
class _BriefingSupervisorState(AgentState[Any]):
    briefing_data: dict[str, Any]
    plan_data: dict[str, Any]
```

This exists solely to make `langchain_create_agent()` aware of the `briefing_data` and `plan_data` keys so they're shared between the supervisor subgraph and the parent `BackcastSupervisorState`. It's a LangGraph pattern requirement but could be documented more clearly.

---

## Quick Reference: Key Line Numbers

| What | File | Lines |
|---|---|---|
| Graph wiring (edges) | `supervisor_orchestrator.py` | 438–448 |
| Router function | `supervisor_orchestrator.py` | 460–544 |
| Specialist wrapper | `supervisor_orchestrator.py` | 546–804 |
| Briefing initialization | `supervisor_orchestrator.py` | 361–387 |
| Planner node fn | `supervisor_orchestrator.py` | 398–427 |
| Supervisor prompt assembly | `supervisor_orchestrator.py` | 310–339 |
| Handoff tool creation | `handoff_tools.py` | 39–137 |
| State schema | `supervisor_state.py` | 23–64 |
| PlanDocument model | `plan.py` | 66–201 |
| BriefingDocument model | `briefing.py` | 35–123 |
| Planner LLM call | `planner.py` | 218–305 |
| Specialist compilation | `subagent_compiler.py` | 97–224 |
| Specialist DB loading | `db_loader.py` | 71–102 |
| ContextGuardMiddleware | `middleware/context_guard.py` | 161–243 |
| PlanAwareToolMiddleware | `middleware/plan_aware_tools.py` | 123–196 |
| Fallback graph | `supervisor_orchestrator.py` | 817–832 |
