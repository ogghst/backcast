# Technical Debt Register

**Last Updated:** 2026-05-24
**Total Open Items:** 14
**Total Estimated Effort:** ~13.5 days

---

This file tracks active technical debt items. For completed/closed debt, see [technical-debt-archive.md](./technical-debt-archive.md).

---

## High Severity (P0 - P1)

### [TD-099] ~~Test DB Fixture Uses create_all() Instead of Alembic Migrations~~

- **Status:** ✅ Resolved (2026-05-19) — The `apply_migrations` fixture already uses `command.upgrade(alembic_cfg, "head")` (Alembic migrations). All 24 seeder tests pass. See archive.

---

### [TD-095] ~~Migration Verification Tests for Unified RBAC~~

- **Status:** ✅ Resolved (2026-05-19) — One-time data migration already ran; source data (User.role, ProjectMember) no longer exists. Migration is not re-runnable, so verification tests are moot. See archive.

---

### [TD-096] ~~Security Tests for Unified RBAC~~

- **Status:** ✅ Resolved (2026-05-19) — Created `tests/unit/core/test_rbac_unified_security.py` with 27 tests across 5 classes: metadata injection, expired role denial, cache poisoning, scope isolation, admin bypass. Found and documented gap: `get_user_roles()` does not filter expired assignments. See archive.

---

### [TD-097] ~~Performance Benchmarks for Unified RBAC~~

- **Status:** ✅ Resolved (2026-05-19) — Created `tests/perf/bench_rbac_unified.py` with 4 benchmarks. All targets met: cached 0.00ms, cold 1.80ms, bulk worst 4.27ms, invalidation 0.18ms. See archive.

---

### [TD-098] ~~Delete Deprecated RBAC Files After Validation~~

- **Status:** ✅ Resolved (2026-05-16) — Completed by unified-rbac-cleanup iteration. See archive.

---

### [TD-092] ~~Frontend TypeScript Errors (Pre-existing)~~

- **Status:** ✅ Resolved (2026-05-19) — `npx tsc --noEmit` passes with zero errors. The 26 pre-existing TypeScript errors were fixed incidentally during subsequent iterations. See archive.

---

### [TD-093] Test Coverage Gap (Project-Wide)

- **Source:** 2026-05-10-co-critical-fixes CHECK phase report
- **Description:** Project-wide test coverage is 31.97%, significantly below the 80% target. Services needing coverage: AI services (agent_service, ai_tool_service), RBAC (rbac_service, rbac_admin_service), change_order, and several other services. New code in this iteration achieved 100% coverage but project-wide debt remains.
- **Impact:** Reduced confidence in code changes, higher regression risk, difficulty refactoring without safety net
- **Estimated Effort:** 8 hours (ongoing)
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P1 (High)
- **Blocker:** No
- **Suggested Approach:** Prioritize coverage for high-risk services (RBAC, change_order), then add tests for AI services. Use `pytest --cov=app --cov-report=term-missing` to identify untested lines. Target 80% coverage per service, not project-wide.

---

### [TD-094] Missing E2E Integration Tests for Change Order Workflows

- **Source:** 2026-05-10-co-critical-fixes CHECK phase report
- **Description:** Change order workflows (submit, approve, reject, recover) lack E2E integration tests. Manual verification was performed during this iteration but automated tests are needed for regression prevention. Frontend crash blocking E2E testing has been fixed, removing blocker.
- **Impact:** High-risk workflows without automated validation, manual testing required for each change
- **Estimated Effort:** 2 days
- **Status:** Open
- **Owner:** QA/Backend Developer
- **Priority:** P1 (High)
- **Blocker:** No (frontend crash fixed in 2026-05-10-co-critical-fixes)
- **Suggested Approach:** Create test suite `tests/integration/test_change_order_workflow_e2e.py` covering: submit → approve → merge, submit → reject → discard, admin recovery workflow, empty branch handling. Use test database and real API routes.

---

---

### [TD-084] ~~Decompose `_run_agent_graph` Method~~

- **Status:** ✅ Resolved (2026-05-20) — Decomposed 957-line method into 14 focused units. Created `StreamState` and `GraphContext` dataclasses in `graph_params.py`. Extracted 12 methods: `_prepare_graph_execution`, `_process_stream_events`, `_persist_session_messages`, `_finalize_execution`, and 9 event handler methods. Main method reduced to 84-line orchestrator. See archive.

---

