# Implementation Plan: Consistent Seed Entity IDs

## Overview

Implement deterministic, namespace-based UUIDs for all entities in seed data to ensure consistent relationships and repeatable seeding results.

## Decisions from Analysis Phase

| Decision | Choice |
|----------|--------|
| **Entity Scope** | ALL entities (temporal + simple) |
| **UUID Pattern** | UUIDv5 (namespace-based) |
| **API Policy** | Reject client-provided root IDs in production API |

---

## Architecture Design

### UUIDv5 Namespace Strategy

**Namespace Hierarchy:**
```
Base Namespace: 6ba7b810-9dad-11d1-80b4-00c04fd430c8 (DNS namespace)
├── Entity Type Namespaces (derived from entity names)
│   ├── Project: UUIDv5(base, "backcast.org.project")
│   ├── WBE: UUIDv5(base, "backcast.org.wbe")
│   ├── CostElement: UUIDv5(base, "backcast.org.cost_element")
│   ├── Department: UUIDv5(base, "backcast.org.department")
│   ├── CostElementType: UUIDv5(base, "backcast.org.cost_element_type")
│   └── User: UUIDv5(base, "backcast.org.user")
└── Entity Instance UUIDs: UUIDv5(entity_namespace, entity_code)
    ├── Project PRJ-DEMO-001 → UUIDv5(project_ns, "PRJ-DEMO-001")
    ├── WBE PRJ-DEMO-001-L1-1 → UUIDv5(wbe_ns, "PRJ-DEMO-001-L1-1")
    └── User admin@backcast.org → UUIDv5(user_ns, "admin@backcast.org")
```

**Benefits:**
- Deterministic: Same code always produces same UUID
- Human-readable: Can derive UUID from known code
- Collision-resistant: Namespace prevents cross-entity conflicts
- Debuggable: Can reverse-engineer UUID to verify entity type

### API Validation Strategy

**Two-tier validation:**

1. **Internal/Seed Context**: Allow explicit root IDs
   - Services check for `is_seed_operation` flag
   - Bypass validation when seeding

2. **Production API**: Reject client-provided root IDs
   - Pydantic validators ensure root ID fields are `None` in API requests
   - Services generate IDs for all public API calls

**Implementation:**
```python
# In Pydantic schemas
@field_validator('wbe_id')
@classmethod
def reject_provided_wbe_id(cls, v: UUID | None) -> UUID | None:
    if v is not None and not is_seed_operation():
        raise ValueError("Cannot provide wbe_id in create request")
    return v
```

---

## Implementation Tasks

### Phase 1: Infrastructure (Backend)

#### Task 1.1: Create UUID Utility Module
**File:** `backend/app/core/uuid_utils.py`

**Responsibilities:**
- Define entity namespaces (UUIDv5 derived from DNS namespace)
- `generate_entity_uuid(entity_type: str, identifier: str) -> UUID`
- `get_entity_namespace(entity_type: str) -> UUID`
- List of supported entity types

**Entity Type Constants:**
```python
ENTITY_TYPE_PROJECT = "project"
ENTITY_TYPE_WBE = "wbe"
ENTITY_TYPE_COST_ELEMENT = "cost_element"
ENTITY_TYPE_DEPARTMENT = "department"
ENTITY_TYPE_COST_ELEMENT_TYPE = "cost_element_type"
ENTITY_TYPE_USER = "user"
```

**Testing:**
- Verify deterministic output (same input → same UUID)
- Verify uniqueness across entity types
- Test against known vectors

---

#### Task 1.2: Extend Pydantic Schemas
**Files:**
- `backend/app/models/schemas/wbe.py`
- `backend/app/models/schemas/cost_element.py`
- `backend/app/models/schemas/department.py`
- `backend/app/models/schemas/cost_element_type.py`
- `backend/app/models/schemas/user.py`

**Changes per schema:**

1. **Temporal entities** (WBE, CostElement):
   - Add optional root ID field to `*Create` schema
   - Add validator to reject client-provided IDs (except seed)
   - Example:
   ```python
   class WBECreate(BaseModel):
       wbe_id: UUID | None = Field(default=None, hidden=True)  # Internal use
       # ... rest of fields

       @field_validator('wbe_id')
       @classmethod
       def reject_provided_wbe_id(cls, v: UUID | None) -> UUID | None:
           if v is not None and not is_seed_operation():
               raise ValueError("Cannot provide wbe_id in create request")
           return v
   ```

