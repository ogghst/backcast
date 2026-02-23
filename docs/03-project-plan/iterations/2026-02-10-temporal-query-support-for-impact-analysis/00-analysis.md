# Analysis: Impact Analysis Service Temporal Query Support

**Created:** 2026-02-10
**Related Iteration:** [2026-02-10-impact-analysis-temporal-query-support](../2026-02-10-impact-analysis-temporal-query-support/)

---

## Executive Summary

The `impact_analysis_service.py` file does not properly handle the `as_of` date parameter according to architectural standards. While partial implementation exists (WBE queries use temporal filters), **10+ query locations still use hardcoded "current version" filters**, causing time-travel queries to return incorrect results.

**Impact**: Users cannot perform historical impact analysis (e.g., "show impact as of January 15th") because many queries return current data instead of historical data.

---

## Clarified Requirements

### User Request

> "impact_analysis_service.py does not take into account the as_of date as per temporal-query-reference.md and evm-api-guide.md and api-conventions.md. the impact analysis shall be done considering also the control date."

### Functional Requirements

1. **API Route**: Accept `as_of` query parameter for time-travel queries
2. **Service Methods**: ALL methods must thread `as_of` parameter through call chain
3. **Database Queries**: ALL queries must use temporal filters (no hardcoded "current" filters)
4. **EVM Integration**: Pass `as_of` to EVM service as `control_date`
5. **Backward Compatibility**: Default `as_of` to `datetime.now(UTC)`

### Non-Functional Requirements

- **Pattern Compliance**: Must follow `TemporalService._apply_bitemporal_filter()` pattern
- **Performance**: No degradation (temporal indexes exist)
- **Testability**: Comprehensive integration tests validate temporal behavior

### Constraints

- Must follow [temporal-query-reference.md](../../../../02-architecture/cross-cutting/temporal-query-reference.md)
- Must follow [api-conventions.md](../../../../02-architecture/cross-cutting/api-conventions.md) for query parameters
- Must follow [evm-api-guide.md](../../../../02-architecture/evm-api-guide.md) for EVM integration

---

## Current State Analysis

### What's Already Implemented (Partial)

**Completed:**
- `_apply_temporal_filter()` helper method exists (lines 73-116)
- `analyze_impact()` accepts `as_of` parameter with default (line 125)
- `_perform_analysis()` accepts `as_of` parameter (line 227)
- `_compare_entities()` accepts `as_of` parameter (line 521)
- WBE queries use `_apply_temporal_filter()` (lines 550, 560)

**Evidence from code:**
```python
# ✅ GOOD: WBE queries use temporal filter
main_wbes_stmt = self._apply_temporal_filter(main_wbes_stmt, WBE, as_of)
```

### What's Still Missing (Critical Gaps)

**Gap 1: API Route Missing `as_of` Parameter**

**File**: `backend/app/api/routes/change_orders.py`

```python
# ❌ CURRENT: No as_of parameter
@router.get("/{change_order_id}/impact")
async def get_change_order_impact(
    change_order_id: UUID,
    branch_name: str = Query(...),
    mode: str = Query("merged", ...),
) -> ImpactAnalysisResponse:
    # as_of is hardcoded or not passed
```

**Gap 2: CostElement Queries Use Hardcoded "Current" Filter**

**File**: `impact_analysis_service.py`, lines 588-614

```python
# ❌ CURRENT: Ignores as_of parameter
main_ce_stmt = (
    select(CostElement)
    .join(WBE, CostElement.wbe_id == WBE.wbe_id)
    .where(
        WBE.project_id == project_id,
        CostElement.branch == "main",
        func.upper(cast(Any, CostElement).valid_time).is_(None),  # ❌ Hardcoded
        cast(Any, CostElement).deleted_at.is_(None),              # ❌ No temporal check
    )
)
```

**Gap 3: CostRegistration Queries Use Hardcoded "Current" Filter**

**File**: `impact_analysis_service.py`, lines 639-667

```python
# ❌ CURRENT: Ignores as_of parameter
main_cr_stmt = (
    select(CostRegistration)
    .join(CostElement, CostRegistration.cost_element_id == CostElement.cost_element_id)
    .where(
        WBE.project_id == project_id,
        CostElement.branch == "main",
        CostRegistration.deleted_at.is_(None),
        func.upper(CostRegistration.valid_time).is_(None),  # ❌ Hardcoded
    )
)
```

**Gap 4: ScheduleBaseline Queries Use Hardcoded "Current" Filter**

