# Plan: One Schedule Baseline Per Cost Element (Branchable)

**Created:** 2026-01-18
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 - One Schedule Baseline Per Cost Element (Branchable)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 - One Schedule Baseline Per Cost Element (Branchable)
- **Architecture**: Enforce strict 1:1 relationship between Cost Elements and Schedule Baselines using foreign key constraint, leverage EVCS branching for what-if scenarios
- **Key Decisions**:
  - Add `schedule_baseline_id` FK to `cost_elements` table (nullable for migration)
  - Remove `cost_element_id` FK from `schedule_baselines` table (inverse relationship)
  - Enforce 1:1 relationship via unique constraint on `schedule_baseline_id`
  - Auto-create schedule baseline when cost element is created
  - Nest baseline management endpoints under cost elements
  - Migrate existing data by selecting most recent baseline per cost element

### Success Criteria

**Functional Criteria:**

- [ ] Each cost element has exactly one schedule baseline (enforced at database level) VERIFIED BY: Integration test querying cost elements with multiple baselines returns zero results
- [ ] Creating a cost element automatically creates a default schedule baseline VERIFIED BY: Unit test verifying baseline exists after cost element creation
- [ ] Updating a cost element's schedule data updates the linked baseline VERIFIED BY: Integration test verifying baseline update via cost element endpoint
- [ ] Soft deleting a cost element cascades to linked schedule baseline VERIFIED BY: Integration test verifying baseline deleted_at is set
- [ ] PV calculation uses the single baseline from cost element VERIFIED BY: E2E test calculating PV returns correct value
- [ ] Change order branches can modify schedule independently VERIFIED BY: Integration test verifying branch isolation
- [ ] Historical baselines are preserved via migration to archive table VERIFIED BY: Migration test verifying archived records
- [ ] Attempting to create duplicate baseline raises validation error VERIFIED BY: Unit test verifying exception raised

**Technical Criteria:**

- [ ] Performance: PV calculation completes in <100ms VERIFIED BY: Load test with 1000 concurrent requests
- [ ] Database: Foreign key constraint prevents orphaned baselines VERIFIED BY: Database constraint test
- [ ] Code Quality: MyPy strict mode (zero errors) VERIFIED BY: CI pipeline
- [ ] Code Quality: Ruff linting (zero errors) VERIFIED BY: CI pipeline
- [ ] Test Coverage: >=80% for new/modified code VERIFIED BY: Coverage report
- [ ] Migration: Zero data loss during schema migration VERIFIED BY: Migration verification script

**Business Criteria:**

- [ ] PV calculations are unambiguous - always use the one baseline VERIFIED BY: User acceptance testing
- [ ] What-if scenario analysis supported via branching VERIFIED BY: User acceptance testing
- [ ] Clear audit trail of schedule changes VERIFIED BY: History retrieval test

### Scope Boundaries

**In Scope:**

- Database schema changes (FK constraints, indexes)
- Migration of existing schedule baseline data
- Backend service layer modifications (validation, CRUD operations)
- API endpoint restructuring (nest under cost elements)
- Frontend component updates for new API structure
- Unit, integration, and E2E tests
- Migration rollback strategy
- Documentation updates (API docs, architecture docs)

**Out of Scope:**

- Changes to progression calculation algorithms (LINEAR, GAUSSIAN, LOGARITHMIC)
- Changes to other cost element fields or relationships
- Frontend redesign (only API integration changes)
- Performance optimization beyond PV calculation requirement
- Historical baseline comparison UI (deferred to future iteration)
- Schedule baseline templates (deferred to future iteration)

---

## Work Decomposition

### Task Breakdown