### [TD-085] Migrate `astream_events` from v1 to v2

- **Source:** LangGraph best practices review (Context7 docs)
- **Description:** `_process_stream_events` uses `graph.astream_events(..., version="v1")`. LangGraph recommends `version="v2"` which changes the event format and provides cleaner stream modes (`updates`, `custom`, `messages`). The v1 API is legacy and may be deprecated. Migration requires updating all 9 event handler methods.
- **Impact:** Stuck on deprecated API; v2 offers `stream_mode=["updates", "custom"]` which could replace manual event bus publishing and simplify token streaming via `get_stream_writer()`.
- **Estimated Effort:** 2 days
- **Status:** Open
- **Owner:** Backend Developer
- **Suggested Approach:** Migrate event handlers to v2 format first (no behavior change), then evaluate replacing manual `StreamState.publish` / `StreamState.token_buffer` with LangGraph's `get_stream_writer()` and `stream_mode=["updates", "custom", "messages"]`.

---

## Medium Severity (P2 - P3)

### [TD-091] ~~Unit Test Failures (Pre-existing)~~

- **Status:** ✅ Resolved (2026-05-19) — All 1279 unit tests pass (0 failures). Root causes: (1) `get_accessible_projects` admin path didn't filter `None` scope_ids, (2) RBAC migration read from deleted `config/rbac.json` instead of `seed/rbac_roles.json`, (3) test conftest truncated `rbac_roles`/`rbac_role_permissions` seed tables. All three fixed. See archive.

---

### [TD-016] ~~Performance Optimization (Large Projects)~~

- **Status:** ✅ Resolved (2026-05-19) — Backend supports pagination (`page`/`per_page`), `useWBEs` defaults to pageSize 20, and ProjectTree uses lazy loading via `loadData`. See archive.

### [TD-086] ~~Stringly-Typed Event Types and Tool Names~~

- **Status:** Resolved (2026-05-19) -- Created `AgentEventType` and `ExecutionStatus` enums in `backend/app/ai/event_types.py`. Updated all references in `agent_service.py`, `agent_event_bus.py`, `ai_chat.py` routes, `app/main.py`, and `app/models/schemas/ai.py`. See archive.

### [TD-087] ~~Parameter Sprawl in Graph Creation Methods~~

- **Status:** ✅ Resolved (2026-05-19) — Created `GraphCreationParams` and `GraphExecutionParams` dataclasses in `app/ai/graph_params.py`. Refactored `_create_deep_agent_graph` (11→1 param) and `_run_agent_graph` (13→1 param) to accept grouped params with destructuring. `start_execution` public API unchanged. See archive.

---

### [TD-100] ~~Role Dropdown Shows All Roles in Project Context~~

- **Status:** ✅ Resolved (2026-05-19) — Added `PROJECT_ASSIGNABLE_ROLES` filter constant in `useProjectRoleMap` hook to exclude AI-specific and system-only roles from the project member dropdown. See archive.

---

### [TD-101] ~~Admin Role Assignments Page Shows "—" for User Name~~

- **Status:** ✅ Resolved (2026-05-19) — The list endpoint already enriches with `user_name`, `role_name`, `granted_by_name` via batch JOINs. The enrichment was implemented as part of the unified RBAC iteration. See archive.

---

### [TD-102] ~~Dual-Source RBAC Config (JSON vs DB) Without Sync Validation~~

- **Status:** ✅ Resolved (2026-05-19) — Removed `config/rbac.json` and all legacy `RBAC_PROVIDER=json` code paths. `seed/rbac_roles.json` is now the single source of truth. Updated seeder, config, env files, tests, and Docker configs. See archive.

---

### [TD-103] ~~Temporal Context Not Propagated to Global AI Chat~~

- **Status:** ✅ Resolved (2026-05-19) — Added `globalSelectedTime` to Time Machine store, made UI components work without projectId (date-only, no branch selector). See archive.

---

### [TD-104] ~~Currency Hardcoded to EUR~~

- **Status:** ✅ Resolved (2026-05-19) — Added `currency` field (ISO 4217, default "EUR") to Project model with Alembic migration. Created `useProjectCurrency` hook and updated `formatCurrency`/`formatCompactCurrency`/`getCurrencySymbol` to accept currency param. Replaced all 40+ hardcoded EUR/€ references across 25+ frontend components. Both `ProjectModal` (list) and `ProjectEditModal` (overview) include currency dropdown with 5 options. E2E verified: EUR→USD→EUR round-trip works correctly across project list, edit modal, and overview page. See archive.