**File**: `impact_analysis_service.py`, lines 1250-1333

```python
# ❌ CURRENT: Ignores as_of parameter
main_sb_stmt = select(ScheduleBaseline).where(
    ScheduleBaseline.schedule_baseline_id.in_(main_baseline_ids),
    ScheduleBaseline.branch == "main",
    func.upper(cast(Any, ScheduleBaseline).valid_time).is_(None),  # ❌ Hardcoded
    cast(Any, ScheduleBaseline).deleted_at.is_(None),
)
```

**Gap 5: EVM Service Uses Hardcoded `datetime.now(UTC)`**

**File**: `impact_analysis_service.py`, line 1432

```python
# ❌ CURRENT: Hardcoded
control_date = datetime.now(UTC)

# ✅ REQUIRED:
control_date = as_of  # Pass from parameter
```

**Gap 6: Time-Series Generation Uses Hardcoded "Current" Filter**

**File**: `impact_analysis_service.py`, lines 1035-1080

```python
# ❌ CURRENT: Ignores as_of parameter
main_budget_stmt = select(func.sum(WBE.budget_allocation)).where(
    WBE.project_id == project_id,
    WBE.branch == "main",
    func.upper(cast(Any, WBE).valid_time).is_(None),  # ❌ Hardcoded
    cast(Any, WBE).deleted_at.is_(None),
)
```

### Gap Summary Table

| Line(s)  | Method                               | Entity         | Current Filter                      | Required Fix                     |
| -------- | ------------------------------------ | -------------- | ----------------------------------- | -------------------------------- |
| 528-571  | (API Route)                          | N/A            | `as_of` parameter missing            | Add query parameter               |
| 588-614  | `_compare_entities`                  | CostElement    | `upper(valid_time).is_(None)`        | Use `_apply_temporal_filter`      |
| 639-667  | `_compare_entities`                  | CostRegistration | `upper(valid_time).is_(None)`      | Use `_apply_temporal_filter`      |
| 1035-1080| `_generate_time_series`              | WBE            | `upper(valid_time).is_(None)`        | Use `_apply_temporal_filter`      |
| 1271-1333| `_fetch_and_compare_schedule_baselines` | CostElement/ScheduleBaseline | `upper(valid_time).is_(None)` | Use `_apply_temporal_filter` |
| 1432     | `_fetch_and_compare_evm_metrics`     | N/A            | `datetime.now(UTC)` hardcoded        | Use `as_of` parameter              |

**Total**: 10+ locations requiring fixes

---

## Architectural Pattern Review

### TemporalService Pattern (Required)

