# Plan: One Forecast Per Cost Element (Branchable)

**Created:** 2026-01-18
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 - One Forecast Per Cost Element (Branchable)
**Reference Pattern:** Schedule Baseline 1:1 Implementation (2026-01-18)
**Data Strategy:** Fresh start (no migration needed - past data to be wiped)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 - One Forecast Per Cost Element (Branchable)
- **Architecture**: Enforce strict 1:1 relationship between Cost Elements and Forecasts using inverted foreign key, leverage EVCS branching for what-if scenarios
- **Key Decisions**:
  - Add `forecast_id` column to `cost_elements` table (nullable)
  - Remove `cost_element_id` FK from `forecasts` table (inverse relationship)
  - Enforce 1:1 relationship via unique index on `cost_elements.forecast_id`
  - Auto-create forecast when cost element is created
  - Nest forecast management endpoints under cost elements
  - **No data migration needed** - starting fresh with wiped data
  - **Follow exact schedule baseline pattern** (migration: 20260118_080108)

### Success Criteria

**Functional Criteria:**

- [ ] Each cost element has exactly one forecast (enforced at database level) VERIFIED BY: Integration test querying cost elements with multiple forecasts returns zero results
- [ ] Creating a cost element automatically creates a default forecast VERIFIED BY: Unit test verifying forecast exists after cost element creation
- [ ] Updating a cost element's forecast data updates the linked forecast VERIFIED BY: Integration test verifying forecast update via cost element endpoint
- [ ] Soft deleting a cost element cascades to linked forecast VERIFIED BY: Integration test verifying forecast deleted_at is set
- [ ] EAC calculation uses the single forecast from cost element VERIFIED BY: E2E test calculating EAC returns correct value
- [ ] Change order branches can modify forecast independently VERIFIED BY: Integration test verifying branch isolation
- [ ] Attempting to create duplicate forecast raises validation error VERIFIED BY: Unit test verifying exception raised

**Technical Criteria:**

- [ ] Performance: EAC calculation completes in <100ms VERIFIED BY: Load test with 1000 concurrent requests
- [ ] Database: Unique index constraint prevents duplicate forecasts VERIFIED BY: Database constraint test
- [ ] Code Quality: MyPy strict mode (zero errors) VERIFIED BY: CI pipeline
- [ ] Code Quality: Ruff linting (zero errors) VERIFIED BY: CI pipeline
- [ ] Test Coverage: >=80% for new/modified code VERIFIED BY: Coverage report

**Business Criteria:**

- [ ] EVM calculations are unambiguous - always use the one forecast VERIFIED BY: User acceptance testing
- [ ] What-if scenario analysis supported via branching VERIFIED BY: User acceptance testing
- [ ] Clear audit trail of forecast changes VERIFIED BY: History retrieval test

### Scope Boundaries

**In Scope:**

- Database schema changes (add forecast_id column, remove cost_element_id FK, unique index)
- Backend service layer modifications (validation, CRUD operations)
- API endpoint restructuring (nest under cost elements)
- Frontend component updates for new API structure
- Unit, integration, and E2E tests
- Documentation updates (API docs, architecture docs)

**Out of Scope:**

- Data migration (not needed - past data to be wiped)
- Changes to EVM calculation algorithms (EAC, VAC, ETC formulas)
- Changes to other cost element fields or relationships
- Frontend redesign (only API integration changes)
- Performance optimization beyond EAC calculation requirement
- Historical forecast comparison UI (deferred to future iteration)
- Forecast templates (deferred to future iteration)

---

## Work Decomposition

### Task Breakdown

