# EV S-Curve Bug Investigation Report

**Date:** 2026-02-11  
**Issue:** EV (Earned Value) S-curve always shows 0 values in impact analysis  
**Project:** PRJ-DEMO-002 (ID: `877c4cba-b30e-54c1-b25d-c73fb364019d`)  
**Change Order:** CO-2026-007 (Branch: `BR-CO-2026-007`)

---

## Executive Summary

**ROOT CAUSE:** The EV S-curve shows 0 values because **PRJ-DEMO-002 has no ProgressEntry records** in the database. The EV calculation correctly returns 0 when there is no progress data, which is the expected behavior.

**NOT A BUG:** This is working as designed. The EV formula is:
```
EV = budget_allocation × progress_percentage / 100
```

Without progress entries, `progress_percentage` is undefined/null, resulting in EV = 0.

---

## Investigation Findings

### 1. Database State

#### ProgressEntry Records in Database:
- **Total ProgressEntry records:** 285
- **Project with progress entries:** Demo Project 1 (ID: `d54fbbe6-f3df-51db-9c3e-9408700442be`)
- **PRJ-DEMO-002 progress entries:** **0**

#### CostElements in PRJ-DEMO-002:
- **Total CostElements:** 50 (25 on main branch, 25 on `BR-CO-2026-007`)
- **CostElements with progress:** 0
- **CostElements without progress:** 50

### 2. Code Analysis

The EV calculation logic in `/home/nicola/dev/backcast_evs/backend/app/services/impact_analysis_service.py` (lines 1227-1232) is **CORRECT**:

```python
# EV: Use progress entries
pe = progress_lookup.get((ce.cost_element_id, "main"))
if pe:
    ev = budget * pe.progress_percentage / Decimal("100")
    main_ev += ev
# If no progress entry, EV = 0  ← CORRECT BEHAVIOR
```

The code:
1. Looks up progress entries from the database
2. Calculates EV as `budget × progress_percentage / 100`
3. Adds to accumulated EV if progress entry exists
4. **Correctly adds 0 if no progress entry exists** (the commented line shows this is intentional)

### 3. Why EV is 0 - Step by Step

1. **Query for progress entries** (line 1099-1116):
   ```python
   progress_stmt = (
       select(ProgressEntry, CostElement)
       .join(CostElement, ProgressEntry.cost_element_id == CostElement.cost_element_id)
       .join(WBE, CostElement.wbe_id == WBE.wbe_id)
       .where(
           WBE.project_id == PROJECT_ID,  # ← Filters for PRJ-DEMO-002
           CostElement.branch.in_(["main", BRANCH_NAME]),
           # ... other filters
       )
   )
   ```
   Result: **0 rows** because PRJ-DEMO-002 has no progress entries

2. **Build progress lookup** (line 1118-1124):
   ```python
   progress_lookup: dict[tuple[UUID, str], ProgressEntry] = {}
   for pe, ce in progress_rows:  # ← progress_rows is empty
       key = (ce.cost_element_id, ce.branch)
       if key not in progress_lookup:
           progress_lookup[key] = pe
   ```
   Result: **Empty dictionary** `{}`

3. **Calculate EV for each week** (line 1228-1231):
   ```python
   pe = progress_lookup.get((ce.cost_element_id, "main"))  # ← Returns None
   if pe:  # ← Condition is False
       ev = budget * pe.progress_percentage / Decimal("100")
       main_ev += ev
   # main_ev remains 0
   ```
   Result: **EV = 0** for all weeks

---

## Verification

### SQL Queries Run

1. **Count ProgressEntry for PRJ-DEMO-002:**
   ```sql
   SELECT COUNT(*) 
   FROM progress_entries pe
   JOIN cost_elements ce ON pe.cost_element_id = ce.cost_element_id
   JOIN wbes ON ce.wbe_id = wbes.wbe_id
   WHERE wbes.project_id = '877c4cba-b30e-54c1-b25d-c73fb364019d'
     AND pe.deleted_at IS NULL
     AND upper(pe.valid_time) IS NULL;
   ```
   **Result:** 0

