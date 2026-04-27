# Analysis: Supervisor Orchestrator Efficiency Issues

**Date:** 2026-04-27
**Scope:** AI agent supervisor orchestrator — redundant synthesis, tool call efficiency, follow-up context
**Status:** Research & Analysis

---

## Executive Summary

End-to-end testing of the supervisor orchestrator (Expert mode, Senior Project Manager assistant) revealed 4 efficiency issues. A project creation with 10 WBEs triggered **51 tool calls** (20 of which were redundant post-creation verification) and took ~8 minutes. A simple follow-up to rename one WBE triggered **16 tool calls** for what should be a 2-3 call operation. The supervisor generates a full re-synthesis after the specialist already provided a comprehensive response.

**Root causes:** graph routing always returns to supervisor after specialist, LLM ignores efficiency prompt instructions, tool results from previous turns are not replayed.

---

## Test Scenario

**Configuration:** Expert mode, Senior Project Manager assistant, supervisor orchestrator with 7 specialists, model glm-4.7

**Message 1:** "create a new project to renew a house, 15 days from now, duration 200 days. include expenses and proper planning with consistent relationships for hydraulic, electrical, floors, roof, ceiling, heating systems, doors, windows, garden, gate"

**Message 2:** "update the name of the last WBE created to 'Main Entrance Gate'"

---

## Finding 1: Supervisor Redundant Synthesis

### Observation

After the `project_manager` specialist produced a comprehensive response (project overview, 10 WBE table, 4 construction phases, budget distribution, next steps), the supervisor made an additional LLM call to generate a synthesis. The supervisor's synthesis largely repeated the specialist's output:

> Specialist (streamed live): Full detailed response with tables, phases, dependencies, budget distribution
> Supervisor (persisted): "I notice that I've already successfully created a comprehensive house renovation project called 'HOUSE-RENEW-2026'... [re-lists all 10 WBEs]"

### Data

| Metric | Value |
|--------|-------|
| Specialist response | 5,496 chars (detailed) |
| Supervisor synthesis | ~1,500 chars (repetitive) |
| Extra LLM call | ~10s (supervisor synthesis) |
| Extra tool calls | `get_project_kpis` + `global_search` by supervisor during synthesis |

### Root Cause

1. **`SUPERVISOR_SYSTEM_PROMPT`** (`supervisor_orchestrator.py:64`) explicitly instructs: "After receiving a response from a specialist, provide a brief, helpful synthesis."
2. **Graph routing**: `_make_specialist_router` (`supervisor_orchestrator.py:295-296`) always returns `"supervisor"` when there's no peer handoff. The specialist cannot signal "I'm done, no synthesis needed."
3. **Persistence model**: Only the supervisor's text is captured into `main_agent_segments` (`agent_service.py:924-931`). Specialist tokens go to `_token_accumulator` for live streaming but NOT to the persisted message. This means the supervisor's synthesis is the ONLY persisted "official" response.

### Context7 Research: `create_forward_message_tool`

LangGraph's `langgraph-supervisor` library provides `create_forward_message_tool` — a tool the supervisor can call to forward the specialist's message directly to the output, bypassing re-processing. This preserves information fidelity and saves tokens.

### Proposed Fix

**Architectural:** Modify `_make_specialist_router` to route directly to `END` when the specialist's last AIMessage has text content and no tool calls. Capture specialist tokens into `main_agent_segments` on `on_chain_end`.

**Files:**
- `backend/app/ai/supervisor_orchestrator.py` — `_make_specialist_router` (lines 276-298), edge list (line 227)
- `backend/app/ai/agent_service.py` — specialist `on_chain_end` handler (lines 897-911)
- `backend/app/ai/supervisor_orchestrator.py` — `SUPERVISOR_SYSTEM_PROMPT` (line 64) as safety net for peer handoff cases

---

## Finding 2: Post-Creation Verification Calls (20 Redundant)

### Observation

After batch-creating 10 cost elements, the specialist called `get_cost_element` 10 times and `global_search` 10 times to verify each creation. But `create_cost_element` already returns full entity data.

### Tool Call Timeline (First Execution)

```
00:20:25 - Supervisor graph created
00:20:32 - get_temporal_context (supervisor)
00:20:39 - write_todos (planning)
00:20:49 - handoff_to_project_manager (correct routing)
00:20:53 - get_temporal_context (specialist)
00:20:58 - create_project + list_cost_element_types (parallel)
00:21:15 - 10x create_wbe (parallel batch, <4ms each)
           --- verification round starts ---
00:21:~   - 10x create_cost_element
00:21:~   - 10x get_cost_element (REDUNDANT)
00:21:~   - 10x global_search (REDUNDANT)
           --- verification round ends ---
00:22:~   - get_project, get_project_structure, list_wbes, list_cost_elements
00:24:~   - global_search
00:25:~   - get_project_kpis
00:28:19 - COMPLETE (473s, 40+ tool calls)
```

### Data

| Tool | Count | Needed? |
|------|-------|---------|
| `get_temporal_context` | 2 | Yes (one per agent) |
| `write_todos` | 1 | Yes (planning) |
| `handoff_to_project_manager` | 1 | Yes (routing) |
| `create_project` | 1 | Yes |
| `list_cost_element_types` | 1 | Yes |
| `create_wbe` | 10 | Yes (parallel batch) |
| `create_cost_element` | 10 | Yes (parallel batch) |
| `get_cost_element` | 10 | **NO — create returns full data** |
| `global_search` | 10 | **NO — not needed after creation** |
| `get_project`, `get_project_structure`, `list_wbes`, `list_cost_elements` | 4 | Marginal (for summary) |

