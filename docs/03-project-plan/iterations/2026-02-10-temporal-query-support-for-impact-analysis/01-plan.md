# PLAN: Impact Analysis Temporal Query Support

**Created:** 2026-02-10
**Analysis Reference:** [`00-analysis.md`](./00-analysis.md)

---

## Phase 1: Scope & Success Criteria

### 1.1 Approved Approach

- **Selected Option**: Comprehensive Fix - Replace ALL hardcoded "current" filters with `_apply_temporal_filter()` calls
- **Architecture**: Routes → Services → Database (no commands for read operations)
- **Key Decisions**:
  - Add `as_of` query parameter to API route
  - Update all service method signatures to accept `as_of`
  - Replace ~10-15 hardcoded queries with temporal filters
  - Pass `as_of` to EVM service as `control_date`
  - Maintain backward compatibility (default `as_of = datetime.now(UTC)`)

### 1.2 Success Criteria (Measurable)

**Functional Criteria:**

- [ ] Impact analysis endpoint accepts `as_of` query parameter
- [ ] Query at T0 returns baseline metrics (delta = 0)
- [ ] Query at T1 returns modified metrics (delta = +20k)
- [ ] Query at T2 returns reverted metrics (delta = 0)
- [ ] EVM metrics respect control_date (AC increases over time)
- [ ] Deleted entities not visible after deletion date
- [ ] Default behavior unchanged (backward compatible)

**Technical Criteria:**

- [ ] Performance: No degradation vs current implementation
- [ ] Code Quality: mypy strict + ruff clean
- [ ] Pattern Compliance: Uses TemporalService pattern

### 1.3 Scope Boundaries

**In Scope:**

- API route parameter addition (`as_of` query param)
- Service method signature updates (3 methods missing `as_of`)
- Query replacements (~10 locations)
- EVM service integration (pass `control_date`)
- Integration tests (3 scenarios)

**Out of Scope:**

- Frontend Time Machine integration (future iteration)
- Refactoring to inherit from TemporalService (future consideration)

---

## Phase 2: Work Decomposition

### 2.1 Task Breakdown

| #   | Task                                         | Files                              | Dependencies | Success Criteria                          | Complexity |
| --- | -------------------------------------------- | ---------------------------------- | ------------ | ----------------------------------------- | ---------- |
| 1   | Add `as_of` parameter to API route           | `change_orders.py`                 | none         | OpenAPI schema shows `as_of` param         | Low        |
| 2   | Update `_generate_time_series` signature     | `impact_analysis_service.py`       | none         | Method accepts `as_of` parameter           | Low        |
| 3   | Update `_fetch_and_compare_schedule_baselines` | `impact_analysis_service.py`       | none         | Method accepts `as_of` parameter           | Low        |
| 4   | Update `_fetch_and_compare_evm_metrics`      | `impact_analysis_service.py`       | none         | Method accepts `as_of` parameter           | Low        |
| 5   | Fix CostElement queries in `_compare_entities` | `impact_analysis_service.py`       | Task 2       | 2 queries use temporal filter              | Medium     |
| 6   | Fix CostRegistration queries in `_compare_entities` | `impact_analysis_service.py` | Task 2       | 2 queries use temporal filter              | Medium     |
| 7   | Fix time-series WBE queries                  | `impact_analysis_service.py`       | Task 2       | 2 queries use temporal filter              | Medium     |
| 8   | Fix ScheduleBaseline queries                 | `impact_analysis_service.py`       | Task 3       | 4 queries use temporal filter              | Medium     |
| 9   | Fix EVM service hardcoded `now()`            | `impact_analysis_service.py`       | Task 4       | Passes `as_of` to EVM service              | Low        |
| 10  | Write integration test - temporal variations | `test_impact_analysis_temporal.py` | Tasks 1-9    | Test passes: T0/T1/T2 scenarios            | Medium     |
| 11  | Write integration test - EVM temporal        | `test_impact_analysis_temporal.py` | Tasks 1-9    | Test passes: AC increases over time        | Medium     |
| 12  | Write integration test - deleted entities    | `test_impact_analysis_temporal.py` | Tasks 1-9    | Test passes: deleted entity handling       | Medium     |
| 13  | Verify existing tests pass                   | All existing test files            | Tasks 1-9    | All existing tests pass                    | Low        |
| 14  | Run quality gates                            | All files                          | Tasks 1-13   | mypy strict + ruff clean                   | Low        |
| 15  | Manual verification via Swagger              | N/A                                | Tasks 1-9    | Historical queries return different results | Low        |

### 2.2 Test-to-Requirement Traceability

