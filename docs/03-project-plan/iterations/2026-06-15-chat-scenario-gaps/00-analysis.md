# Analysis: Chat Scenario Gaps (Single-step / Multi-step / Replan)

**Created:** 2026-06-15
**Source:** E2E test `e2e/20260615_chat-scenarios-single-multi-replan/` (see `report.md`)
**Request:** Run 3 chat topologies (single-step, multi-step, replan) through the live UI, monitor `app.log`, condense results, identify gaps, and produce an actionable fix plan.

---

## TL;DR

All three scenarios **completed without backend errors**, but **none did what the prompt actually asked**:

| Topology | What we asked | What happened | Severity |
|----------|---------------|---------------|----------|
| Single-step | "contract value of AAA First" | AI said field "not available" — it's **€1,000,000** | 🔴 Correctness |
| Multi-step | "EVM analysis **+ visualization dashboard**" | Planner collapsed to **1 step**; `visualization_specialist` never engaged; fake markdown "dashboard" | 🔴 Capability |
| Replan | deliberately redundant 2-step plan | Both steps ran verbatim; **replan never fired** (0 occurrences ever) | 🔴 Dead feature |

**Common thread:** the planner/supervisor pipeline is reliable at *not crashing* but unreliable at *correctness, multi-specialist decomposition, and adaptive re-planning*.

---

## Gaps (root-caused)

### G1 — `contract_value` is invisible to AI tools 🔴
- **Evidence:** Scenario 1. DB shows `projects.contract_value = 1000000.00` (EUR) for AAA First. The `project_manager` specialist answered *"contract_value... is not exposed by the available project retrieval endpoint; only budget, name, code, status, start_date, end_date, and description are visible."*
- **Root cause:** `contract_value` / `contractValue` appears **nowhere in `backend/app/ai/`**. The project read schema returned by `get_project` (and `global_search`, `get_project_context`) omits it, so the field is literally unsurfaced to the model. Not a specialist misread.
- **Impact:** The system cannot answer the single most basic project-financial question. ask_user then *over-triggers* (G5) to compensate — and even after the user clarified, the answer stayed wrong.

### G2 — Replan never triggers (`request_replan` is dead code) 🔴
- **Evidence:** Scenario 3 created a genuine 2-step plan (`project_manager` → `evm_analyst`, identical redundant task). After step 1 completed, the supervisor **immediately** delegated step 2 — no `request_replan`. The `evm_analyst`'s own briefing noted *"EVM cross-verification confirms project details match project_manager report"* (i.e. redundancy was visible), yet still no replan. Historical scan: **0 `Replan requested` lines across all 11 log files** (`app.log` + `app.log.1..10`).
- **Root cause (hypothesis, to confirm in DO):** the `request_replan` tool is wired (`create_replan_tool()` added to `supervisor_tools` in `supervisor_orchestrator.py:388`), but the supervisor system prompt / router does not reliably steer the LLM to invoke it. The replan-evaluation instruction lives in the supervisor prompt but the routing logic (`_make_supervisor_router`, line 571) forwards to the next specialist by default. With no positive pressure to call `request_replan`, the LLM never does.
- **Impact:** `_merge_replanned_steps`, the max-2-replans guard, and the entire replan revision prompt path are unexercised. Users pay full token cost for redundant steps (43k tokens on scenario 3's duplicate retrieval).

### G3 — Planner over-collapses compound requests to a single step 🔴
- **Evidence:** Scenario 2. Prompt explicitly requested *"EVM analysis **and then** build a visualization dashboard... both analysis and chart-building."* Planner returned `complexity=simple, steps=1` (single `evm_analyst`). The supervisor graph compiled only **4** specialists (accountant, evm_analyst, project_manager, time_traveller) — **`visualization_specialist` was not in the graph at all** for this assistant. `evm_analyst` fabricated a markdown/ASCII "dashboard" instead.
- **Root cause:** (a) planner bias toward single-specialist plans; (b) `visualization_specialist` not compiled into the ai-manager assistant's supervisor graph → real chart rendering is unreachable there. Both need confirmation.

### G4 — Token / context explosion 🟠
- **Evidence:** Scenario 2 burned **118,686 tokens** (16 tool calls, 244s) on an *empty* project (no WBS/costs/budget → "INSUFFICIENT DATA"). Scenario 1 used 47k tokens for one fact.
- **Root cause:** context bloat + redundant retrieval calls (e.g. `get_briefing`, `get_project_context`, `get_project_structure`, `get_temporal_context`, `list_branches`, `global_search`, `get_project`, `get_project_analysis` all called for one EVM question). Consistent with [[10-llm-latency-investigation]].

### G5 — ask_user over-triggers then ignores the answer 🟠
- **Evidence:** Scenario 1 — specialist asked which numeric value to retrieve; user answered "the contract_value field"; specialist still concluded the field is unavailable (because of G1). ask_user was correct to *ask*, but the underlying G1 made the answer moot.

### G6 — Log/DB timezone mismatch 🟡
- **Evidence:** `app.log` writes **local time** (CEST, e.g. `03:33`); `ai_agent_executions.started_at` stores **UTC** (`01:33:11Z`). Correlating a UI action → log → DB row requires manual ±2h conversion. (No bug in data — friction in observability.)

### G7 — Console errors accumulate 🟡
- **Evidence:** console error count grew 1→8 across the session on each navigation. Not blocking; worth a sweep.

---

## Out of scope (data, not code)
- AAA First has **no WBS / work packages / cost events / budget** → EVM is correctly "INSUFFICIENT DATA". This is a *seed-data* gap, not a defect. Future EVM tests should target a fully-populated project.

## Context Discovery

- **Bounded contexts:** AI Agent (`backend/app/ai/`) — planner.py, supervisor_orchestrator.py, handoff_tools.py, tools/project_tools.py; Frontend Chat (`frontend/src/features/ai/chat/`).
- **Key files:**
  - `backend/app/ai/tools/project_tools.py` — `get_project` (line 191); response omits `contract_value`.
  - `backend/app/ai/handoff_tools.py:142` — `create_replan_tool()` / `request_replan` (wired but unused).
  - `backend/app/ai/supervisor_orchestrator.py:388` — replan tool registration; `:571` `_make_supervisor_router`; `:630` max-replan guard.
  - `backend/app/ai/planner.py` — planner + replan-revision prompts (`_merge_replanned_steps:218`).
- **Verification baseline:** the 3 e2e scenarios in `e2e/20260615_chat-scenarios-single-multi-replan/` are the regression harness for this iteration.

See `01-plan.md` for the prioritized, actionable fix plan.
