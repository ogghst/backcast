# Plan: AI Chat Reliability Fixes (RBAC Cache + Tab Rendering)

**Created:** 2026-05-14
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 2 -- On-Demand Synchronous Cache Refresh

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 2 from analysis -- On-Demand Synchronous Cache Refresh for RBAC; browser-level investigation for tab rendering
- **Architecture**: Convert `filter_tools_by_role()` to async; on cache miss, `await refresh_permissions_cache()` before filtering. For the frontend, investigate the `PageNavigation` tab click-to-route interaction and fix or validate it.
- **Key Decisions**:
  1. Accept sync-to-async propagation of `filter_tools_by_role()` as the necessary trade-off for guaranteed fresh permissions
  2. Browser-level investigation for P1 before writing code -- may be an E2E test interaction artifact rather than a code bug
  3. P2 (temporal propagation to global chat) deferred to TD-068 -- project-scoped chat fix (P1) is the correct path
  4. P3 (configurable currency) deferred to TD-069

### Success Criteria

**Functional Criteria:**

- [ ] **FC-1**: When `_get_cached_permissions()` returns `None` (cache miss or TTL expiry), `filter_tools_by_role()` refreshes the cache from the database and returns the correct filtered tool list (not an empty list). VERIFIED BY: unit test with mocked cache miss
- [ ] **FC-2**: After cache refresh, all permission-gated tools that the role should have access to are present in the filtered result. VERIFIED BY: unit test asserting tool count matches expected for each role
- [ ] **FC-3**: When the cache is already warm (not expired), `filter_tools_by_role()` does NOT trigger a database query. VERIFIED BY: unit test asserting no refresh call
- [ ] **FC-4**: Clicking "AI Chat" tab in a project page navigates to `/projects/:projectId/chat` and renders `ChatInterface` content. VERIFIED BY: browser-level manual verification or E2E test
- [ ] **FC-5**: All existing callers of `filter_tools_by_role()` continue to work after the async conversion. VERIFIED BY: existing integration tests pass without modification to assertions

**Technical Criteria:**

- [ ] **TC-1**: MyPy strict mode passes with zero errors on all modified files. VERIFIED BY: `uv run mypy app/`
- [ ] **TC-2**: Ruff passes with zero errors on all modified files. VERIFIED BY: `uv run ruff check .`
- [ ] **TC-3**: All existing tests in `backend/tests/unit/ai/tools/test_role_filtering.py` pass after the async conversion. VERIFIED BY: `uv run pytest tests/unit/ai/tools/test_role_filtering.py`
- [ ] **TC-4**: All existing tests in `backend/tests/security/ai/test_tool_rbac.py` pass after the async conversion. VERIFIED BY: `uv run pytest tests/security/ai/test_tool_rbac.py`
- [ ] **TC-5**: No new database tables or migrations introduced. VERIFIED BY: no new Alembic revision files
- [ ] **TC-6**: ERROR-level log emitted when cache miss is detected and refresh is triggered. VERIFIED BY: unit test asserting log output
- [ ] **TC-7**: Frontend linting and TypeScript checks pass. VERIFIED BY: `npm run lint && npm run typecheck`

**TDD Criteria:**

- [ ] **TDD-1**: New test for cache-miss-then-refresh scenario written before implementation
- [ ] **TDD-2**: New test for cache-warm-no-refresh scenario written before implementation
- [ ] **TDD-3**: New test for refresh-failure-logging scenario written before implementation
- [ ] **TDD-4**: Test coverage for modified functions >= 80%

### Scope Boundaries

**In Scope:**

- RBAC cache refresh on demand within `filter_tools_by_role()`
- Async propagation to `filter_tools_for_context()`, callers in `supervisor_orchestrator.py`, `deep_agent_orchestrator.py`, `agent_service.py`
- Unit and integration test updates for async signature changes
- Browser investigation and fix (if needed) for project AI Chat tab rendering
- ERROR-level logging on cache miss detection

**Out of Scope:**