---

### [TD-105] ~~Pre-existing MyPy Type-Var Errors in change_order_service.py~~

- **Status:** ✅ Resolved (2026-05-19) — MyPy passes clean on `change_order_service.py`. Errors were likely fixed incidentally during a prior iteration. See archive.

---

### [TD-106] ~~Import-Sorting Errors in Test Files (167 I001 Ruff Errors)~~

- **Status:** ✅ Resolved (2026-05-16) — Fixed with `ruff check --fix tests/` in ACT phase.

### [TD-107] ~~Dashboard Widgets Ignore Temporal Context~~

- **Status:** ✅ Resolved (2026-05-19) — Added `useTimeMachineParams()` to `useDashboardData` hook, updated query key to include temporal params, added `branch` and `as_of` params to backend endpoint and service. See archive.

### [TD-109] Add trim_messages to Streaming Execution Path

- **Source:** AI chat overhead analysis (May 2026) — agent session with 13 LLM calls for 9 tool calls, 149s execution time
- **Description:** The main streaming execution path (`_process_stream_events` in `agent_service.py`) has no message trimming. Full conversation history is sent to the LLM on every call, causing exponential latency growth (2.7s → 26.6s across 13 calls). LangGraph's `trim_messages()` utility or tighter `SummarizationMiddleware` integration could bound context size.
- **Impact:** LLM calls grow exponentially slower as conversation accumulates; DeepSeek costs scale with token count
- **Estimated Effort:** 1 day
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P2 (Medium)
- **Suggested Approach:** Investigate `trim_messages(strategy="last", max_tokens=...)` as a preprocessing step before each LLM call in the streaming path. Consider `SummarizationMiddleware` integration with the non-supervisor graph. Requires analysis of how trimming interacts with the briefing system and specialist isolation.

---

### [TD-110] Enable Parallel Tool Calls for Batch Operations

- **Source:** AI chat overhead analysis (May 2026)
- **Description:** `graph.py` sets `parallel_tool_calls=False` (line 128), forcing all tool calls to execute sequentially. For batch operations like creating multiple cost elements or WBEs, this causes multiple full supervisor→specialist→supervisor cycles. Enabling parallelism would reduce sequential LLM rounds.
- **Impact:** Batch operations take 3-5x longer than necessary; recursion limit hit on comprehensive project creation
- **Estimated Effort:** 4 hours
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P3 (Medium)
- **Suggested Approach:** Investigate impact on `SequentialToolCallsMiddleware`, `RBACToolNode` permission checking, and `BackcastSecurityMiddleware`. These middlewares may rely on sequential execution order. Start by enabling parallelism only for read-only tools as a safe first step.

---

### [TD-111] Reduce Supervisor Intermediate Message Accumulation

- **Source:** AI chat overhead analysis (May 2026) — `output_mode="last_message"` doesn't exist on `langchain.create_agent`
- **Description:** The supervisor agent's intermediate messages (routing decisions, handoff tool calls) accumulate in parent state via `operator.add` on `messages`. This inflates context sent to the LLM on each iteration, contributing to exponential latency growth. The `output_mode="last_message"` parameter only exists in the `langgraph-supervisor` package (not installed).
- **Impact:** Each supervisor cycle adds 2-3 intermediate messages to context; 4 empty supervisor turns wasted ~60s in the analyzed session
- **Estimated Effort:** 1 day
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P2 (Medium)
- **Suggested Approach:** Either (a) install `langgraph-supervisor` and refactor to use `create_supervisor()` with `output_mode="last_message"`, or (b) replace `operator.add` on messages with a custom reducer that keeps only the final AIMessage from each supervisor turn, discarding intermediate tool-call chatter.

---

### [TD-108] ~~Home Dashboard Card Shows Wrong Currency Symbol~~

- **Status:** ✅ Resolved (2026-05-23) — Root cause: `transformProjectSpotlight` had hardcoded `Intl.NumberFormat("USD")`. Fixed by: (1) added `currency` field to backend `ProjectSpotlight` schema and service, (2) replaced hardcoded formatter with `formatCompactCurrency` in frontend transformer, (3) updated mock handlers and test expectations. See archive.

---

### [TD-112] Migration `dedup_dashboard_layouts` Breaks Test DB Setup

