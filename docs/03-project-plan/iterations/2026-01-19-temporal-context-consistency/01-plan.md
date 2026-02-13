# Plan: Temporal and Branch Context Consistency

**Created:** 2026-01-19
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1: Full Body Parameter Consistency

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1: Full Body Parameter Consistency
- **Architecture**: All write operation parameters (`branch`, `control_date`) will be in request bodies for POST/PUT/PATCH operations. DELETE operations will continue using query parameters (HTTP constraint). Schedule baselines MUST be created on "main" branch first, then use branching operations to create in other branches.
- **Key Decisions**:
  - Complete the pattern established by Projects, WBEs, and CostElements
  - Schedule baselines enforce "create on main first" approach (branch field defaults to "main" only, not configurable by API consumer)
  - To create in other branches, use branching operations (create branch, etc.)
  - Type safety via Pydantic schemas
  - Clear API design: body for writes, query for filtering
  - DELETE operations explicitly documented as exception due to HTTP/1.1 constraints
  - Frontend changes included in scope (not deferred to sprint backlog)

### Success Criteria

**Functional Criteria:**

- [ ] Schedule baseline CREATE endpoint accepts `branch` (defaulted to "main" only) and `control_date` in request body VERIFIED BY: API integration test
- [ ] Schedule baseline UPDATE endpoint accepts `branch` (defaulted to "main" only) and `control_date` in request body VERIFIED BY: API integration test
- [ ] Schedule baseline creation is restricted to main branch (branch field not configurable by API consumer) VERIFIED BY: API integration test
- [ ] Nested schedule baseline endpoints in cost_elements.py accept `branch` (defaulted to "main" only) and `control_date` in request body VERIFIED BY: API integration test
- [ ] Forecast UPDATE endpoint accepts `branch` and `control_date` in request body (from query) VERIFIED BY: API integration test
- [ ] DELETE endpoints continue using query parameters (all entities) VERIFIED BY: API integration test
- [ ] Default values work correctly (`branch="main"`, `control_date=None`) VERIFIED BY: Unit test
- [ ] Request body validation catches invalid values VERIFIED BY: Unit test
- [ ] Frontend OpenAPI client regenerated with updated types VERIFIED BY: File existence check
- [ ] Frontend CREATE mutations include `control_date` from TimeMachine context VERIFIED BY: Frontend unit test
- [ ] Frontend nested API hooks move `branch` from query params to body VERIFIED BY: Frontend unit test

**Technical Criteria:**

- [ ] Performance: No measurable impact on endpoint response times VERIFIED BY: Before/after timing comparison
- [ ] Security: Existing RBAC permissions continue to work VERIFIED BY: Security test
- [ ] Code Quality: MyPy strict mode (zero errors), Ruff (zero errors), 80%+ test coverage VERIFIED BY: CI pipeline

**TDD Criteria:**

- [ ] All tests written **before** implementation code
- [ ] Each test failed first (documented in DO phase log)
- [ ] Test coverage >= 80% for modified files
- [ ] Tests follow Arrange-Act-Assert pattern

### Scope Boundaries

**In Scope:**

- **Backend Changes:**
  - Schedule baseline schema updates (add `branch` and `control_date` fields, defaulted to "main" only)
  - Schedule baseline route updates (extract from body instead of hardcoding)
  - Nested schedule baseline endpoints in cost_elements.py
  - Forecast PUT endpoint (move `branch` and `control_date` from query to body)
  - Update API conventions documentation to explicitly document DELETE exception
  - All associated backend tests (unit, integration)
- **Frontend Changes:**
  - Regenerate OpenAPI client from updated backend spec
  - Update direct schedule baseline API hooks (`useScheduleBaselines.ts`)
  - Update nested cost element schedule baseline API hooks (`useCostElementScheduleBaseline.ts`)
  - Update frontend unit tests to match new request payloads

**Out of Scope:**

