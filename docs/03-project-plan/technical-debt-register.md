# Technical Debt Register

**Last Updated:** 2026-05-14
**Total Open Items:** 21
**Total Estimated Effort:** ~21 days

---

This file tracks active technical debt items. For completed/closed debt, see [technical-debt-archive.md](./technical-debt-archive.md).

---

## High Severity (P0 - P1)

### [TD-099] Test DB Fixture Uses create_all() Instead of Alembic Migrations

- **Source:** 2026-05-10-rbac-seeding-fix CHECK phase -- Root cause analysis of 13 pre-existing test_seeder.py failures
- **Description:** The test database session fixture in `tests/conftest.py` uses SQLAlchemy `create_all()` (model metadata) instead of running the full Alembic migration chain. After the `user_role_assignments` table was added in the unified RBAC iteration (migration `20260510_add_user_role_assignments_table.py`), the FK constraint `FOREIGN KEY(granted_by) REFERENCES users(user_id)` fails because `create_all()` does not replicate the unique constraint on `users.user_id` that was added in an earlier migration (`42751fa7cef1`). This causes 13 existing seeder tests to ERROR with `asyncpg.exceptions.InvalidForeignKeyError`.
- **Impact:** HIGH -- 13 tests in `test_seeder.py` ERROR at setup. Any future migration adding cross-table FK relationships will cause similar failures. Test DB schema does not match production schema.
- **Estimated Effort:** 1 day
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P1 (High)
- **Blocker:** No
- **Suggested Approach:** Replace `create_all()` in the test session fixture with `alembic.command.upgrade(config, "head")` to run the full migration chain against the test database. Alternatively, add the missing unique constraint explicitly in the test fixture. Verify by running the full test_seeder.py suite. Consider creating a dedicated CI step that validates all Alembic migrations against a fresh database.

---

### [TD-095] Migration Verification Tests for Unified RBAC

- **Source:** 2026-05-10-unified-rbac-refactoring CHECK phase (BE-020)
- **Description:** The data migration `20260510b_migrate_existing_roles_to_unified_rbac.py` copies User.role and ProjectMember data into the unified `user_role_assignments` table. This migration has no automated verification tests. The SQL looks correct but is untested. The downgrade logic is imprecise -- deletes by pattern rather than migration tracking, which could delete manually-created assignments.
- **Impact:** HIGH -- Data integrity risk during production migration. Could lose role assignments or create duplicates without detection.
- **Estimated Effort:** 4 hours
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P1 (High)
- **Blocker:** No (but should be completed before next production deployment)
- **Suggested Approach:** Create `tests/integration/test_rbac_migration.py` with tests for: up migration with existing User.role data, up migration with ProjectMember data, idempotency (run twice), down migration cleanup, edge cases (NULL roles, missing users). Consider adding migration_id column for precise downgrade tracking.

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

### [TD-097] Performance Benchmarks for Unified RBAC

- **Source:** 2026-05-10-unified-rbac-refactoring CHECK phase (BE-024)
- **Description:** The unified RBAC uses a two-tier cache (1h permissions, 5min assignments) designed for <5ms cached permission checks. No performance benchmarks exist to verify this target. The cache-first design should achieve this, but it is unverified.
- **Impact:** LOW -- Cache design is sound, but target is unverified.
- **Estimated Effort:** 4 hours
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P3 (Low)
- **Blocker:** No
- **Suggested Approach:** Create `tests/perf/bench_rbac_unified.py` with benchmarks for: cached permission check latency, cache miss latency, bulk assignment loading, cache invalidation performance. Target: cached check <5ms, cold check <50ms.

---

### [TD-098] Delete Deprecated RBAC Files After Validation