| #   | Task                                                                                                                                                                | Files                                                                                                                                                 | Dependencies        | Success Criteria                                                                                                                                                            | Complexity |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| 1   | Create database migration for 1:1 relationship                                                                                                                       | `backend/alembic/versions/YYYYMMDD_schedule_baseline_1to1.py`                                                                                         | None                | Migration applies successfully, FK constraint created, existing data migrated without loss                                                                                  | High       |
| 2   | Update CostElement model to include schedule_baseline_id FK                                                                                                          | `backend/app/models/domain/cost_element.py`                                                                                                           | Task 1              | Model compiles, FK column defined with nullable=True                                                                                                                       | Low        |
| 3   | Remove cost_element_id FK from ScheduleBaseline model                                                                                                                | `backend/app/models/domain/schedule_baseline.py`                                                                                                      | Task 1              | Model compiles, FK column removed, model still branchable/versionable                                                                                                      | Low        |
| 4   | Add BaselineAlreadyExistsError exception                                                                                                                             | `backend/app/services/schedule_baseline_service.py` (or new exceptions file)                                                                          | None                | Exception class defined with proper error message                                                                                                                          | Low        |
| 5   | Add get_for_cost_element() method to ScheduleBaselineService                                                                                                         | `backend/app/services/schedule_baseline_service.py`                                                                                                   | Task 2, Task 3      | Method returns single baseline or None, query uses cost_element.schedule_baseline_id                                                                                      | Medium     |
| 6   | Add validation to prevent duplicate baselines in ScheduleBaselineService.create()                                                                                   | `backend/app/services/schedule_baseline_service.py`                                                                                                   | Task 5              | Attempting to create second baseline for same cost element raises BaselineAlreadyExistsError                                                                               | Medium     |
| 7   | Add ensure_exists() method to ScheduleBaselineService for auto-creation                                                                                              | `backend/app/services/schedule_baseline_service.py`                                                                                                   | Task 5              | Method creates baseline if none exists, returns existing baseline if present                                                                                               | Medium     |
| 8   | Modify CostElementService.create_root() to auto-create default schedule baseline                                                                                     | `backend/app/services/cost_element_service.py`                                                                                                       | Task 7              | Creating cost element results in schedule baseline with default values (name="Default Schedule", 90-day duration, LINEAR progression)                                      | Medium     |
| 9   | Modify CostElementService.soft_delete() to cascade delete to schedule baseline                                                                                      | `backend/app/services/cost_element_service.py`                                                                                                       | Task 2, Task 3      | Soft deleting cost element sets deleted_at on linked baseline                                                                                                              | Medium     |
| 10  | Update ScheduleBaselineCreate schema (remove cost_element_id field)                                                                                                  | `backend/app/models/schemas/schedule_baseline.py`                                                                                                    | None                | Schema compiles, cost_element_id field removed                                                                                                                             | Low        |
| 11  | Update ScheduleBaselineRead schema to include cost element data                                                                                                      | `backend/app/models/schemas/schedule_baseline.py`                                                                                                    | None                | Schema includes cost_element details (code, name)                                                                                                                          | Low        |
| 12  | Add GET /api/v1/cost-elements/{id}/schedule-baseline endpoint                                                                                                         | `backend/app/api/routes/cost_elements.py` (new route)                                                                                                 | Task 5              | Endpoint returns schedule baseline for cost element, 404 if none exists                                                                                                    | Medium     |
| 13  | Add PUT /api/v1/cost-elements/{id}/schedule-baseline endpoint                                                                                                        | `backend/app/api/routes/cost_elements.py` (new route)                                                                                                 | Task 5              | Endpoint creates or updates schedule baseline for cost element                                                                                                             | Medium     |
| 14  | Add DELETE /api/v1/cost-elements/{id}/schedule-baseline endpoint                                                                                                      | `backend/app/api/routes/cost_elements.py` (new route)                                                                                                 | Task 9              | Endpoint soft deletes schedule baseline, requires confirmation                                                                                                              | Medium     |
| 15  | Deprecate old schedule baseline CRUD endpoints (POST /schedule-baselines, etc.)                                                                                      | `backend/app/api/routes/schedule_baselines.py` (add deprecation notices)                                                                             | Task 12, 13, 14     | Old endpoints return 410 Gone deprecation notice pointing to new endpoints                                                                                                 | Low        |
| 16  | Update PV calculation to use cost element's schedule baseline                                                                                                        | `backend/app/services/evm_calculations.py` (or wherever PV is calculated)                                                                            | Task 5              | PV calculation queries baseline via cost element, raises clear error if missing                                                                                            | Medium     |
| 17  | Write migration verification script to check data integrity                                                                                                          | `backend/scripts/verify_migration.py` (new file)                                                                                                      | Task 1              | Script reports zero orphaned baselines, all cost elements have baseline, zero data loss                                                                                     | Medium     |
| 18  | Write migration rollback script                                                                                                                                       | `backend/alembic/versions/YYYYMMDD_schedule_baseline_1to1.py` (downgrade)                                                                            | Task 1              | Rollback restores old schema, data integrity verified                                                                                                                      | High       |
| 19  | Unit tests for ScheduleBaselineService methods (get_for_cost_element, ensure_exists, validation)                                                                     | `backend/tests/unit/services/test_schedule_baseline_service.py` (new or update)                                                                      | Task 5, 6, 7        | Tests cover happy path, edge cases (no baseline, duplicate attempt), error handling, 100% coverage of new methods                                                          | Medium     |
| 20  | Unit tests for CostElementService auto-creation and cascade delete                                                                                                   | `backend/tests/unit/services/test_cost_element_service.py` (update)                                                                                  | Task 8, 9           | Tests verify baseline created with cost element, cascade delete on soft delete, mock schedule_baseline_service                                                             | Medium     |
| 21  | Integration tests for new API endpoints (GET/PUT/DELETE cost-elements/{id}/schedule-baseline)                                                                         | `backend/tests/api/test_cost_elements_schedule_baseline.py` (new file)                                                                              | Task 12, 13, 14     | Tests verify endpoint responses, validation, branch isolation, error handling, 80%+ coverage                                                                               | Medium     |
| 22  | Integration test for PV calculation using cost element's baseline                                                                                                    | `backend/tests/api/test_evm_calculations.py` (update or new)                                                                                         | Task 16             | Test verifies PV calculation returns correct value, uses baseline from cost element, handles missing baseline error                                                        | Medium     |
| 23  | E2E test for cost element creation with auto-created baseline                                                                                                        | `frontend/e2e/cost-element.spec.ts` (new or update)                                                                                                  | Task 12, 13, 14     | Test creates cost element via UI, verifies baseline exists, updates baseline, verifies cascade delete                                                                       | High       |
| 24  | Update frontend API client to use new endpoints                                                                                                                      | `frontend/src/api/client.ts` (update)                                                                                                                | Task 12, 13, 14     | Client methods updated to call new endpoints, TypeScript types updated                                                                                                     | Low        |
| 25  | Update frontend schedule baseline components to use new API structure                                                                                                | `frontend/src/features/cost-elements/components/ScheduleBaseline.tsx` (update or new)                                                                 | Task 24             | Component renders baseline from cost element endpoint, handles updates/deletes, displays errors                                                                             | Medium     |
| 26  | Update API documentation (OpenAPI spec, endpoint docs)                                                                                                               | `docs/api/schedule-baselines.md` (update)                                                                                                            | Task 12, 13, 14     | Documentation reflects new endpoint structure, deprecation notices included, examples provided                                                                              | Low        |
| 27  | Update architecture documentation to reflect 1:1 relationship                                                                                                        | `docs/02-architecture/01-bounded-contexts.md` (update)                                                                                               | Task 1              | Documentation describes new relationship, migration strategy, rationale                                                                                                    | Low        |
| 28  | Run full quality check (MyPy, Ruff, test coverage)                                                                                                                   | CI pipeline                                                                                                                                           | All tasks           | MyPy strict mode: 0 errors, Ruff: 0 errors, Test coverage: >=80%                                                                                                           | Medium     |