- DELETE operations (query parameter usage is correct per HTTP spec, just needs documentation)
- Other entity types (Projects, WBEs, CostElements already compliant)
- Database schema changes (no SQL migrations required)
- Service layer changes (already expects these parameters)
- Branching operations themselves (existing functionality for creating branches)

---

## Work Decomposition

### Task Breakdown

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | --- | --- | --- | --- | --- |
| **Backend Tasks** |
| 1 | Add `branch` (defaulted to "main" only) and `control_date` to ScheduleBaselineCreate schema | `backend/app/models/schemas/schedule_baseline.py` | None | Schema validates with `branch="main"` hardcoded default, `control_date=None`, field not configurable by consumer | Low |
| 2 | Add `branch` (defaulted to "main" only) and `control_date` to ScheduleBaselineUpdate schema | `backend/app/models/schemas/schedule_baseline.py` | Task 1 | Schema validates with `branch="main"` hardcoded default, nullable `control_date` | Low |
| 3 | Update schedule baseline POST route to extract `branch` and `control_date` from request body | `backend/app/api/routes/schedule_baselines.py` | Task 1 | Route uses `baseline_in.branch` and `baseline_in.control_date` instead of hardcoded values | Low |
| 4 | Update schedule baseline PUT route to extract `branch` and `control_date` from request body | `backend/app/api/routes/schedule_baselines.py` | Task 2 | Route uses `baseline_in.branch` and `baseline_in.control_date` instead of hardcoded values | Low |
| 5 | Update nested schedule baseline POST endpoint in cost_elements.py | `backend/app/api/routes/cost_elements.py` (lines 348-399) | Task 1 | Extract `branch` and `control_date` from request body dict | Medium |
| 6 | Update nested schedule baseline PUT endpoint in cost_elements.py | `backend/app/api/routes/cost_elements.py` (lines 402-466) | Task 2 | Extract `branch` and `control_date` from request body dict | Medium |
| 7 | Update forecast PUT endpoint to accept `branch` and `control_date` in request body | `backend/app/api/routes/cost_elements.py` (lines 635-774) | None | Extract from `forecast_in` dict instead of query parameters | Medium |
| 8 | Write unit tests for schema validation | `backend/tests/unit/models/schemas/test_schedule_baseline.py` (new or update existing) | Tasks 1, 2 | All schema validation scenarios covered, including branch="main" enforcement | Low |
| 9 | Write integration tests for schedule baseline endpoints | `backend/tests/api/test_schedule_baselines.py` | Tasks 3, 4 | All CRUD operations tested with new parameter locations, branch restriction verified | Medium |
| 10 | Write integration tests for nested schedule baseline endpoints | `backend/tests/api/test_cost_elements_schedule_baseline.py` | Tasks 5, 6 | All nested operations tested with new parameter locations | Medium |
| 11 | Write integration tests for forecast endpoint | `backend/tests/api/test_cost_elements_forecast.py` | Task 7 | Forecast PUT tested with body parameters | Medium |
| 12 | Update API conventions documentation to explicitly document DELETE exception | `docs/02-architecture/cross-cutting/api-conventions.md` | All backend implementation tasks | Documentation clearly explains DELETE as exception due to HTTP/1.1 constraints | Low |
| **Frontend Tasks** |
| 13 | Regenerate OpenAPI client from updated backend spec | `frontend/src/api/generated/*` | Tasks 1, 2, 3, 4, 5, 6, 7 | Generated TypeScript types include `branch` and `control_date` in ScheduleBaselineCreate/Update | Low |
| 14 | Update direct schedule baseline CREATE mutation to include `control_date` from TimeMachine | `frontend/src/features/schedule-baselines/api/useScheduleBaselines.ts` | Task 13 | CREATE mutation payload includes `control_date` from `useTimeMachineParams()` context | Low |
| 15 | Update direct schedule baseline UPDATE mutation to include `branch` and `control_date` | `frontend/src/features/schedule-baselines/api/useScheduleBaselines.ts` | Task 13 | UPDATE mutation payload includes `branch` and `control_date` | Low |
| 16 | Update nested schedule baseline CREATE to move `branch` from query to body | `frontend/src/features/schedule-baselines/api/useCostElementScheduleBaseline.ts` | Task 13 | CREATE mutation removes `branch` from query params, includes in body payload | Medium |
| 17 | Update nested schedule baseline UPDATE to move `branch` from query to body | `frontend/src/features/schedule-baselines/api/useCostElementScheduleBaseline.ts` | Task 13 | UPDATE mutation removes `branch` from query params, includes in body payload | Medium |
| 18 | Update frontend unit tests for direct schedule baseline hooks | `frontend/src/features/schedule-baselines/api/__tests__/useScheduleBaselines.test.ts` | Tasks 14, 15 | Tests verify `control_date` inclusion in payloads | Low |
| 19 | Update frontend unit tests for nested schedule baseline hooks | `frontend/src/features/schedule-baselines/api/__tests__/useCostElementScheduleBaseline.test.ts` | Tasks 16, 17 | Tests verify `branch` moved from query to body | Low |

