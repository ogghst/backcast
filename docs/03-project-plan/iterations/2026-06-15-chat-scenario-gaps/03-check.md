# CHECK: P0 — Re-run results & acceptance

**Iteration:** `2026-06-15-chat-scenario-gaps` · **Re-run date:** 2026-06-15
**Scenario:** e2e Scenario 1 — `What is the contract value of project "AAA First"?`
**Assistant:** Senior Project Manager (`ai-manager`), standard mode · **Session:** `bf96cf52-652c-4c9e-97fd-f412c4dfa7e2` · **Execution:** `096834f2-29c8-4387-ad89-1599f438d917`

---

## Verdict: ✅ PASS (all P0 acceptance criteria met)

| # | Acceptance criterion (from `01-plan.md`) | Result | Evidence |
|---|------------------------------------------|--------|----------|
| 1 | Assistant answers **€1,000,000 (EUR)** | ✅ PASS | UI bubble + persisted message: *"…the contract value for project "AAA First" is: **€1,000,000.00 EUR**"* |
| 2 | **No ask_user** | ✅ PASS | No `ask_user` tool call in `app.log`; no clarification modal in UI |
| 3 | **No "not available"** wording | ✅ PASS | Answer is the correct value; the prior "not exposed by the available project retrieval endpoint" wording is gone |
| 4 | Unit test: `get_project` JSON contains `contract_value` | ✅ PASS | `tests/ai/test_project_tools_contract_value.py` — 3 passed |

## Before / after (Scenario 1)

| Metric | Before (broken) | After (P0) | Δ |
|--------|-----------------|------------|---|
| Answer correctness | ❌ "field not available" | ✅ €1,000,000.00 EUR | fixed |
| ask_user fired | yes (295s auto-expire round-trip) | no | removed |
| Tool calls | 12 | 10 | −2 |
| Tokens (`total_tokens`) | 47,218 | 40,999 | −13% |
| Wall-clock duration | 156s | 87s | −44% |

Token/duration gains are a direct consequence of eliminating the ask_user clarification round-trip that the broken serialization forced.

## DB evidence

```
ai_agent_executions[096834f2…]:
  status=completed, total_tokens=40999, tool_calls_count=10,
  error_message=NULL, started_at=04:14:02Z, completed_at=04:15:29Z (87s)

ai_conversation_messages[bf96cf52…] (2 rows):
  user:      "What is the contract value of project \"AAA First\"?"
  assistant: "Based on the findings, the contract value for project **\"AAA First\"** is:
              **€1,000,000.00 EUR**
              - Project Code: SORT-A
              - Status: Active
              - Budget allocated: None (budget field is null)"
```

The assistant now **correctly distinguishes** `contract_value` (€1M) from `budget` (null) — better than the original ask, which conflated them.

## Log evidence (`backend/logs/app.log`, window 04:14–04:15Z)

- `[TOOL_START] … handoff_to_project_manager`, `global_search`, `get_project`, `get_briefing` — retrieval flow, no clarification.
- `[RUN_AGENT_GRAPH_COMPLETE] duration_ms=83896 | total_tokens=40999 | tool_calls_count=10`.
- **No** `ask_user`, **no** `Replan requested`, **no** `ERROR`/traceback.

## Residual / non-blocking observations (carried to ACT)

1. **Supervisor routing warnings** (pre-existing, unrelated to P0): `[SUPERVISOR] Max iterations (5) reached, forcing END` and `[SPECIALIST_NODE] No matching step found for 'project_manager'`. Correct answer still produced. Belongs to P1 (G2) territory.
2. **Log TZ is launch-env-dependent** (confirmed during this re-run): the restarted process writes UTC to the file; the prior process wrote local. This is the G6 mechanism → P4.

## Artifact

- Screenshot: `e2e/20260615_chat-scenarios-single-multi-replan/snapshots/sc1-p0-fix-verified.png`

P0 is **done and verified**. The remaining items (P1–P5) are independently schedulable per `01-plan.md`.
