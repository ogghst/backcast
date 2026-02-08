# Change Order Seed Data

Comprehensive seed data for testing change order impact analysis with full EVCS (Entity Versioning Control System) compliance.

## Overview

This seed data demonstrates 6 different change order scenarios with complete bitemporal versioning, branch isolation, and impact analysis capabilities.

## Change Order Scenarios

### CO-2026-001: Scope Addition

**Branch:** `BR-a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d`
**Status:** Draft
**Impact:** MEDIUM

**Changes:**

- Adds 2 new L3 WBEs (secondary conveyor system)
- Adds 5 new cost elements (LAB, MAT, EQP, SUB, TRV)
- Adds 5 new schedule baselines
- Budget Impact: +$150,000 (+15%)
- Timeline Impact: +3 months (extended to 2026-06-30)

**Use Case:** Testing budget increases and timeline extensions from pure scope addition.

---

### CO-2026-002: Scope Modification

**Branch:** `BR-b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e`
**Status:** Submitted for Approval
**Impact:** HIGH

**Changes:**

- Modifies 3 existing WBEs (safety upgrades)
- Modifies 3 existing cost elements (+10% budget each)
- Modifies 3 existing schedule baselines (extended +2 weeks)
- Budget Impact: +$45,000 (+4.5%)
- Timeline Impact: +2 weeks

**Use Case:** Testing budget reallocation and minor schedule adjustments on existing entities.

---

### CO-2026-006: Scope Reduction (REJECTED)

**Branch:** `BR-f6a7b8c9-d0e1-4f6a-3b4c-5d6e7f8a9b0c`
**Status:** Rejected
**Impact:** HIGH

**Changes:**

- Soft-deletes 2 existing L3 WBEs
- Soft-deletes 2 existing cost elements
- Soft-deletes 2 existing schedule baselines
- Budget Impact: -$125,000 (-12.5%)
- Timeline Impact: -1 month
- **Status:** REJECTED (data preserved for analysis)

**Use Case:** Testing soft delete pattern, rejection workflow, and revert capability.

---

### CO-2026-003: Schedule Adjustment Only

**Branch:** `BR-c3d4e5f6-a7b8-4c5d-0e1f-2a3b4c5d6e7f`
**Status:** Approved
**Impact:** LOW

**Changes:**

- Modifies 5 existing schedule baselines only
- Changes progression type: LINEAR → GAUSSIAN
- No WBE or cost element changes
- Budget Impact: $0
- Timeline Impact: 0 days (progression curve change only)

**Use Case:** Testing schedule modification without budget impact (S-curve effect).

---

### CO-2026-004: Cost Reallocation

**Branch:** `BR-d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a`
**Status:** Draft
**Impact:** MEDIUM

**Changes:**

- Modifies 5 existing cost elements only
- LAB cost elements: +$20K × 2 = +$40K
- MAT cost elements: -$13.33K × 3 = -$40K
- No WBE or schedule baseline changes
- Budget Impact: $0 (internal reallocation)
- Timeline Impact: None

**Use Case:** Testing internal budget transfers without net change.

---

### CO-2026-005: Critical Scope Addition

**Branch:** `BR-e5f6a7b8-c9d0-4e5f-2a3b-4c5d6e7f8a9b`
**Status:** Submitted for Approval
**Impact:** CRITICAL

**Changes:**

- Adds complete 5-WBE hierarchy (1 L1, 2 L2, 2 L3)
- Adds 25 new cost elements (5 per WBE)
- Adds 25 new schedule baselines
- Budget Impact: +$375,000 (+37.5%)
- Timeline Impact: +6 months (extended to 2026-08-31)

**Use Case:** Testing large-scale scope addition and complete hierarchy creation.

## Entity Counts

| Entity Type | Main Branch | Branch Versions | Total |
|-------------|-------------|------------------|-------|
| **WBEs** | 20 | 12 | 32 |
| **Cost Elements** | 100 | 40 | 140 |
| **Schedule Baselines** | 100 | 40 | 140 |
| **Branches** | - | 6 | 6 |