**Task Ordering Principles:**

1. **Backend Schemas first (Tasks 1-2)** - Foundation for type safety
2. **Backend Routes second (Tasks 3-7)** - Core operations depend on schemas
3. **Backend Tests alongside (Tasks 8-11)** - TDD approach, written before/with implementation
4. **Backend Documentation (Task 12)** - Update after implementation verified
5. **Frontend Client Regeneration (Task 13)** - Depends on all backend schema/route changes
6. **Frontend Hook Updates (Tasks 14-17)** - Depend on regenerated types
7. **Frontend Tests (Tasks 18-19)** - Update after hook changes

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| --- | --- | --- | --- |
| **Backend Tests** |
| Schedule baseline CREATE accepts `branch` (main only) and `control_date` in body | T-001 | `tests/api/test_schedule_baselines.py` | POST request with `branch="main"` (or omitted) and `control_date` in body creates baseline in main branch only |
| Schedule baseline UPDATE accepts `branch` (main only) and `control_date` in body | T-002 | `tests/api/test_schedule_baselines.py` | PUT request with `branch="main"` (or omitted) and `control_date` in body updates baseline in main branch only |
| Schedule baseline creation is restricted to main branch | T-003 | `tests/api/test_schedule_baselines.py` | POST request with `branch="feature-branch"` is rejected or defaults to "main" (field not configurable) |
| Default values work correctly | T-004 | `tests/unit/models/schemas/test_schedule_baseline.py` | Schema with no `branch` defaults to `"main"`, no `control_date` defaults to `None` |
| Request body validation catches invalid values | T-005 | `tests/unit/models/schemas/test_schedule_baseline.py` | Invalid `branch` type raises ValidationError |
| Nested schedule baseline POST accepts body parameters | T-006 | `tests/api/test_cost_elements_schedule_baseline.py` | POST to `/{cost_element_id}/schedule-baseline` with `branch` in body creates baseline in main branch only |
| Nested schedule baseline PUT accepts body parameters | T-007 | `tests/api/test_cost_elements_schedule_baseline.py` | PUT to `/{cost_element_id}/schedule-baseline/{id}` with `branch` in body updates baseline in main branch only |
| Forecast PUT accepts body parameters | T-008 | `tests/api/test_cost_elements_forecast.py` | PUT to `/{cost_element_id}/forecast` with `branch` and `control_date` in body updates forecast correctly |
| DELETE continues using query parameters | T-009 | `tests/api/test_schedule_baselines.py` | DELETE request with `?branch=main&control_date=...` successfully soft deletes |
| Existing RBAC permissions work | T-010 | `tests/api/test_schedule_baselines.py` | Requests without required permissions return 403 |
| **Frontend Tests** |
| Frontend CREATE mutation includes `control_date` from TimeMachine | T-FE-01 | `frontend/src/features/schedule-baselines/api/__tests__/useScheduleBaselines.test.ts` | Mutation payload includes `control_date` value from `useTimeMachineParams()` context |
| Frontend UPDATE mutation includes `branch` and `control_date` | T-FE-02 | `frontend/src/features/schedule-baselines/api/__tests__/useScheduleBaselines.test.ts` | Mutation payload includes both `branch` and `control_date` in body |
| Frontend nested CREATE moves `branch` from query to body | T-FE-03 | `frontend/src/features/schedule-baselines/api/__tests__/useCostElementScheduleBaseline.test.ts` | Mutation removes `branch` from query params, includes in body payload |
| Frontend nested UPDATE moves `branch` from query to body | T-FE-04 | `frontend/src/features/schedule-baselines/api/__tests__/useCostElementScheduleBaseline.test.ts` | Mutation removes `branch` from query params, includes in body payload |