- **Source:** Test suite run (2026-05-24) — 69 ERROR results across test suite
- **Description:** The `dedup_dashboard_layouts` migration references the `dashboard_layouts` table before it's been created by its own migration. When Alembic runs migrations in order, this migration executes before the table-creating migration, causing `UndefinedTableError: relation "dashboard_layouts" does not exist` in every test that uses the `apply_migrations` fixture.
- **Impact:** All integration and service tests that need a fresh DB fail at setup. Tests affected: `test_work_package_service` (22 tests), `test_evm_service` (26 tests), `test_evm_service_wbe_project` (11 tests), `test_impact_analysis_service` (3 tests), and various temporal tests — 69+ errors total.
- **Estimated Effort:** 2 hours
- **Status:** Done
- **Owner:** Backend Developer
- **Priority:** P1 (High)
- **Suggested Approach:** Added `depends_on = "20260405_add_dashboard_layouts"` to the migration so Alembic ensures the table exists before the data migration runs.

---

### [TD-116] Work Package Service Tests Missing PackageType Seed Data

- **Source:** Test suite run (2026-05-24) — 20 FAILED results in `tests/services/test_work_package_service.py`
- **Description:** `_validate_package_type()` queries the DB for active `PackageType` records, but no test fixture seeds them. Every test that creates a work package fails with `ValueError: Invalid package_type 'quality_impact'. No active package type with that code found.` The DB-driven validation was added in the PackageType feature but tests still assume hardcoded type strings work without seed data.
- **Impact:** All 20 work package service tests fail, blocking any regression testing for the work package domain
- **Estimated Effort:** 1-2 hours
- **Status:** ✅ Resolved (2026-05-25) — Added `seed_package_types` autouse fixture that reads `seed/package_types.json` and creates all 5 package types via `PackageTypeService`. Added `"package_types"` to conftest truncation list. 21/22 tests now pass; the remaining failure (`test_create_work_package_invalid_type_raises`) is a pre-existing test bug expecting Pydantic `ValidationError` on a plain `str` field.

---

### [TD-117] Agent Service Unit Tests Use Stale `_run_agent_graph` Signature

- **Source:** Test suite run (2026-05-24) — 7 FAILED results in `tests/unit/services/test_agent_service.py`
- **Description:** Tests call `AgentService._run_agent_graph(message=...)` but the method no longer accepts a `message` keyword argument — it was changed during the recent briefing/streaming refactor. All 7 tests fail with `TypeError: AgentService._run_agent_graph() got an unexpected keyword argument 'message'`.
- **Impact:** All agent service unit tests are broken, preventing regression testing for event publishing, metrics, and error handling
- **Estimated Effort:** 1 hour
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P1 (High)
- **Suggested Approach:** Read current `_run_agent_graph()` signature and update all 7 test calls to match. Likely the param was renamed or absorbed into a params dataclass.

---

### [TD-113] BriefingDocument.from_state Recovers from Invalid Data Instead of Failing

- **Source:** Test suite run (2026-05-24) — `test_briefing_room_orchestrator.py::TestCreateGetBriefingTool::test_returns_default_when_briefing_data_invalid`
- **Description:** `BriefingDocument.from_state({"garbage": True})` returns a "recovered" briefing document instead of raising or returning a sentinel. The test expects `"No briefing available yet."` but gets `"# Briefing Document\n## Request\n(recovered)"`. The recovery logic is too lenient — arbitrary dict input produces a synthetic briefing rather than a clear error/default.
- **Impact:** Test failure masks potential briefing corruption; AI agents may operate on fabricated briefing data when state is corrupted
- **Estimated Effort:** 4 hours
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P2 (Medium)
- **Suggested Approach:** Either (a) make `from_state` raise `ValidationError` on structurally invalid input and catch it at the call site to return the sentinel, or (b) add a `is_recovered` flag and have the get_briefing tool return the default message when the briefing is recovered rather than genuine.

---

### [TD-114] Performance Tests Missing Async Event Loop Fixture

- **Source:** Test suite run (2026-05-24) — 5 FAILED results in `tests/performance/`
- **Description:** Performance tests (`test_risk_check_overhead.py`, `test_tool_performance.py`) fail with `RuntimeError: no running event loop`. The tests use scoped sessions (`scoped_session`) that require an active asyncio event loop, but the test functions are not marked `async` or lack proper `@pytest.mark.asyncio` setup.
- **Impact:** All performance benchmark tests are broken, preventing regression detection for tool execution and RBAC overhead
- **Estimated Effort:** 4 hours
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P3 (Medium)
- **Suggested Approach:** Add `@pytest.mark.asyncio` to test functions, or refactor to use sync wrappers that create their own event loop. Ensure benchmark fixtures work with async test functions.

