# Plan: AI Chat Session Context System

**Created:** 2026-04-13
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 - JSONB-based flexible context field

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 - Nullable JSONB `context` column
- **Architecture**: Store structured context data as JSONB with stable context types (general, project, wbe, cost_element)
- **Key Decisions**:
  - Use `context` JSONB column instead of separate context table (simpler, adequate for 4-5 stable types)
  - Context data includes `type`, `id`, and `name` fields for structured filtering
  - Backward compatibility: existing sessions default to `{"type": "general"}`
  - No migration needed for adding new context types (application-level validation)
  - Frontend auto-sets context based on route (`/chat` → general, `/projects/:id/chat` → project)

### Success Criteria

**Functional Criteria:**

- [ ] **Session Context Field**: `AIConversationSession.context` JSONB column stores context data with type, id, and name fields VERIFIED BY: Database integration tests
- [ ] **Context Filtering**: Session list API and frontend support filtering by context type (general/project/wbe/cost_element) VERIFIED BY: API integration tests
- [ ] **Auto-Context Assignment**: New sessions automatically receive appropriate context based on route (main nav → general, project chat → project context) VERIFIED BY: E2E tests
- [ ] **Agent Context Injection**: Agent system prompt receives context data for contextual awareness VERIFIED BY: Agent service unit tests
- [ ] **Backward Compatibility**: Existing sessions without context default to "general" type VERIFIED BY: Migration test

**Technical Criteria:**

- [ ] **Performance**: Session filtering by context type completes within 500ms for 1000+ sessions VERIFIED BY: Performance test with composite index
- [ ] **Type Safety**: Python Pydantic schemas and TypeScript types enforce context structure VERIFIED BY: MyPy strict mode and TypeScript strict mode
- [ ] **Code Quality**: Zero MyPy errors, zero Ruff errors, 80%+ test coverage VERIFIED BY: CI pipeline
- [ ] **Index Efficiency**: Composite index on `(user_id, context->>'type')` for fast filtering VERIFIED BY: EXPLAIN ANALYZE query plan

**TDD Criteria:**

- [ ] All tests written **before** implementation code (RED-GREEN-REFACTOR)
- [ ] Each test failed first (documented in DO phase log)
- [ ] Test coverage ≥80% for modified code
- [ ] Tests follow Arrange-Act-Assert pattern

### Scope Boundaries

**In Scope:**

- Database migration to add `context` JSONB column to `ai_conversation_sessions`
- Backend model, schema, and service updates for context field
- Backend API filtering support by context type
- Frontend TypeScript type updates for context
- Frontend session list filter UI (tabs or dropdown)
- Frontend auto-context assignment based on route
- Agent system prompt context injection
- Tests (unit, integration, E2E) for all changes

**Out of Scope:**

- Context administration UI (manual DB management sufficient)
- WBE-specific and cost_element-specific chat pages (future iterations)
- Context migration/editing for existing sessions (manual DB update only)
- Analytics/reporting on context usage
- Context-based permission changes (existing RBAC remains)

---

## Work Decomposition

