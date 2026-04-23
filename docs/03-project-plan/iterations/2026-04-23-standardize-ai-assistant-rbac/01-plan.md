# Plan: Standardize AI Assistant RBAC

**Created:** 2026-04-23
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 (Remove Redundancy + Fix Session Injection + AI-Specific Roles)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 from analysis, augmented with AI-specific RBAC roles
- **Architecture**: Contextvar-based session injection, single permission check in middleware, three new AI roles in `rbac.json`, tool filtering by assistant role
- **Key Decisions**:
  1. Add `ai-viewer`, `ai-manager`, `ai-admin` roles to `rbac.json` matching existing assistant profiles
  2. Standard roles sufficient; finer granularity deferred
  3. Full permission check: both user role AND assistant role must permit the tool
  4. Simple dropdown (existing `AssistantSelector`) - no UI redesign
  5. Show only tools available to the selected assistant's role

### Success Criteria

**Functional Criteria:**

- [ ] AI tool permission is checked exactly once (middleware only) VERIFIED BY: unit test
- [ ] `ai-viewer` role has read-only permissions matching "Friendly Project Analyzer" assistant VERIFIED BY: RBAC unit test
- [ ] `ai-manager` role has CRUD permissions matching "Senior Project Manager" assistant VERIFIED BY: RBAC unit test
- [ ] `ai-admin` role has admin permissions matching "System Manager" assistant VERIFIED BY: RBAC unit test
- [ ] Each AI assistant only receives tools its role permits VERIFIED BY: integration test
- [ ] Session injection uses contextvars, no singleton mutation VERIFIED BY: concurrent test
- [ ] Existing API endpoint RBAC continues working unchanged VERIFIED BY: existing tests pass

**Technical Criteria:**

- [ ] Performance: Permission checks add < 1ms latency VERIFIED BY: timing benchmark
- [ ] Thread-safety: Concurrent WebSocket sessions do not corrupt each other's session VERIFIED BY: concurrency test
- [ ] Code Quality: mypy strict + ruff clean VERIFIED BY: CI pipeline
- [ ] Net code reduction: Fewer lines after removing redundant check VERIFIED BY: line count

**TDD Criteria:**

- [ ] All tests written before implementation code
- [ ] Each test failed first (documented in DO phase log)
- [ ] Test coverage >= 80% on changed files
- [ ] Tests follow Arrange-Act-Assert pattern

### Scope Boundaries

**In Scope:**

- Add three new AI roles to `rbac.json`
- Add `default_role` field to `AIAssistantConfig` model + migration
- Update seed data with `default_role` mapping
- Remove redundant permission check from `@ai_tool` decorator
- Add contextvar-based session injection to `rbac.py`
- Update `ProjectRoleChecker` and middleware to use contextvars
- Filter tools by assistant role when creating agent
- Update `AssistantSelector` to show only tools available for selected assistant's role
- Unit and integration tests for all changes

**Out of Scope:**