| Acceptance Criterion                        | Test ID | Test File                        | Expected Behavior                                           |
| ------------------------------------------- | ------- | -------------------------------- | ----------------------------------------------------------- |
| Impact analysis accepts `as_of` parameter   | T-001   | Manual (Swagger UI)              | Parameter appears in OpenAPI schema                         |
| Query at T0 returns baseline (delta = 0)    | T-002   | `test_impact_analysis_temporal.py` | `test_...at_different_control_dates` asserts delta = 0      |
| Query at T1 returns modified (delta = +20k) | T-003   | `test_impact_analysis_temporal.py` | `test_...at_different_control_dates` asserts delta > 0      |
| Query at T2 returns reverted (delta = 0)    | T-004   | `test_impact_analysis_temporal.py` | `test_...at_different_control_dates` asserts delta = 0      |
| EVM metrics respect control_date            | T-005   | `test_impact_analysis_temporal.py` | `test_...evm_metrics_temporal` asserts AC increases         |
| Deleted entities not visible after deletion | T-006   | `test_impact_analysis_temporal.py` | `test_...deleted_entities_temporal` asserts count decreases |
| Backward compatible (default to now)        | T-007   | `test_impact_analysis.py` (existing) | All existing tests pass                                     |

---

## Phase 3: Test Specification

### 3.1 Test Hierarchy

```text
├── Integration Tests (tests/integration/)
│   └── test_impact_analysis_temporal.py (NEW)
│       ├── test_impact_analysis_at_different_control_dates (T-002, T-003, T-004)
│       ├── test_impact_analysis_evm_metrics_temporal (T-005)
│       └── test_impact_analysis_deleted_entities_temporal (T-006)
└── API Tests (tests/api/)
    └── test_impact_analysis.py (EXISTING - must still pass)
```

### 3.2 Test Cases

| Test ID | Test Name                                      | Criterion | Type        | Expected Result                          |
| ------- | ---------------------------------------------- | --------- | ----------- | ---------------------------------------- |
| T-002   | test_impact_analysis_at_different_control_dates (T0) | AC-2    | Integration | `kpi_scorecard.bac.delta == "0.00"`      |
| T-003   | test_impact_analysis_at_different_control_dates (T1) | AC-3    | Integration | `kpi_scorecard.bac.delta == "20000.00"`  |
| T-004   | test_impact_analysis_at_different_control_dates (T2) | AC-4    | Integration | `kpi_scorecard.bac.delta == "0.00"`      |
| T-005   | test_impact_analysis_evm_metrics_temporal              | AC-5    | Integration | `ac_t2 > ac_t1` (AC increases over time) |
| T-006   | test_impact_analysis_deleted_entities_temporal         | AC-6    | Integration | `len(wbes_t1) < len(wbes_t0)`            |
| T-007   | test_get_impact_success (existing)                     | AC-7    | Integration | Passes without `as_of` param             |

---

## Phase 4: Implementation Guide

### File 1: `backend/app/api/routes/change_orders.py`

**Changes:**

Add `as_of` parameter to `get_change_order_impact` function (around line 528).

```python
@router.get("/{change_order_id}/impact", ...)
async def get_change_order_impact(
    change_order_id: UUID,
    branch_name: str = Query(...),
    mode: str = Query("merged", ...),
    as_of: datetime | None = Query(
        None,
        description="Time-travel date: view impact as of this timestamp (ISO 8601)"
    ),
    service: ImpactAnalysisService = Depends(...),
) -> ImpactAnalysisResponse:
    """Get impact analysis with temporal query support."""
    from datetime import UTC

    # Default to current time (backward compatible)
    if as_of is None:
        as_of = datetime.now(UTC)

    branch_mode = BranchMode.MERGE if mode == "merged" else BranchMode.STRICT

    return await service.analyze_impact(
        change_order_id,
        branch_name,
        branch_mode=branch_mode,
        as_of=as_of,
    )
```

### File 2: `backend/app/services/impact_analysis_service.py`

**Section 1: Method Signatures (3 methods to add `as_of`)**

1. `_generate_time_series()` (line ~1035):
   - Add `as_of: datetime` parameter
   - Pass through to queries

2. `_fetch_and_compare_schedule_baselines()` (line ~1250):
   - Add `as_of: datetime` parameter
   - Pass through to queries

3. `_fetch_and_compare_evm_metrics()` (line ~1413):
   - Add `as_of: datetime` parameter
   - Use for `control_date` in EVM service call

**Section 2: Query Replacements (~10 locations)**

```python
# ❌ BEFORE (CostElement queries, lines 588-614):
main_ce_stmt = (
    select(CostElement)
    .join(WBE, CostElement.wbe_id == WBE.wbe_id)
    .where(
        WBE.project_id == project_id,
        CostElement.branch == "main",
        func.upper(cast(Any, CostElement).valid_time).is_(None),
        cast(Any, CostElement).deleted_at.is_(None),
    )
)

# ✅ AFTER:
main_ce_stmt = (
    select(CostElement)
    .join(WBE, CostElement.wbe_id == WBE.wbe_id)
    .where(
        WBE.project_id == project_id,
        CostElement.branch == "main",
    )
)
main_ce_stmt = self._apply_temporal_filter(main_ce_stmt, CostElement, as_of)
```

Apply this pattern to:
- CostElement queries in `_compare_entities` (2 locations)
- CostRegistration queries in `_compare_entities` (2 locations)
- WBE queries in `_generate_time_series` (2 locations)
- CostElement/ScheduleBaseline queries in `_fetch_and_compare_schedule_baselines` (4 locations)
- EVM service call in `_fetch_and_compare_evm_metrics` (1 location)