Per [`TemporalService._apply_bitemporal_filter`](../../../../backend/app/core/versioning/service.py#L243-L277):

```python
def _apply_bitemporal_filter(self, stmt: Any, as_of: datetime) -> Any:
    """Apply standardized bitemporal WHERE clauses."""
    from sqlalchemy import cast as sql_cast, func, or_
    from sqlalchemy.dialects.postgresql import TIMESTAMP

    as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))

    return stmt.where(
        self.entity_class.valid_time.op("@>")(as_of_tstz),
        func.lower(self.entity_class.valid_time) <= as_of_tstz,
        or_(
            self.entity_class.deleted_at.is_(None),
            self.entity_class.deleted_at > as_of_tstz
        )
    )
```

**Key Requirements:**
1. MUST cast `as_of` to `TIMESTAMP(timezone=True)` for proper timezone handling
2. MUST check both `@>` operator AND lower bound
3. MUST check `deleted_at` temporally (not just `IS NULL`)

### ImpactAnalysisService Already Has This Pattern

The service already has `_apply_temporal_filter()` (lines 73-116) that correctly implements this pattern:

```python
def _apply_temporal_filter(
    self, stmt: Any, entity_class: type, as_of: datetime
) -> Any:
    """Apply standardized bitemporal filter (mirrors TemporalService pattern).

    Filters for:
    - valid_time contains as_of (time travel based on business validity)
    - deleted_at IS NULL OR deleted_at > as_of
    """
    from sqlalchemy import cast as sql_cast, func, or_
    from sqlalchemy.dialects.postgresql import TIMESTAMP

    as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))

    return stmt.where(
        entity_class.valid_time.op("@>")(as_of_tstz),
        func.lower(entity_class.valid_time) <= as_of_tstz,
        or_(
            entity_class.deleted_at.is_(None),
            entity_class.deleted_at > as_of_tstz,
        ),
    )
```

**The problem**: This helper exists but is NOT used in 10+ query locations.

---

## Solution Options

### Option 1: Comprehensive Fix (Recommended)

**Description**: Replace ALL hardcoded "current" filters with `_apply_temporal_filter()` calls.

**Pros:**
- Full compliance with temporal-query-reference.md
- Consistent behavior across all queries
- Proper time-travel support
- Testable with integration tests

**Cons:**
- ~10-15 locations to update
- Requires careful testing

**Complexity**: Medium

### Option 2: Partial Fix (Not Recommended)

**Description**: Only fix critical paths, leave some queries with hardcoded filters.

**Pros:**
- Less work upfront

**Cons:**
- Inconsistent behavior
- Time-travel queries still return wrong results in some cases
- Violates architectural standards
- Harder to maintain

**Complexity**: Low

**Recommendation**: Option 1 - Comprehensive Fix

---

## Implementation Strategy

### Architecture

**Routes → Services → Database**

1. Route accepts `as_of` query parameter (defaults to `now()`)
2. Service threads `as_of` through ALL method signatures
3. ALL database queries use `_apply_temporal_filter()` helper
4. EVM service receives `as_of` as `control_date`

**No commands layer** (read operations only)

### Step-by-Step Implementation

#### Step 1: API Route (BE-001)

**File**: `backend/app/api/routes/change_orders.py`

Add `as_of` query parameter to `get_change_order_impact` endpoint.

#### Step 2: Service Method Signatures (BE-002 to BE-004)

**File**: `backend/app/services/impact_analysis_service.py`

Ensure these methods accept `as_of`:
- `_generate_time_series()` - currently missing `as_of` parameter
- `_fetch_and_compare_schedule_baselines()` - currently missing `as_of` parameter
- `_fetch_and_compare_evm_metrics()` - currently missing `as_of` parameter

#### Step 3: Query Replacements (BE-005 to BE-010)

Replace hardcoded filters with `_apply_temporal_filter()` in:
- CostElement queries (lines 588-614)
- CostRegistration queries (lines 639-667)
- Time-series WBE queries (lines 1035-1080)
- ScheduleBaseline queries (lines 1271-1333)
- EVM service call (line 1432)

#### Step 4: Integration Tests (BE-011 to BE-013)

**File**: `backend/tests/integration/test_impact_analysis_temporal.py` (NEW)

Test scenarios:
1. Query at T0 (before changes) → delta = 0
2. Query at T1 (after branch changes) → delta = +20k
3. Query at T2 (after branch revert) → delta = 0
4. EVM metrics respect control_date (AC increases over time)
5. Deleted entities handled correctly

#### Step 5: Quality Gates (BE-014 to BE-015)

- mypy strict mode
- ruff linting
- All existing tests pass

---

## Verification Plan

### Automated Tests

```bash
# New integration tests
pytest backend/tests/integration/test_impact_analysis_temporal.py -v

# Existing tests (regression)
pytest backend/tests/api/test_impact_analysis.py -v
pytest backend/tests/integration/test_change_order_impact_analysis_serialization.py -v
```

### Manual Verification

Using Swagger UI (`http://localhost:8000/docs`):

1. Test without `as_of` (baseline)
2. Test with `as_of=2026-01-15T10:00:00Z` (historical)
3. Verify different `as_of` values return different deltas

---

## Trade-offs

| Aspect            | Assessment                                           |
| ----------------- | ---------------------------------------------------- |
| Pros              | Full compliance; Complete temporal support; Testable |
| Cons              | ~15 query locations to update                        |
| Complexity        | Medium (systematic, repetitive changes)              |
| Maintainability   | Excellent (follows TemporalService pattern)          |
| Performance       | Same (temporal indexes exist)                        |
| Architectural Fit | Perfect (mirrors established patterns)               |

---

## Estimated Effort

- API route changes: 10 minutes
- Service signature updates: 15 minutes
- Query replacements (~10 locations): 45 minutes
- Integration tests: 45 minutes
- Manual verification: 15 minutes

**Total**: ~2 hours

---

## References

- [Temporal Query Reference](../../../../02-architecture/cross-cutting/temporal-query-reference.md)
- [TemporalService._apply_bitemporal_filter](../../../../backend/app/core/versioning/service.py#L243-L277)
- [EVM API Guide](../../../../02-architecture/evm-api-guide.md)
- [API Conventions](../../../../02-architecture/cross-cutting/api-conventions.md)
- [Related Iteration](../2026-02-10-impact-analysis-temporal-query-support/)
