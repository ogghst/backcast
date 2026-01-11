# Request Analysis: Control Date CRUD Operations

**Date:** 2026-01-10  
**Analyst:** AI Assistant  
**Status:** ANALYSIS PHASE

---

## Problem Statement

### Current Behavior (Gap Identified)

The TimeMachine component allows users to select a **control date** (e.g., 2026-03-03), but:

- ❌ CRUD operations (Create/Update/Delete) still happen at **current timestamp**
- ✅ Query operations correctly show data "as of" the control date

**Evidence:**

- User set control date to 2026-03-03
- Created WBE with ID `e6e29061-2a12-43ed-b22b-0b81f6bee89d`
- Database shows creation at `2026-01-10 09:17:17` (current time)
- Expected: Both `valid_time` and `transaction_time` should start at `2026-03-03`

### Desired Behavior

When a control date is selected:

1. **Create** operations should set `valid_time` and `transaction_time` to start at the control date
2. **Update** operations should close old version at control date, new version starts at control date
3. **Delete** operations should set `deleted_at` to the control date
4. **Query** operations already work correctly (implemented)

---

## User Intent & Business Requirements

### Use Cases

1. **Backdating Data Entry**

   - User: "I need to record project changes that happened last month"
   - Current: Must manually edit timestamps in database
   - Desired: Set control date to last month, enter data normally

2. **Future Planning & Forecasting**

   - User: "Create Q2 budget allocation now for implementation next month"
   - Current: Cannot create future-dated data
   - Desired: Set control date to future Q2 start, enter planned data

3. **Historical Scenario Modeling**

   - User: "What if we had made this decision at project kickoff?"
   - Current: Cannot create historical "what-if" scenarios
   - Desired: Set control date to kickoff, model alternatives

4. **Baseline Reconstruction**

   - User: "Recreate the project state at contract signing"
   - Current: Can only view history, not edit it
   - Desired: Set control date to signing, enter baseline data

5. **EVM Analysis & Forecasting**
   - User: "Calculate earned value metrics as of each control date and forecast"
   - Current: All data timestamped at entry time, not event time
   - Desired: Data timestamped at actual/planned event time

### Business Value

- **Accurate Historical Records**: Data reflects when events actually occurred
- **Auditable Backdating**: Legitimate corrections with full audit trail
- **Scenario Planning**: Model historical alternatives for learning
- **Regulatory Compliance**: Prove data state at specific regulatory dates

---

## Architecture Analysis

### Current Implementation

**TimeMachine Store (Frontend):**

```typescript
interface TimeMachineState {
  selectedTime: Date | null; // Control date
  branch: string;
  // ... other fields
}
```

**API Calls (Frontend):**

```typescript
// Current: Only adds as_of to query params
const response = await fetch(`/api/v1/wbes/${id}?as_of=${controlDate}`);

// Missing: No control date sent on CREATE/UPDATE/DELETE
await fetch("/api/v1/wbes", {
  method: "POST",
  body: JSON.stringify(data),
  // ❌ No control date passed!
});
```

**Backend Services:**

```python
# CreateVersionCommand - uses NOW
version = EntityClass(created_by=actor_id, **fields)
# DB default: valid_time = tstzrange(now(), NULL)
# ❌ Ignores any desired control date
```

### Architectural Challenges

| Challenge                      | Impact                                             | Solution Approach                                                         |
| ------------------------------ | -------------------------------------------------- | ------------------------------------------------------------------------- |
| **Future dating**              | Control date > now() creates "future" planned data | **ALLOWED** - Enables planning & forecasting scenarios                    |
| **Transaction time semantics** | transaction_time = when recorded, not when valid   | Keep transaction_time = now(), only set valid_time = control_date         |
| **Audit trail**                | Need to know when backdated entry was made         | transaction_time shows actual recording time, valid_time shows event time |
| **Backdating restrictions**    | Can't edit before last edit                        | Validate: valid_time.lower >= last_edit_time (TD-023)                     |

---

## Solution Options

### Option A: Valid Time as Control Date, Transaction Time as Now

**Description:** Use control date for `valid_time` (when event occurred), keep `transaction_time` as now() (when recorded).

**Implementation:**

```python
async def create(
    self,
    actor_id: UUID,
    control_date: datetime | None = None,  # NEW parameter
    **fields
) -> TVersionable:
    effective_date = control_date or datetime.now(UTC)

    version = EntityClass(created_by=actor_id, **fields)
    session.add(version)
    await session.flush()

    # Set valid_time to control date
    stmt = text(f"""
        UPDATE {table}
        SET valid_time = tstzrange(:effective_date, NULL, '[]'),
        transaction_time = tstzrange(clock_timestamp(), NULL, '[]')
        WHERE id = :id
    """)
    await session.execute(stmt, {
        "effective_date": effective_date,
        "id": version.id
    })
```

**Pros:**
| Benefit | Description |
|---------|-------------|
| **Bitemporal Correctness** | Separates when event occurred (valid) from when recorded (transaction) |
| **Audit Trail** | transaction_time shows when data was entered, not backdated |
| **Regulatory Compliance** | Clear distinction between event time and recording time |
| **Time Travel** | Queries work correctly with both dimensions |

**Cons:**
| Drawback | Description |
|----------|-------------|
| **API Changes** | Need to pass control_date through all layers |
| **Frontend Changes** | All CRUD hooks need to send selectedTime |
| **Validation Complexity** | Must validate control_date constraints |

---

### Option B: Both Times as Control Date (Simpler but Wrong)

**Description:** Set both `valid_time` and `transaction_time` to control date.

**Pros:**

- Simpler implementation
- Data "looks like" it was entered at that time

**Cons:**