**Task Ordering Principles:**

1. **Database/Models First**: Tasks 1-3 establish the schema foundation
2. **Service Layer**: Tasks 4-9 implement business logic and validation
3. **API Layer**: Tasks 10-16 expose functionality via endpoints
4. **Testing**: Tasks 17-23 verify functionality at all levels
5. **Frontend**: Tasks 24-25 integrate with new API structure
6. **Documentation**: Tasks 26-27 keep docs in sync
7. **Quality Gate**: Task 28 ensures all standards met

### Test-to-Requirement Traceability

| Acceptance Criterion                                                                                                                                                      | Test ID | Test File                                                                          | Expected Behavior                                                                                                                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Each cost element has exactly one schedule baseline (enforced at database level)                                                                                           | T-001   | `backend/tests/api/test_cost_elements_schedule_baseline.py::test_duplicate_baseline_fails`              | Attempting to create second baseline for cost element via API raises 400 Bad Request with BaselineAlreadyExistsError message                                                                                                                |
| Creating a cost element automatically creates a default schedule baseline                                                                                                  | T-002   | `backend/tests/unit/services/test_cost_element_service.py::test_create_auto_creates_baseline`              | Creating cost element via service creates baseline with name="Default Schedule", 90-day duration, LINEAR progression, cost_element_id matches                                                                                              |
| Updating a cost element's schedule data updates the linked baseline                                                                                                       | T-003   | `backend/tests/api/test_cost_elements_schedule_baseline.py::test_update_baseline_via_cost_element`         | PUT to /cost-elements/{id}/schedule-baseline updates baseline fields (start_date, end_date, progression_type), returns updated ScheduleBaselineRead                                                                                       |
| Soft deleting a cost element cascades to linked schedule baseline                                                                                                          | T-004   | `backend/tests/api/test_cost_elements_schedule_baseline.py::test_delete_cost_element_cascades_to_baseline`  | DELETE to /cost-elements/{id} sets deleted_at on cost element AND linked schedule baseline, querying baseline afterwards returns 404                                                                                                      |
| PV calculation uses the single baseline from cost element                                                                                                                  | T-005   | `backend/tests/api/test_evm_calculations.py::test_pv_uses_cost_element_baseline`                          | PV calculation endpoint queries cost element's schedule_baseline_id, calculates progress from that baseline, returns correct PV = BAC × progress                                                                                           |
| Change order branches can modify schedule independently                                                                                                                    | T-006   | `backend/tests/api/test_cost_elements_schedule_baseline.py::test_branch_isolation`                       | Creating baseline in change order branch doesn't affect main branch, PV calculation uses baseline from selected branch, merging branch updates main baseline                                                                             |
| Historical baselines are preserved via migration to archive table                                                                                                          | T-007   | `backend/scripts/verify_migration.py::test_historical_baselines_archived`                                | Migration script creates `schedule_baselines_archive` table, inserts all but most recent baseline per cost element, archived records retain all fields (valid_time, transaction_time, etc.)                                                 |
| Attempting to create duplicate baseline raises validation error                                                                                                           | T-008   | `backend/tests/unit/services/test_schedule_baseline_service.py::test_create_duplicate_raises_error`        | ScheduleBaselineService.create_for_cost_element() raises BaselineAlreadyExistsError when baseline already exists for cost_element in specified branch                                                                                      |
| PV calculation completes in <100ms                                                                                                                                          | T-009   | `backend/tests/performance/test_pv_calculation.py::test_pv_performance`                                  | Load test with 1000 concurrent PV calculation requests, 95th percentile latency <100ms, average latency <50ms                                                                                                                               |
| Database FK constraint prevents orphaned baselines                                                                                                                        | T-010   | `backend/tests/integration/test_constraints.py::test_fk_constraint_prevents_orphans`                     | Attempting to insert schedule_baseline with invalid schedule_baseline_id violates FK constraint, attempting to delete cost_element with baseline without cascade fails                                                                  |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests
│   ├── ScheduleBaselineService methods
│   │   ├── get_for_cost_element() - returns baseline or None
│   │   ├── ensure_exists() - creates if missing
│   │   ├── create_for_cost_element() - validation, duplicate prevention
│   │   └── Edge cases (no baseline, deleted cost element, wrong branch)
│   ├── CostElementService methods
│   │   ├── create_root() - auto-creates baseline
│   │   ├── soft_delete() - cascades to baseline
│   │   └── Error handling (baseline creation failure)
│   └── Model validation
│       └── FK constraint, nullable field, relationship definition
├── Integration Tests
│   ├── API endpoints
│   │   ├── GET /cost-elements/{id}/schedule-baseline
│   │   ├── PUT /cost-elements/{id}/schedule-baseline
│   │   └── DELETE /cost-elements/{id}/schedule-baseline
│   ├── Branch isolation
│   │   ├── Main branch vs change order branch
│   │   ├── Merge behavior
│   │   └── Cascade delete per branch
│   ├── PV calculation
│   │   ├── Uses correct baseline from cost element
│   │   ├── Handles missing baseline error
│   │   └── Branch context respects selected branch
│   └── Migration integrity
│       ├── All cost elements have baseline
│       ├── No orphaned baselines
│       └── Historical baselines archived
└── E2E Tests
    ├── Cost element creation flow
    │   ├── Create cost element → baseline auto-created
    │   ├── Verify baseline in UI
    │   └── Update baseline via UI
    ├── Change order workflow
    │   ├── Create branch → modify schedule
    │   ├── Compare branches (schedule diff)
    │   └── Merge branch → schedule updated
    └── PV calculation in UI
        ├── View PV for cost element
        ├── Verify uses correct baseline
        └── Switch branches → PV updates