---

## Test Specification

### Test Hierarchy

```
├── Backend Unit Tests
│   ├── Schema validation
│   │   ├── ScheduleBaselineCreate with defaults (branch="main")
│   │   ├── ScheduleBaselineCreate with explicit control_date
│   │   ├── ScheduleBaselineCreate with invalid types
│   │   ├── ScheduleBaselineCreate branch field not configurable (rejects non-main)
│   │   ├── ScheduleBaselineUpdate with all fields
│   │   ├── ScheduleBaselineUpdate with partial fields
│   │   └── ScheduleBaselineUpdate with invalid types
│   └── Pydantic field exclusion (schedule_baseline_id)
├── Backend Integration Tests
│   ├── Schedule baseline CRUD
│   │   ├── CREATE with body parameters (branch="main")
│   │   ├── CREATE with control_date in body
│   │   ├── CREATE with default values
│   │   ├── CREATE rejected for non-main branch (branch restriction)
│   │   ├── UPDATE with body parameters (branch="main")
│   │   ├── UPDATE with control_date in body
│   │   ├── DELETE with query parameters
│   │   └── READ with branch filtering
│   ├── Nested schedule baseline endpoints
│   │   ├── POST with body parameters (branch="main")
│   │   ├── POST with control_date in body
│   │   ├── PUT with body parameters (branch="main")
│   │   └── PUT with control_date in body
│   └── Forecast endpoint
│       ├── PUT with body parameters
│       ├── PUT in non-main branch
│       └── DELETE with query parameters
├── Frontend Unit Tests
│   ├── Direct schedule baseline hooks
│   │   ├── CREATE includes control_date from TimeMachine context
│   │   ├── UPDATE includes branch and control_date in payload
│   │   └── DELETE continues using query parameters
│   └── Nested schedule baseline hooks
│       ├── CREATE moves branch from query to body
│       ├── CREATE includes control_date in body
│       ├── UPDATE moves branch from query to body
│       └── UPDATE includes control_date in body
└── Security Tests
    ├── RBAC enforcement (all endpoints)
    └── Invalid branch handling
```

### Test Cases (First 10)

| Test ID | Test Name | Criterion | Type | Expected Result |
| --- | --- | --- | --- | --- |
| T-001 | `test_schedule_baseline_create_with_branch_main_in_body_creates_in_main` | AC: CREATE accepts body params (main only) | Integration | Baseline created with `branch="main"` is retrievable via GET in main branch |
| T-002 | `test_schedule_baseline_create_with_control_date_in_body_uses_specified_date` | AC: CREATE accepts body params | Integration | Baseline's `valid_time` lower bound equals `control_date` from request body |
| T-003 | `test_schedule_baseline_create_with_defaults_uses_main_branch` | AC: Default values work | Integration | Request without `branch` field creates baseline in `"main"` branch |
| T-004 | `test_schedule_baseline_create_with_non_main_branch_defaults_to_main` | AC: Branch restriction enforced | Integration | Request with `branch="feature-branch"` defaults to `"main"` (field not configurable) |
| T-005 | `test_schedule_baseline_update_with_branch_in_body_updates_in_specified_branch` | AC: UPDATE accepts body params | Integration | Baseline updated with `branch="main"` creates new version in main branch |
| T-006 | `test_schedule_baseline_create_schema_with_explicit_control_date_validates` | AC: Request body validation | Unit | Schema with `control_date="2026-01-19T00:00:00Z"` validates successfully |
| T-007 | `test_schedule_baseline_create_schema_with_invalid_branch_type_raises_validation_error` | AC: Request body validation | Unit | Schema with `branch=123` raises `Pydantic ValidationError` |
| T-008 | `test_nested_schedule_baseline_post_with_branch_in_body_creates_in_main` | AC: Nested endpoints accept body params | Integration | POST to `/{ce_id}/schedule-baseline` with `branch="main"` creates baseline in main branch |
| T-009 | `test_forecast_update_with_branch_in_body_updates_in_specified_branch` | AC: Forecast PUT accepts body params | Integration | PUT to `/{ce_id}/forecast` with `branch="feature"` in body updates forecast in that branch |
| T-010 | `test_schedule_baseline_delete_with_query_params_succeeds` | AC: DELETE uses query params | Integration | DELETE with `?branch=main&control_date=...` soft deletes the baseline |

