# Analysis: The Briefing Room — Karpathy-Inspired Agent Orchestration

**Date:** 2026-04-27
**Scope:** Agent orchestration context management — a new `BriefingRoomOrchestrator` that uses compiled briefing documents instead of raw message transcript sharing
**Status:** Research & Analysis

---

## Executive Summary

The current `SupervisorOrchestrator` shares **full message transcripts** between all specialists. Every specialist sees every previous specialist's raw tool calls, tool results, and intermediate messages. This causes unbounded context growth and wastes tokens on noise.

Inspired by **Andrej Karpathy's compiler analogy** (raw articles as source code → LLM as compiler → structured wiki as executable), we propose **The Briefing Room pattern** as a **new `BriefingRoomOrchestrator`**: a shared, compiled knowledge document (briefing) that specialists read from and write to, replacing raw message transcript passing.

**Recommendation:** Create a new `BriefingRoomOrchestrator` that uses a compiled `BriefingDocument` instead of shared `messages`. The existing `SupervisorOrchestrator` remains unchanged — users choose between patterns based on their use case. Specialists in the collaborator pattern see ~300-700 tokens of structured briefing instead of ~3000-8000 tokens of raw messages — a **5-10x context window reduction**. Multi-turn conversations benefit most: the briefing from turn 1 is already compressed, so turn 2 specialists don't re-process the entire history.

---

## The Problem: Unbounded Context Growth

### Current Supervisor Pattern

```
Specialist A sees:  [User msg] [Supervisor handoff]                           → ~300 tokens of useful signal
                    + [Specialist A's own tool calls/results]                  → ~2000 tokens
                                                                         Total: ~2300 tokens

Specialist B sees:  [User msg] [Supervisor handoff]
                    + [ALL of A's tool calls/results] [A's response]          → ~3000 tokens of A's work
                    + [A's handoff to B]
                    + [B's own tool calls/results]                            → ~2000 tokens
                                                                         Total: ~5000+ tokens

Supervisor (synth): [Everything from all specialists]                          → ~8000+ tokens
```

### What Grows the Context

| Source | Token Cost | Useful for Next Specialist? |
|--------|-----------|---------------------------|
| Raw tool call arguments (JSON) | High (~500-1000/tool call) | No — the result matters, not the args |
| Raw tool results (JSON payloads) | High (~500-2000/tool call) | Partially — only the key findings matter |
| Intermediate reasoning messages | Medium (~200-500/msg) | No — only the final conclusion matters |
| Specialist's final output | Low (~200-500) | Yes — this is the synthesized knowledge |
| Routing messages (handoffs) | Low (~50-100/msg) | No — just control flow |

**~80% of the context is noise** — raw tool payloads and intermediate reasoning that subsequent specialists don't need.

### Multi-Turn Amplification

On follow-up messages, the problem compounds:
- Turn 1 builds ~8000 tokens of message history
- Turn 2 loads ALL of turn 1's messages + the new question
- Turn 2 specialists see ~10,000+ tokens
- Turn 3: ~12,000+ tokens

There is no compression between turns.

---

## The Compiler Analogy Applied

Karpathy's insight: don't query raw documents — compile them into a wiki first, then query the wiki.

| Analogy Component | Agent Orchestration Equivalent |
|-------------------|-------------------------------|
| Source code (raw, verbose) | Raw tool calls, tool results, intermediate messages |
| Compiler (LLM) | Briefing compiler — extracts findings, structures them |
| Compiled executable (wiki) | BriefingDocument — structured, deduplicated, queryable |
| Compilation passes | Each specialist contribution refines the briefing |
| Query the wiki | Supervisor reads briefing, not raw messages |

### Multi-Pass Compilation

```
Pass 1: User question → Initial briefing (scope, question)
Pass 2: project_manager contributes → Briefing + project findings
Pass 3: evm_analyst contributes → Briefing + project + EVM findings
Pass 4: Supervisor synthesizes → Final response
```

Each pass produces a progressively more useful compiled artifact. No pass needs to re-process the raw source.

---

## The Briefing Room Pattern

### Real-Life Metaphor