```

### Test Cases (first 5)

| Test ID | Test Name                                                                      | Criterion | Type    | Expected Result                                                                                                                                                                                                                              |
| ------- | ------------------------------------------------------------------------------ | --------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-001   | `test_schedule_baseline_get_for_cost_element_returns_baseline`                  | AC-1      | Unit    | Given cost element with schedule_baseline_id, when get_for_cost_element() called, returns ScheduleBaseline with matching ID, branch filters correctly                                                                                       |
| T-002   | `test_schedule_baseline_get_for_cost_element_returns_none_when_missing`         | AC-1      | Unit    | Given cost element with schedule_baseline_id=NULL, when get_for_cost_element() called, returns None                                                                                                                                          |
| T-003   | `test_cost_element_create_auto_creates_default_schedule_baseline`               | AC-2      | Unit    | Given valid CostElementCreate data, when CostElementService.create() called, creates CostElement AND ScheduleBaseline with name="Default Schedule", start_date=today, end_date=today+90days, progression_type="LINEAR", branch="main" |
| T-004   | `test_cost_element_create_baseline_failure_rolls_back_cost_element`             | AC-2      | Unit    | Given schedule_baseline_service.create() raises exception, when CostElementService.create() called, transaction rolls back, no CostElement created, exception propagated                                                                     |
| T-005   | `test_schedule_baseline_create_duplicate_raises_baseline_already_exists_error`  | AC-8      | Unit    | Given cost element with existing schedule_baseline_id, when ScheduleBaselineService.create_for_cost_element() called, raises BaselineAlreadyExistsError with cost_element_id in message                                                      |

### Test Infrastructure Needs

**Fixtures needed:**

- `db_session` - Async database session (from `backend/tests/conftest.py`)
- `test_user` - Authenticated user for API tests (from `backend/tests/conftest.py`)
- `test_cost_element` - Cost element fixture with default values
  ```python
  @pytest.fixture
  async def test_cost_element(db_session, test_user):
      cost_element = CostElement(
          cost_element_id=uuid4(),
          wbe_id=uuid4(),
          cost_element_type_id=uuid4(),
          code="TEST-001",
          name="Test Cost Element",
          budget_amount=Decimal("100000.00"),
          created_by=test_user.user_id,
          branch="main"
      )
      db_session.add(cost_element)
      await db_session.commit()
      await db_session.refresh(cost_element)
      return cost_element
  ```
- `test_schedule_baseline` - Schedule baseline fixture linked to cost element
- `test_branch` - Change order branch fixture (for isolation tests)

**Mocks/stubs:**

- `schedule_baseline_service` - Mock for testing CostElementService auto-creation
  ```python
  @pytest.fixture
  def mock_schedule_baseline_service():
      with patch('app.services.cost_element_service.ScheduleBaselineService') as mock:
          yield mock
  ```
- Time-dependent logic - Freeze time for temporal tests using `freezegun`

**Database state:**

- Seed data for migration tests:
  - 10 cost elements with multiple baselines (test duplicate selection)
  - 5 cost elements with no baselines (test auto-creation)
  - 3 cost elements in change order branches (test isolation)
- Clean state for each test (use transaction rollback)

---

## Risk Assessment

| Risk Type   | Description                                                                                     | Probability | Impact   | Mitigation                                                                                                                                                                                                                                                                  |
| ----------- | ----------------------------------------------------------------------------------------------- | ----------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Technical   | Migration failure due to existing duplicate baselines                                           | Medium      | High     | **Pre-migration analysis**: Run script to identify all cost elements with multiple baselines before migration. **Staged migration**: Migrate in batches (development → staging → production). **Backup**: Full database backup before migration. |
| Technical   | Foreign key constraint violates existing data                                                   | Medium      | High     | **Data validation**: Run validation script to check for orphaned baselines. **Nullable transition**: Make FK nullable initially, set values, then add constraint. **Rollback plan**: Immediate rollback script available.                    |
| Integration | Frontend breaks due to API endpoint changes                                                     | High        | Medium   | **Deprecation headers**: Return 410 Gone with new endpoint URLs from old endpoints. **Feature flags**: Gradual rollout using feature flags. **Monitoring**: Track 404/410 errors during rollout.                                            |
| Integration | PV calculation failures due to missing baselines                                                | Medium      | High     | **Graceful degradation**: Return 0 with warning if baseline missing. **Data validation**: Script to ensure all cost elements have baselines before deploying PV calculation changes. **Error handling**: Clear error messages for users.    |
| Performance | PV calculation slower due to additional join via cost element                                    | Low         | Medium   | **Indexing**: Ensure schedule_baseline_id is indexed. **Query optimization**: Use JOIN instead of separate queries. **Load testing**: Verify <100ms target before deployment.                                                              |
| Data        | Historical baseline data lost during migration                                                   | Low         | High     | **Archive table**: Create `schedule_baselines_archive` table before migration. **Backup**: Export all schedule baseline data to CSV. **Verification**: Compare record counts before/after.                                                |
| Business    | User confusion due to API changes (can't create independent baselines anymore)                  | Medium      | Medium   | **Documentation**: Update API docs with clear examples. **Release notes**: Explain rationale and new workflow. **Support**: Train support team on new pattern.                                                                           |
| Business    | Change order workflow breaks (branches can't modify schedule independently)                       | Low         | High     | **Testing**: Comprehensive E2E tests for branch isolation. **Validation**: Verify merging preserves schedule changes. **Documentation**: Clear guide on schedule management in branches.                                                   |

---

## Prerequisites & Dependencies

### Technical Prerequisites

- [ ] PostgreSQL 15+ database with existing `schedule_baselines` and `cost_elements` tables
- [ ] Python 3.12+ environment with `uv` package manager
- [ ] All existing migrations applied (verified via `alembic current`)
- [ ] Database backup completed before migration (automated script)
- [ ] Test database configured for migration testing
- [ ] CI/CD pipeline access for automated quality checks
- [ ] Staging environment for pre-production testing

### Documentation Prerequisites

- [x] Analysis phase approved (00-analysis.md)
- [ ] ADR-005: Bitemporal Versioning Pattern reviewed
- [ ] Bounded Contexts documentation reviewed (Context 6: Cost Element & Financial Tracking)
- [ ] EVCS Core documentation reviewed (branching, versioning commands)
- [ ] Functional Requirements - Section 6.1.1 (Cost Element Schedule Baseline) reviewed
- [ ] Functional Requirements - Section 12.2 (EVM Calculations) reviewed

### External Dependencies

- **Backend Dependencies**:
  - `alembic` for database migrations
  - `sqlalchemy[asyncio]` for async database operations
  - `asyncpg` for PostgreSQL async driver
  - `pytest-asyncio` for async test support
  - `freezegun` for time-based test mocking
- **Frontend Dependencies**:
  - `@tanstack/react-query` for API state management
  - `axios` for HTTP client
  - TypeScript types from OpenAPI spec
- **Infrastructure**:
  - Database connection string (from `app.core.config`)
  - Test database credentials
  - Migration backup storage location

### Skill Requirements

- **Backend Developer**: Python/AsyncIO, SQLAlchemy, Alembic, PostgreSQL
- **Frontend Developer**: React, TypeScript, TanStack Query
- **QA Engineer**: pytest, E2E testing (Playwright)
- **DevOps Engineer**: Database backup/restore, CI/CD pipelines

---

## Documentation References

### Required Reading

- **Coding Standards**: `/home/nicola/dev/backcast_evs/docs/00-meta/coding_standards.md`
- **ADR-005: Bitemporal Versioning Pattern**: `/home/nicola/dev/backcast_evs/docs/02-architecture/decisions/ADR-005-bitemporal-versioning.md`
- **Bounded Contexts**: `/home/nicola/dev/backcast_evs/docs/02-architecture/01-bounded-contexts.md` (Context 6: Cost Element & Financial Tracking)
- **Functional Requirements - Section 6.1.1**: `/home/nicola/dev/backcast_evs/docs/01-functional-requirements/functional-requirements.md#611-cost-element-schedule-baseline`
- **Functional Requirements - Section 12.2**: `/home/nicola/dev/backcast_evs/docs/01-functional-requirements/functional-requirements.md#122-core-evm-metrics`