### Frontend Test Cases (Additional)

| Test ID | Test Name | Criterion | Type | Expected Result |
| --- | --- | --- | --- | --- |
| T-FE-01 | `test_use_create_schedule_baseline_includes_control_date_from_time_machine` | AC: Frontend CREATE includes control_date | Unit | Mutation payload includes `control_date` value from `useTimeMachineParams()` hook |
| T-FE-02 | `test_use_update_schedule_baseline_includes_branch_and_control_date` | AC: Frontend UPDATE includes both params | Unit | Mutation payload includes both `branch` and `control_date` fields |
| T-FE-03 | `test_use_create_cost_element_schedule_baseline_moves_branch_to_body` | AC: Frontend nested CREATE moves branch | Unit | Mutation removes `branch` from query params, includes in body payload |
| T-FE-04 | `test_use_update_cost_element_schedule_baseline_moves_branch_to_body` | AC: Frontend nested UPDATE moves branch | Unit | Mutation removes `branch` from query params, includes in body payload |

### Test Infrastructure Needs

**Backend Fixtures needed:**
- `mock_admin_user` (already exists in test files)
- `client` (AsyncClient from conftest.py)
- `setup_dependencies` (already exists in test_cost_elements_schedule_baseline.py)

**Backend Mocks/stubs:**
- Authentication dependencies (already mocked in test files)
- RBAC service (already mocked in test files)

**Backend Database state:**
- Clean database per test (pytest-asyncio with transaction rollback)
- Seed data: Department, CostElementType, Project, WBE, CostElement (from existing fixtures)

**Frontend Test Infrastructure:**
- Vitest configuration (already exists)
- Mock for `useTimeMachineParams` hook (to provide `asOf` and `branch` values)
- Mock for OpenAPI client `__request` function (to verify request payloads)
- React Query wrappers for mutation testing (already exists in test setup)

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| Technical | Breaking change for existing API consumers | Medium | High | No external consumers beyond frontend (confirmed in analysis). Frontend updates included in this plan. |
| Integration | Schema changes might affect OpenAPI spec generation | Low | Medium | Verify OpenAPI docs after changes using `/docs` endpoint, regenerate client before frontend updates |
| Integration | Nested endpoints use dict instead of Pydantic models | Medium | Medium | Extract fields from dict manually (already pattern in cost_elements.py) |
| Testing | Existing backend tests might fail with hardcoded values | High | Medium | Run full test suite before starting, update all affected tests |
| Testing | Frontend tests may fail after OpenAPI regeneration | Medium | Medium | Update frontend tests to match new type definitions (Tasks 18-19) |
| Documentation | API docs might not reflect the DELETE exception | Low | Low | Explicitly document DELETE as exception in API conventions (Task 12) |
| Integration | Frontend TimeMachine context may not provide `asOf` value | Low | Medium | Verify `useTimeMachineParams` hook implementation before Task 14 |

---

## Documentation References

### Required Reading

