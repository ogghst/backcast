# Plan: [E05-U01] Register Actual Costs against Cost Elements

**Created:** 2026-01-15
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Versioned CostRegistration (Non-Branchable)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Versioned CostRegistration (Non-Branchable)
- **Architecture**: Cost registrations are versioned facts, global across all branches (not copied to branches)
- **Key Decisions**:
  - Use `VersionableMixin` only (NOT `BranchableMixin`)
  - Extend `TemporalService[CostRegistration]` (NOT `BranchableService`)
  - Costs are queried from main branch only
  - Budgets are branchable - impact analysis compares branch budget vs global actual costs
  - Table partitioning by quarter for high volume (20k/month)
  - Partial indexes for current versions only
  - Cache budget status with 5-minute TTL

### Success Criteria

**Functional Criteria:**

- Cost registration CRUD operations with bitemporal versioning VERIFIED BY: Integration tests
- Budget validation on create/update (warn at 80%, block at 100%+) VERIFIED BY: Unit tests for validation logic
- Time-travel queries (as_of parameter) for historical cost analysis VERIFIED BY: Unit tests
- Change order impact analysis includes cost registrations VERIFIED BY: Integration tests
- Soft delete with reversibility VERIFIED BY: Unit tests

**Technical Criteria:**

- Performance: <100ms for single CREATE, <200ms for paginated list VERIFIED BY: Performance tests
- Data Integrity: Transactional rollback on validation failure VERIFIED BY: Integration tests
- Type Safety: MyPy strict mode (zero errors), Pydantic V2 strict VERIFIED BY: CI quality gates
- Code Quality: Ruff zero errors VERIFIED BY: CI quality gates
- Test Coverage: ≥80% overall, 100% for validation logic VERIFIED BY: `pytest --cov` report

**Business Criteria:**

- Users can track actual costs against budget elements VERIFIED BY: E2E tests
- Budget overspend prevention reduces variance VERIFIED BY: User acceptance testing
- Historical cost tracking supports auditing VERIFIED BY: Time-travel query tests
- Change order impact analysis includes cost impact VERIFIED BY: Impact analysis integration tests

**TDD Criteria:**

- [ ] All tests written **before** implementation code VERIFIED BY: Git commit history (test commits before implementation)
- [ ] Tests validate **all acceptance criteria** VERIFIED BY: Test-to-requirement traceability matrix below
- [ ] Each test **failed first** (RED phase) VERIFIED BY: Do-prompt daily log entries
- [ ] Test coverage ≥80% VERIFIED BY: `pytest --cov=app.services.cost_registration_service --cov-report=term-missing`
- [ ] Tests follow Arrange-Act-Assert pattern VERIFIED BY: Code review against plan examples
- [ ] Fixtures used for shared test setup VERIFIED BY: Reference to [conftest.py](../../../../backend/tests/conftest.py)

### Scope Boundaries

**In Scope:**

- `CostRegistration` domain model (versioned, non-branchable)
- `CostRegistrationService` extending `TemporalService[T]`
- Budget validation logic (threshold: 80% warn, 100% block)
- CRUD API endpoints with time-travel support
- Budget status endpoint (used/remaining/percentage)
- Frontend components for cost registration UI
- Change order impact analysis integration
- Database migration with partitioning strategy

**Out of Scope:**

- Multi-currency support (single currency assumed)
- Cost approval workflow (direct registration only)
- Cost allocation across multiple cost elements
- Automated cost import from external accounting systems
- Forecasting/prediction based on cost trends
- Currency conversion
- Tax calculation
- Invoice attachment/upload (invoice number only)

---

## Work Decomposition

### Task Breakdown (Test-First)

