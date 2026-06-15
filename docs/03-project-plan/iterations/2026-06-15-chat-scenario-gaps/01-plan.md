# Plan: Chat Scenario Gaps (Single-step / Multi-step / Replan)

**Created:** 2026-06-15 · **Iteration:** `2026-06-15-chat-scenario-gaps`
**Analysis:** see `00-analysis.md`. **Regression harness:** `e2e/20260615_chat-scenarios-single-multi-replan/` (3 scenarios).

This plan is ordered by **impact × confidence × reversibility**. Each item lists files, the change, acceptance criteria, and the exact e2e scenario that verifies it. Defer items you don't want now — they are independent.

---

## P0 — G1: Surface `contract_value` to AI tools (correctness, ~1h)

**Why first:** it is the only gap producing a flatly *wrong* answer, the root cause is confirmed and localized, and the fix is small and safe.

**Change:**
- `backend/app/ai/tools/project_tools.py` (`get_project`, `global_search`, `get_project_context`): ensure the project read/response schema serialized back to the model includes `contract_value` and `currency`.
- Confirm the underlying Pydantic read schema (`app/schemas/project*.py` or the DTO used by `response.model_dump()` at line 359) carries the field; if it's the public API schema, do **not** break the API contract — add to the AI-facing serialization, not strip from the API.
- Add `contract_value`/`currency` to the field descriptions the specialist can discover.

**Acceptance:**
- Re-run Scenario 1. The assistant answers **€1,000,000 (EUR)** (or "1,000,000.00 EUR") with **no ask_user** and **no** "not available" wording.
- Unit test: `get_project` response JSON contains `contract_value` key.

**Verify:** e2e Scenario 1.

---

## P1 — G2: Make replan actually fire (dead feature, ~1–2d, has unknowns)

**Why:** an entire adaptive-planning subsystem (replan tool, max-2 guard, `_merge_replanned_steps`, revision prompt) ships but is never exercised. Highest-value but most uncertain — needs a short spike first.

**Spike (DO, ~2h) to confirm root cause before committing the fix:**
1. Turn on debug logging for the supervisor router; run Scenario 3.
2. Inspect the supervisor's tool-selection step: is `request_replan` in the offered tool list? Does the prompt's "REDUNDANT/ALREADY_ACCOMPLISHED/CONTRADICTORY" guidance reach the model? Is the router short-circuiting to the next specialist before the LLM can call it?

**Change (after spike confirms):**
- `backend/app/ai/supervisor_orchestrator.py`: in `_make_supervisor_router` (line ~571–640), give the supervisor an explicit **redundancy check** before auto-forwarding — e.g. when the next step's task is near-identical to the just-completed step's task, inject a strong prompt nudge toward `request_replan` (or auto-skip with a logged reason).
- Strengthen `backend/app/ai/planner.py` replan-revision prompt so the model is *instructed* (not merely permitted) to call `request_replan` when findings are redundant.
- Optional: add a deterministic heuristic fallback (cosine/exact match of consecutive step task descriptions) so replan isn't 100% LLM-dependent.

**Acceptance:**
- Re-run Scenario 3. Log shows **`Replan requested (count=1)`**; the redundant `evm_analyst` step is dropped/merged; final answer still correct.
- Replanning is **observable in the UI** (plan step removed or a "replanned" indicator), not just in logs.
- New unit test: a redundant 2-step plan triggers `_merge_replanned_steps`.

**Verify:** e2e Scenario 3. **Risk:** LLM non-determinism — accept a ≥N/5-runs trigger rate as the bar, not 100%.

---

## P2 — G3: Stop the planner collapsing compound requests (capability, ~1d)