2. **Count CostElements for PRJ-DEMO-002:**
   ```sql
   SELECT COUNT(*), ce.branch
   FROM cost_elements ce
   JOIN wbes ON ce.wbe_id = wbes.wbe_id
   WHERE wbes.project_id = '877c4cba-b30e-54c1-b25d-c73fb364019d'
     AND ce.deleted_at IS NULL
     AND upper(ce.valid_time) IS NULL
   GROUP BY ce.branch;
   ```
   **Result:** 
   - main: 25
   - BR-CO-2026-007: 25

3. **Check which project has progress entries:**
   ```sql
   SELECT p.name, COUNT(*) as progress_count
   FROM progress_entries pe
   JOIN cost_elements ce ON pe.cost_element_id = ce.cost_element_id
   JOIN wbes ON ce.wbe_id = wbes.wbe_id
   JOIN projects p ON wbes.project_id = p.project_id
   WHERE pe.deleted_at IS NULL
     AND upper(pe.valid_time) IS NULL
   GROUP BY p.name, p.project_id;
   ```
   **Result:** Demo Project 1: 285 progress entries

---

## Solutions

### Option 1: Add Progress Entry Data (Recommended for Testing)

To see non-zero EV values, you need to create progress entries for PRJ-DEMO-002:

```python
from datetime import datetime, UTC
from decimal import Decimal
from uuid import uuid4

from app.db.session import async_session_maker
from app.models.domain.progress_entry import ProgressEntry

async def create_test_progress():
    async with async_session_maker() as session:
        # Create progress entries for cost elements
        # Replace cost_element_id with actual IDs from PRJ-DEMO-002
        pe = ProgressEntry(
            progress_entry_id=uuid4(),
            cost_element_id="2b5d4292-27cb-591c-92e4-e586e02a9de4",  # Example CE ID
            progress_percentage=Decimal("50.00"),  # 50% complete
            valid_time="(datetime(2026, 1, 15, tzinfo=UTC),)",
            transaction_time="(datetime(2026, 1, 15, tzinfo=UTC),)",
            created_by=uuid4(),
        )
        session.add(pe)
        await session.commit()
```

### Option 2: Update UI to Handle Missing Data

Update the S-curve component to show a message when EV is 0 due to missing progress:

```typescript
if (evData.every(point => point.mainValue === 0 && point.changeValue === 0)) {
  return (
    <Alert 
      message="No Progress Data" 
      description="Earned Value requires progress entries. Please add progress data for cost elements." 
      type="info" 
    />
  );
}
```

### Option 3: Use Test Data with Existing Progress

Use "Demo Project 1" for testing instead of PRJ-DEMO-002, since it has 285 progress entries.

---

## Conclusion

**The EV S-curve is working correctly.** The 0 values are due to missing ProgressEntry data for PRJ-DEMO-002, not a code bug.

### Impact Analysis Service Code Status:
- ✅ Progress entry query is correct
- ✅ Progress lookup logic is correct
- ✅ EV calculation formula is correct
- ✅ Handling of missing progress is correct (EV = 0)

### Data Status:
- ❌ PRJ-DEMO-002 has no progress entries
- ✅ Demo Project 1 has 285 progress entries

### Recommended Actions:
1. **For testing:** Use Demo Project 1 or create progress entries for PRJ-DEMO-002
2. **For production:** Add progress entry creation to the project setup workflow
3. **For UX:** Add UI indicators when progress data is missing

---

## Files Reviewed

- `/home/nicola/dev/backcast_evs/backend/app/services/impact_analysis_service.py` (lines 967-1352)
- `/home/nicola/dev/backcast_evs/backend/app/models/domain/progress_entry.py`
- `/home/nicola/dev/backcast_evs/backend/app/db/session.py`

## Test Scripts Created

- `/home/nicola/dev/backcast_evs/backend/debug_ev_issue.py`
- `/home/nicola/dev/backcast_evs/backend/find_progress_entries.py`