| Task | Description | Files | Dependencies | Success | Est. Complexity |
| ---- | ----------- | ------ | ------------ | -------- | --------------- |
| 1 | Database migration for cost_registrations table | `backend/alembic/versions/xxx_create_cost_registrations.py` | None | Migration applies successfully, table created with indexes | Low |
| 2 | Unit tests for CostRegistration model | `backend/tests/unit/models/test_cost_registration.py` | Task 1 | All model tests pass (versioning fields, relationships) | Low |
| 3 | Implement CostRegistration domain model | `backend/app/models/domain/cost_registration.py` | Tasks 1, 2 | Model tests pass, satisfies VersionableProtocol | Low |
| 4 | Unit tests for CostRegistrationService CRUD | `backend/tests/unit/services/test_cost_registration_service.py` | Task 3 | Service tests pass (create, update, delete, get_by_id) | Medium |
| 5 | Implement CostRegistrationService | `backend/app/services/cost_registration_service.py` | Tasks 3, 4 | Service unit tests pass | Medium |
| 6 | Unit tests for budget validation logic | `backend/tests/unit/services/test_cost_registration_budget_validation.py` | Task 5 | Validation tests pass (thresholds, blocking, edge cases) | Medium |
| 7 | Implement budget validation in service | `backend/app/services/cost_registration_service.py` (extend) | Tasks 5, 6 | Budget validation unit tests pass | Medium |
| 8 | Unit tests for time-travel queries | `backend/tests/unit/services/test_cost_registration_time_travel.py` | Task 5 | Time-travel tests pass (as_of parameter) | Medium |
| 9 | Implement time-travel query methods | `backend/app/services/cost_registration_service.py` (extend) | Tasks 5, 8 | Time-travel query tests pass | Medium |
| 10 | Pydantic schemas for cost registration | `backend/app/models/schemas/cost_registration.py` | Task 3 | Schemas pass Pydantic V2 validation, MyPy strict | Low |
| 11 | API integration tests for cost registrations | `backend/tests/api/test_cost_registrations.py` | Task 10 | API tests pass (CRUD, filtering, pagination) | Medium |
| 12 | Implement cost registrations API routes | `backend/app/api/routes/cost_registrations.py` | Tasks 5, 10, 11 | API integration tests pass | Medium |
| 13 | Unit tests for budget status endpoint | `backend/tests/unit/services/test_budget_status.py` | Task 7 | Budget status tests pass (used/remaining/percentage) | Low |
| 14 | Implement budget status endpoint | `backend/app/api/routes/cost_registrations.py` (extend) | Tasks 7, 13 | Budget status API tests pass | Low |
| 15 | Integration test for impact analysis | `backend/tests/integration/test_impact_analysis_with_costs.py` | Task 5 | Impact analysis includes cost registrations | High |
| 16 | Modify ImpactAnalysisService to include costs | `backend/app/services/impact_analysis_service.py` | Task 15 | Impact analysis integration test passes | High |
| 17 | Performance tests for high volume | `backend/tests/performance/test_cost_registration_performance.py` | Task 12 | Performance targets met (<100ms CRUD) | Medium |
| 18 | Add table partitioning to migration | `backend/alembic/versions/xxx_create_cost_registrations.py` (modify) | Task 17 | Partition tests pass, query performance verified | Medium |
| 19 | Frontend: Cost registration components | `frontend/src/features/cost-registrations/components/*` | Task 12 | Component renders, form validation works | Medium |
| 20 | Frontend: Budget status card component | `frontend/src/features/cost-elements/components/BudgetStatusCard.tsx` | Task 14 | Budget status displays correctly | Medium |
| 21 | E2E tests for cost registration flow | `frontend/tests/e2e/test_cost_registration.spec.ts` | Tasks 19, 20 | E2E tests pass (critical user flows) | High |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| -------------------- | ------- | --------- | ----------------- |
| Cost registration CRUD with bitemporal versioning | T-001, T-002, T-003 | `test_cost_registration_service.py` | Create creates version, update creates new version, delete soft deletes |
| Budget validation (warn at 80%, block at 100%+) | T-004, T-005, T-006, T-007 | `test_cost_registration_budget_validation.py` | Warns at threshold, blocks over budget, handles concurrent updates |
| Time-travel queries (as_of parameter) | T-011, T-012 | `test_cost_registration_time_travel.py` | Returns costs as of specific date, handles future dates |
| Change order impact analysis includes costs | T-013 | `test_impact_analysis_with_costs.py` | Impact report includes actual costs from main branch |
| Soft delete with reversibility | T-003, T-014 | `test_cost_registration_service.py` | Soft delete marks deleted_at, can be undone |
| Performance: <100ms CRUD | T-015 | `test_cost_registration_performance.py` | Single create <100ms |
| Budget status endpoint (used/remaining/%) | T-017, T-018 | `test_budget_status.py` | Returns budget, actual, remaining, percentage |
| API filtering and pagination | T-019, T-020 | `test_cost_registrations.py` | Filters by cost_element, date range; paginates correctly |

**Requirements Traceability Validation:**
- ✅ Each acceptance criterion has ≥1 test
- ✅ Test names clearly indicate which criterion they validate
- ✅ Complex criteria have multiple tests (happy path, edge cases, errors)

