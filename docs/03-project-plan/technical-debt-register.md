# Technical Debt Register

**Last Updated:** 2026-05-19
**Total Open Items:** 14
**Total Estimated Effort:** ~15.5 days

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

### [TD-096] Security Tests for Unified RBAC

- **Source:** 2026-05-10-unified-rbac-refactoring CHECK phase (BE-025)
- **Description:** The unified RBAC system has fail-secure defaults tested at the unit level, but lacks dedicated security tests for edge cases: metadata injection (arbitrary authority_level values in JSONB), expired role denial, cache poisoning scenarios, privilege escalation via scope manipulation, and concurrent assignment modification.
- **Impact:** MEDIUM -- Fail-secure defaults work, but no automated tests for adversarial edge cases.
- **Estimated Effort:** 1 day
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P2 (Medium)
- **Blocker:** No
- **Suggested Approach:** Create `tests/unit/core/test_rbac_unified_security.py` with tests for: setting arbitrary authority_level values, expired role assignments being denied, concurrent cache invalidation, role assignment with conflicting scopes, admin bypass verification.

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

### [TD-088] Test Fixture RBAC Implementations Outdated

- **Source:** Test failure analysis during simplify refactor work (2026-04-27)
- **Description:** `AllowAllRBAC` and `DenyAIRBAC` test fixtures in `tests/api/routes/ai_chat/test_websocket_integration.py` were missing async abstract methods (`has_project_access`, `get_user_projects`, `get_project_role`) required by `RBACServiceABC`. The abstract base class was updated to include these methods, but test fixtures were not updated accordingly, causing 16 test errors during CI.
- **Impact:** 16 websocket integration tests failing at setup due to `TypeError: Can't instantiate abstract class`. Blocks integration testing of AI chat features.
- **Estimated Effort:** 4 hours
- **Status:** ✅ Fixed (2026-04-27)
- **Owner:** Backend Developer
- **Fix:** Added implementations of missing async abstract methods to both `AllowAllRBAC` and `DenyAIRBAC` classes with reasonable default return values for testing.

---

### [TD-089] Test Fixtures Reference Removed `allowed_tools` Column

- **Source:** Test failure analysis during simplify refactor work (2026-04-27)
- **Description:** `AIAssistantConfig` model schema removed the `allowed_tools` column in a prior migration, but test fixtures in `tests/conftest.py` (`test_ai_assistant`, `inactive_ai_assistant`, `test_ai_provider_with_config_factory`) were still instantiating with `allowed_tools=["list_projects"]` parameter. This caused `TypeError: 'allowed_tools' is an invalid keyword argument for AIAssistantConfig`.
- **Impact:** 12 websocket integration tests failing at fixture setup. Tests cannot instantiate AI assistant configurations for integration testing.
- **Estimated Effort:** 2 hours
- **Status:** ✅ Fixed (2026-04-27)
- **Owner:** Backend Developer
- **Fix:** Removed all `allowed_tools` parameter references from `AIAssistantConfig` instantiations in test fixtures.

---

### [TD-084] Decompose `_run_agent_graph` Method

- **Source:** Code review `/simplify` pass on `backend/app/ai/agent_service.py`
- **Description:** `_run_agent_graph` is ~800 lines with deep nesting (try/try/try/except/finally), handling graph setup, event processing, error handling, token batching, and message persistence in a single method. The event processing loop contains 15+ state tracking variables that could be grouped into a dataclass.
- **Impact:** Hard to test, maintain, and reason about. Any change to streaming, persistence, or event handling risks regressions across all concerns.
- **Estimated Effort:** 2 days
- **Status:** Open
- **Owner:** Backend Developer
- **Suggested Approach:** Extract into focused methods: `_init_execution_state()`, `_setup_graph()`, `_process_stream_events()`, `_cleanup_execution()`, `_persist_results()`. Group the 15+ tracking variables into an `ExecutionState` dataclass.

---

### [TD-085] Migrate `astream_events` from v1 to v2

- **Source:** LangGraph best practices review (Context7 docs)
- **Description:** `_run_agent_graph` uses `graph.astream_events(..., version="v1")`. LangGraph recommends `version="v2"` which changes the event format and provides cleaner stream modes (`updates`, `custom`, `messages`). The v1 API is legacy and may be deprecated. Migration requires updating all event type handling in the 400+ line event loop.
- **Impact:** Stuck on deprecated API; v2 offers `stream_mode=["updates", "custom"]` which could replace manual event bus publishing and simplify token streaming via `get_stream_writer()`.
- **Estimated Effort:** 2 days
- **Status:** Open
- **Owner:** Backend Developer
- **Suggested Approach:** Migrate event loop to v2 format first (no behavior change), then evaluate replacing manual `_publish` / `_token_accumulator` with LangGraph's `get_stream_writer()` and `stream_mode=["updates", "custom", "messages"]`.

---

## Medium Severity (P2 - P3)

### [TD-090] WebSocket Integration Test Failures (Pre-existing)

- **Source:** Test failure analysis during simplify refactor work (2026-04-27)
- **Description:** 12 websocket integration tests in `tests/api/routes/ai_chat/test_websocket_integration.py` are failing with pre-existing issues unrelated to recent code changes. Failures include: connection acceptance errors, streaming token issues, tool execution problems, session persistence errors, and various edge case validations. Root causes appear to be: missing OpenAI API keys in test environment, database state inconsistencies, and test isolation issues.
- **Impact:** Cannot validate AI chat WebSocket functionality end-to-end. Blocking confidence in chat feature reliability.
- **Estimated Effort:** 1 day
- **Status:** Open
- **Owner:** Backend Developer
- **Suggested Approach:** Investigate each failure category separately: (1) Add test-only OpenAI API mocking or key setup, (2) Improve database isolation between tests, (3) Fix fixture teardown/cleanup issues.