## Budget Impact Summary

| Change Order | Original | Modified | Delta | % Change |
|--------------|----------|----------|-------|----------|
| **Main** | $1,000,000 | $1,000,000 | $0 | 0% |
| **CO-A** | $1,000,000 | $1,150,000 | +$150,000 | +15% |
| **CO-B** | $1,000,000 | $1,045,000 | +$45,000 | +4.5% |
| **CO-C** | $1,000,000 | $875,000 | -$125,000 | -12.5% |
| **CO-D** | $1,000,000 | $1,000,000 | $0 | 0% |
| **CO-E** | $1,000,000 | $1,000,000 | $0 | 0% (realloc) |
| **CO-F** | $1,000,000 | $1,375,000 | +$375,000 | +37.5% |

## Timeline Impact Summary

| Change Order | Original Duration | Modified Duration | Delta | Impact Type |
|--------------|-------------------|-------------------|-------|-------------|
| **Main** | 12 months | 12 months | 0 days | - |
| **CO-A** | 12 months | 15 months | +90 days | Extension |
| **CO-B** | 12 months | 12.5 months | +14 days | Minor Extension |
| **CO-C** | 12 months | 11 months | -30 days | Reduction (rejected) |
| **CO-D** | 12 months | 12 months | 0 days | Progression Change |
| **CO-E** | 12 months | 12 months | 0 days | No Change |
| **CO-F** | 12 months | 18 months | +180 days | Major Extension |

## EVCS Architecture Compliance

### Bitemporal Versioning

All versioned entities (WBEs, Cost Elements, Schedule Baselines) follow the TemporalBase pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                    TemporalBase Entity                       │
├─────────────────────────────────────────────────────────────┤
│ id: UUID                    → Unique version ID             │
│ {entity}_id: UUID           → Stable root ID                │
│ valid_time: TSTZRANGE       → Business time effectiveness   │
│ transaction_time: TSTZRANGE  → System recording time        │
│ branch: str                 → Branch isolation (default: "main") │
│ parent_id: UUID | None      → DAG version chain             │
│ deleted_at: datetime | None → Soft delete timestamp         │
└─────────────────────────────────────────────────────────────┘
```

### Branch Isolation Pattern

Each change order creates an isolated branch:

```
main branch (baseline)
  │
  ├─→ WBE-001 (version 1)
  │   └─ valid_time: [2026-01-01, ∞)
  │   └─ branch: "main"
  │   └─ parent_id: null
  │
  └─→ BR-a1b2c3d4 branch (change order)
      │
      ├─→ WBE-001 (version 2 - cloned)
      │   └─ valid_time: [2026-02-01, ∞)
      │   └─ branch: "BR-a1b2c3d4-..."
      │   └─ parent_id: <WBE-001 version 1 ID>
      │
      └─→ WBE-003 (version 1 - new)
          └─ valid_time: [2026-02-01, ∞)
          └─ branch: "BR-a1b2c3d4-..."
          └─ parent_id: null (new entity)
```

### 1:1 Relationship Pattern

Cost Elements ↔ Schedule Baselines:

```
┌─────────────────┐         ┌──────────────────────┐
│  Cost Element   │────────→│  Schedule Baseline   │
├─────────────────┤  1:1   ├──────────────────────┤
│ cost_element_id │         │ schedule_baseline_id │
│ schedule_baseline_id ──── │ │  (inverted FK)      │
│ budget_amount   │         │ start_date           │
│ ...             │         │ end_date             │
└─────────────────┘         │ progression_type     │
                            │ ...                  │
                            └──────────────────────┘

Constraint: One schedule baseline per cost element
Migration: Inverted FK (cost_elements.schedule_baseline_id → schedule_baselines.schedule_baseline_id)
```

## Testing Capabilities

### 1. Branch Comparison Tests

```python
# Test: Budget delta between branches
async def test_budget_impact_co_a():
    main_budget = await get_project_budget(project_id, branch="main")
    co_budget = await get_project_budget(project_id, branch="BR-a1b2c3d4-...")
    assert co_budget - main_budget == 150000.00