---

## Test Specification (Test-First)

### Test Hierarchy

```
├── Unit Tests (write first - drive interface design)
│   ├── Test file structure: tests/unit/services/test_cost_registration_service.py
│   ├── Happy path tests (start here)
│   │   ├── test_create_cost_registration_with_valid_data_returns_registration
│   │   ├── test_get_total_for_cost_element_returns_sum
│   │   └── test_budget_status_returns_used_remaining_percentage
│   ├── Edge cases and boundaries
│   │   ├── test_create_with_zero_amount_blocks
│   │   ├── test_create_with_negative_amount_blocks
│   │   ├── test_create_with_future_date_succeeds
│   │   └── test_get_total_for_nonexistent_element_returns_zero
│   ├── Versioning behavior
│   │   ├── test_update_creates_new_version
│   │   ├── test_update_preserves_cost_registration_id
│   │   └── test_soft_delete_marks_deleted_at
│   └── Error handling
│       ├── test_create_with_invalid_cost_element_raises_404
│       ├── test_create_exceeding_budget_raises_validation_error
│       └── test_create_at_warning_threshold_returns_warning
│
├── Integration Tests (write after unit tests pass)
│   ├── Test file structure: tests/api/test_cost_registrations.py
│   ├── Database/repository integration
│   │   ├── test_create_cost_element_end_to_end
│   │   └── test_concurrent_budget_validation_prevents_overspend
│   └── Service layer integration
│       ├── test_budget_status_query_with_existing_costs
│       └── test_time_travel_query_returns_historical_totals
│
└── End-to-End Tests (write last - critical user flows)
    ├── Test file structure: frontend/tests/e2e/test_cost_registration.spec.ts
    ├── Critical user flows
    │   ├── test_user_registers_cost_sees_budget_update
    │   └── test_user_exceeds_budget_sees_error
    └── Change order impact
        └── test_user_views_change_order_impact_sees_cost_data
```

### Test Cases

| Test ID | Test Name | Acceptance Criterion | Type | Verification |
| ------- | --------- | -------------------- | ---- | ------------ |
| T-001 | test_create_cost_registration_with_valid_data_returns_registration | CRUD with versioning | Unit | Returns CostRegistrationRead with all fields, cost_registration_id set |
| T-002 | test_create_cost_registration_sets_valid_time_and_transaction_time | CRUD with versioning | Unit | valid_time starts at control_date (or now), transaction_time starts now |
| T-003 | test_soft_delete_cost_registration_marks_deleted_at | Soft delete | Unit | deleted_at is set, is_deleted returns True |
| T-004 | test_create_cost_registration_when_at_80_percent_budget_returns_warning | Budget validation | Unit | Returns CostRegistrationRead with warning in metadata |
| T-005 | test_create_cost_registration_when_exceeding_budget_raises_error | Budget validation | Unit | Raises BudgetExceededError with budget and actual amounts |
| T-006 | test_create_cost_registration_when_blocking_disabled_allows_overspend | Budget validation | Unit | Creates registration even when exceeding budget (config-based) |
| T-007 | test_concurrent_cost_registrations_prevent_race_condition_overspend | Budget validation | Integration | Two simultaneous requests cannot both exceed budget |
| T-011 | test_get_total_for_cost_element_with_as_of_past_returns_historical_sum | Time-travel | Unit | Returns sum of costs as of past date (excludes future costs) |
| T-012 | test_get_total_for_cost_element_with_as_of_future_returns_current_sum | Time-travel | Unit | Returns current sum (future date treated as now) |
| T-013 | test_impact_analysis_includes_cost_registrations_from_main | Change order impact | Integration | ImpactReport includes actual_costs field from main branch |
| T-014 | test_soft_delete_cost_registration_can_be_undone | Soft delete | Unit | After soft delete, new version with deleted_at=None restores record |
| T-015 | test_single_create_performance_under_100ms | Performance | Performance | Create operation completes in <100ms (measured with 1000 iterations) |
| T-017 | test_budget_status_returns_used_remaining_and_percentage | Budget status | Unit | Returns BudgetStatus with used=500, remaining=500, percentage=50 |
| T-018 | test_budget_status_for_element_with_no_costs_returns_zero_used | Budget status | Unit | Returns BudgetStatus with used=0, remaining=budget, percentage=0 |
| T-019 | test_list_cost_registrations_filters_by_cost_element_id | API filtering | Integration | Returns only registrations for specified cost_element |
| T-020 | test_list_cost_registrations_filters_by_date_range | API filtering | Integration | Returns only registrations within date range (inclusive) |
| T-021 | test_list_cost_registrations_paginates_correctly | API filtering | Integration | Page 1 returns first 20, page 2 returns next 20 |
| T-022 | test_update_cost_registration_creates_new_version_preserving_root_id | Versioning | Unit | New version has different id but same cost_registration_id |
| T-023 | test_update_cost_registration_with_amount_change_closes_old_version | Versioning | Unit | Old version has closed valid_time, new version has open valid_time |