| #   | Task                                                                                                                                                                | Files                                                                                                                                                 | Dependencies        | Success Criteria                                                                                                                                                            | Complexity |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| 1   | Create database migration for 1:1 relationship (no data migration)                                                                                                    | `backend/alembic/versions/YYYYMMDD_forecast_1to1.py`                                                                                                  | None                | Migration applies successfully, forecast_id column added, cost_element_id FK removed, unique index created                                                                  | Medium    |
| 2   | Update CostElement model to include forecast_id column                                                                                                               | `backend/app/models/domain/cost_element.py`                                                                                                           | Task 1              | Model compiles, forecast_id column defined with nullable=True, index=True                                                                                                  | Low        |
| 3   | Remove cost_element_id FK from Forecast model                                                                                                                        | `backend/app/models/domain/forecast.py`                                                                                                               | Task 1              | Model compiles, cost_element_id FK removed, model still branchable/versionable                                                                                              | Low        |
| 4   | Add ForecastAlreadyExistsError exception                                                                                                                             | `backend/app/services/forecast_service.py` (or new exceptions file)                                                                                   | None                | Exception class defined with proper error message                                                                                                                          | Low        |
| 5   | Add get_for_cost_element() method to ForecastService                                                                                                                 | `backend/app/services/forecast_service.py`                                                                                                            | Task 2, Task 3      | Method returns single forecast or None, query uses cost_element.forecast_id                                                                                                | Medium     |
| 6   | Add validation to prevent duplicate forecasts in ForecastService.create()                                                                                           | `backend/app/services/forecast_service.py`                                                                                                            | Task 5              | Attempting to create second forecast for same cost element raises ForecastAlreadyExistsError                                                                               | Medium     |
| 7   | Add ensure_exists() method to ForecastService for auto-creation                                                                                                      | `backend/app/services/forecast_service.py`                                                                                                            | Task 5              | Method creates forecast if none exists, returns existing forecast if present                                                                                               | Medium     |
| 8   | Modify CostElementService.create_root() to auto-create default forecast                                                                                              | `backend/app/services/cost_element_service.py`                                                                                                        | Task 7              | Creating cost element results in forecast with default values (eac_amount=budget_amount, basis="Initial forecast")                                                         | Medium     |
| 9   | Modify CostElementService.soft_delete() to cascade delete to forecast                                                                                                | `backend/app/services/cost_element_service.py`                                                                                                        | Task 2, Task 3      | Soft deleting cost element sets deleted_at on linked forecast                                                                                                               | Medium     |
| 10  | Update ForecastCreate schema (remove cost_element_id field)                                                                                                          | `backend/app/models/schemas/forecast.py`                                                                                                              | Task 3              | Schema compiles, cost_element_id field removed                                                                                                                             | Low        |
| 11  | Update ForecastRead schema to include cost element data                                                                                                              | `backend/app/models/schemas/forecast.py`                                                                                                              | None                | Schema includes cost_element details (code, name, budget_amount)                                                                                                           | Low        |
| 12  | Add GET /api/v1/cost-elements/{id}/forecast endpoint                                                                                                                 | `backend/app/api/routes/cost_elements.py` (new route)                                                                                                 | Task 5              | Endpoint returns forecast for cost element, 404 if none exists                                                                                                             | Medium     |
| 13  | Add PUT /api/v1/cost-elements/{id}/forecast endpoint                                                                                                                 | `backend/app/api/routes/cost_elements.py` (new route)                                                                                                 | Task 5              | Endpoint creates or updates forecast for cost element                                                                                                                      | Medium     |
| 14  | Add DELETE /api/v1/cost-elements/{id}/forecast endpoint                                                                                                              | `backend/app/api/routes/cost_elements.py` (new route)                                                                                                 | Task 9              | Endpoint soft deletes forecast, requires confirmation                                                                                                                       | Medium     |
| 15  | Deprecate old forecast CRUD endpoints (POST /forecasts, etc.)                                                                                                        | `backend/app/api/routes/forecasts.py` (add deprecation notices)                                                                                      | Task 12, 13, 14     | Old endpoints return 410 Gone deprecation notice pointing to new endpoints                                                                                                 | Low        |
| 16  | Update EVM calculations to use cost element's forecast                                                                                                              | `backend/app/services/evm_service.py` (or wherever EAC is calculated)                                                                                | Task 5              | EAC calculation queries forecast via cost element, raises clear error if missing                                                                                            | Medium     |
| 17  | Unit tests for ForecastService methods (get_for_cost_element, ensure_exists, validation)                                                                             | `backend/tests/unit/services/test_forecast_service.py` (new or update)                                                                               | Task 5, 6, 7        | Tests cover happy path, edge cases (no forecast, duplicate attempt), error handling, 100% coverage of new methods                                                          | Medium     |
| 18  | Unit tests for CostElementService auto-creation and cascade delete                                                                                                   | `backend/tests/unit/services/test_cost_element_service.py` (update)                                                                                  | Task 8, 9           | Tests verify forecast created with cost element, cascade delete on soft delete, mock forecast_service                                                                      | Medium     |
| 19  | Integration tests for new API endpoints (GET/PUT/DELETE cost-elements/{id}/forecast)                                                                                  | `backend/tests/api/test_cost_elements_forecast.py` (new file)                                                                                        | Task 12, 13, 14     | Tests verify endpoint responses, validation, branch isolation, error handling, 80%+ coverage                                                                               | Medium     |
| 20  | Integration test for EVM calculations using cost element's forecast                                                                                                  | `backend/tests/api/test_evm_metrics.py` (update or new)                                                                                              | Task 16             | Test verifies EAC calculation returns correct value, uses forecast from cost element, handles missing forecast error                                                       | Medium     |
| 21  | E2E test for cost element creation with auto-created forecast                                                                                                        | `frontend/e2e/cost-element-forecast.spec.ts` (new or update)                                                                                         | Task 12, 13, 14     | Test creates cost element via UI, verifies forecast exists, updates forecast, verifies cascade delete                                                                       | High       |
| 22  | Update frontend API client to use new endpoints                                                                                                                      | `frontend/src/api/client.ts` (update)                                                                                                                | Task 12, 13, 14     | Client methods updated to call new endpoints, TypeScript types updated                                                                                                     | Low        |
| 23  | Update frontend forecast components to use new API structure                                                                                                         | `frontend/src/features/cost-elements/components/ForecastTab.tsx` (update or new)                                                                     | Task 22             | Component renders forecast from cost element endpoint, handles updates/deletes, displays errors                                                                             | Medium     |
| 24  | Update API documentation (OpenAPI spec, endpoint docs)                                                                                                               | `docs/api/forecasts.md` (update)                                                                                                                     | Task 12, 13, 14     | Documentation reflects new endpoint structure, deprecation notices included, examples provided                                                                              | Low        |
| 25  | Update architecture documentation to reflect 1:1 relationship                                                                                                        | `docs/02-architecture/01-bounded-contexts.md` (update)                                                                                               | Task 1              | Documentation describes new relationship, rationale                                                                                                                        | Low        |
| 26  | Run full quality check (MyPy, Ruff, test coverage)                                                                                                                   | CI pipeline                                                                                                                                           | All tasks           | MyPy strict mode: 0 errors, Ruff: 0 errors, Test coverage: >=80%                                                                                                           | Medium     |