### Task Breakdown

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | --- | --- | --- | --- | --- |
| 1 | **Database Migration**: Add `context` JSONB column to `ai_conversation_sessions` table with default value and composite index | `backend/alembic/versions/XXXX_add_session_context.py` | None | Migration runs successfully, column exists with correct defaults, index created, existing rows get `{"type": "general"}` | Low |
| 2 | **Backend Model Update**: Add `context` field to `AIConversationSession` model with JSONB type annotation | `backend/app/models/domain/ai.py` | Task 1 | Model field defined with correct type, MyPy passes | Low |
| 3 | **Backend Schema Updates**: Update Pydantic schemas to include context field in create/public models | `backend/app/models/schemas/ai.py` | Task 2 | Schemas compile, TypeScript types generated, validation works | Low |
| 4 | **Backend Service Layer**: Update `AIConfigService` to handle context parameter in `create_session()` and `list_sessions()` filtering | `backend/app/services/ai_config_service.py` | Task 3 | Service methods accept context parameter, filtering logic works | Medium |
| 5 | **Backend API Routes**: Update session endpoints to support context filtering query parameter | `backend/app/api/routes/ai_chat.py` | Task 4 | API endpoints accept optional `context_type` filter, return filtered results | Medium |
| 6 | **Agent Context Injection**: Pass context to agent system prompt in `agent_service.py` | `backend/app/ai/agent_service.py` | Task 3 | Agent receives context data, system prompt includes context info | Medium |
| 7 | **Backend Tests**: Write unit/integration tests for context field and filtering | `backend/tests/unit/test_ai_config_service.py`, `backend/tests/integration/test_ai_chat_routes.py` | Task 5 | All tests pass, coverage ≥80% | Medium |
| 8 | **Frontend Type Updates**: Add context field to TypeScript types and update query keys | `frontend/src/features/ai/types.ts`, `frontend/src/features/ai/chat/types.ts`, `frontend/src/api/queryKeys.ts` | Task 3 | TypeScript compiles with strict mode, types match backend | Low |
| 9 | **Frontend API Hooks**: Update session hooks to support context filtering | `frontend/src/features/ai/chat/api/useChatSessions.ts`, `frontend/src/features/ai/chat/api/useChatSessionsPaginated.ts` | Task 8 | Hooks accept optional context filter parameter | Low |
| 10 | **Frontend Session List Filter**: Add context filter UI (tabs or dropdown) to SessionList component | `frontend/src/features/ai/chat/components/SessionList.tsx` | Task 9 | UI renders filter, filtering works, state persists | Medium |
| 11 | **Frontend Auto-Context Assignment**: Update chat interfaces to auto-set context based on route | `frontend/src/pages/chat/ChatInterface.tsx`, `frontend/src/pages/projects/ProjectChat.tsx` | Task 9 | General chat sets context to `{"type": "general"}`, project chat sets project context | Medium |
| 12 | **Frontend Tests**: Write tests for context filtering and auto-assignment | `frontend/src/features/ai/chat/components/__tests__/SessionList.test.tsx`, `frontend/src/features/ai/chat/api/__tests__/useChatSessions.test.tsx` | Task 11 | All tests pass, coverage ≥80% | Medium |
| 13 | **E2E Tests**: Add end-to-end tests for context-aware session creation and filtering | `frontend/src/features/ai/chat/e2e/session-context.e2e.ts` (new) | Task 12 | E2E tests verify complete user flows | Medium |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| --- | --- | --- | --- |
| Session Context Field stores data | T-001 | `tests/integration/test_ai_config_service.py` | `test_create_session_with_context` creates session with valid JSONB context |
| Context Filtering works | T-002 | `tests/integration/test_ai_chat_routes.py` | `test_list_sessions_filtered_by_context` returns only sessions matching context type |
| Auto-Context Assignment (general) | T-003 | `e2e/session-context.e2e.ts` | `test_general_chat_creates_general_context` verifies session has `{"type": "general"}` |
| Auto-Context Assignment (project) | T-004 | `e2e/session-context.e2e.ts` | `test_project_chat_creates_project_context` verifies session has project context |
| Agent Context Injection | T-005 | `tests/unit/test_agent_service.py` | `test_agent_receives_context_in_prompt` verifies system prompt includes context |
| Backward Compatibility | T-006 | `tests/integration/test_ai_config_service.py` | `test_existing_sessions_default_to_general` verifies sessions without context return as general |
| Performance: Filtering speed | T-007 | `tests/performance/test_session_filtering.py` | `test_filter_1000_sessions_by_context` completes within 500ms |
| Type Safety: Pydantic validation | T-008 | `tests/unit/test_ai_schemas.py` | `test_context_schema_validation_rejects_invalid_types` rejects malformed context |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests
│   ├── Backend model tests (AIConversationSession context field)
│   ├── Backend schema tests (Pydantic validation)
│   ├── Backend service tests (context filtering logic)
│   ├── Agent service tests (context injection)
│   ├── Frontend type tests (TypeScript types)
│   └── Frontend hook tests (context filtering)
├── Integration Tests
│   ├── Database migration tests
│   ├── API endpoint tests (context filtering)
│   └── Service layer integration (context CRUD)
└── E2E Tests
    ├── General chat creates general context
    ├── Project chat creates project context
    └── Session list filters by context