### Test Infrastructure

**Framework**: pytest with pytest-asyncio (strict mode)

**Required Fixtures** (from `backend/tests/conftest.py`):
- `db_session` - Async database session with transaction rollback
- `db_engine` - Async engine for test DB
- `client` - Async HTTP client for API tests

**Custom Fixtures Needed** (add to `backend/tests/conftest.py`):

```python
@pytest.fixture
async def sample_cost_element(db_session: AsyncSession) -> CostElement:
    """Create a sample cost element for tests."""
    # Create department, cost element type, project, WBE, then cost element
    # Returns CostElement with budget_amount=1000

@pytest.fixture
async def sample_cost_registration(db_session: AsyncSession, sample_cost_element: CostElement) -> CostRegistration:
    """Create a sample cost registration for tests."""
    # Returns CostRegistration with amount=100, sample_cost_element.id
```

**Mock/Stub Requirements**:
- Time-dependent logic: Use `control_date` parameter (project pattern)
- Database state: Use fresh `db_session` per test
- External APIs: None for this feature
- RBAC: Mock `get_rbac_service` in API tests (follow `test_cost_elements.py` pattern)

### Test Examples (AAA Pattern)

**Example 1: Happy Path Create**
```python
@pytest.mark.asyncio
async def test_create_cost_registration_with_valid_data_returns_registration(
    db_session: AsyncSession, sample_cost_element: CostElement
) -> None:
    """Test creating a cost registration with valid data.

    Acceptance Criteria:
    - Cost registration created with provided amount, date, description
    - cost_registration_id is set (root ID)
    - Valid time starts at registration_date
    - Transaction time starts now
    """
    # Arrange
    service = CostRegistrationService(db_session)
    registration_in = CostRegistrationCreate(
        cost_element_id=sample_cost_element.cost_element_id,
        amount=Decimal("100.00"),
        registration_date=date(2026, 1, 15),
        description="Equipment rental"
    )
    actor_id = uuid4()

    # Act
    result = await service.create(registration_in, actor_id=actor_id)

    # Assert
    assert result.cost_registration_id is not None
    assert result.amount == Decimal("100.00")
    assert result.registration_date == date(2026, 1, 15)
    assert result.description == "Equipment rental"
    assert result.created_by == actor_id
```

**Example 2: Budget Validation**
```python
@pytest.mark.asyncio
async def test_create_cost_registration_when_at_80_percent_budget_returns_warning(
    db_session: AsyncSession, sample_cost_element: CostElement
) -> None:
    """Test budget validation warning at 80% threshold.

    Acceptance Criteria:
    - When used/budget >= 80%, return warning
    - Registration still succeeds
    - Warning message includes percentage
    """
    # Arrange
    service = CostRegistrationService(db_session)
    # sample_cost_element has budget=1000, create 700 in costs (70%)
    for _ in range(7):
        await service.create(
            CostRegistrationCreate(
                cost_element_id=sample_cost_element.cost_element_id,
                amount=Decimal("100.00"),
                registration_date=date.today()
            ),
            actor_id=uuid4()
        )

    # Add another 100 (reaches 80%)
    registration_in = CostRegistrationCreate(
        cost_element_id=sample_cost_element.cost_element_id,
        amount=Decimal("100.00"),
        registration_date=date.today()
    )

    # Act
    result = await service.create(registration_in, actor_id=uuid4())

    # Assert
    assert result.amount == Decimal("100.00")
    # Service should attach warning to result or metadata
    # (Implementation detail: may return tuple (result, warnings))
```