2. **Simple entities** (Department, CostElementType, User):
   - Add optional `id` field to `*Create` schema
   - Same validation pattern as temporal entities
   - Example:
   ```python
   class DepartmentCreate(BaseModel):
       id: UUID | None = Field(default=None, hidden=True)
       # ... rest of fields
   ```

**Schema Updates:**
- `WBECreate`: Add `wbe_id`
- `CostElementCreate`: Add `cost_element_id`
- `DepartmentCreate`: Add `id`
- `CostElementTypeCreate`: Add `id`
- `UserRegister`: Add `id`

**Note:** `ProjectCreate` already has `project_id` - add validation only.

---

#### Task 1.3: Update Service Layer
**Files:**
- `backend/app/services/wbe.py`
- `backend/app/services/cost_element_service.py`
- `backend/app/services/department.py`
- `backend/app/services/cost_element_type_service.py`
- `backend/app/services/user.py`
- `backend/app/services/project.py` (add validation)

**Changes per service:**

1. **Update `create_*` methods:**
   ```python
   # Before
   def create_wbe(self, wbe_in: WBECreate, actor_id: UUID) -> WBE:
       wbe_id = uuid4()
       ...

   # After
   def create_wbe(self, wbe_in: WBECreate, actor_id: UUID) -> WBE:
       wbe_id = wbe_in.wbe_id or uuid4()
       ...
   ```

2. **For simple entities (using `id` instead of root ID):**
   ```python
   def create_department(self, dept_in: DepartmentCreate, actor_id: UUID) -> Department:
       # If id provided in seed, use it; otherwise generate
       dept_id = dept_in.id or uuid4()
       # Override SQLAlchemy's auto-generation
       department = Department(
           id=dept_id,  # Explicit ID assignment
           ...
       )
   ```

**Important:** SQLAlchemy's `default=uuid4()` in `EntityBase` will be overridden when `id` is explicitly passed to constructor.

---

#### Task 1.4: Create Seed Context Manager
**File:** `backend/app/db/seed_context.py`

**Purpose:** Thread-safe context to mark seed operations for validation bypass

**Implementation:**
```python
from contextvars import ContextVar

_seed_operation: ContextVar[bool] = ContextVar('_seed_operation', default=False)

@contextmanager
def seed_operation():
    """Context manager to mark current operation as seed data import."""
    token = _seed_operation.set(True)
    try:
        yield
    finally:
        _seed_operation.reset(token)

def is_seed_operation() -> bool:
    """Check if current execution context is a seed operation."""
    return _seed_operation.get()
```

**Usage in seeder:**
```python
async def seed_wbes(self, session: AsyncSession) -> None:
    with seed_operation():  # Allow explicit IDs
        # ... seeding logic
```

---

### Phase 2: Update Seed Data Files

#### Task 2.1: Generate UUIDv5 IDs for All Entities
**Tool:** Create helper script `backend/scripts/generate_seed_uuids.py`

**Output:** Report mapping of all codes → UUIDv5

**Example output:**
```
Project UUIDs:
  PRJ-DEMO-001 → a1b2c3d4-...
  PRJ-DEMO-002 → e5f6g7h8-...

WBE UUIDs:
  PRJ-DEMO-001-L1-1 → 12345678-...
  ...
```

---

#### Task 2.2: Update Seed JSON Files

**Per-file changes:**

1. **`backend/seed/projects.json`**:
   - Verify existing `project_id` values match UUIDv5
   - Update if needed

2. **`backend/seed/wbes.json`**:
   - Add `wbe_id` field to each WBE
   - Use UUIDv5 generated from WBE code

3. **`backend/seed/cost_elements.json`**:
   - Add `cost_element_id` field to each cost element
   - Use UUIDv5 generated from cost element code

4. **`backend/seed/departments.json`**:
   - Add `id` field to each department
   - Use UUIDv5 generated from department code

5. **`backend/seed/cost_element_types.json`**:
   - Add `id` field to each cost element type
   - Use UUIDv5 generated from type code

6. **`backend/seed/users.json`**:
   - Add `id` field to each user
   - Use UUIDv5 generated from email

**Example transformation:**
```json
// Before (wbes.json)
{
  "project_code": "PRJ-DEMO-001",
  "code": "PRJ-DEMO-001-L1-1",
  "name": "L1 WBE 1",
  ...
}

// After
{
  "wbe_id": "uuidv5-here",
  "project_code": "PRJ-DEMO-001",
  "code": "PRJ-DEMO-001-L1-1",
  "name": "L1 WBE 1",
  ...
}
```

