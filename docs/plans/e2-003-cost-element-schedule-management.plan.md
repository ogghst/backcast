# E2-003: Cost Element Schedule Management - Detailed Implementation Plan

**Task:** Implement CRUD operations for Cost Element Schedules

**Epic:** Epic 2 - Budget and Revenue Management

**Sprint:** Sprint 2

**Status:** Ready for Implementation

---

## Overview

Implement full CRUD operations for Cost Element Schedules, enabling users to define time-phased work plans for cost elements. The schedule includes start date, end date, and progression type (linear, gaussian, logarithmic) that will be used to calculate Planned Value (PV) in future sprints.

**Key Requirements:**

- Auto-create initial schedule when CostElement is created
- CRUD operations for schedules via API
- Frontend form for schedule creation/editing
- Validation: end_date >= start_date
- Integration into CostElement edit form

---

## TDD Implementation Strategy

Following working agreements:

- **Failing test first** for each feature
- **Incremental commits** (<100 lines, <5 files per commit)
- **Follow existing patterns** from BudgetAllocation implementation
- **No code duplication** - reuse abstractions

---

## Phase 1: Backend API - Schedule Router (TDD)

### Commit 1.1: Test - GET schedule by cost_element_id

**File:** `backend/tests/api/routes/test_cost_element_schedules.py` (NEW)

```python
def test_get_schedule_by_cost_element_id(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting schedule for a cost element."""
    # Setup: Create project, WBE, cost element, schedule
    from tests.utils.project import create_random_project
    from tests.utils.wbe import create_random_wbe
    from tests.utils.cost_element import create_random_cost_element
    from app.models import CostElementSchedule, CostElementScheduleCreate

    project = create_random_project(db)
    wbe = create_random_wbe(db, project.project_id)
    cost_element = create_random_cost_element(db, wbe.wbe_id)

    schedule_in = CostElementScheduleCreate(
        cost_element_id=cost_element.cost_element_id,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        progression_type="linear",
        created_by_id=uuid.uuid4(),  # Will be current user in real scenario
    )
    schedule = CostElementSchedule.model_validate(schedule_in)
    db.add(schedule)
    db.commit()

    # Test: GET /cost-element-schedules/?cost_element_id={id}
    response = client.get(
        f"{settings.API_V1_STR}/cost-element-schedules/",
        headers=superuser_token_headers,
        params={"cost_element_id": str(cost_element.cost_element_id)},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["cost_element_id"] == str(cost_element.cost_element_id)
    assert content["start_date"] == "2025-01-01"
    assert content["end_date"] == "2025-12-31"
    assert content["progression_type"] == "linear"
```