- UI redesign of assistant selector (existing simple dropdown is sufficient)
- Per-tool permission override per assistant (use role-based approach)
- Fine-grained permission editing UI
- New AI assistant profiles beyond the three existing ones
- Removing or restructuring existing RBAC service architecture

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|-----------------|------------|
| 1 | Add AI roles to `rbac.json` | `backend/config/rbac.json` | none | All three AI roles have correct permissions matching assistant tool lists | Low |
| 2 | Add `default_role` to `AIAssistantConfig` model + migration | `backend/app/models/domain/ai.py`, `backend/alembic/versions/` | none | Model has nullable `default_role` string field | Med |
| 3 | Update seed data with role mapping | `backend/seed/ai_assistant_configs.json`, `backend/app/db/seeder.py` | 1, 2 | Each assistant config has correct `default_role` value | Low |
| 4 | Remove redundant permission check from `@ai_tool` decorator | `backend/app/ai/tools/decorator.py` | none | Lines 150-161 removed, middleware-only enforcement | Low |
| 5 | Add contextvar session injection to `rbac.py` | `backend/app/core/rbac.py` | none | `_rbac_session` ContextVar, `get/set_rbac_session()` helpers, fallback in `has_project_access()`, `get_user_projects()`, `get_project_role()` | Med |
| 6 | Update `ProjectRoleChecker` to use contextvar | `backend/app/api/dependencies/auth.py` | 5 | Uses `set_rbac_session()` instead of mutating singleton | Low |
| 7 | Update middleware to use contextvar | `backend/app/ai/middleware/backcast_security.py` | 5 | Uses `set_rbac_session()`, removes try/finally session swap | Low |
| 8 | Filter tools by assistant role in agent creation | `backend/app/ai/deep_agent_orchestrator.py`, `backend/app/ai/tools/__init__.py` | 1, 2 | Agent only receives tools the assistant's role permits | Med |
| 9 | Update `AssistantSelector` to show available tool count | `frontend/src/features/ai/chat/components/AssistantSelector.tsx` | 8 | Shows tool count or availability indicator per assistant | Low |
| 10 | Write unit tests for AI roles | `backend/tests/unit/core/test_rbac.py` | 1 | Each AI role has correct permission set | Low |
| 11 | Write unit tests for contextvar session injection | `backend/tests/unit/core/test_rbac.py` | 5 | Concurrent sessions don't corrupt each other | Med |
| 12 | Write integration tests for tool filtering | `backend/tests/security/ai/test_tool_rbac.py` | 8 | Each assistant only gets permitted tools | Med |
| 13 | Verify existing tests pass | All existing test suites | all | Zero regressions | Low |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---|---|---|---|
| AI roles have correct permissions | T-001 | `tests/unit/core/test_rbac.py` | `has_permission("ai-viewer", "project-read")` returns True; `has_permission("ai-viewer", "project-create")` returns False |
| ai-manager has CRUD permissions | T-002 | `tests/unit/core/test_rbac.py` | `has_permission("ai-manager", "cost-element-create")` returns True |
| ai-admin has admin permissions | T-003 | `tests/unit/core/test_rbac.py` | `has_permission("ai-admin", "user-delete")` returns True |
| Contextvar session isolation | T-004 | `tests/unit/core/test_rbac.py` | Two concurrent async tasks setting different sessions don't interfere |
| Middleware single check | T-005 | `tests/security/ai/test_tool_rbac.py` | Decorator does NOT check permissions; middleware does |
| Tool filtering by role | T-006 | `tests/security/ai/test_tool_rbac.py` | Agent with `ai-viewer` role gets no create/update/delete tools |
| Existing API RBAC unchanged | T-007 | `tests/api/` (existing) | All existing API auth tests pass unchanged |

---

## Test Specification

### Test Hierarchy