---

### [TD-091] Unit Test Failures (Pre-existing)

- **Source:** Test failure analysis during simplify refactor work (2026-04-27)
- **Description:** Approximately 33 unit tests are failing with pre-existing issues across multiple test files. These failures existed before the simplify refactor work and are unrelated to recent changes. Categories include: database assertion mismatches, async fixture setup issues, and mock configuration problems.
- **Impact:** Reduces confidence in test suite. Developers must manually verify which failures are regressions vs pre-existing.
- **Estimated Effort:** 1 day
- **Status:** Open
- **Owner:** Backend Developer
- **Suggested Approach:** Categorize failures by root cause (database, async, mocking), fix in priority order, add CI baseline tracking to distinguish new failures from pre-existing ones.

---

### [TD-016] Performance Optimization (Large Projects)

- **Source:** Hierarchical Nav ACT phase
- **Description:** `useWBEs` fetches full list. Needs pagination or server-side tree loading.
- **Impact:** Slow load times for large datasets
- **Estimated Effort:** 3 hours
- **Status:** ⏸️ Deferred (2026-04-23)
- **Owner:** Full Stack Developer

### [TD-086] ~~Stringly-Typed Event Types and Tool Names~~

- **Status:** Resolved (2026-05-19) -- Created `AgentEventType` and `ExecutionStatus` enums in `backend/app/ai/event_types.py`. Updated all references in `agent_service.py`, `agent_event_bus.py`, `ai_chat.py` routes, `app/main.py`, and `app/models/schemas/ai.py`. See archive.

### [TD-087] Parameter Sprawl in Graph Creation Methods

- **Source:** Code review `/simplify` pass on `backend/app/ai/agent_service.py`
- **Description:** `_create_deep_agent_graph` takes 12 parameters and `_run_agent_graph` takes 13. Many are optional with complex interdependencies (e.g., `websocket` is only needed when `interrupt_node` is used). The parameter lists make callers hard to read and error-prone to extend.
- **Impact:** Adding new graph configuration (e.g., supervisor mode toggles, new middleware) requires modifying long parameter lists in multiple methods.
- **Estimated Effort:** 1 day
- **Status:** Open
- **Owner:** Backend Developer
- **Suggested Approach:** Group parameters into TypedDicts/dataclasses: `GraphCreationConfig` (llm, tool_context, assistant_config), `GraphExecutionParams` (message, session_id, user_id, project_id, temporal params), `StreamConfig` (event_bus, execution_mode).

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

### [TD-104] Currency Hardcoded to EUR

- **Source:** 2026-05-14 E2E test `20260514_0007-ai-cost-progress` and `20260513_2113-ai-chat-van-project`
- **Description:** All monetary amounts in the frontend are displayed in EUR regardless of project or user input. Currency formatting is hardcoded in: `CostHistoryChart.tsx` (`createCurrencyFormatter("EUR")`), `ForecastHistoryView.tsx` (hardcoded `€` symbols), `GanttChartOptions.ts` (`Intl.NumberFormat("en-US", { currency: "EUR" })`), `ProjectList.columns.tsx` (`currency: "EUR"`). When a user enters "$45,000", the system displays "€45.0K".
- **Impact:** LOW — No multi-currency support. Not a regression — has been this way since initial implementation.
- **Estimated Effort:** 1 day
- **Status:** Open
- **Owner:** Full Stack Developer
- **Priority:** P3 (Low)
- **Blocker:** No
- **Suggested Approach:** Add `currency` field to project settings (default "EUR"). Create shared `useCurrencyFormatter(projectId)` hook. Replace all hardcoded `€` and `"EUR"` references with the dynamic formatter. AI tools should read and pass the project's currency when registering costs.

---

### [TD-105] ~~Pre-existing MyPy Type-Var Errors in change_order_service.py~~

- **Status:** ✅ Resolved (2026-05-19) — MyPy passes clean on `change_order_service.py`. Errors were likely fixed incidentally during a prior iteration. See archive.

---

### [TD-106] ~~Import-Sorting Errors in Test Files (167 I001 Ruff Errors)~~

- **Status:** ✅ Resolved (2026-05-16) — Fixed with `ruff check --fix tests/` in ACT phase.

### [TD-107] ~~Dashboard Widgets Ignore Temporal Context~~

- **Status:** ✅ Resolved (2026-05-19) — Added `useTimeMachineParams()` to `useDashboardData` hook, updated query key to include temporal params, added `branch` and `as_of` params to backend endpoint and service. See archive.

---

---

## Summary

| Priority | Count | Total Effort |
|----------|-------|--------------|
| High (P0-P1) | 4 | ~10.5 days |
| Medium (P2-P3) | 7 | ~7 days |
| Low (P4+) | 2 | 5 hours |
| **Total** | **13** | **~15.5 days** |

---

## Links

- [Technical Debt Archive](./technical-debt-archive.md) - Completed debt items (35 items)
- [Sprint Backlog](./sprint-backlog.md) - Current iteration
- [Product Backlog](./product-backlog.md) - All pending work