- ❌ **Violates bitemporal semantics** - transaction_time should be when recorded
- ❌ **Audit trail loss** - Can't prove when data was actually entered
- ❌ **Regulatory issues** - Looks like data manipulation
- ❌ **Time travel breaks** - Future queries won't see "past" entries

**Recommendation:** ❌ DO NOT USE - Violates core bitemporal principles

---

### Option C: Separate "Effective Date" Field

**Description:** Add new `effective_date` field, keep temporal fields unchanged.

**Implementation:**

```python
effective_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
# valid_time and transaction_time remain as-is
```

**Pros:**

- No changes to temporal logic
- Simple to add

**Cons:**

- ❌ Doesn't solve the problem - user wants valid_time set
- ❌ Confusion about which field to use when
- ❌ Duplicate information

**Recommendation:** ❌ REJECTED - Doesn't meet requirements

---

## Recommended Solution: Option A

**Use control date for `valid_time`, keep `transaction_time` as actual recording time.**

### Why This Is Correct

1. **Bitemporal Semantics:**

   - `valid_time`: When the fact was true in the real world → Use control date
   - `transaction_time`: When the fact was recorded in the database → Use now()

2. **Audit Trail:**

   - Can prove: "This data was entered on 2026-01-10"
   - Can query: "What data was valid on 2026-03-03"
   - Both questions answered correctly

3. **Regulatory Compliance:**
   - Clear audit trail of when data was entered
   - Backdating is explicit and traceable
   - Cannot hide when modifications were made

---

## Implementation Plan

### Backend Changes

1. **Commands Layer:**

   ```python
   class CreateVersionCommand:
       def __init__(self, ..., control_date: datetime | None = None):
           self.control_date = control_date or datetime.now(UTC)
   ```

2. **Service Layer:**

   ```python
   async def create(self, actor_id, control_date=None, **fields):
       cmd = CreateVersionCommand(..., control_date=control_date)
       return await cmd.execute(session)
   ```

3. **API Layer:**
   ```python
   @router.post("/wbes")
   async def create_wbe(
       wbe: WBECreate,
       control_date: datetime | None = None # Explicit arg or in wbe model
   ):
       # control_date passed via body/model
       return await service.create(..., control_date=wbe.control_date)
   ```

### Frontend Changes

1. **API Client:**

   ```typescript
   const createWBE = async (data: WBECreate) => {
     // Inject control date into payload
     const payload = {
       ...data,
       control_date: selectedTime ? selectedTime.toISOString() : undefined,
     };
     return fetch("/api/v1/wbes", {
       method: "POST",
       body: JSON.stringify(payload),
     });
   };
   ```

2. **Hooks Update:**
   - Modify `useCreateWBE`, `useUpdateWBE` (Body)
   - Modify `useDeleteWBE` (Query Param)
   - Read `selectedTime` from TimeMachineStore
   - Inject into body or query params

### Validation Rules

1. **No Date Restrictions:**

   ```python
   # Future dating ALLOWED for planning/forecasting
   # Past dating ALLOWED for backdating/corrections
   # No timestamp validation needed - any control_date is valid
   ```

2. **Control Date >= Last Edit** (Future Enhancement - TD-023):
   ```python
   # Optional validation to prevent editing historical data
   last_edit = await get_last_edit_time(entity_id)
   if control_date < last_edit:
       raise ValueError("Cannot backdate before last edit")
   ```

---

## Risks & Mitigations

| Risk                   | Probability | Impact | Mitigation                                |
| ---------------------- | ----------- | ------ | ----------------------------------------- |
| Breaking existing CRUD | Low         | High   | Default control_date=None (use now())     |
| Frontend complexity    | Medium      | Medium | Clear API client abstraction              |
| User confusion         | High        | Medium | UI indicators showing control date active |
| Performance            | Low         | Low    | No additional queries needed              |
| Data integrity         | Low         | High   | Comprehensive validation                  |

---

## Success Criteria

### Functional

- [ ] Create operation sets valid_time to control date
- [ ] Update operation uses control date for version boundaries
- [ ] Delete operation sets deleted_at to control date
- [ ] transaction_time always reflects actual recording time
- [ ] UI shows clear indicator when control date is active

### Technical

- [ ] All existing tests still pass
- [ ] New tests for control date CRUD pass
- [ ] MyPy strict compliance
- [ ] Backward compatible (default behavior unchanged)

### Business

- [ ] User can backdate data entry
- [ ] Audit trail shows when data was entered vs when it was effective
- [ ] EVM calculations use correct effective dates

---

## Documentation Updates Needed

1. **Architecture Docs:**

   - Update bitemporal semantics explanation
   - Document control_date parameter
   - Clarify valid_time vs transaction_time

2. **API Docs:**

   - Document control_date body/query param
   - Update request/response examples
   - Explain validation rules

3. **User Guide:**
   - How to use control date for backdating
   - Audit trail interpretation
   - Best practices

---

## Technical Debt Created

| ID     | Description                              | Priority | Effort |
| ------ | ---------------------------------------- | -------- | ------ |
| TD-023 | Validate control_date >= last_edit_time  | Medium   | 2h     |
| TD-024 | Admin override for backdating validation | Low      | 2h     |
| TD-025 | Control date picker UX improvements      | Low      | 4h     |
| TD-026 | Bulk import with control dates           | Low      | 6h     |

---

## Questions for User (Answered)

1. ✅ **Future Dating:** YES - Allow control_date > now() for planning/forecasting
2. **Backdating Limits:** No limits - users can backdate to any past date
3. **UI Behavior:** Should control date auto-clear after each operation or stay set?
4. **Validation:** Should we prevent backdating before last edit, or just warn?

---

## Approved for PLAN Phase?

**Ready to proceed with Option A implementation.**