---

#### Task 2.3: Update Seeder
**File:** `backend/app/db/seeder.py`

**Changes:**

1. **Import seed context:**
   ```python
   from app.db.seed_context import seed_operation
   ```

2. **Wrap each seed method with context:**
   ```python
   async def seed_wbes(self, session: AsyncSession) -> None:
       with seed_operation():
           # ... existing logic
   ```

3. **For temporal entities** (WBEs, CostElements):
   - Pass root ID from JSON to schema
   - Root ID already in JSON data → schema accepts it

4. **For simple entities** (Departments, Users, CostElementTypes):
   - Pass `id` from JSON to schema
   - Need to modify seeder to extract and pass `id`

**Example change for WBEs:**
```python
# Current: wbe_in = WBECreate(**item)
# Updated: item already contains wbe_id from JSON
wbe_in = WBECreate(**item)  # Just pass through
```

---

### Phase 3: Testing

#### Task 3.1: Unit Tests
**File:** `backend/tests/unit/test_uuid_utils.py`

**Test cases:**
- Deterministic UUID generation (same input → same output)
- Namespace isolation (different entity types → different UUIDs)
- Valid UUIDv5 format verification

---

#### Task 3.2: Schema Validation Tests
**File:** `backend/tests/unit/test_schemas.py`

**Test cases:**
- API rejects provided root IDs (seed context off)
- Seed context accepts provided root IDs
- Missing IDs still generate correctly

---

#### Task 3.3: Integration Tests
**File:** `backend/tests/api/test_seeding.py`

**Test cases:**
- Seeding produces identical database state on repeated runs
- All entity relationships resolve correctly
- Generated IDs match expected UUIDv5 values

---

#### Task 3.4: Update Existing Tests
**Files:** All test files that create entities

**Changes:**
- Ensure tests don't accidentally provide IDs (should be rejected)
- Update any tests that relied on specific auto-generated UUIDs
- Add assertions for ID format where appropriate

---

### Phase 4: Documentation

#### Task 4.1: Update Architecture Documentation
**File:** `docs/02-architecture/00-system-map.md`

**Add:**
- UUID generation strategy section
- Entity ID patterns
- Namespace hierarchy diagram

---

#### Task 4.2: Create Seeding Guide
**File:** `docs/02-architecture/seeding-guide.md`

**Content:**
- How to add new seed data
- UUID generation process
- ID assignment rules
- Testing seeded data

---

#### Task 4.3: Update API Documentation
**File:** Auto-generated OpenAPI spec

**Note:** Root ID fields should be marked as `hidden: true` in Pydantic to exclude from OpenAPI docs.

---

## Implementation Order

### Priority 1: Core Infrastructure
1. Create `uuid_utils.py` (Task 1.1)
2. Create `seed_context.py` (Task 1.4)
3. Write unit tests for UUID utilities (Task 3.1)

### Priority 2: Schema & Service Updates
4. Update Pydantic schemas (Task 1.2)
5. Update service layer (Task 1.3)
6. Write schema validation tests (Task 3.2)

### Priority 3: Seed Data Migration
7. Generate UUIDv5 for all entities (Task 2.1)
8. Update seed JSON files (Task 2.2)
9. Update seeder (Task 2.3)
10. Write integration tests (Task 3.3)

### Priority 4: Cleanup & Documentation
11. Update existing tests (Task 3.4)
12. Update documentation (Tasks 4.1, 4.2, 4.3)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing API | Root ID fields optional; validation only rejects non-null values |
| UUID collision | UUIDv5 with namespace ensures uniqueness |
| Performance impact | UUIDv5 calculation is O(1), negligible |
| Test fragility | Tests updated to not rely on specific IDs unless seeded |
| Seeding idempotency | Verify with integration tests |

---

## Success Criteria

1. **Determinism**: Running seeder twice produces byte-for-byte identical database
2. **Test Stability**: Tests can reference known entity IDs from seed data
3. **API Security**: Production API rejects client-provided root IDs
4. **Backward Compatibility**: Existing code continues to work
5. **Documentation**: All changes documented and reviewable

---

## Rollback Plan

If issues arise:
1. Revert schema changes (remove optional root ID fields)
2. Revert service changes (remove ID override logic)
3. Keep seed JSON files with IDs (harmless, will be ignored)
4. Revert seeder changes
5. Re-enable auto-generation in services

No database migration required - changes are code-only.