- Coding Standards: `docs/02-architecture/backend/coding-standards.md`
- API Conventions: `docs/02-architecture/cross-cutting/api-conventions.md`
- Temporal Query Reference: `docs/02-architecture/cross-cutting/temporal-query-reference.md`
- ADR-005: Bitemporal Versioning: `docs/02-architecture/decisions/ADR-005-bitemporal-versioning.md`

### Code References

- Backend pattern (Schedule Baseline): `backend/app/models/schemas/schedule_baseline.py`
- Backend pattern (similar implementation): `backend/app/models/schemas/project.py` (lines 23-54)
- Backend pattern (similar implementation): `backend/app/models/schemas/cost_element.py` (lines 19-51)
- Test pattern: `backend/tests/api/test_cost_elements_schedule_baseline.py`
- Test pattern: `backend/tests/api/test_cost_elements_forecast.py`
- Service layer: `backend/app/services/schedule_baseline_service.py` (no changes needed)

**Frontend References:**
- Direct schedule baseline hooks: `frontend/src/features/schedule-baselines/api/useScheduleBaselines.ts`
- Nested schedule baseline hooks: `frontend/src/features/schedule-baselines/api/useCostElementScheduleBaseline.ts`
- TimeMachine context hook: `frontend/src/features/time-machine/api/useTimeMachineParams.ts` (verify provides `asOf` value)

### "Create on Main First" Policy

Schedule baselines MUST be created on the "main" branch first. The API enforces this by:

1. **Schema Level**: `ScheduleBaselineCreate.branch` field defaults to "main" and is not configurable by API consumers
2. **Route Level**: POST endpoint will always use `branch="main"` regardless of what the client sends
3. **Branching Operations**: To create a schedule baseline in a non-main branch:
   - First create the baseline on main branch (via POST)
   - Then use branching operations to create the target branch (if not exists)
   - The baseline will be available in the new branch via EVCS inheritance

**Rationale:**
- Ensures all schedule baselines originate from a single source of truth
- Simplifies branching workflow - baselines are inherited, not duplicated
- Prevents orphaned baselines in feature branches that cannot be merged back to main
- Aligns with Git-like branching model where branches diverge from main

### Similar Implementations

**ProjectCreate/Update** (`backend/app/models/schemas/project.py`):
```python
class ProjectCreate(ProjectBase):
    branch: str = Field("main", description="Branch name for creation")
    control_date: datetime | None = Field(
        None, description="Optional control date for creation"
    )

class ProjectUpdate(BaseModel):
    # ... fields ...
    branch: str | None = Field(None, description="Branch name for update")
    control_date: datetime | None = Field(None, description="Control date")
```

**Project POST route** (`backend/app/api/routes/projects.py`):
```python
@router.post("")
async def create_project(
    project_in: ProjectCreate,  # Includes branch and control_date
    current_user: User = Depends(get_current_active_user),
    service: ProjectService = Depends(get_project_service),
) -> Project:
    return await service.create(
        create_schema=project_in,
        actor_id=current_user.user_id,
        branch=project_in.branch,  # From body
        control_date=project_in.control_date,  # From body
    )
```

---

## Prerequisites

### Technical

- [x] Python 3.12+ installed
- [x] PostgreSQL 15+ running via Docker
- [x] Database migrations applied (`alembic upgrade head`)
- [x] Dependencies installed (`uv sync`)
- [x] Test database configured

### Documentation

- [x] Analysis phase approved (`00-analysis.md` complete with approved option)
- [x] Architecture docs reviewed (API conventions, temporal query reference)
- [x] ADR-005 understood (bitemporal versioning)
- [ ] Frontend `useTimeMachineParams` hook verified to provide `asOf` value (TODO before Task 14)

---

## Task Dependency Graph