```

### Test Cases (first 8)

| Test ID | Test Name | Criterion | Type | Expected Result |
| --- | --- | --- | --- | --- |
| T-001 | `test_create_session_with_valid_context` | Session Context Field | Unit | Session created with `context={"type": "project", "id": "uuid", "name": "Project Name"}` |
| T-002 | `test_create_session_with_invalid_context_type` | Type Safety | Unit | Pydantic validation error for invalid context type |
| T-003 | `test_list_sessions_filtered_by_general_context` | Context Filtering | Integration | Returns only sessions with `context->>'type' = 'general'` |
| T-004 | `test_list_sessions_filtered_by_project_context` | Context Filtering | Integration | Returns only sessions with `context->>'type' = 'project'` |
| T-005 | `test_list_sessions_without_filter_returns_all` | Context Filtering | Integration | Returns all sessions when no context filter specified |
| T-006 | `test_agent_system_prompt_includes_project_context` | Agent Context Injection | Unit | System prompt contains project name and ID when context is project |
| T-007 | `test_existing_session_without_context_defaults_to_general` | Backward Compatibility | Integration | Session with NULL context returns as `{"type": "general"}` |
| T-008 | `test_general_chat_route_creates_general_context_session` | Auto-Context Assignment | E2E | Creating session from `/chat` route sets context to `{"type": "general"}` |

### Test Infrastructure Needs

**Fixtures needed:**
- `test_session_with_context` - Factory fixture for sessions with various context types
- `test_project_context` - Fixture with valid project context data
- `test_general_context` - Fixture with general context data

**Mocks/stubs:**
- Agent service execution (to avoid full LLM calls in tests)
- WebSocket connection (for E2E tests)

**Database state:**
- Seed data for 50+ sessions across different context types (for pagination/filtering tests)
- Test project and user fixtures for project context

---

## Task Dependency Graph

```yaml
# Task Dependency Graph for AI Chat Session Context System

tasks:
  - id: BE-001
    name: "Database migration: Add context JSONB column"
    agent: pdca-backend-do-executor
    dependencies: []
    group: migration

  - id: BE-002
    name: "Backend model update: Add context field to AIConversationSession"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Backend schema updates: Pydantic schemas for context field"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-004
    name: "Backend service: Update AIConfigService for context filtering"
    agent: pdca-backend-do-executor
    dependencies: [BE-003]

  - id: BE-005
    name: "Backend API: Update routes for context filtering"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: BE-006
    name: "Agent service: Inject context into system prompt"
    agent: pdca-backend-do-executor
    dependencies: [BE-003]

  - id: BE-007
    name: "Backend tests: Unit and integration tests for context"
    agent: pdca-backend-do-executor
    dependencies: [BE-005, BE-006]
    kind: test

  - id: FE-001
    name: "Frontend types: Add context field to TypeScript types"
    agent: pdca-frontend-do-executor
    dependencies: [BE-003]

  - id: FE-002
    name: "Frontend API hooks: Update session hooks for context filtering"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-003
    name: "Frontend UI: Add context filter to SessionList component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]

  - id: FE-004
    name: "Frontend auto-context: Update chat pages for route-based context"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]

  - id: FE-005
    name: "Frontend tests: Unit tests for context filtering and auto-assignment"
    agent: pdca-frontend-do-executor
    dependencies: [FE-004]
    kind: test

  - id: E2E-001
    name: "E2E tests: Context-aware session creation and filtering"
    agent: pdca-frontend-do-executor
    dependencies: [BE-007, FE-005]
    kind: test