A manager receives a complex question:
1. Creates a **shared briefing document** with the question and context
2. Assigns work to specialists (team members)
3. Each specialist **reads the briefing**, does their work, **writes findings back**
4. The briefing evolves: raw question → research → synthesized findings → polished response
5. Nobody reads the full transcript of everyone's work — they read the **compiled briefing**

### State Schema

```python
class BriefingState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]  # routing messages only (handoff ToolMessages)
    briefing: str                          # Compiled knowledge document (markdown)
    briefing_data: dict                    # Serialized BriefingDocument (for compilation)
    active_agent: str
    tool_call_count: Annotated[int, operator.add]
    max_tool_iterations: int
```

Key difference from `BackcastSupervisorState`: `briefing` replaces `messages` as the primary knowledge carrier. `messages` still exists but only carries lightweight routing messages (handoff ToolMessages) — stays under ~200 tokens total.

### BriefingDocument Model

```python
class BriefingSection(BaseModel):
    specialist: str
    domain: str
    findings: str                          # Distilled, human-readable markdown
    structured_data: dict | None = None    # Pydantic-serialized data (EVM metrics, etc.)
    tools_used: list[str] = []
    open_questions: list[str] = []

class BriefingDocument(BaseModel):
    user_request: str
    scope: dict                            # project_id, branch_name, branch_mode, as_of
    sections: list[BriefingSection] = []
    iteration: int = 0

    def to_context_string(self) -> str:
        """Compile into markdown for specialist context."""

    def add_section(self, section: BriefingSection) -> "BriefingDocument":
        """Add or update a specialist's section (specialists can refine their own)."""
```

### Graph Structure

```
START → Supervisor (sees briefing + handoff tools)
         ↓ handoff_to_X
       Specialist Wrapper Node X
         ├─ Reads briefing from state
         ├─ Creates isolated context: [SystemPrompt + Briefing as HumanMessage]
         ├─ Runs specialist agent loop (tools, middleware)
         └─ Returns findings
         ↓
       Briefing Compiler
         ├─ Merges specialist findings into briefing
         └─ Updates briefing markdown
         ↓
       Router → Supervisor (next specialist) or END
```

### Specialist Wrapper Node

The key architectural change. Each specialist is wrapped in a function node that:

1. Reads the briefing from parent state
2. Creates an **isolated** message list for the specialist (briefing as HumanMessage)
3. Runs the specialist's compiled agent graph in isolation
4. Captures the specialist's final output
5. Passes it to the briefing compiler

Specialists see **zero** messages from the parent graph. The specialist's agent loop (tool calls, results, reasoning) happens entirely in isolation. Only the **final distilled output** is written back to the briefing.

### Briefing Compiler

After each specialist contribution:
1. Extract specialist's final AIMessage
2. Wrap in a `BriefingSection`
3. Call `briefing_doc.add_section(section)`
4. Regenerate `briefing_doc.to_context_string()`
5. Return updated `briefing` and `briefing_data` to state

Two strategies:
- **String-based** (default, zero-cost): Direct section assembly into markdown
- **LLM-based** (optional): Fast model to compress and deduplicate when briefing exceeds ~1500 tokens

---

## SupervisorOrchestrator vs BriefingRoomOrchestrator

### When to Use Each

| Use Case | Recommended Orchestrator | Why |
|----------|------------------------|-----|
| Single-turn queries, 2-3 specialists | `SupervisorOrchestrator` | Simpler, adequate context size |
| Multi-turn conversations (3+ turns) | `BriefingRoomOrchestrator` | Briefing compression prevents exponential growth |
| Complex cross-domain analysis | `BriefingRoomOrchestrator` | Structured briefing aids synthesis |
| Debugging specialist behavior | `SupervisorOrchestrator` | Full message transcript available |
| Token-constrained deployments | `BriefingRoomOrchestrator` | 5-10x context reduction |

### Comparison

| Aspect | SupervisorOrchestrator | BriefingRoomOrchestrator |
|--------|------------------------|-------------------------|
| Knowledge sharing | Full message transcript | Compiled briefing document |
| Context per specialist | ~3000-5000 tokens | ~300-700 tokens |
| Specialist execution | Sequential handoffs | Sequential handoffs |
| Multi-turn growth | Linear (~2x per turn) | Capped (briefing compresses) |
| Debuggability | High (full transcript) | Medium (briefing + events) |
| Best for | Single-turn, debugging | Multi-turn, token-constrained |