**Change:**
- `backend/app/ai/planner.py`: tune the planner system prompt (`build_planner_system_prompt`) so a request naming **two distinct capabilities** (e.g. "analyze **and** visualize") yields ≥2 steps with the correct specialists. Add a few-shot example mirroring Scenario 2.
- Ensure `visualization_specialist` is **compiled into the supervisor graph** for ai-manager (and any assistant expected to produce charts). It was absent from the Scenario-2 graph — confirm in `supervisor_orchestrator.create_supervisor_graph` specialist loading and the assistant's `delegation_config`/allowed specialists.

**Acceptance:**
- Re-run Scenario 2. Plan shows **`steps≥2`** including a `visualization_specialist` step; a **real chart component** renders (not a markdown/ASCII box). If the project has no EVM data, the assistant says so clearly *before* attempting visualization.

**Verify:** e2e Scenario 2 (ideally on a project populated with EVM data).

---

## P3 — G4: Cut token/context bloat (latency/cost, ~1d)

**Change:**
- Reduce redundant context fetches per turn: the EVM question called 8 distinct retrieval tools. Add a "context budget" — e.g. `get_project_context` + `get_project_analysis` should satisfy EVM without also calling `get_briefing`/`get_project_structure`/`get_temporal_context`/`list_branches` in the same turn (specialist prompt guidance + tool consolidation).
- Aligns with prior work in [[10-llm-latency-investigation]] (DB dedup, RBAC caching, prompt caching).

**Acceptance:**
- Scenario 2 re-run: **token count < 40k** and **tool calls ≤ 6** for the same prompt, with no loss of answer quality.

**Verify:** e2e Scenario 2 execution row (`total_tokens`, `tool_calls_count`).

---

## P4 — G6: Unify log/DB timestamps (observability, ~30min)

**Change:**
- Make `app.log` timestamps **UTC** (or document the offset prominently). Configure the logging formatter (`backend/app/core/logging*` / `app/main.py` logging setup) to emit `%Y-%m-%d %H:%M:%S` **UTC** (or include explicit timezone offset like `+00:00`).

**Acceptance:**
- A `date -u` timestamp matches an `app.log` line for the same event within the same second; `ai_agent_executions.started_at` and the corresponding log line are in the same timezone.

**Verify:** manual — send a message, compare `date -u`, the log line, and the execution row.

---

## P5 — G5/G7: ask_user hygiene + console error sweep (polish, ~1h)

- **G5:** ask_user should not fire for fields that exist but are merely named differently (mitigated largely by P0). Add a guard: before ask_user for "which value", check known synonyms against available tool output.
- **G7:** capture the accumulating console errors (1→8) during a chat session; file/triage individually. Likely PWA/React-Query dev noise, but confirm none are real.

**Verify:** e2e Scenario 1 (no spurious ask_user); `browser_console_messages(level=error)` after a full scenario.

---

## Suggested sequencing & ownership

| Phase | Items | Owner | Exit gate |
|-------|-------|-------|-----------|
| DO-1 | P0 (G1), P4 (G6) | backend-developer | Scenario 1 returns €1M; timestamps align |
| DO-2 | P2 (G3) spike + fix | backend-developer | Scenario 2 yields ≥2 steps + real chart |
| DO-3 | P1 (G2) spike + fix | backend-developer | Scenario 3 replans on redundancy |
| DO-4 | P3 (G4) | backend-developer | Scenario 2 tokens < 40k |
| DO-5 | P5 (G5/G7) | backend + frontend | no spurious ask_user; console clean |

**Definition of Done:** re-run all 3 e2e scenarios; each meets its acceptance criteria; no new `ERROR`/traceback; `02-do.md` / `03-check.md` / `04-act.md` filled from the re-run.

## Notes
- Replan (P1) is the only item with material LLM non-determinism — set a statistical acceptance bar, not a hard pass/fail.
- These fixes are largely independent; P0 can ship alone immediately.
- Consider seeding one **fully-populated** project (WBS + costs + budget + schedule) so EVM/visualization scenarios have real data to work with — removes the "INSUFFICIENT DATA" confound from Scenario 2.