**Task Ordering Principles:**

1. **Database/Models First**: Tasks 1-3 establish the schema foundation
2. **Service Layer**: Tasks 4-9 implement business logic and validation
3. **API Layer**: Tasks 10-16 expose functionality via endpoints
4. **Testing**: Tasks 17-21 verify functionality at all levels
5. **Frontend**: Tasks 22-23 integrate with new API structure
6. **Documentation**: Tasks 24-25 keep docs in sync
7. **Quality Gate**: Task 26 ensures all standards met

### Test-to-Requirement Traceability

| Acceptance Criterion                                                                                                                                                      | Test ID | Test File                                                                          | Expected Behavior                                                                                                                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Each cost element has exactly one forecast (enforced at database level)                                                                                                   | T-F-001 | `backend/tests/api/test_cost_elements_forecast.py::test_duplicate_forecast_fails`                    | Attempting to create second forecast for cost element via API raises 400 Bad Request with ForecastAlreadyExistsError message                                                                                                                |
| Creating a cost element automatically creates a default forecast                                                                                                          | T-F-002 | `backend/tests/unit/services/test_cost_element_service.py::test_create_auto_creates_forecast`              | Creating cost element via service creates forecast with eac_amount=budget_amount, basis="Initial forecast", cost_element_id matches                                                                                              |
| Updating a cost element's forecast data updates the linked forecast                                                                                                       | T-F-003 | `backend/tests/api/test_cost_elements_forecast.py::test_update_forecast_via_cost_element`               | PUT to /cost-elements/{id}/forecast updates forecast fields (eac_amount, basis_of_estimate), returns updated ForecastRead                                                                                       |
| Soft deleting a cost element cascades to linked forecast                                                                                                                  | T-F-004 | `backend/tests/api/test_cost_elements_forecast.py::test_delete_cost_element_cascades_to_forecast`        | DELETE to /cost-elements/{id} sets deleted_at on cost element AND linked forecast, querying forecast afterwards returns 404                                                                                                      |
| EAC calculation uses the single forecast from cost element                                                                                                                | T-F-005 | `backend/tests/api/test_evm_metrics.py::test_eac_uses_cost_element_forecast`                            | EAC calculation endpoint queries cost element's forecast_id, returns forecast.eac_amount, raises clear error if missing                                                                                           |
| Change order branches can modify forecast independently                                                                                                                   | T-F-006 | `backend/tests/api/test_cost_elements_forecast.py::test_branch_isolation`                             | Creating forecast in change order branch doesn't affect main branch, EAC calculation uses forecast from selected branch, merging branch updates main forecast                                                                             |
| Attempting to create duplicate forecast raises validation error                                                                                                          | T-F-007 | `backend/tests/unit/services/test_forecast_service.py::test_create_duplicate_raises_error`               | ForecastService.create_for_cost_element() raises ForecastAlreadyExistsError when forecast already exists for cost element in specified branch                                                                                      |
| EAC calculation completes in <100ms                                                                                                                                        | T-F-008 | `backend/tests/performance/test_eac_calculation.py::test_eac_performance`                              | Load test with 1000 concurrent EAC calculation requests, 95th percentile latency <100ms, average latency <50ms                                                                                                                               |
| Database unique index prevents duplicate forecasts                                                                                                                         | T-F-009 | `backend/tests/integration/test_constraints.py::test_unique_index_prevents_duplicates`                   | Attempting to set forecast_id on cost element when another cost element has that value violates unique index constraint                                                                                                                                  |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests
│   ├── ForecastService methods
│   │   ├── get_for_cost_element() - returns forecast or None
│   │   ├── ensure_exists() - creates if missing
│   │   ├── create_for_cost_element() - validation, duplicate prevention
│   │   └── Edge cases (no forecast, deleted cost element, wrong branch)
│   ├── CostElementService methods
│   │   ├── create_root() - auto-creates forecast
│   │   ├── soft_delete() - cascades to forecast
│   │   └── Error handling (forecast creation failure)
│   └── Model validation
│       └── forecast_id field, nullable, index, relationship
├── Integration Tests
│   ├── API endpoints
│   │   ├── GET /cost-elements/{id}/forecast
│   │   ├── PUT /cost-elements/{id}/forecast
│   │   └── DELETE /cost-elements/{id}/forecast
│   ├── Branch isolation
│   │   ├── Main branch vs change order branch
│   │   ├── Merge behavior
│   │   └── Cascade delete per branch
│   ├── EVM calculations
│   │   ├── Uses correct forecast from cost element
│   │   ├── Handles missing forecast error
│   │   └── Branch context respects selected branch
│   └── Database constraints
│       ├── Unique index enforcement
│       └── Referential integrity
└── E2E Tests
    ├── Cost element creation flow
    │   ├── Create cost element → forecast auto-created
    │   ├── Verify forecast in UI
    │   └── Update forecast via UI
    ├── Change order workflow
    │   ├── Create branch → modify forecast
    │   ├── Compare branches (forecast diff)
    │   └── Merge branch → forecast updated
    └── EVM calculations in UI
        ├── View EAC for cost element
        ├── Verify uses correct forecast
        └── Switch branches → EAC updates