**Example 3: Budget Exceeded Block**
```python
@pytest.mark.asyncio
async def test_create_cost_registration_when_exceeding_budget_raises_error(
    db_session: AsyncSession, sample_cost_element: CostElement
) -> None:
    """Test budget validation blocking when exceeding budget.

    Acceptance Criteria:
    - When used + new_amount > budget, raise BudgetExceededError
    - Error includes current budget and used amounts
    - No registration is created
    """
    # Arrange
    service = CostRegistrationService(db_session)
    # Create costs totaling 1000 (full budget)
    for _ in range(10):
        await service.create(
            CostRegistrationCreate(
                cost_element_id=sample_cost_element.cost_element_id,
                amount=Decimal("100.00"),
                registration_date=date.today()
            ),
            actor_id=uuid4()
        )

    # Try to add more
    registration_in = CostRegistrationCreate(
        cost_element_id=sample_cost_element.cost_element_id,
        amount=Decimal("1.00"),
        registration_date=date.today()
    )

    # Act & Assert
    with pytest.raises(BudgetExceededError) as exc_info:
        await service.create(registration_in, actor_id=uuid4())

    assert exc_info.value.budget == Decimal("1000.00")
    assert exc_info.value.used == Decimal("1000.00")
```

**Example 4: Time-Travel Query**
```python
@pytest.mark.asyncio
async def test_get_total_for_cost_element_with_as_of_past_returns_historical_sum(
    db_session: AsyncSession, sample_cost_element: CostElement
) -> None:
    """Test time-travel query for historical cost totals.

    Acceptance Criteria:
    - as_of parameter queries cost state as of that date
    - Costs created after as_of are excluded
    - Costs deleted after as_of are included
    """
    # Arrange
    service = CostRegistrationService(db_session)
    actor_id = uuid4()

    # Create cost on Jan 1
    await service.create(
        CostRegistrationCreate(
            cost_element_id=sample_cost_element.cost_element_id,
            amount=Decimal("100.00"),
            registration_date=date(2026, 1, 1)
        ),
        actor_id=actor_id
    )

    # Create cost on Jan 15
    await service.create(
        CostRegistrationCreate(
            cost_element_id=sample_cost_element.cost_element_id,
            amount=Decimal("200.00"),
            registration_date=date(2026, 1, 15)
        ),
        actor_id=actor_id
    )

    # Act - Query as of Jan 10
    total = await service.get_total_for_cost_element(
        cost_element_id=sample_cost_element.cost_element_id,
        as_of=datetime(2026, 1, 10, 12, 0, 0)
    )

    # Assert - Only Jan 1 cost included
    assert total == Decimal("100.00")
```

### TDD Validation Checklist

Before implementation (for each test):

- [ ] Test file created following naming convention (`test_*.py`)
- [ ] Test written with AAA structure (Arrange-Act-Assert)
- [ ] Test runs and fails with **expected error** (not pre-existing bug)
- [ ] Test failure reason documented in do-prompt log
- [ ] Test name clearly describes expected behavior

After implementation:

- [ ] New test passes
- [ ] All existing tests still pass (no regressions)
- [ ] Coverage report shows ≥80% (or 100% for critical paths)
- [ ] Code passes mypy strict and ruff checks

---

## Risk Assessment

### Risks and Mitigations

| Risk Type | Description | Probability | Impact | Mitigation Strategy |
|-----------|-------------|------------|--------|---------------------|
| Technical | Budget validation race condition with concurrent requests | Medium | High | Use `SELECT FOR UPDATE` on cost_element row or application-level locking with Redis |
| Technical | Performance degradation at high volume (240k+/year) | Medium | High | Table partitioning by quarter, partial indexes, performance testing before deployment |
| Integration | Impact analysis integration breaks existing change order workflows | Low | Medium | Comprehensive integration tests, backward compatibility checks, gradual rollout |
| Technical | Table partitioning complexity increases migration risk | Low | Medium | Thorough migration testing, staging environment validation, rollback plan |
| Integration | Frontend-backend API contract mismatch | Low | Low | OpenAPI spec validation, generated TypeScript client, integration tests |

---

## Documentation References

### Required Documentation

**Architecture & Standards:**
- Coding Standards: [docs/02-architecture/coding-standards.md](../../02-architecture/coding-standards.md)
- Bounded Contexts: [docs/02-architecture/01-bounded-contexts.md](../../02-architecture/01-bounded-contexts.md) (Context 6: Cost Element & Financial Tracking)
- EVCS Core: [docs/02-architecture/02-evcs-framework.md](../../02-architecture/02-evcs-framework.md) (Versioning framework reference)

