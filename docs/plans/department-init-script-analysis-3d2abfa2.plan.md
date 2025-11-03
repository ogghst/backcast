<!-- 3d2abfa2-d269-4e7c-9f5b-ecfe923533ce 73d4343c-762d-4af8-ad13-973e772393f0 -->
# Department Seed Module Implementation

## Approach: Separate Seed Module

Create `backend/app/core/seeds.py` module to house all seed functions, refactoring existing `_seed_cost_element_types()` and adding new `_seed_departments()`.

## Implementation Steps

### Phase 1: Create Seeds Module and Refactor

**File:** `backend/app/core/seeds.py` (NEW)

- Move `_seed_cost_element_types()` from `db.py`
- Import required models and dependencies
- Maintain exact functionality

**File:** `backend/app/core/db.py`

- Remove `_seed_cost_element_types()` function
- Import `_seed_cost_element_types` from `app.core.seeds`
- Update `init_db()` to call from new location

**Test:** Verify existing tests still pass (regression check)

### Phase 2: Add Department Seed Function

**File:** `backend/app/core/departments_seed.json` (NEW)

- Create JSON with 9 departments: MECH, ELEC, SW, ASM, COM, PM, SUPPORT, MAT, OTHER
- Structure: `[{"department_code": "...", "department_name": "...", "description": "...", "is_active": true}]`

**File:** `backend/app/core/seeds.py`

- Add `_seed_departments(session: Session)` function
- Follow same pattern as `_seed_cost_element_types()`
- Check for existing by `department_code` before creating
- Idempotent behavior

**File:** `backend/app/core/db.py`

- Import `_seed_departments` from `app.core.seeds`
- Call `_seed_departments()` **BEFORE** `_seed_cost_element_types()` in `init_db()`
- Add comment explaining order dependency

### Phase 3: Tests (TDD)

**File:** `backend/tests/core/test_seeds.py` (NEW)

Test cases:

1. `test_seed_departments_creates_records` - Creates departments from JSON
2. `test_seed_departments_idempotent` - No duplicates on re-run
3. `test_seed_departments_missing_file` - Graceful handling of missing file
4. `test_seed_order_departments_first` - Integration test verifying departments seed before cost element types
5. `test_seed_cost_element_types_still_works` - Regression test after refactor

## Files Changed

**New:**

- `backend/app/core/seeds.py`
- `backend/app/core/departments_seed.json`
- `backend/tests/core/test_seeds.py`

**Modified:**

- `backend/app/core/db.py`

## Department Names (Default Assumptions)

- MECH → "Mechanical Engineering"
- ELEC → "Electrical Engineering"
- SW → "Software Development"
- ASM → "Assembly"
- COM → "Commissioning"
- PM → "Project Management"
- SUPPORT → "Support & Documentation"
- MAT → "Materials"
- OTHER → "Other"

These can be adjusted in the JSON file.

## Implementation Order (TDD)

1. Write failing test for `_seed_departments()`
2. Create `seeds.py` and move `_seed_cost_element_types()` (refactor)
3. Verify regression tests pass
4. Implement `_seed_departments()` to make test pass
5. Update `init_db()` with correct order
6. Add integration test for seed order