### Code References

- **Backend Pattern - BranchableService**: `/home/nicola/dev/backcast_evs/backend/app/core/branching/service.py`
- **Backend Pattern - CostElementService**: `/home/nicola/dev/backcast_evs/backend/app/services/cost_element_service.py`
- **Backend Pattern - ScheduleBaselineService (current)**: `/home/nicola/dev/backcast_evs/backend/app/services/schedule_baseline_service.py`
- **Test Pattern - Conftest fixtures**: `/home/nicola/dev/backcast_evs/backend/tests/conftest.py`
- **Test Pattern - Example integration test**: `/home/nicola/dev/backcast_evs/backend/tests/api/test_cost_elements.py`
- **Migration Pattern - Example migration**: `/home/nicola/dev/backcast_evs/backend/alembic/versions/f1a2b3c4d5e6_add_schedule_baselines_table.py`

### API References

- **Current Schedule Baseline API**: `/home/nicola/dev/backcast_evs/backend/app/api/routes/schedule_baselines.py`
- **Cost Element API**: `/home/nicola/dev/backcast_evs/backend/app/api/routes/cost_elements.py`
- **OpenAPI Spec**: `http://localhost:8000/docs` (when running locally)

---

## Rollout Plan

### Phase 1: Preparation (Days 1-2)