# Test: Timeline impact
async def test_schedule_impact_co_f():
    main_end = await get_project_end_date(project_id, branch="main")
    co_end = await get_project_end_date(project_id, branch="BR-e5f6a7b8-...")
    assert (co_end - main_end).days == 180  # 6 months
```

### 2. Impact Analysis Tests

```python
# Test: Entity count changes
async def test_entity_count_changes():
    impact = await analyze_change_order_impact(
        change_order_id="a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"
    )
    assert impact.wbes_added == 2
    assert impact.wbes_removed == 0
    assert impact.cost_elements_added == 5

# Test: Soft delete detection
async def test_soft_delete_detection():
    impact = await analyze_change_order_impact(
        change_order_id="f6a7b8c9-d0e1-4f6a-3b4c-5d6e7f8a9b0c"
    )
    assert impact.wbes_soft_deleted == 2
    assert impact.cost_elements_soft_deleted == 2
```

### 3. Version Chain Tests

```python
# Test: Parent ID chain traversal
async def test_version_chain():
    main_wbe = await get_wbe(wbe_id="...", branch="main")
    co_wbe = await get_wbe(wbe_id="...", branch="BR-b2c3d4e5-...")
    assert co_wbe.parent_id == main_wbe.id
    assert co_wbe.wbe_id == main_wbe.wbe_id  # Same root ID

# Test: Soft delete revert capability
async def test_revert_soft_delete():
    # Soft delete on CO-C branch
    await soft_delete_wbe(wbe_id, branch="BR-f6a7b8c9-...")
    # Verify main branch unaffected
    main_wbe = await get_wbe(wbe_id, branch="main")
    assert main_wbe.deleted_at is None
```

### 4. Merge Preparation Tests

```python
# Test: Conflict detection
async def test_merge_conflicts():
    conflicts = await detect_merge_conflicts(
        source_branch="BR-a1b2c3d4-...",
        target_branch="main"
    )
    # Should detect 2 new WBEs that need merging
    assert len(conflicts.wbe_conflicts) == 2

# Test: Budget reconciliation
async def test_merge_budget_reconciliation():
    current_budget = await get_project_budget(project_id, branch="main")
    merge_budget = await calculate_merge_impact(
        source_branch="BR-e5f6a7b8-...",
        target_branch="main"
    )
    assert merge_budget.delta == 375000.00
```

### 5. Schedule Baseline Tests

```python
# Test: Progression type changes (CO-D)
async def test_progression_type_change():
    main_baseline = await get_schedule_baseline(cost_element_id, branch="main")
    co_baseline = await get_schedule_baseline(cost_element_id, branch="BR-c3d4e5f6-...")
    assert main_baseline.progression_type == "LINEAR"
    assert co_baseline.progression_type == "GAUSSIAN"
    assert main_baseline.budget_amount == co_baseline.budget_amount  # Unchanged

# Test: 1:1 relationship integrity
async def test_one_to_one_relationship():
    cost_elements = await get_cost_elements(project_id, branch="main")
    for ce in cost_elements:
        baseline = await get_schedule_baseline_by_cost_element(ce.cost_element_id)
        assert baseline is not None
        assert baseline.schedule_baseline_id == ce.schedule_baseline_id
```

## File Structure

```
backend/seed/
├── README.md                          ← This file
├── SEED_DATA_PLAN.md                  ← Detailed implementation plan
├── projects.json                      ← 2 projects
├── change_orders.json                 ← 6 change orders
├── branches.json                      ← 6 branch entities
├── wbes.json                          ← 32 WBEs (20 main + 12 branch versions)
├── cost_elements.json                 ← 140 CEs (100 main + 40 branch versions)
├── schedule_baselines.json            ← 140 SBs (100 main + 40 branch versions)
├── cost_registrations.json            ← Cost registrations (main branch only)
├── progress_entries.json              ← Progress entries (main branch only)
├── users.json                         ← System users
├── departments.json                   ← Department reference data
├── cost_element_types.json            ← Cost element type reference data
├── generate_seed_data.py              ← Initial seed data generator
├── update_cost_elements.py            ← Add schedule_baseline_id FK
└── add_change_order_scenarios.py      ← Add all 6 change order scenarios
```

## Usage

### Loading Seed Data

```bash
# From project root
cd backend

