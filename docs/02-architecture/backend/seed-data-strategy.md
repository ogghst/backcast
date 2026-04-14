# Seed Data Strategy

**Last Updated:** 2026-04-14
**Status:** Implemented

## Overview

The seed data system provides deterministic, repeatable database initialization for development, testing, and staging environments. All entities use UUIDv5 namespace-based identifiers for consistency across environments.

## Key Principles

1. **Deterministic IDs**: Same code always produces the same UUID (UUIDv5 namespace-based)
2. **ID-Based Relationships**: Foreign keys use explicit UUIDs instead of code lookups
3. **Explicit Root IDs**: All entities declare their root entity ID in JSON files
4. **Security Isolation**: API rejects client-provided root IDs (internal-only)
5. **Test Reliability**: Predictable entity IDs enable stable test assertions

---

## UUIDv5 Namespace Strategy

### Namespace Hierarchy

```mermaid
graph TD
    A[DNS Namespace: uuid.NAMESPACE_DNS] --> B[Entity Type Namespace]
    B --> C1[Project Namespace]
    B --> C2[WBE Namespace]
    B --> C3[User Namespace]
    B --> C4[Department Namespace]
    B --> C5[CostElement Namespace]
    B --> C6[CostElementType Namespace]

    C1 --> D1[PRJ-DEMO-001 → d54f...]
    C2 --> D2[PRJ-DEMO-001-L1-1 → 3a42...]
    C3 --> D3[admin@backcast.org → e035...]
```

### Generation Algorithm

```python
# From: app/core/uuid_utils.py
from uuid import uuid5, NAMESPACE_DNS

def generate_entity_uuid(entity_type: str, identifier: str) -> UUID:
    """Generate deterministic UUID for an entity using UUIDv5."""
    # Create entity-specific namespace from DNS namespace
    namespace = uuid5(NAMESPACE_DNS, f"entities.{entity_type}.backcast.org")
    # Generate deterministic UUID from identifier
    return uuid5(namespace, identifier)
```

### Entity-Specific Functions

| Entity Type | Identifier | Function | Example |
| ----------- | ---------- | -------- | ------- |
| Project | `project_code` | `generate_project_uuid(code)` | `PRJ-DEMO-001` → `d54fbbe6-f3df-51db-9c3e-9408700442be` |
| WBE | `wbe_code` | `generate_wbe_uuid(code)` | `PRJ-DEMO-001-L1-1` → `3a42f62c-96f8-5392-bff1-2e16f97734f0` |
| User | `email` | `generate_user_uuid(email)` | `admin@backcast.org` → `e03556f3-4385-5d68-a685-af307fc8af5c` |
| Department | `department_code` | `generate_department_uuid(code)` | `ENG` → `e498f139-05b6-5da8-9008-31a8d760bcdc` |
| Cost Element | `cost_element_code` | `generate_cost_element_uuid(code)` | `CE-001` → `18c26d12-9789-5004-b766-3b099405e884` |
| Cost Element Type | `cost_element_type_code` | `generate_cost_element_type_uuid(code)` | `LAB` → `6a483c4e-893c-5a92-8db9-6f5ac937c63f` |

---

## Seed File Structure

### JSON Schema Convention

All seed files follow this pattern:

```json
[
  {
    "{entity}_id": "<uuidv5>",
    "code": "<unique_code>",
    "name": "<display_name>",
    "<relationship_id>": "<related_uuid>",
    ...
  }
]
```

### Example: projects.json

```json
[
  {
    "project_id": "d54fbbe6-f3df-51db-9c3e-9408700442be",
    "code": "PRJ-DEMO-001",
    "name": "Demo Project 1",
    "budget": 1000000.0,
    "contract_value": 1200000.0,
    "description": "Auto-generated demo project 1",
    "start_date": "2026-01-07T05:49:36.993776",
    "end_date": "2027-01-07T05:49:36.993839"
  }
]
```

### Example: wbes.json (ID-Based Relationships)

```json
[
  {
    "wbe_id": "3a42f62c-96f8-5392-bff1-2e16f97734f0",
    "code": "PRJ-DEMO-001-L1-1",
    "name": "L1 WBE 1",
    "project_id": "d54fbbe6-f3df-51db-9c3e-9408700442be",
    "parent_wbe_id": null,
    "budget_allocation": 100000.0,
    "level": 1,
    "description": "Level 1 Parent WBE"
  }
]
```