### UC1: Project Health Check

**SupervisorOrchestrator (raw messages):**
```
project_manager: [User msg + handoff] + [list_projects, get_project results] = ~3000 tokens
evm_analyst:     [All above] + [calculate_evm_metrics results]              = ~5000 tokens
supervisor:      [Everything]                                               = ~8000+ tokens
                                                                          TOTAL: ~16000 tokens
```

**BriefingRoomOrchestrator (briefing):**
```
project_manager: [Briefing: question + scope]                              = ~300 tokens
  → Briefing compiled: + project findings (~200 tokens)
evm_analyst:     [Briefing: question + scope + project findings]           = ~500 tokens
  → Briefing compiled: + EVM findings (~200 tokens)
supervisor:      [Final briefing: ~700 tokens]                             = ~700 tokens
                                                                          TOTAL: ~1500 tokens
```

**Reduction: ~10x**

### UC2: Multi-Turn Follow-up

```
Turn 1: "What's the status of PRJ-001?"
  SupervisorOrchestrator: Builds ~8000 tokens of message history
  BriefingRoomOrchestrator: Briefing built: ~700 tokens

Turn 2: "How would CO-0042 affect this?"
  SupervisorOrchestrator: Loads ALL turn 1 messages (~8000 tokens) + new question
  BriefingRoomOrchestrator: Loads compiled briefing from turn 1 (~700 tokens) + new question

  change_order_manager sees:
    SupervisorOrchestrator: ~10000 tokens of raw messages from turn 1 + new question
    BriefingRoomOrchestrator: ~700 tokens of structured briefing + "How would CO-0042 affect this?"

  Key: The briefing already contains project details and EVM baseline.
       change_order_manager does NOT need to re-fetch project data.
       Zero redundant API calls.
```

### UC3: Cross-Domain Analysis

```
User: "Compare forecast vs actuals for all active projects"

forecast_manager adds forecasts → briefing updated
project_manager adds actuals   → reads forecasts from briefing (knows what to compare)
evm_analyst calculates variance → reads both forecasts and actuals from briefing
supervisor synthesizes comparison from final briefing
```

---

## Implementation Assessment

### New Files

| File | Responsibility |
|------|---------------|
| `ai/briefing.py` | `BriefingDocument`, `BriefingSection` models, compilation logic |
| `ai/briefing_state.py` | `BriefingState` TypedDict |
| `ai/briefing_compiler.py` | `compile_specialist_output()`, briefing compression |
| `ai/briefing_specialist.py` | `create_briefing_specialist_node()` wrapper factory |
| `ai/briefing_room_orchestrator.py` | **NEW** orchestrator using briefing pattern |
| `ai/handoff_tools.py` (extend) | Add `briefing_handoff_to_*` variants for briefing room |

### Modified Files

| File | Changes |
|------|---------|
| `core/config.py` | Add `"briefing_room"` to `AI_ORCHESTRATOR` valid values |
| `ai/agent_service.py` | Add `BriefingRoomOrchestrator` to routing, briefing initialization |
| `ai/execution/agent_event.py` | Add `BRIEFING_INITIALIZED`, `BRIEFING_UPDATED`, `BRIEFING_FINALIZED` event type constants |
| `ai/subagents/__init__.py` | Add optional briefing-aware prompt instructions |

### Unchanged

| File | Why |
|------|-----|
| `ai/supervisor_orchestrator.py` | **NOT modified** — existing pattern remains available |
| `ai/deep_agent_orchestrator.py` | Different pattern (task-based isolation), not affected |
| `ai/state.py` | Still used by individual specialist agents internally |
| `ai/middleware/*` | Applies to specialist_graphs unchanged |
| `ai/tools/*` | Tool definitions unchanged |
| `ai/execution/*` | Event bus structure unchanged |

---

## Edge Cases

### Contradictions Between Specialists
If specialist B's findings contradict specialist A's, the contradiction is visible in the briefing (both sections present). The supervisor resolves it during synthesis. The compilation step does NOT auto-resolve contradictions — that's the supervisor's responsibility.