# Run database migrations
uv run alembic upgrade head

# Load seed data via seeder
uv run python -m app.db.seed
```

### Testing Change Order Scenarios

```python
from app.services.change_order_service import ChangeOrderService

# Analyze CO-A impact
service = ChangeOrderService(db_session)
impact = await service.analyze_impact(
    change_order_id="a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
    project_id="d54fbbe6-f3df-51db-9c3e-9408700442be"
)

print(f"Budget Impact: ${impact.budget_delta:,.2f}")
print(f"Timeline Impact: {impact.timeline_delta_days} days")
print(f"WBEs Added: {impact.wbes_added}")
print(f"WBEs Removed: {impact.wbes_removed}")
```

### Branch Comparison

```python
from app.services.project_service import ProjectService

# Compare main branch with CO-F branch
service = ProjectService(db_session)

main_budget = await service.get_budget(
    project_id="877c4cba-b30e-54c1-b25d-c73fb364019d",
    branch="main"
)

co_budget = await service.get_budget(
    project_id="877c4cba-b30e-54c1-b25d-c73fb364019d",
    branch="BR-e5f6a7b8-c9d0-4e5f-2a3b-4c5d6e7f8a9b"
)

print(f"Main Budget: ${main_budget:,.2f}")
print(f"CO-F Budget: ${co_budget:,.2f}")
print(f"Increase: ${co_budget - main_budget:,.2f}")
```

## Expected Test Results

### CO-A (Scope Addition)

- Budget: +$150,000
- Timeline: +90 days
- New WBEs: 2
- New Cost Elements: 5
- New Schedule Baselines: 5

### CO-B (Scope Modification)

- Budget: +$45,000
- Timeline: +14 days
- Modified WBEs: 3
- Modified Cost Elements: 3
- Modified Schedule Baselines: 3

### CO-C (Scope Reduction)

- Budget: -$125,000
- Timeline: -30 days
- Soft-deleted WBEs: 2
- Soft-deleted Cost Elements: 2
- Soft-deleted Schedule Baselines: 2
- Status: REJECTED

### CO-D (Schedule Only)

- Budget: $0
- Timeline: 0 days
- Modified Schedule Baselines: 5
- Progression Type: LINEAR → GAUSSIAN

### CO-E (Cost Reallocation)

- Budget: $0 (net)
- Timeline: 0 days
- Modified Cost Elements: 5
- LAB: +$40,000
- MAT: -$40,000

### CO-F (Critical Addition)

- Budget: +$375,000
- Timeline: +180 days
- New WBEs: 5
- New Cost Elements: 25
- New Schedule Baselines: 25

## Success Metrics

✅ **Data Quality**: All UUIDs unique, FKs valid, dates consistent
✅ **EVCS Compliance**: TemporalBase pattern followed, branches isolated
✅ **Test Coverage**: All 6 change order types represented
✅ **Documentation**: Clear usage examples and expected results
✅ **Realism**: Business values reflect actual scenarios

## Contributing

When adding new change order scenarios:

1. Follow the TemporalBase pattern for all versioned entities
2. Ensure proper branch isolation (use unique branch names)
3. Maintain parent_id chains for version tracking
4. Add soft delete support for reversible deletions
5. Include both WBE and cost element changes for scope modifications
6. Update this README with scenario details
7. Add test cases demonstrating the scenario

## References

- [EVCS Architecture](../../docs/02-architecture/backend/contexts/evcs-core/)
- [Change Order Requirements](../../docs/01-product-scope/functional-requirements.md#6-change-order-processing)
- [Testing Patterns](../../docs/02-architecture/testing-patterns.md)
- [ADR-005: Bitemporal Versioning](../../docs/02-architecture/decisions/ADR-005-bitemporal-versioning.md)
