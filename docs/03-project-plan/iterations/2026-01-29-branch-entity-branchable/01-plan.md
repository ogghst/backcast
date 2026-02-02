# Plan: Make Branch Entity Versionable

**Created:** 2026-01-29  
**Analysis Reference:** [00-analysis.md](00-analysis.md)  
**Selected Option:** Option 2 - Versionable Entity (without branching)

---

## Approved Approach Summary

- **Selected Option:** Option 2 - Convert Branch to a Versionable entity with bitemporal tracking
- **Architecture:** `EntityBase + VersionableMixin` (no `BranchableMixin` - Branch doesn't branch itself)
- **Key Decisions:**
  1. Lock/unlock operations update in-place (no version history for lock state changes)
  2. Add `branch_id` UUID as root identifier (following `project_id`, `wbe_id` patterns)
  3. Frontend BranchSelector component will support `as_of` temporal queries
  4. Composite PK `(name, project_id)` remains for lookup, with `branch_id` as stable root ID

---

## Success Criteria

### Functional Criteria

- [ ] **AC-1:** Branch entity has bitemporal fields (`valid_time`, `transaction_time`) VERIFIED BY: Unit test
- [ ] **AC-2:** Branch queries support `as_of` time-travel VERIFIED BY: Integration test
- [ ] **AC-3:** New branches receive `branch_id` UUID on creation VERIFIED BY: Unit test
- [ ] **AC-4:** Lock/unlock operations update branch in-place VERIFIED BY: Unit test
- [ ] **AC-5:** Frontend BranchSelector fetches branches with `as_of` context VERIFIED BY: Manual verification
- [ ] **AC-6:** Existing data migrates correctly with temporal ranges VERIFIED BY: Migration test

### Technical Criteria

- [ ] MyPy strict mode passes VERIFIED BY: `uv run mypy --config pyproject.toml backend/app`
- [ ] Ruff passes VERIFIED BY: `uv run ruff check backend/app`
- [ ] Existing tests pass VERIFIED BY: `uv run pytest backend/tests/unit/test_branch*.py -v`

### TDD Criteria

- [ ] All tests written before implementation code
- [ ] Test coverage maintained ≥80%
- [ ] Tests follow Arrange-Act-Assert pattern

---

## Scope Boundaries

### In Scope

- Branch model with `VersionableMixin`
- Add `branch_id` UUID field
- BranchService with temporal query support (`get_as_of`)
- Database migration for temporal fields
- Frontend BranchSelector temporal support
- API route updates for `as_of` parameter
- Branch schema updates (`BranchRead`, `BranchCreate`)

### Out of Scope (Deferred)

- Full version history for Branch (no `BranchableService[Branch]`)
- Branch lock audit trail (lock updates in-place per decision)
- Frontend branch version history viewer
- Branch deletion temporal semantics (existing `deleted_at` pattern preserved)

---

## Work Decomposition

### Task Breakdown

| #   | Task                                       | Files                | Dependencies | Success Criteria               | Complexity |
| --- | ------------------------------------------ | -------------------- | ------------ | ------------------------------ | ---------- |
| 1   | Update Branch model with VersionableMixin  | `branch.py`          | None         | Model compiles, fields present | Low        |
| 2   | Add branch_id UUID field                   | `branch.py`          | Task 1       | Field indexed, migration ready | Low        |
| 3   | Create migration for temporal fields       | `alembic/versions/`  | Task 1, 2    | Migration runs, data preserved | Med        |
| 4   | Update BranchService with temporal queries | `branch_service.py`  | Task 1       | `get_as_of` method works       | Med        |
| 5   | Update Branch API schemas                  | `schemas/branch.py`  | Task 1, 2    | Schemas include new fields     | Low        |
| 6   | Update branch API routes                   | `api/routes/`        | Task 4, 5    | Routes accept `as_of` param    | Med        |
| 7   | Update frontend queryKeys for branches     | `queryKeys.ts`       | Task 6       | Branch keys include context    | Low        |
| 8   | Update BranchSelector for temporal support | `BranchSelector.tsx` | Task 7       | Component uses `as_of`         | Med        |
| 9   | Update unit tests                          | `tests/unit/`        | Task 1-5     | Tests pass                     | Med        |
| 10  | Update integration tests                   | `tests/integration/` | Task 1-6     | Tests pass                     | Med        |

---

## Test-to-Requirement Traceability

| Acceptance Criterion        | Test ID | Test File                                  | Expected Behavior                                   |
| --------------------------- | ------- | ------------------------------------------ | --------------------------------------------------- |
| AC-1: Bitemporal fields     | T-001   | `tests/unit/test_branch_model.py`          | Branch has `valid_time`, `transaction_time` columns |
| AC-2: Time-travel queries   | T-002   | `tests/integration/test_branch_service.py` | `get_as_of()` returns branch at timestamp           |
| AC-3: branch_id UUID        | T-003   | `tests/unit/test_branch_model.py`          | New branch has auto-generated `branch_id`           |
| AC-4: Lock updates in-place | T-004   | `tests/unit/test_branch_service.py`        | Lock/unlock modifies existing row                   |
| AC-5: Frontend as_of        | T-005   | Manual                                     | BranchSelector shows branches valid at `as_of`      |
| AC-6: Migration             | T-006   | Migration script                           | Existing branches have valid temporal ranges        |

---

## Test Specification

### Test Hierarchy

```text
├── Unit Tests (tests/unit/)
│   ├── test_branch_model.py (T-001, T-003)
│   │   ├── test_branch_has_temporal_fields (NEW)
│   │   └── test_branch_has_branch_id_uuid (NEW)
│   └── test_branch_service.py (T-004)
│       └── test_lock_updates_in_place (NEW)
├── Integration Tests (tests/integration/)
│   └── test_branch_service.py (T-002) (EXISTING - extend)
│       └── test_branch_get_as_of_time_travel (NEW)
└── Manual Verification (T-005)
    └── BranchSelector shows correct branches at control_date
```

### Test Cases

| Test ID | Test Name                           | Criterion | Type        | Expected Result                                    |
| ------- | ----------------------------------- | --------- | ----------- | -------------------------------------------------- |
| T-001   | `test_branch_has_temporal_fields`   | AC-1      | Unit        | Branch has `valid_time`, `transaction_time` mapped |
| T-002   | `test_branch_get_as_of_time_travel` | AC-2      | Integration | Branch visible at/after creation, not before       |
| T-003   | `test_branch_has_branch_id_uuid`    | AC-3      | Unit        | `branch_id` is UUID, indexed                       |
| T-004   | `test_lock_updates_in_place`        | AC-4      | Unit        | Lock toggle doesn't create new version             |
| T-005   | Manual: BranchSelector temporal     | AC-5      | Manual      | Selector filters by `as_of`                        |

### Test Infrastructure Needs

- **Fixtures:** Use existing `db_session` from `conftest.py`
- **Mocks:** None required (database integration)
- **Database state:** Create branch at T1, query at T0 (before) and T2 (after)

---

## Proposed Changes

### Backend: Models

#### [MODIFY] [branch.py](file:///home/nicola/dev/backcast_evs/backend/app/models/domain/branch.py)

- Add `VersionableMixin` to class inheritance
- Add `branch_id: UUID` with `index=True`
- Remove `created_at` (derived from `valid_time.lower`)
- Keep `deleted_at` (from `VersionableMixin`)
- Preserve composite PK `(name, project_id)` for lookups

---

### Backend: Services

#### [MODIFY] [branch_service.py](file:///home/nicola/dev/backcast_evs/backend/app/services/branch_service.py)

- Inherit from `TemporalService[Branch]` (for `_apply_bitemporal_filter`)
- Add `get_as_of(name, project_id, as_of)` method
- Add `list_branches_as_of(project_id, as_of)` method
- Modify `lock()`/`unlock()` to update in-place (not create new version)
- Update `get_by_name_and_project` to filter by temporal context

---

### Backend: Schemas

#### [MODIFY] [branch.py](file:///home/nicola/dev/backcast_evs/backend/app/models/schemas/branch.py)

- Add `branch_id: UUID` to `BranchPublic`
- Add `created_at: datetime` (derived from temporal range)
- Add `BranchRead` schema if not existing

---

### Backend: API Routes

#### [MODIFY] Branch routes (if separate file exists, or in change_orders.py)

- Add `as_of: datetime | None = Query(None)` parameter to list/get endpoints
- Update route to pass `as_of` to service methods

---

### Backend: Migration

#### [NEW] Migration file

```
alembic/versions/XXXX_add_temporal_to_branches.py
```

- Add `branch_id` UUID column with `DEFAULT gen_random_uuid()`
- Add `valid_time` TSTZRANGE column with `DEFAULT tstzrange(NOW(), NULL, '[]')`
- Add `transaction_time` TSTZRANGE column with `DEFAULT tstzrange(NOW(), NULL, '[]')`
- Populate `branch_id` for existing rows
- Remove `created_at` column (or keep as computed/derived)
- Add GiST index on `valid_time`

---

### Frontend: API

#### [MODIFY] [queryKeys.ts](file:///home/nicola/dev/backcast_evs/frontend/src/api/queryKeys.ts)

- Add `branches` entry with `list(projectId, context?)` method
- Include `asOf` in context for cache isolation

---

### Frontend: Components

#### [MODIFY] [BranchSelector.tsx](file:///home/nicola/dev/backcast_evs/frontend/src/components/time-machine/BranchSelector.tsx) or related hook

- Accept `asOf` prop or use `useTimeMachineParams()`
- Pass `asOf` to branch fetch API call

---

## Verification Plan

### Automated Tests

**Command to run all backend tests:**

```bash
cd backend && uv run pytest tests/unit/test_branch*.py tests/integration/test_branch_service.py -v
```

**Command to run mypy:**

```bash
cd backend && uv run mypy --config pyproject.toml app/models/domain/branch.py app/services/branch_service.py
```

**Command to run ruff:**

```bash
cd backend && uv run ruff check app/models/domain/branch.py app/services/branch_service.py
```

### Manual Verification

**Steps to verify frontend BranchSelector temporal support:**

1. Start backend: `cd backend && ./scripts/run-dev.sh`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to a project with change orders
4. Open Time Machine and set control date to a date BEFORE a change order was created
5. **Expected:** The change order branch should NOT appear in the branch selector
6. Set control date to a date AFTER the change order was created
7. **Expected:** The change order branch SHOULD appear in the branch selector

---

## Risk Assessment

| Risk Type   | Description                                              | Probability | Impact | Mitigation                                        |
| ----------- | -------------------------------------------------------- | ----------- | ------ | ------------------------------------------------- |
| Technical   | Composite PK with temporal fields may complicate queries | Low         | Med    | Use `branch_id` for DAG, composite PK for lookup  |
| Migration   | Existing data may have NULL temporal ranges              | Low         | High   | DEFAULT values in migration, validate with SELECT |
| Integration | ChangeOrder → Branch reference may break                 | Med         | Med    | Test branch-CO relationship explicitly            |

---

## Prerequisites & Dependencies

### Technical Prerequisites

- [x] Database migrations up to date
- [x] Backend dev server running
- [x] Frontend dev server running

### Documentation Prerequisites

- [x] Analysis phase approved
- [x] Architecture docs reviewed
- [x] Temporal query reference understood

---

## References

- [Temporal Query Reference](file:///home/nicola/dev/backcast_evs/docs/02-architecture/cross-cutting/temporal-query-reference.md)
- [EVCS Implementation Guide](file:///home/nicola/dev/backcast_evs/docs/02-architecture/backend/contexts/evcs-core/evcs-implementation-guide.md)
- [Entity Classification Guide](file:///home/nicola/dev/backcast_evs/docs/02-architecture/backend/contexts/evcs-core/entity-classification.md)
- [Frontend State & Data](file:///home/nicola/dev/backcast_evs/docs/02-architecture/frontend/contexts/02-state-data.md)