- P2: Temporal propagation to global chat (deferred to TD-068)
- P3: Configurable currency (deferred to TD-069)
- Changes to the cache TTL value or cache invalidation strategy
- Changes to `PageNavigation` component architecture (route-based navigation is correct)
- New database migrations or schema changes

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|------------------|------------|
| 1 | Write tests for async `filter_tools_by_role` cache-miss refresh | `backend/tests/unit/ai/tools/test_role_filtering.py` | None | T-001, T-002, T-003 pass (RED first) | Low |
| 2 | Convert `filter_tools_by_role()` to async with on-demand cache refresh | `backend/app/ai/tools/__init__.py` | Task 1 | FC-1, FC-2, FC-3, TC-6; T-001, T-002, T-003 pass (GREEN) | Med |
| 3 | Propagate async to `filter_tools_for_context()` and its callers | `backend/app/ai/subagent_compiler.py`, `backend/app/ai/agent_service.py`, `backend/app/ai/supervisor_orchestrator.py`, `backend/app/ai/deep_agent_orchestrator.py` | Task 2 | FC-5; TC-1, TC-2, TC-3, TC-4 pass | Med |
| 4 | Update existing tests for async `filter_tools_by_role` signature | `backend/tests/unit/ai/tools/test_role_filtering.py`, `backend/tests/security/ai/test_tool_rbac.py` | Task 3 | All existing tests pass; TC-3, TC-4 | Low |
| 5 | Investigate project AI Chat tab rendering in browser | `frontend/src/components/navigation/PageNavigation.tsx`, `frontend/src/pages/projects/ProjectChat.tsx`, `frontend/src/routes/index.tsx` | None | FC-4 verified or root cause identified | Low |
| 6 | Fix project AI Chat tab rendering (if bug confirmed) | TBD based on Task 5 findings | Task 5 | FC-4 passes in browser | Low-Med |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---|---|---|---|
| FC-1: Cache miss triggers refresh and returns correct tools | T-001 | `tests/unit/ai/tools/test_role_filtering.py` | `filter_tools_by_role()` called with expired cache calls `refresh_permissions_cache()`, then returns tools matching the role's actual permissions |
| FC-2: All permitted tools present after refresh | T-002 | `tests/unit/ai/tools/test_role_filtering.py` | For ai-admin role, all permission-gated tools are included in filtered result after cache refresh |
| FC-3: No refresh when cache is warm | T-003 | `tests/unit/ai/tools/test_role_filtering.py` | `refresh_permissions_cache()` is NOT called when `_get_cached_permissions()` returns valid data |
| FC-5: Callers still work after async conversion | T-004 | `tests/security/ai/test_tool_rbac.py` | Existing integration tests pass without assertion changes |
| TC-6: Error log on cache miss | T-005 | `tests/unit/ai/tools/test_role_filtering.py` | `caplog` captures ERROR-level message when cache miss triggers refresh |

---

## Test Specification

### Test Hierarchy

