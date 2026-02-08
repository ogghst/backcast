# Change Order Impact Analysis Seed Data Plan

## Executive Summary

This plan creates comprehensive seed data demonstrating 6 different change order scenarios with full EVCS (Entity Versioning Control System) compliance, enabling thorough testing of branch creation, impact analysis, budget variance, schedule comparison, and merge preparation capabilities.

## Change Order Scenarios Overview

### 🎯 Type A: Scope Addition (CO-2026-001)
**"Add Secondary Conveyor System"**

| Aspect | Details |
|--------|---------|
| **Branch** | `co-a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d` |
| **Status** | Draft |
| **Impact Level** | MEDIUM |
| **Budget Impact** | +$150,000 (15% increase) |
| **Timeline Impact** | +3 months |
| **New Entities** | 2 WBEs, 5 Cost Elements, 5 Schedule Baselines |
| **Use Case** | Testing budget increases and timeline extensions |

**What Happens**:
- Adds 2 new L3 WBEs under existing parent
- Creates 5 new cost elements (one per type: LAB, MAT, EQP, SUB, TRV)
- Creates 5 associated schedule baselines
- Demonstrates pure scope addition

---

### 🔧 Type B: Scope Modification (CO-2026-002)
**"Safety Upgrades - Emergency Stops"**

| Aspect | Details |
|--------|---------|
| **Branch** | `co-b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e` |
| **Status** | Submitted for Approval |
| **Impact Level** | HIGH |
| **Budget Impact** | +$45,000 (4.5% increase) |
| **Timeline Impact** | +2 weeks |
| **Modified Entities** | 3 WBEs, 3 Cost Elements, 3 Schedule Baselines |
| **Use Case** | Testing budget reallocation and minor schedule adjustments |

**What Happens**:
- Updates descriptions on 3 existing WBEs
- Increases budgets by 10% for safety-related cost elements
- Extends schedule baseline end dates by 2 weeks
- Demonstrates modification of existing entities

---

### ✂️ Type C: Scope Reduction (CO-2026-006)
**"Pallet System Expansion (REJECTED)"**

| Aspect | Details |
|--------|---------|
| **Branch** | `co-f6a7b8c9-d0e1-4f6a-3b4c-5d6e7f8a9b0c` |
| **Status** | Rejected |
| **Impact Level** | HIGH |
| **Budget Impact** | -$125,000 (12.5% decrease) |
| **Timeline Impact** | -1 month |
| **Deleted Entities** | 2 WBEs, 2 Cost Elements, 2 Schedule Baselines |
| **Use Case** | Testing soft delete and rejection analysis |

**What Happens**:
- Soft-deletes 2 existing L3 WBEs (sets `deleted_at`)
- Soft-deletes associated cost elements and baselines
- Maintains `parent_id` chains for revert capability
- Demonstrates soft delete pattern and rejection workflow

---

### 📅 Type D: Schedule Adjustment Only (CO-2026-003)
**"Control Panel Modification"**

| Aspect | Details |
|--------|---------|
| **Branch** | `co-c3d4e5f6-a7b8-4c5d-0e1f-2a3b4c5d6e7f` |
| **Status** | Approved |
| **Impact Level** | LOW |
| **Budget Impact** | $0 (no budget change) |
| **Timeline Impact** | 0 days (progression curve change only) |
| **Modified Entities** | 5 Schedule Baselines (no WBE/CE changes) |
| **Use Case** | Testing schedule-only changes and progression types |

**What Happens**:
- Changes `progression_type` from LINEAR to GAUSSIAN
- No changes to WBEs or cost element budgets
- Demonstrates schedule modification without budget impact
- Tests different progression curves (S-curve effect)

---

### 💰 Type E: Cost Reallocation (CO-2026-004)
**"Upgrade HMI Interface"**

| Aspect | Details |
|--------|---------|
| **Branch** | `co-d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a` |
| **Status** | Draft |
| **Impact Level** | MEDIUM |
| **Budget Impact** | $0 (internal reallocation) |
| **Timeline Impact** | None |
| **Modified Entities** | 5 Cost Elements (no WBE/Schedule changes) |
| **Use Case** | Testing internal budget transfers |

**What Happens**:
- Increases LAB budget by +$40,000
- Decreases MAT budget by -$40,000
- Net change: $0 (same total budget, different distribution)
- Demonstrates internal budget reallocation

---