### File 3: `backend/tests/integration/test_impact_analysis_temporal.py` (NEW)

**Structure:**

```python
"""Integration tests for impact analysis temporal query support."""
import pytest
from datetime import datetime, UTC

@pytest.mark.asyncio
async def test_impact_analysis_at_different_control_dates(
    session, seeded_project_temporal, seeded_change_order
):
    """Test impact analysis returns different results at T0, T1, T2."""
    # T0: Before changes - delta should be 0
    as_of_t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    result_t0 = await service.analyze_impact(
        change_order_id, branch_name, as_of=as_of_t0
    )
    assert result_t0.kpi_scorecard.bac.delta == 0

    # T1: After changes - delta should be positive
    as_of_t1 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    result_t1 = await service.analyze_impact(
        change_order_id, branch_name, as_of=as_of_t1
    )
    assert result_t1.kpi_scorecard.bac.delta > 0

    # T2: After revert - delta should be 0
    as_of_t2 = datetime(2026, 2, 1, 12, 0, 0, tzinfo=UTC)
    result_t2 = await service.analyze_impact(
        change_order_id, branch_name, as_of=as_of_t2
    )
    assert result_t2.kpi_scorecard.bac.delta == 0

@pytest.mark.asyncio
async def test_impact_analysis_evm_metrics_temporal(...):
    """Test EVM metrics respect control_date (AC increases)."""
    ...

@pytest.mark.asyncio
async def test_impact_analysis_deleted_entities_temporal(...):
    """Test deleted entities not visible after deletion date."""
    ...
```

---

## Phase 5: Verification Plan

### Automated Tests

```bash
# New integration tests
pytest backend/tests/integration/test_impact_analysis_temporal.py -v

# Existing tests (regression)
pytest backend/tests/api/test_impact_analysis.py -v
pytest backend/tests/integration/test_change_order_impact_analysis_serialization.py -v

# Type checking
cd backend && mypy app/services/impact_analysis_service.py app/api/routes/change_orders.py --strict

# Linting
cd backend && ruff check app/services/impact_analysis_service.py app/api/routes/change_orders.py
```

### Manual Verification

Using Swagger UI (`http://localhost:8000/docs`):

1. **Test 1: Without `as_of` (baseline)**
   - Enter valid `change_order_id` from seed data
   - Enter `branch_name` (e.g., "BR-CO-2026-001")
   - Leave `as_of` empty
   - Expected: 200 OK, returns current impact metrics

2. **Test 2: With historical `as_of`**
   - Same parameters as Test 1
   - Set `as_of` to `2026-01-15T10:00:00Z`
   - Expected: 200 OK, returns metrics as of that date

3. **Test 3: With future `as_of`**
   - Same parameters as Test 1
   - Set `as_of` to `2026-12-31T23:59:59Z`
   - Expected: 200 OK, returns projected future metrics

---

## Phase 6: Risk Assessment

| Risk Type   | Description                                                | Probability | Impact | Mitigation                                             |
| ----------- | ---------------------------------------------------------- | ----------- | ------ | ------------------------------------------------------ |
| Technical   | Timezone handling issues with `as_of` casting              | Medium      | Medium | Use explicit `TIMESTAMP(timezone=True)` cast in helper |
| Technical   | Missing temporal filters in edge cases                     | Low         | High   | Systematic code review of ALL queries                  |
| Integration | Existing tests fail due to signature changes               | Low         | Medium | Maintain backward compatibility with default `as_of`   |
| Integration | EVM service returns incorrect data with old `control_date` | Low         | High   | Explicit integration test for EVM temporal behavior    |

---

## Phase 7: Prerequisites & Dependencies

### Technical Prerequisites

- [x] Database migrations applied (no new migrations needed)
- [x] Dependencies installed (no new dependencies)
- [x] Environment configured (dev-start.sh running)

### Documentation Prerequisites

- [x] Analysis phase approved
- [x] Temporal query reference reviewed
- [x] TemporalService pattern understood

### Code Prerequisites

- [ ] All existing tests passing (verify before starting)

---

## Estimated Effort

- API route changes: 10 min
- Method signature updates: 15 min
- Query replacements (~10 locations): 45 min
- Integration tests: 45 min
- Quality gates: 15 min
- Manual verification: 15 min

**Total:** ~2.5 hours

---

## Key Principles

1. **Sequential execution**: Complete tasks in order (dependencies)
2. **Test-first mindset**: Write test specs in PLAN, implement in DO phase
3. **Pattern compliance**: Mirror `TemporalService._apply_bitemporal_filter`
4. **Backward compatibility**: Default `as_of = now()` preserves existing behavior
5. **Comprehensive coverage**: Update ALL helper methods and queries

---

## References

- [Analysis Document](./00-analysis.md)
- [Temporal Query Reference](../../../../02-architecture/cross-cutting/temporal-query-reference.md)
- [TemporalService Pattern](../../../../backend/app/core/versioning/service.py#L243-L277)
- [API Conventions](../../../../02-architecture/cross-cutting/api-conventions.md)
- [EVM API Guide](../../../../02-architecture/evm-api-guide.md)
