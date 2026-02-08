# Plan: E04-U04 - Allocate Revenue across WBEs

**Created:** 2026-02-03
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 - Service-Layer Validation with Error Enforcement
**Epic:** E004 (Project Structure Management)
**Story Points:** 5

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option:** Option 1 - Service-Layer Validation with Error Enforcement
- **Architecture:** Add `revenue_allocation` DECIMAL(15, 2) field to WBE model with service-layer validation to ensure sum of all WBE revenues equals project contract_value
- **Key Decisions:**
  - Validation raises ValueError when total allocations != contract_value (exact match required)
  - Nullable field with default None for backward compatibility
  - Validation excludes current WBE during updates (prevent double-counting)
  - Validation skips when project.contract_value is None
  - Follows existing pattern from budget_allocation field

### Success Criteria

**Functional Criteria:**

- [ ] Users can allocate revenue amounts to WBEs via API (POST /api/v1/wbes) VERIFIED BY: Integration test T-006
- [ ] Users can update revenue allocations on existing WBEs via API (PUT /api/v1/wbes/{id}) VERIFIED BY: Integration test T-007
- [ ] Backend validates that sum of WBE revenues = project contract_value exactly VERIFIED BY: Unit test T-001, T-002, T-003
- [ ] Validation raises ValueError with clear message when mismatch occurs VERIFIED BY: Unit test T-002, T-003
- [ ] Validation excludes current WBE when updating (prevents double-counting) VERIFIED BY: Unit test T-005
- [ ] Validation allows None contract_value (graceful skip) VERIFIED BY: Unit test T-004
- [ ] Frontend displays revenue_allocation field in WBE modal VERIFIED BY: Frontend unit test T-F001
- [ ] Frontend shows validation errors from backend VERIFIED BY: Frontend integration test T-F003
- [ ] Revenue allocation supports versioning (changes tracked in EVCS) VERIFIED BY: Integration test T-008
- [ ] Branch isolation works (revenue changes in branch don't affect main) VERIFIED BY: Integration test T-009

**Technical Criteria:**

- [ ] Performance: Validation query completes in <200ms VERIFIED BY: Performance test T-P001
- [ ] Security: Validation prevents invalid revenue states VERIFIED BY: Unit tests T-001 through T-005
- [ ] Code Quality: MyPy strict mode (zero errors) VERIFIED BY: CI pipeline `uv run mypy app/`
- [ ] Code Quality: Ruff linting (zero errors) VERIFIED BY: CI pipeline `uv run ruff check .`
- [ ] Test Coverage: ≥80% for new validation logic VERIFIED BY: `pytest --cov=app/services/wbe`
- [ ] Frontend: TypeScript strict mode (no type errors) VERIFIED BY: `npm run type-check`
- [ ] Frontend: ESLint (zero errors) VERIFIED BY: `npm run lint`

**Business Criteria:**

- [ ] Revenue data integrity maintained (no orphaned allocations) VERIFIED BY: Integration test T-010
- [ ] User workflow not disrupted (clear error messages) VERIFIED BY: Frontend test T-F003
- [ ] Change order workflows supported (branch isolation) VERIFIED BY: Integration test T-009

### Scope Boundaries

**In Scope:**

- Add `revenue_allocation` field to WBE model (nullable DECIMAL(15, 2))
- Database migration to add column with default None
- Update WBE schemas (WBEBase, WBECreate, WBEUpdate, WBERead)
- Implement `_validate_revenue_allocation()` method in WBEService
- Call validation in `create_wbe()` and `update_wbe()` methods
- Add revenue_allocation InputNumber field to WBEModal.tsx
- Update frontend types after regenerating OpenAPI client
- Unit and integration tests for validation logic
- Frontend tests for modal field and error display

**Out of Scope:**

- Revenue allocation summary dashboard (deferred to EVM epic)
- Revenue allocation status endpoint (deferred if needed)
- Revenue validation configuration (strict vs. warning mode)
- Automatic revenue distribution algorithms
- Revenue allocation import/export functionality
- Currency conversion (assumes EUR only)

---

## Work Decomposition

### Task Breakdown

| #   | Task                                         | Files                                                                                               | Dependencies  | Success Criteria                                                                                                   | Complexity |
| --- | --------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------ | ---------- |
| BE-001 | Create database migration                     | `backend/alembic/versions/YYYYMMDD_add_revenue_allocation_to_wbes.py`                                | None          | Migration applies successfully, rollback works, revenue_allocation column exists with nullable=True                  | Low        |
| BE-002 | Update WBE model                              | `backend/app/models/domain/wbe.py`                                                                  | BE-001        | Model has `revenue_allocation: Mapped[Decimal\|None]` field, passes MyPy                                         | Low        |
| BE-003 | Update WBE schemas                            | `backend/app/models/schemas/wbe.py`                                                                 | BE-002        | WBEBase, WBECreate, WBEUpdate, WBERead include revenue_allocation with ge=0 validation                          | Low        |
| BE-004 | Implement validation method                   | `backend/app/services/wbe.py` (_validate_revenue_allocation)                                        | BE-002        | Method sums revenues, compares to contract_value, excludes current WBE, raises ValueError on mismatch            | Medium     |
| BE-005 | Integrate validation in create_wbe            | `backend/app/services/wbe.py` (create_wbe method)                                                   | BE-004        | Validation called before creation, errors propagate to API                                                        | Low        |
| BE-006 | Integrate validation in update_wbe            | `backend/app/services/wbe.py` (update_wbe method)                                                   | BE-005        | Validation called with exclude_wbe_id parameter, errors propagate to API                                         | Low        |
| BE-007 | Write validation unit tests                   | `backend/tests/unit/services/test_wbe_service_revenue_validation.py`                                | BE-006        | 9 test cases covering happy path, edge cases, errors (T-001 through T-005), all pass, coverage ≥80%               | Medium     |
| BE-008 | Write API integration tests                   | `backend/tests/integration/test_revenue_allocation_api.py`                                          | BE-007        | 4 test cases covering create/update flows, batch operations, change orders (T-006 through T-009), all pass       | Medium     |
| BE-009 | Backend quality verification                  | All backend files                                                                                    | BE-008        | MyPy strict (0 errors), Ruff (0 errors), pytest --cov (≥80%), migration tested with rollback                     | Low        |
| FE-001 | Regenerate OpenAPI client                     | `frontend/src/api/generated/` (all files)                                                           | BE-003        | revenue_allocation field present in WBECreate, WBEUpdate, WBERead types, TypeScript strict mode passes            | Low        |
| FE-002 | Add revenue field to WBEModal                 | `frontend/src/features/wbes/components/WBEModal.tsx`                                                | FE-001        | revenue_allocation InputNumber field rendered, Euro formatter applied, default value 0, edit mode loads existing | Low        |
| FE-003 | Write WBEModal frontend tests                 | `frontend/src/features/wbes/components/WBEModal.test.tsx`                                           | FE-002        | Field rendering test (T-F001), form validation test (T-F002), error display test (T-F003), all pass              | Medium     |
| FE-004 | Frontend quality verification                 | All frontend files                                                                                   | FE-003        | TypeScript strict (0 errors), ESLint (0 errors), tests pass, coverage ≥80%                                      | Low        |
| DOC-001 | Update API documentation                      | Review auto-generated OpenAPI at `/docs`                                                            | BE-009        | revenue_allocation field documented with description, example values shown                                      | Low        |
| DOC-002 | Update user guide                             | `docs/01-product-scope/user-guide.md` or new section                                                | DOC-001       | Revenue allocation workflow documented with screenshots                                                          | Medium     |

### Task Dependency Graph

```yaml
# Task Dependency Graph for E04-U04

tasks:
  # Backend tasks (sequential with BE-001 starting point)
  - id: BE-001
    name: "Create database migration for revenue_allocation column"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Update WBE model with revenue_allocation field"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Update WBE schemas (WBEBase, WBECreate, WBEUpdate, WBERead)"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-004
    name: "Implement _validate_revenue_allocation method in WBEService"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-005
    name: "Integrate validation in create_wbe method"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: BE-006
    name: "Integrate validation in update_wbe method"
    agent: pdca-backend-do-executor
    dependencies: [BE-005]

  - id: BE-007
    name: "Write validation unit tests"
    agent: pdca-backend-do-executor
    dependencies: [BE-006]

  - id: BE-008
    name: "Write API integration tests"
    agent: pdca-backend-do-executor
    dependencies: [BE-007]

  - id: BE-009
    name: "Backend quality verification (MyPy, Ruff, coverage)"
    agent: pdca-backend-do-executor
    dependencies: [BE-008]

  # Frontend tasks (can start in parallel after BE-003)
  - id: FE-001
    name: "Regenerate OpenAPI client with revenue_allocation field"
    agent: pdca-frontend-do-executor
    dependencies: [BE-003]

  - id: FE-002
    name: "Add revenue_allocation field to WBEModal component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-003
    name: "Write WBEModal frontend tests"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]

  - id: FE-004
    name: "Frontend quality verification (TypeScript, ESLint, tests)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  # Documentation tasks (start after backend completion)
  - id: DOC-001
    name: "Update and review API documentation"
    agent: pdca-backend-do-executor
    dependencies: [BE-009]

  - id: DOC-002
    name: "Update user guide with revenue allocation workflow"
    agent: pdca-frontend-do-executor
    dependencies: [DOC-001, FE-004]
```

**Parallel Execution Opportunities:**

- **Level 0 (Can run immediately):** BE-001 (database migration)
- **Level 1:** BE-002 (model update) - depends on BE-001
- **Level 2:** BE-003 (schemas), BE-004 (validation method) - can run in parallel after BE-002
- **Level 3:** BE-005 (create validation) - depends on BE-004
- **Level 4:** BE-006 (update validation) - depends on BE-005
- **Level 5:** BE-007 (unit tests) - depends on BE-006
- **Level 6:** BE-008 (integration tests) - depends on BE-007
- **Level 7:** BE-009 (backend QA) - depends on BE-008
- **Frontend starts after BE-003:** FE-001 → FE-002 → FE-003 → FE-004 can overlap with backend testing
- **Documentation after backend complete:** DOC-001 → DOC-002

### Test-to-Requirement Traceability

| Acceptance Criterion                                      | Test ID | Test File                                          | Expected Behavior                                                                                       |
| --------------------------------------------------------- | ------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Users can allocate revenue via POST /wbes                 | T-006   | tests/integration/test_revenue_allocation_api.py   | POST request with valid revenue_allocation succeeds, returns WBERead with revenue value                  |
| Users can update revenue via PUT /wbes/{id}               | T-007   | tests/integration/test_revenue_allocation_api.py   | PUT request with new revenue_allocation updates value, validates against contract_value                 |
| Sum of WBE revenues = project contract_value (exact)      | T-001   | tests/unit/services/test_wbe_service_revenue_validation.py | Create WBE with revenue that matches contract_value, validation passes                                  |
| Validation raises ValueError when total > contract_value  | T-002   | tests/unit/services/test_wbe_service_revenue_validation.py | Create WBE with revenue exceeding contract_value, raises ValueError with difference message               |
| Validation raises ValueError when total < contract_value  | T-003   | tests/unit/services/test_wbe_service_revenue_validation.py | Create WBE with revenue under contract_value, raises ValueError with difference message                  |
| Validation excludes current WBE during update             | T-005   | tests/unit/services/test_wbe_service_revenue_validation.py | Update WBE revenue, validation sums other WBEs + new value (not old value), passes if valid             |
| Validation allows None contract_value                     | T-004   | tests/unit/services/test_wbe_service_revenue_validation.py | Create WBE when project.contract_value is None, validation skipped, no error raised                     |
| Frontend displays revenue_allocation field               | T-F001  | frontend/src/features/wbes/components/WBEModal.test.tsx | WBEModal renders InputNumber for revenue_allocation, Euro formatter applied                              |
| Frontend shows validation errors                          | T-F003  | frontend/src/features/wbes/components/WBEModal.test.tsx | Modal submission with invalid revenue displays backend error message (e.g., "Total revenue €X != €Y") |
| Revenue allocation supports versioning                    | T-008   | tests/integration/test_revenue_allocation_api.py   | Create WBE, update revenue, query history returns both versions with different revenue_allocation values |
| Branch isolation works                                    | T-009   | tests/integration/test_revenue_allocation_api.py   | Create branch, modify WBE revenue, main branch unchanged, branch has new value                           |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests (backend/tests/unit/services/)
│   ├── test_wbe_service_revenue_validation.py
│   │   ├── Happy path: Valid revenue allocation (T-001)
│   │   ├── Edge case: Revenue exceeds contract value (T-002)
│   │   ├── Edge case: Revenue under contract value (T-003)
│   │   ├── Edge case: Project with None contract value (T-004)
│   │   ├── Edge case: Update excludes current WBE (T-005)
│   │   ├── Edge case: Decimal precision quantization
│   │   ├── Edge case: Empty WBE list (sum=0)
│   │   ├── Edge case: Soft-deleted WBEs excluded
│   │   └── Edge case: Branch isolation
│
├── Integration Tests (backend/tests/integration/)
│   └── test_revenue_allocation_api.py
│       ├── Create WBE with valid revenue (T-006)
│       ├── Create WBE with invalid revenue (error response)
│       ├── Update WBE with valid revenue (T-007)
│       ├── Update WBE with invalid revenue (error response)
│       ├── Batch operations (multiple WBE creates)
│       ├── Versioning history query (T-008)
│       └── Branch isolation (T-009)
│
├── Frontend Unit Tests (frontend/src/features/wbes/components/)
│   └── WBEModal.test.tsx
│       ├── Field rendering test (T-F001)
│       ├── Form validation test (T-F002)
│       └── Error display test (T-F003)
│
└── Performance Tests (backend/tests/performance/)
    └── test_revenue_validation_performance.py
        └── Validation query timing (T-P001)
```

### Test Cases (first 9)

| Test ID | Test Name                                                          | Criterion | Type         | Expected Result                                                                                                |
| ------- | ------------------------------------------------------------------ | --------- | ------------ | ------------------------------------------------------------------------------------------------------------- |
| T-001   | test_validate_revenue_allocation_with_exact_match_passes           | AC-1      | Unit         | Validation passes when sum of WBE revenues equals project.contract_value                                    |
| T-002   | test_validate_revenue_allocation_exceeds_contract_raises_error     | AC-2      | Unit         | Raises ValueError("Total revenue €X does not match project contract value €Y. Difference: €Z") when sum > contract |
| T-003   | test_validate_revenue_allocation_under_contract_raises_error       | AC-2      | Unit         | Raises ValueError with difference message when sum < contract_value                                          |
| T-004   | test_validate_revenue_allocation_with_none_contract_value_skips   | AC-2      | Unit         | Validation returns None (no error) when project.contract_value is None                                       |
| T-005   | test_validate_revenue_allocation_excludes_current_wbe_on_update   | AC-2      | Unit         | Update validation excludes current WBE ID from sum, uses new value instead                                   |
| T-006   | test_create_wbe_with_valid_revenue_allocation_succeeds            | AC-1      | Integration  | POST /wbes with revenue_allocation=100000 returns 201, WBERead includes revenue_allocation                   |
| T-007   | test_update_wbe_with_valid_revenue_allocation_succeeds            | AC-1      | Integration  | PUT /wbes/{id} with new revenue_allocation returns 200, validation passes                                   |
| T-008   | test_revenue_allocation_versioning_creates_history                 | AC-3      | Integration  | Create WBE (revenue=50000), update (revenue=60000), history endpoint returns 2 versions with different values |
| T-009   | test_revenue_allocation_branch_isolation                           | AC-3      | Integration  | Create branch BR-1, update WBE revenue, main branch unchanged, BR-1 has new value                            |

### Test Infrastructure Needs

**Fixtures Needed:**

```python
# backend/tests/conftest.py (additions)

@pytest.fixture
async def project_with_contract_value(session, test_user):
    """Project with contract_value set for revenue validation tests."""
    from app.models.domain.project import Project
    from datetime import datetime

    project = Project(
        project_id=uuid4(),
        code="PRJ-001",
        name="Test Project with Contract",
        contract_value=Decimal("100000.00"),
        branch="main",
        created_by=test_user.user_id,
        valid_time=Tstzrange(datetime.now(timezone.utc), None),
        transaction_time=Tstzrange(datetime.now(timezone.utc), None),
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project

@pytest.fixture
async def wbe_with_revenue(session, project_with_contract_value, test_user):
    """WBE with revenue_allocation for testing."""
    from app.models.domain.wbe import WBE

    wbe = WBE(
        wbe_id=uuid4(),
        project_id=project_with_contract_value.project_id,
        code="1.1",
        name="Test WBE",
        budget_allocation=Decimal("50000.00"),
        revenue_allocation=Decimal("50000.00"),
        branch="main",
        created_by=test_user.user_id,
        # ... versioning fields
    )
    session.add(wbe)
    await session.commit()
    await session.refresh(wbe)
    return wbe
```

**Mocks/Stubs:**

- Time-dependent logic: Use `freeze_time()` from pytest-freezegun for deterministic timestamps
- External services: None (all internal logic)

**Database State:**

- Seed data: project with contract_value=100000.00
- Clean state: Each test uses rollback transaction isolation
- Branch data: Test fixtures for main branch and BR-1 branch

---

## Risk Assessment

| Risk Type   | Description                                                                 | Probability | Impact       | Mitigation                                                                                                                                                                                                      |
| ----------- | --------------------------------------------------------------------------- | ----------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Technical   | Migration fails on production database with existing data                    | Low         | High         | - Test migration on production-like dataset in staging<br>- Include rollback procedure in migration comments<br>- Use nullable=True to avoid breaking existing records                                         |
| Technical   | Decimal precision errors in sum calculation                                  | Medium      | Medium       | - Use Decimal.quantize(Decimal("0.01")) before comparison<br>- Add explicit test case for rounding edge cases<br>- Document Decimal arithmetic requirements                                                   |
| Integration | Frontend doesn't show backend validation errors                             | Medium      | Medium       | - Test backend error response format matches frontend expectations<br>- Use Ant Design Form error handling (automatic on 4xx response)<br>- Add explicit frontend test for error display (T-F003)             |
| Integration | Regenerated OpenAPI client overwrites manual type customizations            | Low         | Low          | - Review generated client before committing<br>- Use .openapi-generator-ignore to preserve customizations if needed<br>- Document any manual type adjustments                                                  |
| Business    | Users confused by strict validation when contract_value not set              | Medium      | Medium       | - Clear error message: "Please set project contract value before allocating revenue"<br>- Update user guide with workflow steps<br>- Consider adding warning banner on project detail page                      |
| Business    | Change order workflow disrupted by validation                                | Low         | Medium       | - Validation applies to current branch only (tested in T-009)<br>- Document branch isolation behavior<br>- Ensure change order UI handles validation errors gracefully                                       |
| Performance | Validation query slow on projects with 100+ WBEs                            | Low         | Medium       | - Add performance test with 100 WBEs (T-P001)<br>- Ensure index exists on project_id column (already present)<br>- Monitor query timing in production after deployment                                      |

---

## Documentation References

### Required Reading

**Architecture Documentation:**

- Coding Standards: `/home/nicola/dev/backcast_evs/docs/02-architecture/backend/coding-standards.md`
  - MyPy strict mode requirements
  - Docstring standard (LLM-optimized)
  - Service layer patterns

- Frontend Coding Standards: `/home/nicola/dev/backcast_evs/docs/02-architecture/frontend/coding-standards.md`
  - TypeScript strict mode
  - JSDoc documentation standard
  - State management patterns (TanStack Query)

- Bounded Contexts: `/home/nicola/dev/backcast_evs/docs/02-architecture/01-bounded-contexts.md#5-project--wbe-management`
  - Project & WBE context
  - Versioning architecture (EVCS Core)

**Product Scope:**

- Functional Requirements: Section 5.1 - Revenue Allocation
  - "Revenue allocations must equal total project contract value (exact match required)"

- Functional Requirements: Section 15.4 - Validation Rules
  - Revenue validation requirements

- Functional Requirements: Section 8.1 - Change Order Support
  - Branch isolation requirements

**Architecture Decisions:**

- ADR-005: Bitemporal Versioning
  - TemporalBase, BranchableMixin patterns
  - Version chain tracking

- ADR-003: Command Pattern
  - CreateVersionCommand, UpdateVersionCommand usage

### Code References

**Backend Patterns:**

- WBE Model: `/home/nicola/dev/backcast_evs/backend/app/models/domain/wbe.py`
  - Line 65: `budget_allocation: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), default=0)` (pattern to follow)

- WBE Service: `/home/nicola/dev/backcast_evs/backend/app/services/wbe.py`
  - Lines 379-411: `create_wbe()` method (add validation call)
  - Lines 414-461: `update_wbe()` method (add validation call)

- WBE Schemas: `/home/nicola/dev/backcast_evs/backend/app/models/schemas/wbe.py`
  - Lines 10-21: WBEBase schema (add revenue_allocation field)
  - Lines 24-39: WBECreate schema (inherits from WBEBase)
  - Lines 41-54: WBEUpdate schema (add optional revenue_allocation)

- Validation Pattern Reference: `/home/nicola/dev/backcast_evs/backend/app/services/cost_registration_service.py`
  - Lines 95-96: Example of previously removed budget validation (shows pattern)

**Frontend Patterns:**

- WBE Modal: `/home/nicola/dev/backcast_evs/frontend/src/features/wbes/components/WBEModal.tsx`
  - Lines 107-118: budget_allocation InputNumber field (copy pattern for revenue_allocation)

- WBE API Tests: `/home/nicola/dev/backcast_evs/frontend/src/features/wbes/api/useWBEs.test.tsx`
  - Control date injection pattern (lines 36-58 for create, 82-103 for update)

**Test Patterns:**

- Conftest Fixtures: `/home/nicola/dev/backcast_evs/backend/tests/conftest.py`
  - Existing project_fixture, wbe_fixture patterns

---

## Prerequisites

### Technical Prerequisites

- [ ] PostgreSQL 15+ database running (`docker-compose up -d postgres`)
- [ ] Backend dependencies installed (`cd backend && uv sync`)
- [ ] Frontend dependencies installed (`cd frontend && npm install`)
- [ ] Database migrations up to date (`cd backend && uv run alembic upgrade head`)
- [ ] Existing test database with seed data

### Documentation Prerequisites

- [x] Analysis phase approved (00-analysis.md reviewed and accepted)
- [ ] EVCS architecture docs reviewed (TemporalBase, BranchableMixin)
- [ ] Service layer patterns understood (CreateVersionCommand, UpdateCommand)
- [ ] Frontend state management patterns understood (TanStack Query, Time Machine)

---

## Implementation Timeline

### Phase 1: Backend Foundation (Estimated: 4-5 hours)

**Tasks:** BE-001 through BE-009

**Deliverables:**

- Database migration created and tested
- WBE model updated with revenue_allocation field
- WBE schemas updated (all 4 schemas)
- Validation method implemented with 9 test cases
- Integration tests for API endpoints
- MyPy strict mode, Ruff linting, 80%+ coverage achieved

**Definition of Done:**

- All backend tests pass (pytest)
- MyPy reports 0 errors
- Ruff reports 0 errors
- Test coverage ≥80% for new code
- Migration can be applied and rolled back cleanly

### Phase 2: Frontend Implementation (Estimated: 2-3 hours)

**Tasks:** FE-001 through FE-004

**Deliverables:**

- OpenAPI client regenerated with new field
- WBEModal component updated with revenue_allocation field
- Frontend tests pass (rendering, validation, error display)
- TypeScript strict mode, ESLint clean

**Definition of Done:**

- All frontend tests pass (npm test)
- TypeScript reports 0 type errors
- ESLint reports 0 errors
- Test coverage ≥80% for new code
- Revenue field visible and functional in UI

### Phase 3: Documentation & QA (Estimated: 1-2 hours)

**Tasks:** DOC-001, DOC-002

**Deliverables:**

- API documentation reviewed and confirmed
- User guide updated with revenue allocation workflow
- End-to-end testing performed

**Definition of Done:**

- OpenAPI docs show revenue_allocation field
- User guide includes step-by-step instructions
- E2E test passes (create project → allocate revenue → verify validation)

### Phase 4: Deployment (Estimated: 30 minutes)

**Tasks:** Code review, merge, deploy, smoke test

**Deliverables:**

- Code reviewed and approved
- Merged to main branch
- Backend migration deployed to staging
- Frontend changes deployed to staging
- Smoke testing completed
- Production deployment (if approved)

**Definition of Done:**

- PR approved by reviewer
- Staging environment smoke test passes
- Production deployment successful
- Error logs monitored for 24 hours

---

## Quality Gates

### Backend Quality Checklist

```bash
# Run from backend directory

# 1. Type checking (MyPy strict mode)
uv run mypy app/ --strict
# Expected: 0 errors

# 2. Linting (Ruff)
uv run ruff check . --fix
# Expected: 0 errors

# 3. Testing (pytest with coverage)
uv run pytest --cov=app --cov-report=html
# Expected: All tests pass, coverage ≥80%

# 4. Migration testing
uv run alembic upgrade head
# Expected: Migration applies successfully
uv run alembic downgrade -1
# Expected: Migration rolls back cleanly
```

### Frontend Quality Checklist

```bash
# Run from frontend directory

# 1. Type checking (TypeScript strict mode)
npm run type-check
# Expected: 0 errors

# 2. Linting (ESLint)
npm run lint
# Expected: 0 errors

# 3. Testing (Vitest with coverage)
npm run test:coverage
# Expected: All tests pass, coverage ≥80%

# 4. Build verification
npm run build
# Expected: Build succeeds without errors
```

### Acceptance Criteria Verification

- [ ] All functional tests pass (T-001 through T-009, T-F001 through T-F003)
- [ ] All edge cases tested and handled
- [ ] Performance test passes (T-P001: <200ms validation query)
- [ ] Versioning works correctly (T-008)
- [ ] Branch isolation works (T-009)
- [ ] Error messages are clear and actionable
- [ ] User workflow is not disrupted

---

## Success Metrics

### Functional Metrics

- **Revenue Allocation Success Rate:** 100% of valid allocations succeed
- **Validation Accuracy:** 100% of invalid allocations are blocked with clear error messages
- **Versioning Integrity:** 100% of revenue changes tracked in audit trail
- **Branch Isolation:** 0 cross-branch data contamination

### Technical Metrics

- **API Response Time:** <200ms for validation query (P95)
- **Test Coverage:** ≥80% for new validation code
- **Type Safety:** 0 MyPy errors, 0 TypeScript errors
- **Code Quality:** 0 Ruff errors, 0 ESLint errors

### User Experience Metrics

- **Error Message Clarity:** User can understand and fix validation errors without support
- **Workflow Disruption:** <5 seconds additional time per WBE create/update
- **Learning Curve:** Existing WBE modal users understand new field without training

---

## Notes for DO Phase Executors

### Key Implementation Details

1. **Validation Logic Pattern:**
   - Query project.contract_value first (return None if not set)
   - Sum all WBE.revenue_allocation for project (exclude deleted)
   - For update: exclude current WBE to prevent double-counting
   - Use `Decimal.quantize(Decimal("0.01"))` before comparison
   - Raise ValueError with formatted message showing totals and difference

2. **Frontend Field Pattern:**
   - Copy budget_allocation InputNumber (lines 107-118)
   - Change label to "Revenue Allocation"
   - Use same Euro formatter: `formatter={(value) => '€ ${value}'.replace(...)}`
   - Default to 0 for new WBEs

3. **Testing Strategy:**
   - Follow RED-GREEN-REFACTOR TDD methodology
   - Write tests BEFORE implementation code
   - Document failing tests in commit messages
   - All tests must pass before completion

4. **Versioning Considerations:**
   - revenue_allocation is a regular field (no special versioning needed)
   - Changes automatically tracked via TemporalBase
   - Validation applies to current branch only (branch parameter passed)

5. **Edge Cases to Handle:**
   - Project with contract_value=None → skip validation
   - Empty WBE list → sum=0, valid if contract_value=0
   - Soft-deleted WBEs → exclude from sum
   - Update operation → exclude current WBE's old value
   - Decimal rounding → quantize before comparison

### Common Pitfalls to Avoid

- **Pitfall 1:** Forgetting to exclude current WBE during update
  - **Solution:** Pass `exclude_wbe_id` parameter to validation method

- **Pitfall 2:** Decimal comparison without quantization
  - **Solution:** Always use `.quantize(Decimal("0.01"))` before comparison

- **Pitfall 3:** Validation blocking when contract_value is None
  - **Solution:** Check `if contract_value is None: return` at start of validation

- **Pitfall 4:** Not regenerating OpenAPI client after schema changes
  - **Solution:** Run `npm run generate-client` after backend changes merged

- **Pitfall 5:** Forgetting to test branch isolation
  - **Solution:** Create explicit test case T-009 for branch behavior

---

**Document Status:** Ready for DO Phase
**Next Phase:** DO (Backend and frontend implementation by pdca-backend-do-executor and pdca-frontend-do-executor)