### Briefing Size Limits
- Target: under ~1500 tokens (~6000 chars)
- Specialists produce concise findings by nature (LLM-generated summaries)
- If briefing exceeds budget: LLM-based compression pass (fast model summarizes)
- Fallback: drop older sections, keep most recent + request

### Specialist Needs Raw Data From Previous Specialist
- Structured data is preserved in `briefing_data.sections[].structured_data`
- E.g., EVM metrics `{cpi: 0.95, spi: 1.02}` are available programmatically
- For truly raw data needs, specialist re-calls the tool (still cheaper than passing all raw messages)

### Structured Output Schemas
- Existing schemas (`EVMMetricsRead`, `ImpactAnalysisResponse`, `ForecastRead`) serialize into `structured_data`
- `_summarize_structured_output()` (already in `subagent_task.py`) generates the `findings` string
- Supervisor gets both summary (markdown) and raw data (dict)

---

## Observing Briefing Content

### Event-Based Streaming

The briefing document evolves through the conversation. Users should see:
1. Initial briefing (user question + scope)
2. After each specialist: updated briefing with their findings
3. Final briefing: complete synthesized document

### New Event Types

```python
# In app/ai/execution/agent_event.py

BRIEFING_INITIALIZED = "briefing_initialized"  # Initial briefing created
BRIEFING_UPDATED = "briefing_updated"           # Specialist contributed
BRIEFING_FINALIZED = "briefing_finalized"       # Orchestrator synthesis complete
```

### Event Payload Structure

```python
# BRIEFING_INITIALIZED
{
    "briefing": str,              # Initial markdown
    "iteration": 0,
    "sections": [],               # Empty initially
    "scope": {...}                # project_id, branch_name, etc.
}

# BRIEFING_UPDATED (after each specialist)
{
    "specialist": str,            # "project_manager", "evm_analyst", etc.
    "briefing": str,              # Updated markdown
    "iteration": int,             # Increments per specialist
    "sections": [                 # All sections so far
        {"specialist": "...", "findings": "..."},
        ...
    ]
}

# BRIEFING_FINALIZED
{
    "briefing": str,              # Final synthesized briefing
    "iteration": int,
    "sections": [...],
    "synthesis": str | None       # Orchestrator's final response (optional)
}
```

### Frontend Display

The WebSocket client receives events and updates a "Briefing" panel:

```
┌─────────────────────────────────────────┐
│  Briefing Room                          │
├─────────────────────────────────────────┤
│  User Request:                          │
│  What's the status of PRJ-001?          │
│                                         │
│  Scope: Project PRJ-001, main branch    │
│                                         │
│  ✓ project_manager contributed         │
│    • PRJ-001: "Assembly Line Retrofit"  │
│    • Status: In Progress (45%)          │
│    • Budget: $500K allocated            │
│                                         │
│  ✓ evm_analyst contributed              │
│    • CPI: 0.95 (over budget)            │
│    • SPI: 1.05 (ahead of schedule)      │
│    • EAC: $525K                         │
│                                         │
│  ✓ change_order_manager contributed     │
│    • CO-0042: $25K impact approved      │
│                                         │
│  Finalizing response...                 │
└─────────────────────────────────────────┘
```

### Debug Observation

For debugging, the full briefing state is logged at each transition:

```python
logger.debug(
    "[BriefingRoom] Iteration %d: Specialist=%s, Briefing length=%d chars",
    state["iteration"], specialist, len(state["briefing"])
)
```

---

## State API vs Store API

| Aspect | State API (recommended) | Store API (future) |
|--------|------------------------|-------------------|
| Implementation | `BriefingState.briefing` field | `InMemoryStore` / `AsyncPostgresStore` |
| Complexity | Simple, observable | Namespaced key-value, more setup |
| Cross-session | No (in-graph only) | Yes (persists across sessions) |
| Debuggability | High (state inspection) | Medium (store queries) |
| Migration effort | Low | Medium |

**Recommendation:** Start with State API. Migrate to Store API if cross-session briefing persistence becomes important.

---

## Migration Path

### Phase 1 — Briefing Infrastructure (no behavior change)
Create `briefing.py`, `briefing_state.py`, `briefing_compiler.py`, `briefing_specialist.py`. All existing tests pass unchanged.