```yaml
# Task Dependency Graph for Temporal Context Consistency
tasks:
  # Backend Tasks (1-12)
  - id: TASK-001
    name: "Add branch (main only) and control_date to ScheduleBaselineCreate schema"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: TASK-002
    name: "Add branch (main only) and control_date to ScheduleBaselineUpdate schema"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: TASK-003
    name: "Update schedule baseline POST route to extract from body"
    agent: pdca-backend-do-executor
    dependencies: [TASK-001]

  - id: TASK-004
    name: "Update schedule baseline PUT route to extract from body"
    agent: pdca-backend-do-executor
    dependencies: [TASK-002]

  - id: TASK-005
    name: "Update nested schedule baseline POST in cost_elements.py"
    agent: pdca-backend-do-executor
    dependencies: [TASK-001]

  - id: TASK-006
    name: "Update nested schedule baseline PUT in cost_elements.py"
    agent: pdca-backend-do-executor
    dependencies: [TASK-002]

  - id: TASK-007
    name: "Update forecast PUT to accept body parameters"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: TASK-008
    name: "Write unit tests for schema validation"
    agent: pdca-backend-do-executor
    dependencies: [TASK-001, TASK-002]

  - id: TASK-009
    name: "Write integration tests for schedule baseline endpoints"
    agent: pdca-backend-do-executor
    dependencies: [TASK-003, TASK-004]

  - id: TASK-010
    name: "Write integration tests for nested schedule baseline endpoints"
    agent: pdca-backend-do-executor
    dependencies: [TASK-005, TASK-006]

  - id: TASK-011
    name: "Write integration tests for forecast endpoint"
    agent: pdca-backend-do-executor
    dependencies: [TASK-007]

  - id: TASK-012
    name: "Update API conventions documentation (DELETE exception)"
    agent: pdca-backend-do-executor
    dependencies: [TASK-003, TASK-004, TASK-005, TASK-006, TASK-007]

  # Frontend Tasks (13-19)
  - id: TASK-013
    name: "Regenerate OpenAPI client from updated backend spec"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-001, TASK-002, TASK-003, TASK-004, TASK-005, TASK-006, TASK-007]

  - id: TASK-014
    name: "Update direct schedule baseline CREATE to include control_date from TimeMachine"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-013]

  - id: TASK-015
    name: "Update direct schedule baseline UPDATE to include branch and control_date"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-013]

  - id: TASK-016
    name: "Update nested schedule baseline CREATE to move branch from query to body"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-013]

  - id: TASK-017
    name: "Update nested schedule baseline UPDATE to move branch from query to body"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-013]

  - id: TASK-018
    name: "Update frontend unit tests for direct schedule baseline hooks"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-014, TASK-015]

  - id: TASK-019
    name: "Update frontend unit tests for nested schedule baseline hooks"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-016, TASK-017]
```

**Parallel Execution Opportunities:**

**Backend Level (Tasks 1-12):**
- TASK-001 and TASK-002 can run in parallel (both schema changes)
- TASK-003 and TASK-007 can run in parallel after TASK-001 (different files)
- TASK-004 and TASK-005 can run in parallel after TASK-002 (different files)
- TASK-008, TASK-009, TASK-010, TASK-011 can run in parallel after their implementation tasks complete

**Frontend Level (Tasks 13-19):**
- All frontend tasks (13-19) depend on TASK-013 (OpenAPI client regeneration)
- TASK-014, TASK-015, TASK-016, TASK-017 can run in parallel after TASK-013 (all hook updates)
- TASK-018 and TASK-019 can run in parallel after their respective hook updates

**Backend-Frontend Dependency:**
- All frontend work (Tasks 13-19) must wait for ALL backend implementation tasks (1-7) to complete before TASK-013 can regenerate the client

---

## Output

**File**: `docs/03-project-plan/iterations/2026-01-19-temporal-context-consistency/01-plan.md`

**Next Phase**: DO phase implementation following RED-GREEN-REFACTOR TDD methodology

---

## Key Principles

1. **Define WHAT, not HOW**: This plan specifies test cases and acceptance criteria, not implementation code
2. **Measurable**: All success criteria are objectively verifiable via tests and measurements
3. **Sequential**: Tasks ordered with clear dependencies to enable incremental progress
4. **Traceable**: Every requirement maps to specific test specifications
5. **Actionable**: Each task is clear enough for DO phase execution with defined file paths and success criteria