```

### Test Cases (first 5)

| Test ID | Test Name                                                                      | Criterion | Type    | Expected Result                                                                                                                                                                                                                              |
| ------- | ------------------------------------------------------------------------------ | --------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-F-001 | `test_forecast_get_for_cost_element_returns_forecast`                          | AC-1      | Unit    | Given cost element with forecast_id, when get_for_cost_element() called, returns Forecast with matching ID, branch filters correctly                                                                                       |
| T-F-002 | `test_forecast_get_for_cost_element_returns_none_when_missing`                 | AC-1      | Unit    | Given cost element with forecast_id=NULL, when get_for_cost_element() called, returns None                                                                                                                                          |
| T-F-003 | `test_cost_element_create_auto_creates_default_forecast`                       | AC-2      | Unit    | Given valid CostElementCreate data, when CostElementService.create() called, creates CostElement AND Forecast with eac_amount=budget_amount, basis="Initial forecast", branch="main" |
| T-F-004 | `test_cost_element_create_forecast_failure_rolls_back_cost_element`            | AC-2      | Unit    | Given forecast_service.create() raises exception, when CostElementService.create() called, transaction rolls back, no CostElement created, exception propagated                                                                     |
| T-F-005 | `test_forecast_create_duplicate_raises_forecast_already_exists_error`          | AC-7      | Unit    | Given cost element with existing forecast_id, when ForecastService.create_for_cost_element() called, raises ForecastAlreadyExistsError with cost_element_id in message                                                      |

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
- `test_forecast` - Forecast fixture linked to cost element
- `test_branch` - Change order branch fixture (for isolation tests)

**Mocks/stubs:**

- `forecast_service` - Mock for testing CostElementService auto-creation
  ```python
  @pytest.fixture
  def mock_forecast_service():
      with patch('app.services.cost_element_service.ForecastService') as mock:
          yield mock
  ```
- Time-dependent logic - Freeze time for temporal tests using `freezegun`

**Database state:**

- Clean state for each test (use transaction rollback)
- Seed data for branch isolation tests (cost elements in multiple branches)

---

## Risk Assessment

| Risk Type   | Description                                                                                     | Probability | Impact   | Mitigation                                                                                                                                                                                                                                                                  |
| ----------- | ----------------------------------------------------------------------------------------------- | ----------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Technical   | Database schema changes break existing queries                                                   | Low         | High     | **Comprehensive testing**: Run full test suite after schema changes. **Staged rollout**: Deploy to development → staging → production. **Rollback plan**: Downgrade migration script available.                                   |
| Integration | Frontend breaks due to API endpoint changes                                                     | High        | Medium   | **Deprecation headers**: Return 410 Gone with new endpoint URLs from old endpoints. **Feature flags**: Gradual rollout using feature flags. **Monitoring**: Track 404/410 errors during rollout.                                            |
| Integration | EVM calculation failures due to missing forecasts                                                | Medium      | High     | **Auto-creation**: Cost elements always auto-create forecasts. **Error handling**: Clear error messages when forecast missing. **Data validation**: Ensure all cost elements have forecasts before EVM deployment.    |
| Performance | EAC calculation slower due to additional join via cost element                                    | Low         | Medium   | **Indexing**: Ensure forecast_id is indexed. **Query optimization**: Use JOIN instead of separate queries. **Load testing**: Verify <100ms target before deployment.                                                              |
| Business    | User confusion due to API changes (can't create independent forecasts anymore)                  | Medium      | Medium   | **Documentation**: Update API docs with clear examples. **Release notes**: Explain rationale and new workflow. **Support**: Train support team on new pattern.                                                                           |
| Business    | Change order workflow breaks (branches can't modify forecast independently)                       | Low         | High     | **Testing**: Comprehensive E2E tests for branch isolation. **Validation**: Verify merging preserves forecast changes. **Documentation**: Clear guide on forecast management in branches.                                                   |

---

## Prerequisites & Dependencies

### Technical Prerequisites

- [x] Schedule baseline 1:1 migration completed (reference pattern available)
- [x] Past data to be wiped (no migration needed)
- [ ] PostgreSQL 15+ database
- [ ] Python 3.12+ environment with `uv` package manager
- [ ] All existing migrations applied (verified via `alembic current`)
- [ ] Test database configured
- [ ] CI/CD pipeline access for automated quality checks
- [ ] Staging environment for pre-production testing

### Documentation Prerequisites

- [x] Analysis phase approved (00-analysis.md)
- [x] Schedule baseline migration reviewed (20260118_080108)
- [ ] ADR-005: Bitemporal Versioning Pattern reviewed
- [ ] Bounded Contexts documentation reviewed (Context 6: Cost Element & Financial Tracking)
- [ ] EVCS Core documentation reviewed (branching, versioning commands)
- [ ] Functional Requirements - EVM Calculations reviewed

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

### Skill Requirements

- **Backend Developer**: Python/AsyncIO, SQLAlchemy, Alembic, PostgreSQL
- **Frontend Developer**: React, TypeScript, TanStack Query
- **QA Engineer**: pytest, E2E testing (Playwright)
- **DevOps Engineer**: CI/CD pipelines

---

## Documentation References

### Required Reading

- **Coding Standards**: `/home/nicola/dev/backcast_evs/docs/00-meta/coding_standards.md`
- **ADR-005: Bitemporal Versioning Pattern**: `/home/nicola/dev/backcast_evs/docs/02-architecture/decisions/ADR-005-bitemporal-versioning.md`
- **Bounded Contexts**: `/home/nicola/dev/backcast_evs/docs/02-architecture/01-bounded-contexts.md` (Context 6: Cost Element & Financial Tracking)
- **Schedule Baseline Analysis**: `/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-18-schedule-baseline-architecture/00-analysis.md`
- **Schedule Baseline Plan**: `/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-18-schedule-baseline-architecture/01-plan.md`

### Code References

- **Backend Pattern - BranchableService**: `/home/nicola/dev/backcast_evs/backend/app/core/branching/service.py`
- **Backend Pattern - CostElementService**: `/home/nicola/dev/backcast_evs/backend/app/services/cost_element_service.py`
- **Backend Pattern - ForecastService (current)**: `/home/nicola/dev/backcast_evs/backend/app/services/forecast_service.py`
- **Reference Migration - Schedule Baseline 1:1**: `/home/nicola/dev/backcast_evs/backend/alembic/versions/20260118_080108_schedule_baseline_1to1.py`
- **Test Pattern - Conftest fixtures**: `/home/nicola/dev/backcast_evs/backend/tests/conftest.py`
- **Test Pattern - Example integration test**: `/home/nicola/dev/backcast_evs/backend/tests/api/test_cost_elements.py`

### API References

- **Current Forecast API**: `/home/nicola/dev/backcast_evs/backend/app/api/routes/forecasts.py`
- **Cost Element API**: `/home/nicola/dev/backcast_evs/backend/app/api/routes/cost_elements.py`
- **OpenAPI Spec**: `http://localhost:8000/docs` (when running locally)