```text
├── Unit Tests (tests/unit/ai/tools/)
│   ├── test_role_filtering.py
│   │   ├── T-001: test_filter_tools_by_role_cache_miss_triggers_refresh
│   │   ├── T-002: test_filter_tools_by_role_cache_miss_returns_all_permitted_tools
│   │   ├── T-003: test_filter_tools_by_role_cache_warm_no_refresh
│   │   └── T-005: test_filter_tools_by_role_cache_miss_logs_error
│   └── (existing tests updated for async)
├── Integration Tests (tests/security/ai/)
│   └── test_tool_rbac.py
│       └── T-004: existing tests pass with async filter
└── Browser Investigation (manual / E2E)
    └── FC-4: project AI Chat tab renders content
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Verification |
|---|---|---|---|---|
| T-001 | `test_filter_tools_by_role_cache_miss_triggers_refresh` | FC-1 | Unit | Mock `_get_cached_permissions` to return `None`; assert `refresh_permissions_cache` awaited once; assert non-empty tool list returned |
| T-002 | `test_filter_tools_by_role_cache_miss_returns_all_permitted_tools` | FC-2 | Unit | Set up ai-admin permissions in mock refresh result; assert all permission-gated tools for ai-admin are in filtered list |
| T-003 | `test_filter_tools_by_role_cache_warm_no_refresh` | FC-3 | Unit | Mock `_get_cached_permissions` to return valid permissions; assert `refresh_permissions_cache` NOT called; assert filtering still works |
| T-004 | (existing integration tests) | FC-5 | Integration | `test_filter_tools_by_role_combined_with_execution_mode` and role-specific tests pass with async signature |
| T-005 | `test_filter_tools_by_role_cache_miss_logs_error` | TC-6 | Unit | Mock cache miss; assert `caplog` contains ERROR-level log with "cache miss" or "expired" message |

### Test Infrastructure Needs

- **Fixtures needed**: Existing `mock_rbac_service` fixture; add `mock_expired_cache` fixture that sets up `_get_cached_permissions` to return `None` for a given role
- **Mocks/stubs**: `UnifiedRBACService.refresh_permissions_cache` (AsyncMock), `UnifiedRBACService._get_cached_permissions` (Mock returning None or list)
- **Database state**: No specific seed data -- unit tests mock the cache layer entirely; integration tests use existing RBAC seed data

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|---|---|---|---|---|
| Technical | Async propagation misses a caller, causing runtime `TypeError: object list can't be used in 'await' expression` | Medium | High | Comprehensive grep for all callers (already done: 5 call sites identified); run existing test suite after changes |
| Technical | `refresh_permissions_cache()` fails during on-demand call (DB unavailable) | Low | High | After refresh failure, log ERROR and return empty tool list (same as current behavior, but now with visibility); the startup cache still provides initial warm state |
| Integration | `agent_service.py` call site at line 711/717 is in a synchronous context that cannot await | Low | Medium | Verify `agent_service.py` method is already async (`async def`); if not, trace upward to the entry point |
| Frontend | P1 tab rendering is not a code bug but an E2E test Playwright interaction issue | Medium | Low | Browser investigation (Task 5) will determine if code changes are needed; if not, update E2E test approach instead |
| Regression | Existing tests fail due to async signature change | Medium | Medium | Task 4 explicitly handles test updates; run full AI-related test suite before merging |

---

## Prerequisites

### Technical

- [x] Database migrations applied (no new migrations needed)
- [x] Dependencies installed (no new dependencies)
- [x] Environment configured (dev environment operational)

### Documentation

- [x] Analysis phase approved (Option 2 selected)
- [x] Architecture docs reviewed (RBAC singleton, ContextVar session pattern, tool filtering pipeline)

---

## Documentation References

### Required Reading

- RBAC service: `backend/app/core/rbac_unified.py` (lines 54-141 for cache methods, lines 99-128 for `refresh_permissions_cache`)
- Tool filtering: `backend/app/ai/tools/__init__.py` (lines 69-113)
- Subagent compiler: `backend/app/ai/subagent_compiler.py` (lines 48-77 for `filter_tools_for_context`, lines 100-183 for `compile_subagents`)
- Agent service callers: `backend/app/ai/agent_service.py` (lines 711-718)
- PageNavigation: `frontend/src/components/navigation/PageNavigation.tsx`
- Project routes: `frontend/src/routes/index.tsx` (lines 134-178)

### Code References

- ContextVar session injection pattern: `backend/app/core/rbac_unified.py` (lines 34-46)
- Existing role filtering tests: `backend/tests/unit/ai/tools/test_role_filtering.py`
- Existing RBAC integration tests: `backend/tests/security/ai/test_tool_rbac.py`
- Similar async pattern in codebase: `refresh_permissions_cache()` already uses `get_unified_rbac_session()` ContextVar

---

# Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  # ── Backend: P0 RBAC Cache Fix ──
  - id: BE-001
    name: "Write tests for async filter_tools_by_role cache-miss refresh (T-001, T-002, T-003, T-005)"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Convert filter_tools_by_role() to async with on-demand cache refresh"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Propagate async to filter_tools_for_context() and all callers (subagent_compiler, agent_service, supervisor_orchestrator, deep_agent_orchestrator)"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-004
    name: "Update existing tests for async filter_tools_by_role signature"
    agent: pdca-backend-do-executor
    dependencies: [BE-003]

  # ── Frontend: P1 Tab Rendering Investigation ──
  - id: FE-001
    name: "Investigate project AI Chat tab rendering in browser (determine if code bug or E2E test issue)"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-002
    name: "Fix project AI Chat tab rendering (if browser investigation confirms a code bug)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  # ── Integration Verification ──
  - id: VERIFY-001
    name: "Run full AI-related test suite and quality checks to verify no regressions"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]
    kind: test
```