```
tests/
├── unit/
│   └── core/
│       └── test_rbac.py
│           ├── test_ai_viewer_permissions
│           ├── test_ai_manager_permissions
│           ├── test_ai_admin_permissions
│           ├── test_contextvar_session_isolation
│           └── test_contextvar_fallback_in_has_project_access
├── security/
│   └── ai/
│       └── test_tool_rbac.py
│           ├── test_decorator_no_permission_check
│           ├── test_middleware_single_permission_check
│           ├── test_tool_filtering_by_assistant_role
│           └── test_middleware_uses_contextvar_session
└── api/
    └── (existing tests - must pass unchanged)
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Expected Result |
|---|---|---|---|---|
| T-001 | `test_ai_viewer_has_read_permissions` | AC-2 | Unit | ai-viewer has all read permissions from its tool list |
| T-002 | `test_ai_viewer_lacks_write_permissions` | AC-2 | Unit | ai-viewer cannot create/update/delete any entity |
| T-003 | `test_ai_manager_has_crud_permissions` | AC-3 | Unit | ai-manager can create/update entities per its tool list |
| T-004 | `test_ai_admin_has_admin_permissions` | AC-4 | Unit | ai-admin can manage users, departments, cost-element-types |
| T-005 | `test_contextvar_session_isolation` | AC-6 | Unit | Two concurrent tasks with different sessions don't interfere |
| T-006 | `test_contextvar_fallback_in_has_project_access` | AC-6 | Unit | `has_project_access` uses contextvar when `self.session` is None |
| T-007 | `test_decorator_skips_permission_check` | AC-1 | Unit | `@ai_tool` wrapper does NOT call `rbac_service.has_permission` |
| T-008 | `test_middleware_checks_permissions_once` | AC-1 | Unit | Middleware `_check_tool_permission` is the sole check point |
| T-009 | `test_tool_filtering_ai_viewer` | AC-5 | Integration | ai-viewer agent receives only read tools |
| T-010 | `test_tool_filtering_ai_manager` | AC-5 | Integration | ai-manager agent receives read + write tools |
| T-011 | `test_existing_api_rbac_unchanged` | AC-7 | Integration | Existing API auth tests pass unchanged |

### Test Infrastructure Needs

- **Fixtures**: `rbac_service` fixture (existing), `async_session` fixture (existing)
- **New fixtures**: `ai_assistant_config` fixture with `default_role` field
- **Mocks**: None needed - RBAC is JSON-based, no external services
- **Database state**: Seed `rbac.json` with new AI roles for integration tests

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|---|---|---|---|---|
| Technical | Removing decorator check breaks AI tools if middleware fails | Low | High | Write test that verifies middleware is sole check BEFORE removing decorator code |
| Technical | Contextvar not properly set in all code paths | Low | High | Add fallback to `self.session` in all `JsonRBACService` methods |
| Integration | AI roles don't exactly match tool permissions | Med | Med | Derive permissions programmatically from tool metadata, verify in tests |
| Migration | Adding `default_role` column requires migration | Low | Low | Nullable column with no default, backward compatible |
| Frontend | AssistantSelector changes break existing UI | Low | Low | Minor change, only adding info display, no structural change |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Add AI roles to rbac.json"
    agent: pdca-backend-do-executor
    dependencies: []
    group: rbac-core

  - id: BE-002
    name: "Add default_role field to AIAssistantConfig model + migration"
    agent: pdca-backend-do-executor
    dependencies: []
    group: rbac-core

  - id: BE-003
    name: "Remove redundant permission check from @ai_tool decorator"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]
    group: rbac-core

  - id: BE-004
    name: "Add contextvar session injection to rbac.py"
    agent: pdca-backend-do-executor
    dependencies: []
    group: rbac-core

  - id: BE-005
    name: "Update ProjectRoleChecker and middleware to use contextvar"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]
    group: rbac-core

  - id: BE-006
    name: "Update seed data with default_role mapping"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002]
    group: rbac-core

  - id: BE-007
    name: "Filter tools by assistant role in agent creation"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002]
    group: rbac-core

  - id: FE-001
    name: "Update AssistantSelector to show tool availability"
    agent: pdca-frontend-do-executor
    dependencies: [BE-007]
    group: frontend

  - id: TEST-001
    name: "Write unit tests for AI roles, contextvar, and decorator removal"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-004, BE-003]
    kind: test
    group: tests

  - id: TEST-002
    name: "Write integration tests for tool filtering and middleware"
    agent: pdca-backend-do-executor
    dependencies: [BE-005, BE-007, TEST-001]
    kind: test
    group: tests

  - id: VERIFY-001
    name: "Run full test suite to verify no regressions"
    agent: pdca-backend-do-executor
    dependencies: [TEST-002]
    kind: test
    group: tests
```

### Execution Levels

```
Level 0 (parallel): BE-001, BE-002, BE-004
Level 1 (parallel): BE-003 (after BE-004), BE-005 (after BE-004), BE-006 (after BE-001+BE-002), BE-007 (after BE-001+BE-002)
Level 2: TEST-001 (after BE-001, BE-003, BE-004)
Level 3: TEST-002 (after BE-005, BE-007, TEST-001)
Level 4: FE-001 (after BE-007), VERIFY-001 (after TEST-002)
```

---

## Prerequisites

### Technical

- [x] Database migrations can be created (Alembic configured)
- [x] `rbac.json` is the single source of truth for role permissions
- [x] AI assistant configs seeded from `backend/seed/ai_assistant_configs.json`
- [x] `@ai_tool` decorator and middleware are the two permission check points

### Documentation

- [x] Analysis phase approved with decisions
- [x] EVCS entity classification reviewed
- [x] RBAC service architecture understood

---

## Documentation References

### Code References

- RBAC service: `backend/app/core/rbac.py`
- RBAC config: `backend/config/rbac.json`
- Auth dependencies: `backend/app/api/dependencies/auth.py`
- AI tool decorator: `backend/app/ai/tools/decorator.py`
- Security middleware: `backend/app/ai/middleware/backcast_security.py`
- Agent orchestrator: `backend/app/ai/deep_agent_orchestrator.py`
- AI assistant model: `backend/app/models/domain/ai.py`
- Seed data: `backend/seed/ai_assistant_configs.json`
- Assistant selector: `frontend/src/features/ai/chat/components/AssistantSelector.tsx`

### Test References

- Existing RBAC tests: `backend/tests/unit/core/test_rbac.py`
- AI tool RBAC tests: `backend/tests/security/ai/test_tool_rbac.py`