- **Source:** 2026-05-10-unified-rbac-refactoring CHECK phase (BE-027), updated 2026-05-11 unified RBAC cutover
- **Description:** The unified RBAC cutover is complete. All active app code now uses `UnifiedRBACService` exclusively. Legacy RBAC files (`rbac.py`, `rbac_database.py`) have deprecation notices but still exist. `RoleChecker`/`ProjectRoleChecker` no longer have fallback logic. The `RBAC_PROVIDER` config defaults to `"database"`. These legacy files can be fully removed after production validation.
- **Impact:** LOW -- Legacy files are dead code with deprecation notices. No user-facing impact.
- **Estimated Effort:** 2 hours
- **Status:** Deferred (waiting for production validation)
- **Owner:** Backend Developer
- **Priority:** P3 (Low)
- **Blocker:** Requires 1-2 weeks production validation with zero issues
- **Suggested Approach:** After production validation: (1) Delete `app/core/rbac.py`, `app/core/rbac_database.py`, (2) Delete `app/api/routes/project_members.py`, `app/services/project_member.py`, (3) Remove `RBAC_PROVIDER` config setting, (4) Remove `project_members` model/schema files, (5) Run full test suite to verify no regressions.

---

### [TD-092] Frontend TypeScript Errors (Pre-existing)

- **Source:** 2026-05-10-co-critical-fixes CHECK phase report
- **Description:** 26 TypeScript errors exist in frontend codebase, unrelated to iteration changes. Errors include: mock data incomplete (missing `level`, `valid_time_formatted` fields), test setup type mismatches, component prop type mismatches. These errors existed before the iteration and were documented during CHECK phase verification.
- **Impact:** Reduces type safety confidence, may cause runtime issues, blocks full TypeScript strict mode adoption
- **Estimated Effort:** 4 hours
- **Status:** Open
- **Owner:** Frontend Developer
- **Priority:** P2 (Medium)
- **Blocker:** No
- **Suggested Approach:** Fix mock data first (easiest wins), then address component prop types, finally tackle test setup issues. Add baseline tracking to CI to distinguish new errors from pre-existing.

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

### [TD-086] Stringly-Typed Event Types and Tool Names

- **Source:** Code review `/simplify` pass on `backend/app/ai/agent_service.py`
- **Description:** Event types (`"thinking"`, `"tool_call"`, `"subagent"`, `"complete"`, etc.), tool names (`"task"`, `"write_todos"`), and execution statuses (`"running"`, `"completed"`, `"error"`) are raw strings scattered across `_run_agent_graph`. These are also referenced by the frontend, so changes must be coordinated. Hardcoded strings risk typos and make refactoring error-prone.
- **Impact:** No compile-time safety; renaming an event type requires finding all string literals across backend and frontend.
- **Estimated Effort:** 1 day
- **Status:** Open
- **Owner:** Backend Developer
- **Suggested Approach:** Create `AgentEventType` and `ExecutionStatus` enums in backend. Export as constants that frontend can import via shared types or OpenAPI spec.

### [TD-087] Parameter Sprawl in Graph Creation Methods

- **Source:** Code review `/simplify` pass on `backend/app/ai/agent_service.py`
- **Description:** `_create_deep_agent_graph` takes 12 parameters and `_run_agent_graph` takes 13. Many are optional with complex interdependencies (e.g., `websocket` is only needed when `interrupt_node` is used). The parameter lists make callers hard to read and error-prone to extend.
- **Impact:** Adding new graph configuration (e.g., supervisor mode toggles, new middleware) requires modifying long parameter lists in multiple methods.
- **Estimated Effort:** 1 day
- **Status:** Open
- **Owner:** Backend Developer
- **Suggested Approach:** Group parameters into TypedDicts/dataclasses: `GraphCreationConfig` (llm, tool_context, assistant_config), `GraphExecutionParams` (message, session_id, user_id, project_id, temporal params), `StreamConfig` (event_bus, execution_mode).

---

### [TD-100] Role Dropdown Shows All Roles in Project Context