---

## Rollout Plan

### Phase 1: Preparation (Days 1-2)

1. **Environment Setup**:
   - Create feature branch `feature/forecast-1to1`
   - Set up staging database for testing
   - Configure CI/CD for feature branch
   - Review schedule baseline migration for reference

### Phase 2: Backend Implementation (Days 3-7)

1. **Database Migration** (Day 3):
   - Implement migration script (Tasks 1-3)
   - Test migration on development database
   - Verify schema changes

2. **Service Layer** (Days 4-5):
   - Implement service changes (Tasks 4-9)
   - Write unit tests (Tasks 17-18)
   - Verify all tests pass

3. **API Layer** (Days 6-7):
   - Implement new endpoints (Tasks 10-16)
   - Write integration tests (Tasks 19-20)
   - Update API documentation (Task 24)

### Phase 3: Frontend Implementation (Days 8-10)

1. **API Client Update** (Day 8):
   - Update frontend API client (Task 22)
   - Regenerate TypeScript types from OpenAPI spec

2. **Component Updates** (Days 9-10):
   - Update forecast components (Task 23)
   - Write E2E tests (Task 21)

### Phase 4: Testing & Quality Assurance (Days 11-12)

1. **Full Quality Check** (Day 11):
   - Run MyPy strict mode (Task 26)
   - Run Ruff linting (Task 26)
   - Verify test coverage >=80% (Task 26)