1. **Pre-migration Analysis**:
   - Run script to identify cost elements with multiple baselines
   - Document current state (count of duplicates, orphans)
   - Create database backup

2. **Environment Setup**:
   - Create feature branch `feature/schedule-baseline-1to1`
   - Set up staging database for testing
   - Configure CI/CD for feature branch

### Phase 2: Backend Implementation (Days 3-7)

1. **Database Migration** (Day 3):
   - Implement migration script (Tasks 1-3)
   - Test migration on development database
   - Verify data integrity with verification script

2. **Service Layer** (Days 4-5):
   - Implement service changes (Tasks 4-9)
   - Write unit tests (Tasks 19-20)
   - Verify all tests pass

3. **API Layer** (Days 6-7):
   - Implement new endpoints (Tasks 10-16)
   - Write integration tests (Tasks 21-22)
   - Update API documentation (Task 26)

### Phase 3: Frontend Implementation (Days 8-10)

1. **API Client Update** (Day 8):
   - Update frontend API client (Task 24)
   - Regenerate TypeScript types from OpenAPI spec

2. **Component Updates** (Days 9-10):
   - Update schedule baseline components (Task 25)
   - Write E2E tests (Task 23)

### Phase 4: Testing & Quality Assurance (Days 11-12)

1. **Full Quality Check** (Day 11):
   - Run MyPy strict mode (Task 28)
   - Run Ruff linting (Task 28)
   - Verify test coverage >=80% (Task 28)