---

### [TD-115] RBAC Singleton State Leaks Between Test Classes

- **Source:** Test suite run (2026-05-24) — `test_rbac_unified.py::TestSingleton::test_get_unified_rbac_service_creates_singleton`
- **Description:** The test passes in isolation but fails when run as part of the full suite. `get_unified_rbac_service()` returns a singleton whose state (permission cache, role assignments) persists across test classes. When a prior test modifies the singleton's cache, the singleton test observes stale state.
- **Impact:** Flaky test failure; reduced confidence in RBAC test results; singleton pattern makes unit testing unreliable
- **Estimated Effort:** 2 hours
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P3 (Medium)
- **Suggested Approach:** Add a `reset()` or `_clear_cache()` method to `UnifiedRBACService` and call it in a `@pytest.fixture(autouse=True)` or `setUp` in affected test classes. Alternatively, patch `_instance = None` in the module between tests.

---

### [TD-118] WBE Test Assertion Doesn't Handle TSTZRANGE Format

- **Source:** Test suite run (2026-05-24) — `tests/api/routes/wbes/test_wbes.py::test_create_wbe_with_control_date`
- **Description:** Test asserts `data["valid_time"].startswith(control_date[:10])` but the API now returns `valid_time` as a PostgreSQL TSTZRANGE string like `'["2026-03-03T10:00:00+00:00",)'` which starts with `[`, not the date. The assertion fails because the response format changed to include the range wrapper.
- **Impact:** False test failure masks actual WBE creation correctness
- **Estimated Effort:** 15 minutes
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P2 (Medium)
- **Suggested Approach:** Update assertion to extract the date from the TSTZRANGE string, e.g. `assert control_date[:10] in data["valid_time"]`, or parse the JSON range before asserting.

---

### [TD-119] Performance Tests Fail on Environment-Dependent Thresholds

- **Source:** Test suite run (2026-05-24) — 12 FAILED results across `tests/performance/`
- **Description:** Performance benchmark tests (agent latency, streaming throughput, tool execution p50/p99, EVM calculation, merge, risk check overhead) fail against fixed thresholds. Results are sensitive to machine load, CI runner specs, and whether a live LLM endpoint is available. The AI performance tests additionally require a configured LLM and fail without one.
- **Impact:** Performance regression detection is non-functional; tests are noisy in CI
- **Estimated Effort:** 2 hours
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P3 (Low)
- **Suggested Approach:** Widen thresholds with generous margins for CI variance. Mark AI-dependent performance tests as `@pytest.mark.skipif` when no LLM endpoint is configured. Consider converting strict assertions to warnings or using `@pytest.mark.xfail(strict=False)` for inherently flaky benchmarks.

---

### [TD-120] AI Security & Concurrency Tests Require Live LLM Endpoint

- **Source:** Test suite run (2026-05-24) — 3 FAILED results in `tests/integration/ai/test_temporal_security.py` (2) and `tests/integration/ai/tools/test_concurrent_tool_execution.py` (1)
- **Description:** Prompt injection resistance tests and concurrent tool execution tests depend on a live LLM endpoint to validate behavior. Without one, these integration tests fail. The temporal security tests verify that the AI cannot bypass `as_of` and `branch_mode` constraints via prompt injection.
- **Impact:** AI security regression tests are non-functional without LLM; prompt injection vulnerabilities could go undetected
- **Estimated Effort:** 1 hour
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P3 (Medium)
- **Suggested Approach:** Add `@pytest.mark.skipif` guards that check for a configured LLM endpoint. Ensure these tests run in CI with a test LLM provider, or add mock-based alternatives for core assertion logic.

---

---

## Summary

| Priority | Count | Total Effort |
|----------|-------|--------------|
| High (P0-P1) | 3 | ~2 days |
| Medium (P2-P3) | 10 | ~10 days |
| Low (P4+) | 1 | ~5 hours |
| **Total** | **14** | **~12 days** |

---

## Links

- [Technical Debt Archive](./technical-debt-archive.md) - Completed debt items (54 items)
- [Sprint Backlog](./sprint-backlog.md) - Current iteration
- [Product Backlog](./product-backlog.md) - All pending work