### 🤖 Type F: Critical Scope Addition (CO-2026-005)
**"Robot Cell Integration"**

| Aspect | Details |
|--------|---------|
| **Branch** | `co-e5f6a7b8-c9d0-4e5f-2a3b-4c5d6e7f8a9b` |
| **Status** | Submitted for Approval |
| **Impact Level** | CRITICAL |
| **Budget Impact** | +$375,000 (37.5% increase) |
| **Timeline Impact** | +6 months |
| **New Entities** | 5 WBEs (full hierarchy), 25 Cost Elements, 25 Schedule Baselines |
| **Use Case** | Testing large-scale scope addition and complete hierarchy creation |

**What Happens**:
- Creates complete 3-level WBE hierarchy (1 L1, 2 L2, 2 L3)
- Adds 25 cost elements (5 per WBE × 5 WBEs)
- Adds 25 associated schedule baselines
- Demonstrates large-scale, critical change orders

---

## Entity State Comparison

### WBEs (Work Breakdown Elements)

| Branch | Main | CO-A | CO-B | CO-C | CO-D | CO-E | CO-F |
|--------|------|------|------|------|------|------|------|
| **Existing** | 20 | 20 | 20 (mod) | 20 | 20 | 20 | 20 |
| **New** | - | +2 | - | - | - | - | +5 |
| **Deleted** | - | - | - | 2 (soft) | - | - | - |
| **Total** | 20 | 22 | 20 | 18 | 20 | 20 | 25 |

### Cost Elements

| Branch | Main | CO-A | CO-B | CO-C | CO-D | CO-E | CO-F |
|--------|------|------|------|------|------|------|------|
| **Existing** | 100 | 100 | 100 (mod) | 100 | 100 | 100 (mod) | 100 |
| **New** | - | +5 | - | - | - | - | +25 |
| **Deleted** | - | - | - | 2 (soft) | - | - | - |
| **Total** | 100 | 105 | 100 | 98 | 100 | 100 | 125 |

### Schedule Baselines (1:1 with Cost Elements)

| Branch | Main | CO-A | CO-B | CO-C | CO-D | CO-E | CO-F |
|--------|------|------|------|------|------|------|------|
| **Existing** | 100 | 100 | 100 (mod) | 100 | 100 (mod) | 100 | 100 |
| **New** | - | +5 | - | - | - | - | +25 |
| **Deleted** | - | - | - | 2 (soft) | - | - | - |
| **Total** | 100 | 105 | 100 | 98 | 100 | 100 | 125 |

### Budget Impact Summary

| Change Order | Original | Modified | Delta | % Change |
|--------------|----------|----------|-------|----------|
| **Main** | $1,000,000 | $1,000,000 | $0 | 0% |
| **CO-A** | $1,000,000 | $1,150,000 | +$150,000 | +15% |
| **CO-B** | $1,000,000 | $1,045,000 | +$45,000 | +4.5% |
| **CO-C** | $1,000,000 | $875,000 | -$125,000 | -12.5% |
| **CO-D** | $1,000,000 | $1,000,000 | $0 | 0% |
| **CO-E** | $1,000,000 | $1,000,000 | $0 | 0% (realloc) |
| **CO-F** | $1,000,000 | $1,375,000 | +$375,000 | +37.5% |

### Timeline Impact Summary

| Change Order | Original Duration | Modified Duration | Delta | Impact Type |
|--------------|-------------------|-------------------|-------|-------------|
| **Main** | 12 months | 12 months | 0 days | - |
| **CO-A** | 12 months | 15 months | +90 days | Extension |
| **CO-B** | 12 months | 12.5 months | +14 days | Minor Extension |
| **CO-C** | 12 months | 11 months | -30 days | Reduction (rejected) |
| **CO-D** | 12 months | 12 months | 0 days | Progression Change |
| **CO-E** | 12 months | 12 months | 0 days | No Change |
| **CO-F** | 12 months | 18 months | +180 days | Major Extension |

---

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
  └─→ co-a1b2c3d4 branch (change order)
      │
      ├─→ WBE-001 (version 2 - cloned)
      │   └─ valid_time: [2026-02-01, ∞)
      │   └─ branch: "co-a1b2c3d4-..."
      │   └─ parent_id: <WBE-001 version 1 ID>
      │
      └─→ WBE-003 (version 1 - new)
          └─ valid_time: [2026-02-01, ∞)
          └─ branch: "co-a1b2c3d4-..."
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