**Domain & Requirements:**
- Product Backlog: [docs/03-project-plan/product-backlog.md](../product-backlog.md#e05-u01-register-actual-costs-against-cost-elements)
- Current Iteration: [docs/03-project-plan/current-iteration.md](../current-iteration.md)

**Project Context:**
- Analysis Phase: [00-analysis.md](./00-analysis.md)
- Related Iterations:
  - [E04-U03] Cost Element Management (completed - reference for patterns)
  - [E08-U03] Calculate AC from Cost Registrations (dependent - uses this data)

### Code References

**Existing Patterns to Follow:**

**Backend:**
- Non-branchable versioned model: [backend/app/models/domain/cost_element_type.py](../../../../backend/app/models/domain/cost_element_type.py) - **Primary reference**
- Branchable model for contrast: [backend/app/models/domain/cost_element.py](../../../../backend/app/models/domain/cost_element.py)
- Non-branchable service: [backend/app/services/cost_element_type_service.py](../../../../backend/app/services/cost_element_type_service.py) - **Primary reference**
- CRUD API routes: [backend/app/api/routes/cost_elements.py](../../../../backend/app/api/routes/cost_elements.py)
- Impact analysis service (to modify): [backend/app/services/impact_analysis_service.py](../../../../backend/app/services/impact_analysis_service.py)

**Frontend:**
- Modal form pattern: [frontend/src/features/cost-elements/components/CostElementModal.tsx](../../../../frontend/src/features/cost-elements/components/CostElementModal.tsx)
- Form validation: Ant Design Form with async rules
- State management: TanStack Query via `createResourceHooks`

**Tests:**
- Service unit tests: [backend/tests/unit/services/test_cost_element_type_service.py](../../../../backend/tests/unit/services/test_cost_element_type_service.py) - **Primary reference for versioning tests**
- API integration tests: [backend/tests/api/test_cost_elements.py](../../../../backend/tests/api/test_cost_elements.py) - **Primary reference for API tests**
- Fixtures: [backend/tests/conftest.py](../../../../backend/tests/conftest.py)

**Database Schema:**

**Tables:**
- `cost_registrations` (NEW) - versioned, non-branchable
- `cost_elements` (EXISTING) - branchable, contains `budget_amount`

**Relationships:**
- `cost_registrations.cost_element_id` → `cost_elements.cost_element_id` (foreign key)
- Costs are global (no branch column)
- Budgets are branchable (has branch column)

**Indexes:**
- Primary: `cost_element_id`, `registration_date`
- Temporal: GIST indexes on `valid_time`, `transaction_time`
- Partial: Current versions only (`WHERE upper(valid_time) IS NULL AND deleted_at IS NULL`)

---

## Prerequisites & Dependencies

### Technical Prerequisites

- [x] Database migrations applied (before running tests)
- [x] Dependencies installed (`uv sync`)
- [x] Environment configured (PostgreSQL running)
- [x] External services available (none for this feature)

### Documentation Prerequisites

- [x] Analysis phase approved (00-analysis.md complete)
- [x] Architecture docs reviewed (bounded contexts, EVCS framework)
- [x] Related ADRs understood (none new - existing patterns apply)

### Implementation Dependencies

**Completed:**
- [x] E04-U03: Cost Element Management (provides parent CostElement entity)
- [x] EVCS versioning framework (provides `TemporalService`, `VersionableMixin`)

**In Scope (this iteration):**
- [ ] E05-U01: Cost Registration (this feature)
- [ ] Change order impact analysis integration

**Future (dependent on this):**
- [ ] E05-U05: Validate Cost Registrations against Budgets
- [ ] E05-U06: View Cost History and Trends
- [ ] E08-U03: Calculate AC from Cost Registrations

---

## TDD Quick Reference

### Test-First Command Sequence

```bash
# 1. Create test file
touch backend/tests/unit/services/test_cost_registration_service.py

# 2. Write test (AAA pattern)
# Edit: test_create_cost_registration_with_valid_data_returns_registration()

# 3. Run test - confirm FAILS (RED phase)
uv run pytest tests/unit/services/test_cost_registration_service.py::test_create_cost_registration_with_valid_data_returns_registration -v

# 4. Implement minimal code to make test pass (GREEN phase)
# Edit: backend/app/services/cost_registration_service.py

# 5. Run test - confirm PASSES
uv run pytest tests/unit/services/test_cost_registration_service.py::test_create_cost_registration_with_valid_data_returns_registration -v

# 6. Refactor for clarity/patterns (REFACTOR phase)

# 7. Run all tests - verify no regressions
uv run pytest tests/unit/services/ -v

# 8. Run coverage
uv run pytest tests/unit/services/test_cost_registration_service.py --cov=app.services.cost_registration_service --cov-report=term-missing
```

### Common Test Patterns

**Service Pattern (Non-Branchable)**:

```python
@pytest.mark.asyncio
async def test_cost_registration_create_with_valid_data_returns_cost_registration(
    db_session: AsyncSession, sample_cost_element: CostElement
) -> None:
    # Arrange
    service = CostRegistrationService(db_session)
    registration_in = CostRegistrationCreate(
        cost_element_id=sample_cost_element.cost_element_id,
        amount=Decimal("100.00"),
        registration_date=date.today()
    )
    actor_id = uuid4()

    # Act
    result = await service.create(registration_in, actor_id=actor_id)

    # Assert
    assert result.cost_registration_id is not None
    assert result.amount == Decimal("100.00")
    assert result.created_by == actor_id
```

**Budget Validation Pattern**:

```python
@pytest.mark.asyncio
async def test_cost_registration_create_when_exceeding_budget_raises_error(
    db_session: AsyncSession, sample_cost_element: CostElement
) -> None:
    # Arrange
    service = CostRegistrationService(db_session)
    # Pre-fill budget
    await create_costs_up_to_budget(service, sample_cost_element)
    registration_in = CostRegistrationCreate(
        cost_element_id=sample_cost_element.cost_element_id,
        amount=Decimal("1.00"),
        registration_date=date.today()
    )

    # Act & Assert
    with pytest.raises(BudgetExceededError) as exc_info:
        await service.create(registration_in, actor_id=uuid4())

    assert exc_info.value.budget == Decimal("1000.00")
```

**API Test Pattern**:

```python
@pytest.mark.asyncio
async def test_create_cost_registration_endpoint_with_valid_data_returns_201(
    client: AsyncClient, setup_dependencies: dict[str, Any]
) -> None:
    # Arrange
    deps = setup_dependencies  # Includes cost_element_id
    registration_data = {
        "cost_element_id": deps["cost_element_id"],
        "amount": 100.00,
        "registration_date": "2026-01-15"
    }

    # Act
    response = await client.post("/api/v1/cost-registrations", json=registration_data)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 100.00
    assert "cost_registration_id" in data
```

---

## Daily PDCA Workflow

### DO Phase Execution Protocol

For each implementation task, follow the RED-GREEN-REFACTOR cycle:

**🔴 RED Phase (Write Failing Test)**:
1. Write test in appropriate test file (unit → integration → e2e)
2. Run test: confirm it fails with **expected error** (not pre-existing bug)
3. Document test name and expected failure in daily log

**🟢 GREEN Phase (Make Test Pass)**:
1. Write **minimal** code to make test pass
2. Run test: confirm it passes
3. Run all related tests: confirm no regressions

**🔵 REFACTOR Phase (Improve Design)**:
1. Review code: apply patterns, extract methods, improve names
2. Run all tests after each small change
3. Ensure mypy and ruff pass

**Daily Log Template** (add to `02-do.md` daily):
```markdown
### 2026-01-XX

**RED Phase Tests Written:**
- [T-XXX] test_name - Expected: Error, Result: Error ✅

**GREEN Phase Implementations:**
- CostRegistrationService.create() - T-XXX passes ✅

**REFACTOR Phase:**
- Extracted validate_budget() method

**Tests Passing: X/Y**
**Coverage: XX%**
```

---

## Output Summary

**Total Tasks:** 21
**Estimated Complexity:** 8 Medium, 9 Low, 4 High

**Critical Path:**
1. Migration → Model → Service → API → Frontend → E2E Tests

**Parallel Opportunities:**
- Tasks 1-9 (Backend foundation) can be done independently of frontend (Tasks 19-21)
- Performance tests (Task 17) can run in parallel with E2E tests

**Test Count:** 20 test cases specified
- Unit: 13
- Integration: 5
- E2E: 2
- Performance: 1

**Success Criteria Verification:**
- All 6 functional criteria mapped to tests ✅
- All 4 technical criteria measurable ✅
- All 4 business criteria testable ✅
- All 6 TDD criteria defined ✅