- **Source:** 2026-05-11 unified RBAC cutover CHECK phase (E2E Finding #2)
- **Description:** The "Select Role" dropdown in the Add Project Member modal shows all 11 RBAC roles including `ai-admin`, `ai-manager`, `ai-viewer`, `change_order_approver`. Only the 4 project-scoped roles (`project_admin`, `project_manager`, `project_editor`, `project_viewer`) are meaningful at project scope.
- **Impact:** LOW -- Cosmetic/UX issue, no security impact. Users could accidentally assign an AI-specific role at project scope.
- **Estimated Effort:** 2 hours
- **Status:** Open
- **Owner:** Frontend Developer
- **Priority:** P3 (Low)
- **Blocker:** No
- **Suggested Approach:** Filter the role dropdown by roles that have project-applicable permissions. The `rbac_roles` table has `is_system=True` for all roles — add a `scope_applicability` column (e.g., `['global', 'project']`) or create a frontend-side filter list. Alternatively, the role-assignments API could expose a `/roles?scope=project` endpoint.

---

### [TD-101] Admin Role Assignments Page Shows "—" for User Name

- **Source:** 2026-05-11 unified RBAC cutover CHECK phase (E2E Finding #3)
- **Description:** The admin Role Assignments page (`/admin/role-assignments`) shows "—" in the User Name column. The `GET /api/v1/role-assignments/` list endpoint returns `user_id` but doesn't enrich with user info (email, full_name). The frontend would need to join or batch-fetch user details.
- **Impact:** LOW -- UX issue. Admins can't identify who an assignment belongs to without cross-referencing user IDs.
- **Estimated Effort:** 3 hours
- **Status:** Open
- **Owner:** Full Stack Developer
- **Priority:** P3 (Low)
- **Blocker:** No
- **Suggested Approach:** Either: (A) Enrich the list endpoint response with user details via a JOIN on the `users` table (add `user_email` and `user_name` fields to `UserRoleAssignmentRead`), or (B) Have the frontend batch-fetch user details via a separate endpoint. Option A is simpler and avoids N+1.

---

### [TD-102] Dual-Source RBAC Config (JSON vs DB) Without Sync Validation

- **Source:** 2026-05-11 unified RBAC cutover CHECK phase
- **Description:** The system has two sources of RBAC role/permission definitions: `config/rbac.json` (used by `JsonRBACService` for legacy tests) and `seed/rbac_roles.json` + `rbac_roles` table (used by `UnifiedRBACService`). During the cutover, `change-order-approve` was accidentally removed from the `viewer` role in `rbac.json`, causing a test regression. There is no validation that the two sources stay in sync.
- **Impact:** MEDIUM -- Config drift between JSON and DB causes confusing test failures. The `RBAC_PROVIDER` now defaults to `"database"` but some tests still use `JsonRBACService` via `rbac.json`.
- **Estimated Effort:** 1 day
- **Status:** Open
- **Owner:** Backend Developer
- **Priority:** P2 (Medium)
- **Blocker:** No
- **Suggested Approach:** Short-term: Add a CI test that validates `config/rbac.json` permissions are a subset of `seed/rbac_roles.json` permissions for each role. Long-term: Remove `JsonRBACService` and `rbac.json` entirely, making the DB the single source of truth for both runtime and tests. Update `test_rbac.py` to test against the database seed data instead of JSON config.

---

### [TD-103] Temporal Context Not Propagated to Global AI Chat

- **Source:** 2026-05-14 E2E test `20260514_0007-ai-cost-progress`
- **Description:** The Time Machine temporal date is not available when using the global `/chat` route. When a user sets the Time Machine to a specific date on the project page and navigates to global chat, the AI agent's `get_temporal_context` returns today's date instead. All tool calls show `as_of=None`. The Time Machine store is project-scoped — `getSelectedTime()` returns `null` when `currentProjectId` is null (global routes).
- **Impact:** MEDIUM — Users cannot perform temporal AI operations (register costs at specific dates, view historical state) from global chat. Workaround exists: use project-scoped chat tab (when rendering correctly).
- **Estimated Effort:** 3 hours
- **Status:** Open
- **Owner:** Full Stack Developer
- **Priority:** P2 (Medium)
- **Blocker:** May become moot if project-scoped chat tab rendering is fixed
- **Suggested Approach:** Primary fix is ensuring project-scoped `/projects/:id/chat` renders correctly. If that's insufficient, allow global chat to accept a `project_id` query parameter that sets Time Machine context for that session. Affected files: `useTimeMachineStore.ts`, `useStreamingChat.ts`, `ProjectChat.tsx`.

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

## Summary

| Priority | Count | Total Effort |
|----------|-------|--------------|
| High (P0-P1) | 8 | ~13 days |
| Medium (P2-P3) | 13 | ~8 days |
| Low (P4+) | 0 | 0 hours |
| **Total** | **21** | **~21 days** |

---

## Links

- [Technical Debt Archive](./technical-debt-archive.md) - Completed debt items (35 items)
- [Sprint Backlog](./sprint-backlog.md) - Current iteration
- [Product Backlog](./product-backlog.md) - All pending work