**Key Changes:**
- `project_code` → `project_id` (direct UUID reference)
- `parent_wbe_code` → `parent_wbe_id` (direct UUID reference)

### Example: users.json (Email-Based UUIDs)

```json
[
  {
    "user_id": "e03556f3-4385-5d68-a685-af307fc8af5c",
    "email": "admin@backcast.org",
    "password": "adminadmin",
    "full_name": "System Administrator",
    "role": "admin",
    "department": "ADMIN"
  }
]
```

---

## Relationship Strategy

### Before (Code-Based)

```json
{
  "wbe_id": "3a42f62c-96f8-5392-bff1-2e16f97734f0",
  "project_code": "PRJ-DEMO-001",
  "parent_wbe_code": null
}
```

**Problems:**
- Required runtime lookup during seeding
- Brittle if codes change
- No type safety

### After (ID-Based)

```json
{
  "wbe_id": "3a42f62c-96f8-5392-bff1-2e16f97734f0",
  "project_id": "d54fbbe6-f3df-51db-9c3e-9408700442be",
  "parent_wbe_id": null
}
```

**Benefits:**
- No lookup required during seeding
- Type-safe foreign keys
- Explicit dependencies
- Faster seeding

### Relationship Mapping

| Entity | Relationship Field | Target Entity |
| ------ | ----------------- | ------------- |
| WBE | `project_id` | Project |
| WBE | `parent_wbe_id` | WBE (self) |
| Cost Element | `wbe_id` | WBE |
| Cost Element | `cost_element_type_id` | CostElementType |
| Cost Element Type | `department_id` | Department |
| User | `department_id` | Department (via code) |

---

## Seeder Implementation

### Seed Context Pattern

The `seed_operation()` context manager allows explicit IDs during seeding while API calls reject them:

```python
# From: app/db/seed_context.py
from contextlib import contextmanager
from contextvars import ContextVar

_seed_operation: ContextVar[bool] = ContextVar("_seed_operation", default=False)

@contextmanager
def seed_operation() -> Generator[None, None, None]:
    """Mark current operation as seed data import (bypasses ID validation)."""
    token = _seed_operation.set(True)
    try:
        yield
    finally:
        _seed_operation.reset(token)

def is_seed_operation() -> bool:
    """Check if currently within a seed_operation() context."""
    return _seed_operation.get()
```

### Seeder Methods

```python
# From: app/db/seeder.py
class DataSeeder:
    async def seed_wbes(self, session: AsyncSession) -> None:
        with seed_operation():  # Allow explicit wbe_id from seed data
            for item in wbe_data:
                # project_id and parent_wbe_id are already UUIDs
                wbe_in = WBECreate(**item)
                created_wbe = await wbe_service.create_wbe(wbe_in, actor_id)
```

**Benefits:**
- No code-to-ID resolution required
- Thread-safe context tracking
- API can check `is_seed_operation()` to reject client IDs

---

## Schema Updates

### Pydantic Create Schemas

All Create schemas accept optional root ID fields (excluded from OpenAPI):

```python
# From: app/models/schemas/project.py
class ProjectCreate(ProjectBase):
    project_id: UUID | None = Field(
        None,
        description="Root Project ID (internal use only for seeding)",
        exclude=True,  # Hide from OpenAPI docs
    )
```

**Security**: `exclude=True` prevents these fields from appearing in API documentation.

### Service Layer Pattern

Services use provided root IDs when available:

```python
# From: app/services/project.py
async def create_project(
    self, project_in: ProjectCreate, actor_id: UUID
) -> Project:
    project_data = project_in.model_dump(exclude_unset=True)

    # Use provided project_id (for seeding) or generate new one
    root_id = project_in.project_id or uuid4()
    project_data["project_id"] = root_id

    # Create via TemporalService
    return await self.service.create(root_id=root_id, **project_data)
```

---

## Migration Strategy

### Migration Script

Existing code-based relationships can be migrated using:

```bash
# From: backend/scripts/update_seed_relationships.py
uv run python scripts/update_seed_relationships.py
```

**Transformations:**
- `project_code` → `project_id` (lookup via `generate_project_uuid`)
- `parent_wbe_code` → `parent_wbe_id` (lookup via wbe_id_map)
- `wbe_code` → `wbe_id` (lookup via wbe_id_map)
- `cost_element_type_code` → `cost_element_type_id` (lookup via cet_id_map)
- `department_code` → `department_id` (lookup via dept_id_map)

### UUID Generation Report

Generate all seed UUIDs for reference:

```bash
# From: backend/scripts/generate_seed_uuids.py
uv run python scripts/generate_seed_uuids.py
```

Output example:
```
=== Seed UUID Report ===

Projects:
  PRJ-DEMO-001 → d54fbbe6-f3df-51db-9c3e-9408700442be
  PRJ-DEMO-002 → 877c4cba-b30e-54c1-b25d-c73fb364019d

WBEs:
  PRJ-DEMO-001-L1-1 → 3a42f62c-96f8-5392-bff1-2e16f97734f0
  ...
```

---

## Testing

### Test Verification

Tests verify that provided root IDs are actually used:

```python
# From: tests/unit/db/test_seeder.py
async def test_seed_wbes_uses_provided_wbe_id(self, db_session: AsyncSession, tmp_path: Path):
    expected_wbe_id = UUID("3a42f62c-96f8-5392-bff1-2e16f97734f0")

    wbe_data = [{
        "wbe_id": str(expected_wbe_id),
        "project_id": "d54fbbe6-f3df-51db-9c3e-9408700442be",
        "code": "TEST-WBE-001",
        ...
    }]

    await seeder.seed_wbes(db_session)

    # Verify the provided wbe_id was actually used
    call_args = mock_service.create_wbe.call_args
    assert call_args[0][0].wbe_id == expected_wbe_id
```

### Running Tests

```bash
cd backend
uv run pytest tests/unit/db/test_seeder.py -v
```

**Results:**
- 18/18 tests passing
- Verifies root ID usage
- Verifies relationship ID usage
- Tests backward compatibility

---

## Security Considerations

### API Rejection of Client IDs

**Future Enhancement**: API routes should reject client-provided root IDs:

```python
# Proposed validation in API routes
from app.db.seed_context import is_seed_operation

@router.post("/projects", response_model=ProjectResponse)
async def create_project(project_in: ProjectCreate, actor_id: UUID):
    # Reject client-provided root IDs (security)
    if project_in.project_id and not is_seed_operation():
        raise HTTPException(
            status_code=400,
            detail="Cannot specify project_id (auto-generated)"
        )
    ...
```

This prevents:
- UUID collision attacks
- ID prediction vulnerabilities
- Authorization bypass via ID reuse

---

## File Locations

| Component | Path |
| --------- | ---- |
| UUID Utilities | `backend/app/core/uuid_utils.py` |
| Seed Context | `backend/app/db/seed_context.py` |
| Seeder | `backend/app/db/seeder.py` |
| Seed Files | `backend/seed/*.json` |
| Migration Script | `backend/scripts/update_seed_relationships.py` |
| UUID Generator | `backend/scripts/generate_seed_uuids.py` |
| Tests | `backend/tests/unit/db/test_seeder.py` |

---

## Benefits Summary

| Aspect | Before | After |
| ------- | ------ | ------ |
| **ID Generation** | Random UUIDv4 | Deterministic UUIDv5 |
| **Relationships** | Code-based lookup | Direct UUID reference |
| **Test Stability** | Unpredictable IDs | Known, stable IDs |
| **Seeding Speed** | N+1 lookup queries | Direct insertion |
| **Type Safety** | String codes | UUID types |
| **Debugging** | Unknown entity IDs | Predictable IDs |
| **Cross-Env** | Different IDs | Same IDs everywhere |

---

## See Also

- [EVCS Core Architecture](./contexts/evcs-core/architecture.md) - Entity versioning system
- [ADR-005: Bitemporal Versioning](../decisions/ADR-005-bitemporal-versioning.md) - Versioning decision
- [Database Strategy](../cross-cutting/database-strategy.md) - PostgreSQL patterns