```

**Execution Notes:**
- Tasks with empty `dependencies: []` (BE-001, FE-001 after BE-003) can run in parallel
- Test tasks (marked with `kind: test`) should run sequentially within the same agent to avoid database conflicts
- Backend and frontend work can proceed in parallel after BE-003 completes schemas

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| **Technical** | JSONB query performance degradation with large datasets | Medium | Medium | Composite index on `(user_id, context->>'type')`; performance test with 1000+ sessions |
| **Integration** | Frontend-backend schema mismatch after TypeScript generation | Low | High | Regenerate OpenAPI client after schema changes; validate types in CI |
| **Integration** | Existing sessions without context break filtering queries | Low | Medium | Database migration sets default `{"type": "general"}`; service layer handles NULL |
| **Technical** | Agent prompt injection via malicious context data | Low | High | Validate context structure; sanitize context data before prompt injection |
| **Integration** | Context field conflicts with existing `project_id`/`branch_id` semantics | Low | Medium | Keep `project_id`/`branch_id` for referential integrity; use `context` for UI filtering only |
| **Business** | Users confused by multiple context types in session list | Medium | Low | Clear UI labels and icons; default to "All" filter |

---

## Documentation References

### Required Reading

- Coding Standards: `docs/02-architecture/backend/coding-standards.md`
- AI Integration Bounded Context: `docs/02-architecture/01-bounded-contexts.md`
- SimpleEntityBase Pattern: `backend/app/core/base/simple.py`
- Existing Session Migration: `backend/alembic/versions/20260320_phase3e_session_context.py`

### Code References

**Backend patterns:**
- JSONB column usage: `backend/app/models/domain/project.py` (metadata field)
- Composite index pattern: `backend/app/models/domain/ai.py` (existing user_id index)
- Service layer filtering: `backend/app/services/ai_config_service.py` (list_sessions pattern)

**Frontend patterns:**
- Session list component: `frontend/src/features/ai/chat/components/SessionList.tsx`
- Route-based context: `frontend/src/pages/projects/ProjectChat.tsx` (project_id usage)
- Query key factories: `frontend/src/api/queryKeys.ts` (ai.chat pattern)

**Test patterns:**
- Service unit tests: `backend/tests/unit/test_ai_config_service.py`
- API integration tests: `backend/tests/integration/test_ai_chat_routes.py`
- Frontend hook tests: `frontend/src/features/ai/chat/api/__tests__/useChatSessions.test.tsx`

---

## Prerequisites

### Technical

- [ ] PostgreSQL 15+ available (supports JSONB indexing)
- [ ] Backend dependencies installed (`uv sync`)
- [ ] Frontend dependencies installed (`npm install`)
- [ ] Database migrations up to date (`alembic upgrade head`)

### Documentation

- [x] Analysis phase approved (`00-analysis.md`)
- [ ] SimpleEntityBase pattern reviewed
- [ ] Existing session context migration reviewed (`20260320_phase3e_session_context.py`)

---

## Context Data Structure

The `context` JSONB column will store structured data with the following format:

```json
// General context (no entity association)
{"type": "general"}

// Project context
{"type": "project", "id": "uuid-here", "name": "Project Name"}

// WBE context (future)
{"type": "wbe", "id": "uuid-here", "project_id": "uuid-here", "name": "WBE Name"}

// Cost element context (future)
{"type": "cost_element", "id": "uuid-here", "project_id": "uuid-here", "name": "Cost Element"}
```

**Valid context types:** `general`, `project`, `wbe`, `cost_element`

**Validation rules:**
- `type` field is required
- `id` is required for all types except `general`
- `name` is required for all types except `general`
- `project_id` is required for `wbe` and `cost_element` types

---

## Implementation Notes

### Backend

1. **Migration** will:
   - Add `context` JSONB column (nullable)
   - Set default `{"type": "general"}` for existing NULL values
   - Create composite index on `(user_id, (context->>'type'))`

2. **Service layer** will:
   - Accept optional `context` parameter in `create_session()`
   - Support `context_type` filter in `list_sessions()` and `list_sessions_paginated()`
   - Return sessions with context in API responses

3. **Agent service** will:
   - Receive context data via `start_execution()`
   - Inject context into system prompt (e.g., "You are in a project-specific chat for {project_name}")

### Frontend

1. **Types** will include:
   ```typescript
   type SessionContext =
     | { type: "general" }
     | { type: "project"; id: string; name: string }
     | { type: "wbe"; id: string; project_id: string; name: string }
     | { type: "cost_element"; id: string; project_id: string; name: string };
   ```

2. **SessionList** will:
   - Add context filter dropdown/tabs (All | General | Projects | WBEs | Cost Elements)
   - Show context icon/badge in session list items
   - Persist filter preference in localStorage

3. **Route-based context**:
   - `/chat` → `ChatInterfacePage` sets `context={{type: "general"}}`
   - `/projects/:projectId/chat` → `ProjectChat` sets `context={{type: "project", id, name}}`

---

## Success Metrics

- **Functional**: All acceptance criteria met (100%)
- **Performance**: Session filtering completes within 500ms for 1000+ sessions
- **Quality**: Zero MyPy/Ruff errors, 80%+ test coverage
- **User**: Sessions correctly categorized by context type in UI