**20 out of ~51 tool calls were redundant.**

### Root Cause

1. The `create_cost_element` tool (`cost_element_template.py:248-374`) returns a comprehensive dict with `id, code, name, budget_amount, schedule_info, forecast_id, schedule_baseline_id, message`. The LLM should not need to re-fetch.
2. The project_manager prompt (`subagents/__init__.py:49-52`) has EFFICIENCY RULES but they're generic: "Call list/read tools ONCE and reuse the results." The LLM ignores this for verification.
3. The tool description doesn't mention that the return value is comprehensive.

### Proposed Fix

**Tool-level (most robust):** Add a `_hint` field to create tool return values: `"_hint": "Entity created successfully with all data above. No need to call get_* or global_search to verify."` This is contextual — appears exactly when the LLM considers verification.

**Prompt-level (defense in depth):** Add explicit anti-patterns to the specialist prompt.

**Tool description enhancement:** Note that returns are comprehensive.

**Files:**
- `backend/app/ai/tools/templates/cost_element_template.py` — return dict (~line 370), description (~line 250)
- `backend/app/ai/tools/templates/crud_template.py` — `create_wbe` return dict (~line 600), description (~line 531)
- `backend/app/ai/subagents/__init__.py` — EFFICIENCY RULES (lines 49-52)

---

## Finding 3: Follow-up Context Inefficiency

### Observation

For the follow-up "update the name of the last WBE created to 'Main Entrance Gate'", the specialist called `list_wbes` 3 times and `list_projects` once — 16 total tool calls for a simple rename.

### Follow-up Tool Call Timeline

```
00:29:38 - Supervisor graph re-created (7 specialists compiled)
00:29:44 - handoff_to_project_manager (correct routing)
00:29:49 - list_wbes (with search param) — missed
           list_wbes (without project_id) — missed
           list_projects (search for project) — redundant (conversation has code)
           list_wbes (with correct project_id) — finally correct
           update_wbe (the actual rename)
           update_wbe (retry/same)
```

### Data

| Tool | Count | Needed? |
|------|-------|---------|
| `handoff_to_project_manager` | 1 | Yes |
| `list_wbes` | 3 | **1 would suffice** |
| `list_projects` | 1 | **NO — conversation has HOUSE-RENEW-2026** |
| `update_wbe` | 2 | **1 would suffice** |

### Root Cause

1. **Tool results not replayed:** `_build_conversation_history` (`agent_service.py:1843`) skips tool messages from previous turns. The specialist has no access to WBE IDs or project IDs from turn 1's tool results.
2. **No session-level entity cache:** There's no mechanism to carry key entity identifiers across turns.
3. The specialist must re-fetch to discover entity IDs, calling `list_wbes` multiple times with different parameter combinations.

### Proposed Fix

**Architectural:** Add a `_build_session_entity_context(session_id)` method that scans recent assistant messages from the DB for entity patterns (codes like "WBE-GTE", project names, budgets). Inject the extracted entities into the system prompt as a context section:

```
Session entities from previous turns:
- Project "House Renovation Project" (HOUSE-RENEW-2026)
- WBE "Gate" (WBE-GTE, budget: $5,000)
- WBE "Roof" (WBE-ROF, budget: $30,000)
```

This provides deterministic entity context regardless of LLM behavior. Token cost is minimal (a few lines).

**Files:**
- `backend/app/ai/agent_service.py` — new method `_build_session_entity_context`, modify `_build_system_prompt`

---

## Finding 4: Deep Agent Synthesis Alignment

### Observation

The deep agent orchestrator's synthesis instructions (`deep_agent_orchestrator.py:303-312`) are also verbose: "highlights the most important findings", "offers relevant next steps".

### Proposed Fix

Tighten to match Issue 1's approach: creation/update → "Done.", analysis → 1-2 sentences, never repeat full output.

**Files:**
- `backend/app/ai/deep_agent_orchestrator.py` — `_build_system_prompt_suffix` (lines 303-312)

---

## Summary Table

| Issue | Impact | Root Cause | Fix Approach | Confidence |
|-------|--------|------------|-------------|------------|
| #1 Supervisor re-synthesis | Extra LLM call + repetitive response | Router always returns to supervisor; persistence only captures supervisor text | Route specialist to END; capture specialist tokens | High |
| #2 Post-creation verification | 20 redundant tool calls (~30% overhead) | LLM ignores generic efficiency rules | `_hint` in tool returns + prompt anti-patterns | Medium-High |
| #3 Follow-up re-fetching | 16 calls for a 2-call operation | Tool results not replayed across turns | Session entity context in system prompt | High |
| #4 Deep agent verbose synthesis | Same as #1 for non-supervisor mode | Prompt says "offer next steps" | Tighten prompt | High |

## Reference Documents

- `docs/02-architecture/ai/supervisor-orchestrator.md` — supervisor handoff architecture
- `docs/02-architecture/ai/agent-common-concepts.md` — shared infrastructure, tools, middleware
- Context7: `langgraph-supervisor` library — `create_forward_message_tool` pattern