**Expected:** Test fails (route doesn't exist)

---

### Commit 1.2: Implement - GET schedule by cost_element_id

**Files:**

1. `backend/app/api/routes/cost_element_schedules.py` (NEW)
2. `backend/app/api/main.py` (MODIFY - add router)

**Implementation:**

- Create router with prefix `/cost-element-schedules`
- GET endpoint: Query by `cost_element_id` parameter
- Return `CostElementSchedulePublic` or 404
- Follow pattern from `cost_elements.py`

**Test:** Should pass

---

### Commit 1.3: Test - POST create schedule

**File:** `backend/tests/api/routes/test_cost_element_schedules.py`

```python
def test_create_schedule(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a new schedule."""
    # Setup
    project = create_random_project(db)
    wbe = create_random_wbe(db, project.project_id)
    cost_element = create_random_cost_element(db, wbe.wbe_id)

    # Test: POST /cost-element-schedules/
    schedule_data = {
        "cost_element_id": str(cost_element.cost_element_id),
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "progression_type": "linear",
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-element-schedules/",
        headers=superuser_token_headers,
        json=schedule_data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["start_date"] == "2025-01-01"
    assert content["end_date"] == "2025-12-31"
    assert content["progression_type"] == "linear"

def test_create_schedule_invalid_dates(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating schedule with end_date < start_date should fail."""
    # Setup
    project = create_random_project(db)
    wbe = create_random_wbe(db, project.project_id)
    cost_element = create_random_cost_element(db, wbe.wbe_id)

    # Test: POST with invalid dates
    schedule_data = {
        "cost_element_id": str(cost_element.cost_element_id),
        "start_date": "2025-12-31",
        "end_date": "2025-01-01",  # End before start
        "progression_type": "linear",
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-element-schedules/",
        headers=superuser_token_headers,
        json=schedule_data,
    )
    assert response.status_code == 400
    assert "end_date must be greater than or equal to start_date" in response.json()["detail"]
```

**Expected:** Tests fail (POST endpoint doesn't exist)

---

### Commit 1.4: Implement - POST create schedule

**File:** `backend/app/api/routes/cost_element_schedules.py`

**Implementation:**

- POST endpoint with validation
- Validate cost_element exists
- Validate end_date >= start_date
- Create schedule with created_by_id from current user
- Follow pattern from `cost_elements.py` create endpoint

**Test:** Should pass

---

### Commit 1.5: Test - PUT update schedule

**File:** `backend/tests/api/routes/test_cost_element_schedules.py`

```python
def test_update_schedule(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating a schedule."""
    # Setup: Create schedule
    project = create_random_project(db)
    wbe = create_random_wbe(db, project.project_id)
    cost_element = create_random_cost_element(db, wbe.wbe_id)
    schedule = create_schedule_for_cost_element(db, cost_element.cost_element_id)

    # Test: PUT /cost-element-schedules/{id}
    update_data = {
        "start_date": "2025-02-01",
        "end_date": "2025-11-30",
        "progression_type": "gaussian",
    }
    response = client.put(
        f"{settings.API_V1_STR}/cost-element-schedules/{schedule.schedule_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["start_date"] == "2025-02-01"
    assert content["end_date"] == "2025-11-30"
    assert content["progression_type"] == "gaussian"
```

**Expected:** Test fails (PUT endpoint doesn't exist)

---

### Commit 1.6: Implement - PUT update schedule

**File:** `backend/app/api/routes/cost_element_schedules.py`

**Implementation:**

- PUT endpoint following update pattern
- Validate schedule exists (404 if not)
- Validate end_date >= start_date on update
- Use `model_dump(exclude_unset=True)` pattern

**Test:** Should pass

---

### Commit 1.7: Test - DELETE schedule

**File:** `backend/tests/api/routes/test_cost_element_schedules.py`

```python
def test_delete_schedule(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test deleting a schedule."""
    # Setup
    project = create_random_project(db)
    wbe = create_random_wbe(db, project.project_id)
    cost_element = create_random_cost_element(db, wbe.wbe_id)
    schedule = create_schedule_for_cost_element(db, cost_element.cost_element_id)

    # Test: DELETE /cost-element-schedules/{id}
    response = client.delete(
        f"{settings.API_V1_STR}/cost-element-schedules/{schedule.schedule_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Schedule deleted successfully"

    # Verify deleted
    response = client.get(
        f"{settings.API_V1_STR}/cost-element-schedules/",
        headers=superuser_token_headers,
        params={"cost_element_id": str(cost_element.cost_element_id)},
    )
    assert response.status_code == 404
```

**Expected:** Test fails (DELETE endpoint doesn't exist)

---

### Commit 1.8: Implement - DELETE schedule

**File:** `backend/app/api/routes/cost_element_schedules.py`

**Implementation:**

- DELETE endpoint
- Return `Message` on success
- Follow pattern from `cost_elements.py` delete endpoint

**Test:** Should pass

---

## Phase 2: Auto-Creation on CostElement Creation (TDD)

### Commit 2.1: Test - Auto-create schedule on CostElement creation

**File:** `backend/tests/api/routes/test_cost_elements.py`

```python
def test_create_cost_element_creates_initial_schedule(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test that creating a cost element automatically creates an initial schedule."""
    from app.models import CostElementSchedule
    from sqlmodel import select

    # Setup
    project = create_random_project(db)
    wbe = create_random_wbe(db, project.project_id)
    cost_element_type = create_random_cost_element_type(db)

    # Create cost element via API
    ce_data = {
        "wbe_id": str(wbe.wbe_id),
        "cost_element_type_id": str(cost_element_type.cost_element_type_id),
        "department_code": "ENG",
        "department_name": "Engineering",
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-elements/",
        headers=superuser_token_headers,
        json=ce_data,
    )
    assert response.status_code == 200
    content = response.json()
    cost_element_id = content["cost_element_id"]

    # Query for CostElementSchedule record
    statement = select(CostElementSchedule).where(
        CostElementSchedule.cost_element_id == uuid.UUID(cost_element_id)
    )
    schedules = db.exec(statement).all()

    # Verify schedule was created with default values
    assert len(schedules) == 1
    schedule = schedules[0]
    assert schedule.cost_element_id == uuid.UUID(cost_element_id)
    # Default dates should be set (e.g., same as today or None - TBD)
    assert schedule.progression_type == "linear"  # Default progression type
```

**Expected:** Test fails (auto-creation not implemented)

---

### Commit 2.2: Implement - Helper function for schedule creation

**File:** `backend/app/api/routes/cost_elements.py`

**Implementation:**

- Add helper function `create_initial_schedule_for_cost_element()`
- Similar pattern to `create_budget_allocation_for_cost_element()`
- Default values: start_date=today, end_date=today+1year, progression_type="linear"
- Takes session, cost_element, created_by_id

**Test:** Helper function tested indirectly via integration test

---

### Commit 2.3: Integrate - Auto-create schedule in CostElement POST

**File:** `backend/app/api/routes/cost_elements.py`

**Implementation:**

- In `create_cost_element()` function, after `session.flush()`
- Call `create_initial_schedule_for_cost_element()`
- Before `session.commit()`

**Test:** Should pass (Commit 2.1 test)

---

## Phase 3: Frontend Components (TDD)

### Commit 3.1: Test - Schedule form component renders

**File:** `frontend/src/components/Projects/CostElementScheduleForm.test.tsx` (NEW - if using React Testing Library)

OR manual testing checklist:

- [ ] Component renders with required fields
- [ ] Date pickers work correctly
- [ ] Progression type dropdown has 3 options
- [ ] Form validation shows errors

---

### Commit 3.2: Implement - Schedule form component

**File:** `frontend/src/components/Projects/CostElementScheduleForm.tsx` (NEW)

**Implementation:**

- Modal form following `EditCostElement.tsx` pattern
- React Hook Form for form management
- Fields:
  - Start Date (date picker)
  - End Date (date picker)
  - Progression Type (select: linear, gaussian, logarithmic)
  - Notes (textarea, optional)
- Validation:
  - end_date >= start_date
  - All fields required except notes
- TanStack Query mutation for create/update
- Toast notifications on success/error

---

### Commit 3.3: Integrate - Schedule form into CostElement edit

**File:** `frontend/src/components/Projects/EditCostElement.tsx`

**Implementation:**

- Add "Schedule" section/tab
- Show existing schedule if present (fetch via API)
- Button to "Edit Schedule" or "Add Schedule"
- Display schedule details: dates, progression type

---

## Phase 4: Model Schema Updates (if needed)

### Commit 4.1: Verify - CostElementSchedulePublic schema

**File:** `backend/app/models/cost_element_schedule.py`

**Check:**

- `CostElementSchedulePublic` includes all necessary fields
- `CostElementSchedulesPublic` exists for list responses (if needed)
- Schema exported in `__init__.py`

**Action:** Update if missing

---

## Phase 5: API Client Generation

### Commit 5.1: Regenerate - Frontend API client

**Command:** Run OpenAPI client generation

- Backend: Ensure `/cost-element-schedules` endpoints in OpenAPI spec
- Frontend: Regenerate client
- Verify: `CostElementSchedulesService` available

---

## Testing Checklist

### Backend Tests

- [ ] GET schedule by cost_element_id (exists)
- [ ] GET schedule by cost_element_id (not found)
- [ ] POST create schedule (success)
- [ ] POST create schedule (invalid dates)
- [ ] POST create schedule (cost_element not found)
- [ ] PUT update schedule (success)
- [ ] PUT update schedule (invalid dates)
- [ ] PUT update schedule (not found)
- [ ] DELETE schedule (success)
- [ ] DELETE schedule (not found)
- [ ] Auto-create schedule on CostElement creation
- [ ] Validation: progression_type enum values
- [ ] Validation: end_date >= start_date

### Frontend Tests (Manual)

- [ ] Schedule form renders correctly
- [ ] Form validation works (date validation)
- [ ] Create schedule via form
- [ ] Update schedule via form
- [ ] Delete schedule (if implemented)
- [ ] Schedule displayed in CostElement edit view
- [ ] Auto-created schedule visible after CostElement creation

---

## Dependencies

**Depends On:**

- ✅ CostElement model exists
- ✅ CostElementSchedule model exists (already in data model)
- ✅ BudgetAllocation pattern established (for helper function pattern)

**Enables:**

- E2-005: Time-Phased Budget Planning (uses schedule data)
- E4-001: Planned Value Calculation (uses schedule dates and progression)

---

## File Structure

**New Files:**

- `backend/app/api/routes/cost_element_schedules.py`
- `backend/tests/api/routes/test_cost_element_schedules.py`
- `frontend/src/components/Projects/CostElementScheduleForm.tsx`

**Modified Files:**

- `backend/app/api/routes/cost_elements.py` (add helper, auto-creation)
- `backend/app/api/main.py` (register router)
- `backend/app/models/__init__.py` (export schemas if needed)
- `frontend/src/components/Projects/EditCostElement.tsx` (integrate schedule form)

---

## Notes

1. **Default Schedule Values:**

   - Start date: Today or CostElement creation date?
   - End date: Start date + 1 year or project completion date?
   - Progression type: "linear" (most common default)
   - **Decision needed:** Confirm default values with stakeholder

2. **Schedule Uniqueness:**

   - Model has unique constraint on `cost_element_id`
   - Only one schedule per cost element
   - UI should handle "replace existing" vs "edit existing" appropriately

3. **Progression Type Values:**

   - Options: "linear", "gaussian", "logarithmic"
   - Frontend dropdown should match these exact values
   - Backend validation should enforce these values (enum validation)

4. **Date Validation:**

   - Client-side: Date pickers ensure end_date >= start_date
   - Server-side: Validate in API route before save
   - Error message: Clear and user-friendly

---

## Success Criteria

✅ Users can create schedules for cost elements

✅ Schedules auto-created when CostElement is created

✅ Users can edit schedule dates and progression type

✅ Validation prevents invalid date ranges

✅ Schedule information visible in CostElement edit view

✅ All tests passing

✅ Follows existing codebase patterns

✅ No code duplication (reuses abstractions)

---

**Ready to Begin:** ✅ Yes, after confirming default schedule values