---

## Testing Capabilities

### 1. Branch Comparison Tests

```python
# Test: Budget delta between branches
async def test_budget_impact_co_a():
    main_budget = await get_project_budget(project_id, branch="main")
    co_budget = await get_project_budget(project_id, branch="co-a1b2c3d4-...")
    assert co_budget - main_budget == 150000.00

# Test: Timeline impact
async def test_schedule_impact_co_f():
    main_end = await get_project_end_date(project_id, branch="main")
    co_end = await get_project_end_date(project_id, branch="co-e5f6a7b8-...")
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
    co_wbe = await get_wbe(wbe_id="...", branch="co-b2c3d4e5-...")
    assert co_wbe.parent_id == main_wbe.id
    assert co_wbe.wbe_id == main_wbe.wbe_id  # Same root ID

# Test: Soft delete revert capability
async def test_revert_soft_delete():
    # Soft delete on CO-C branch
    await soft_delete_wbe(wbe_id, branch="co-f6a7b8c9-...")
    # Verify main branch unaffected
    main_wbe = await get_wbe(wbe_id, branch="main")
    assert main_wbe.deleted_at is None
```

### 4. Merge Preparation Tests

```python
# Test: Conflict detection
async def test_merge_conflicts():
    conflicts = await detect_merge_conflicts(
        source_branch="co-a1b2c3d4-...",
        target_branch="main"
    )
    # Should detect 2 new WBEs that need merging
    assert len(conflicts.wbe_conflicts) == 2

# Test: Budget reconciliation
async def test_merge_budget_reconciliation():
    current_budget = await get_project_budget(project_id, branch="main")
    merge_budget = await calculate_merge_impact(
        source_branch="co-e5f6a7b8-...",
        target_branch="main"
    )
    assert merge_budget.delta == 375000.00
```

### 5. Schedule Baseline Tests

```python
# Test: Progression type changes (CO-D)
async def test_progression_type_change():
    main_baseline = await get_schedule_baseline(cost_element_id, branch="main")
    co_baseline = await get_schedule_baseline(cost_element_id, branch="co-c3d4e5f6-...")
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

---

## File Structure

```
backend/seed/
├── README.md                          ← This file
├── CHANGE_ORDER_SCENARIOS.md          ← Detailed scenario documentation
├── projects.json                      ← 2 projects (existing)
├── change_orders.json                 ← 6 change orders (existing)
├── branches.json                      ← NEW: 6 branch entities
├── wbes.json                          ← ENHANCED: 20 main + 5 branch versions
├── cost_elements.json                 ← ENHANCED: 100 main + 35 branch versions
├── schedule_baselines.json            ← NEW: 100 main + 35 branch versions
├── cost_registrations.json            ← ENHANCED: Add branch-specific registrations
└── progress_entries.json              ← ENHANCED: Add branch-specific progress
```

---

## Implementation Phases

### Phase 1: Foundation
- [ ] Create `schedule_baselines.json` (135 baselines)
- [ ] Create `branches.json` (6 branch entities)

### Phase 2: Scope Addition
- [ ] CO-A: Add 2 WBEs + 5 CEs + 5 SBs
- [ ] CO-F: Add 5 WBEs + 25 CEs + 25 SBs

### Phase 3: Modifications
- [ ] CO-B: Modify 3 WBEs + 3 CEs + 3 SBs
- [ ] CO-D: Modify 5 SBs (progression type)
- [ ] CO-E: Modify 5 CEs (budget reallocation)

### Phase 4: Soft Deletes
- [ ] CO-C: Soft-delete 2 WBEs + 2 CEs + 2 SBs

### Phase 5: Documentation
- [ ] Update README.md with usage examples
- [ ] Create test validation checklist

---

## Success Metrics

✅ **Data Quality**: All UUIDs unique, FKs valid, dates consistent
✅ **EVCS Compliance**: TemporalBase pattern followed, branches isolated
✅ **Test Coverage**: All 6 change order types represented
✅ **Documentation**: Clear usage examples and expected results
✅ **Realism**: Business values reflect actual scenarios

---

## Next Steps

1. Review this plan and approve approach
2. Begin Phase 1 implementation (create missing files)
3. Implement scenarios incrementally (Phases 2-4)
4. Validate each phase with automated tests
5. Create comprehensive documentation (Phase 5)
6. Final validation and quality checks