2. **Staging Deployment** (Day 12):
   - Deploy to staging environment
   - Run E2E tests against staging
   - Performance testing (PV calculation <100ms)

### Phase 5: Production Rollout (Days 13-14)

1. **Production Migration** (Day 13):
   - Schedule maintenance window
   - Create final production backup
   - Run migration script
   - Verify data integrity
   - Deploy backend code

2. **Frontend Deployment** (Day 14):
   - Deploy frontend changes
   - Monitor for errors (404/410 responses)
   - Verify PV calculations working correctly

3. **Post-Deployment** (Day 14+):
   - Monitor application logs for errors
   - Track PV calculation performance
   - Gather user feedback
   - Create rollback plan if issues detected

### Rollback Strategy

**If migration fails**:
1. Stop deployment immediately
2. Run downgrade migration script (Task 18)
3. Restore database from backup
4. Revert code deployment
5. Investigate failure root cause

**If frontend breaks**:
1. Revert frontend deployment
2. Keep backend with deprecated endpoints (still functional)
3. Fix frontend issues
8. Retry deployment

**If performance degrades**:
1. Monitor query performance
2. Add missing indexes if needed
3. Optimize queries
4. Consider caching for PV calculations

---

## Success Metrics

### Technical Metrics

- **Database Migration**: 100% success rate, zero data loss
- **Code Quality**: MyPy strict mode (0 errors), Ruff (0 errors)
- **Test Coverage**: >=80% for new/modified code
- **Performance**: PV calculation <100ms (95th percentile)
- **Integration**: All E2E tests passing

### Business Metrics

- **User Adoption**: Zero support tickets related to baseline confusion
- **Data Integrity**: All cost elements have exactly one baseline
- **Workflow Efficiency**: Time to create cost element with baseline reduced by 50%

### Risk Mitigation Metrics

- **Rollback Readiness**: Rollback script tested and verified
- **Monitoring**: Error rate <0.1% for new endpoints
- **Documentation**: 100% of new endpoints documented

---

## Next Steps

Upon approval of this PLAN:

1. **Create feature branch**: `git checkout -b feature/schedule-baseline-1to1`
2. **Start implementation**: Begin with Task 1 (database migration)
3. **Track progress**: Update task status in this document as tasks complete
4. **DO phase**: Execute implementation following TDD (RED-GREEN-REFACTOR)
5. **CHECK phase**: Verify all success criteria met
6. **ACT phase**: Deploy to production and monitor

---

**Document Status**: Ready for DO phase execution
**Last Updated**: 2026-01-18
**Approved By**: [Pending approval]