2. **Staging Deployment** (Day 12):
   - Deploy to staging environment
   - Run E2E tests against staging
   - Performance testing (EAC calculation <100ms)

### Phase 5: Production Rollout (Days 13-14)

1. **Production Deployment** (Day 13):
   - Deploy backend code during low-traffic period
   - Run migration script
   - Verify schema changes

2. **Frontend Deployment** (Day 14):
   - Deploy frontend changes
   - Monitor for errors (404/410 responses)
   - Verify EVM calculations working correctly

3. **Post-Deployment** (Day 14+):
   - Monitor application logs for errors
   - Track EAC calculation performance
   - Gather user feedback

### Rollback Strategy

**If deployment fails**:
1. Stop deployment immediately
2. Run downgrade migration script
3. Revert code deployment
4. Investigate failure root cause

**If frontend breaks**:
1. Revert frontend deployment
2. Keep backend with deprecated endpoints (still functional)
3. Fix frontend issues
4. Retry deployment

**If performance degrades**:
1. Monitor query performance
2. Add missing indexes if needed
3. Optimize queries
4. Consider caching for EAC calculations

---

## Success Metrics

### Technical Metrics

- **Database Migration**: 100% success rate
- **Code Quality**: MyPy strict mode (0 errors), Ruff (0 errors)
- **Test Coverage**: >=80% for new/modified code
- **Performance**: EAC calculation <100ms (95th percentile)
- **Integration**: All E2E tests passing

### Business Metrics

- **User Adoption**: Zero support tickets related to forecast confusion
- **Data Integrity**: All cost elements have exactly one forecast
- **Workflow Efficiency**: Time to create cost element with forecast reduced by 50%

### Risk Mitigation Metrics

- **Rollback Readiness**: Rollback script tested and verified
- **Monitoring**: Error rate <0.1% for new endpoints
- **Documentation**: 100% of new endpoints documented

---

## Next Steps

Upon approval of this PLAN:

1. **Create feature branch**: `git checkout -b feature/forecast-1to1`
2. **Start implementation**: Begin with Task 1 (database migration)
3. **Track progress**: Update task status in this document as tasks complete
4. **DO phase**: Execute implementation following TDD (RED-GREEN-REFACTOR)
5. **CHECK phase**: Verify all success criteria met
6. **ACT phase**: Deploy to production and monitor

---

**Document Status**: Ready for DO phase execution
**Last Updated**: 2026-01-18
**Approved By**: [Pending approval]
**Reference Implementation**: Schedule Baseline 1:1 (Migration: 20260118_080108)
**Data Strategy**: Fresh start (no migration - past data to be wiped)