### Phase 2 — BriefingRoomOrchestrator Implementation (new feature)
Create `briefing_room_orchestrator.py` using `BriefingState` and wrapper nodes. Add routing in `agent_service.py`. This is **additive** — `SupervisorOrchestrator` continues working unchanged. Integration tests for the new orchestrator.

### Phase 3 — Multi-Turn Persistence
Store `briefing_data` in conversation metadata. Load on follow-up messages. End-to-end multi-turn testing.

### Phase 4 — Optional Enhancements
- LLM-based briefing compression for large briefings (`BriefingConfig.compilation = "llm"`)
- Frontend briefing panel UI (consume new event types)
- Store API migration for cross-session persistence
- Per-agent orchestrator selection (move env var to `AgentConfig.orchestrator_type`)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Specialist loses context from raw messages | Lower quality responses | Briefing carries structured data + summaries; prompt encourages specialists to re-query if needed |
| Briefing compilation adds latency | Slightly slower per-specialist | String-based compilation is instant; LLM-based only when needed |
| Multi-turn briefing grows too large | Token budget exceeded | Compression pass or section pruning |
| Users choose wrong orchestrator | Suboptimal experience | Clear documentation of when to use each; default to `SupervisorOrchestrator` for backward compatibility |
| Two orchestrators increase maintenance burden | More code to maintain | Shared infrastructure (briefing models can be reused by supervisor if needed); separate test suites |
| Wrapper nodes introduce LangGraph edge cases | Subtle routing bugs | Thorough integration tests with real graph execution |

---

## Decision Points

**1. BriefingRoomOrchestrator implementation approach?**
→ **Custom node.** This gives full control over what the orchestrator sees (briefing, not messages). The orchestrator only makes routing decisions — no domain tools needed.

**2. Compilation strategy?**
→ **String-based with pluggable LLM compression.** Start with direct string assembly (instant, ~0ms). Add LLM-based compression in future via configuration flag (`BriefingConfig.compilation: "string" | "llm"`) when briefings regularly exceed ~1500 tokens. The `to_context_string()` method encapsulates the strategy.

**3. Is the pattern sequential?**
→ **Yes, confirmed.** The briefing room is inherently sequential — specialists read from and write to the same shared document. Each specialist's findings are compiled before the next specialist begins. For parallel batch operations, use `SupervisorOrchestrator` with the `task` tool.

**4. How do users choose between orchestrators?**
→ **Existing `AI_ORCHESTRATOR` environment variable.** Update `app/core/config.py` to support three values: `"deep"` (default), `"supervisor"`, or `"briefing_room"`. No UI changes needed for initial implementation.

**5. Deep Agent orchestrator changes?**
→ **No changes.** `DeepAgentOrchestrator` remains the entry point that delegates to the selected orchestrator pattern. The `AI_ORCHESTRATOR` env var selects among all three options.

---

## Expected Outcomes

| Metric | SupervisorOrchestrator (Current) | BriefingRoomOrchestrator | Improvement |
|--------|--------------------------------|-------------------------|-------------|
| Per-specialist context (3-specialist request) | ~3000-5000 tokens | ~300-700 tokens | 5-10x |
| Orchestrator synthesis context | ~8000+ tokens | ~700-1000 tokens | 8-10x |
| Multi-turn context growth | Linear (doubles each turn) | Capped (briefing compresses) | Significant for 3+ turns |
| Redundant API calls (multi-turn) | High (re-fetches data) | None (briefing carries findings) | Eliminates re-fetching |
| Briefing compilation cost | N/A | ~0ms (string-based) | Negligible |
| Debuggability | High (full transcript) | Medium (briefing only) | Trade-off for efficiency |

---

## References

- Karpathy's compiler analogy: [MindStudio blog](https://www.mindstudio.ai/blog/karpathy-llm-knowledge-base-compiler-analogy)
- LangGraph Store API: Cross-agent data sharing via namespaced key-value stores
- LangGraph `output_mode`: `last_message` vs `full_history` in langgraph-supervisor
- LangGraph subgraph state sharing: Matching keys are shared between parent and child
- Previous analysis: `docs/03-project-plan/iterations/2026-04-26-agent-handoff-analysis/`
- Architecture docs: `docs/02-architecture/ai/agent-common-concepts.md`, `docs/02-architecture/ai/supervisor-orchestrator.md`
