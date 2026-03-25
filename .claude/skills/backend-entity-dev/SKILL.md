---
name: backend-entity-dev
description: Create and implement backend entities following EVCS patterns. Determines entity type (Simple, Versionable, Branchable), generates SQLAlchemy models, schemas, services, repositories, and tests with strict typing. Use when creating new entities, adding domain models, implementing database tables, or when user mentions "entity", "model", "schema", "service layer", or "database table".
allowed-tools: [AskUserQuestion, Read, Write, Edit, Glob, Grep]
---

# Backend Entity Development Skill

Guides creation of backend entities following the Backcast  coding standards and EVCS (Entity Versioning Control System) patterns.

## Quick Start

When prompted to create a new backend entity:

1. **Determine Entity Type** - Ask clarifying questions about versioning and branching needs
2. **Generate Model** - Create SQLAlchemy model with proper base class and mixins
3. **Create Schemas** - Generate Pydantic schemas (Create, Update, Public)
4. **Implement Service** - Create service layer with appropriate base service
5. **Add Repository** - Implement repository if custom queries needed
6. **Write Tests** - Create unit and integration tests

## Entity Type Decision Guide

| Question                      | Simple | Versionable | Branchable |
| ----------------------------- | ------ | ----------- | ---------- |
| Need version history?         | No     | Yes         | Yes        |
| Need branching/change orders? | No     | No          | Yes        |
| Soft delete required?         | No     | Yes         | Yes        |
| Audit trail required?         | No     | Yes         | Yes        |

### Quick Decision Tree

```
Need version history?
├─ No → Simple Entity (SimpleEntityBase)
└─ Yes → Need branching/change orders?
    ├─ No → Versionable Entity (EntityBase + VersionableMixin)
    └─ Yes → Branchable Entity (EntityBase + VersionableMixin + BranchableMixin)
```

## Common Entity Types by Domain

### Projects & Planning

- Projects → Branchable
- WBE (Work Breakdown Elements) → Branchable
- Milestones → Branchable
- Project Templates → Simple

### Finance

- Cost Elements → Branchable
- Budget Allocations → Branchable
- Payment Records → Versionable
- Exchange Rates → Simple

### User Management

- Users → Versionable
- Departments → Versionable
- User Preferences → Simple
- Access Logs → Versionable

## Implementation Checklist

### 1. Model (`app/models/domain/[entity].py`)

- [ ] Import correct base class (SimpleEntityBase, EntityBase)
- [ ] Import mixins (VersionableMixin, BranchableMixin) if needed
- [ ] Use `Mapped[]` type annotations for all columns
- [ ] Use `mapped_column()` with proper constraints
- [ ] Define `__tablename__` as lowercase plural
- [ ] Add proper indexes on foreign keys and query columns
- [ ] Use UUID type from `app.models.types` (FG_UUID for FK, PG_UUID for PK)

### 2. Schemas (`app/models/schemas/[entity].py`)

- [ ] Import `BaseModel` and `ConfigDict`
- [ ] Set `model_config = ConfigDict(strict=True)` on all schemas
- [ ] Create: `[Entity]Create`, `[Entity]Update`, `[Entity]Public`
- [ ] Include all fields except auto-generated timestamps
- [ ] Use proper types (str, int, Decimal, UUID, datetime)
- [ ] Mark optional fields with `| None` for Update schemas

### 3. Service (`app/services/[entity]_service.py`)

- [ ] Extend `SimpleService[TSimple]`, `TemporalService[TVersionable]`, or `BranchableService[TBranchable]`
- [ ] Override CRUD methods only if custom logic needed
- [ ] Always accept `actor_id: UUID` for state changes
- [ ] Return domain objects, not ORM rows
- [ ] Raise `ValueError` for business logic violations
- [ ] Add Google-style docstrings for public methods

### 4. Repository (`app/repositories/[entity]_repository.py`)

- [ ] Extend base repository class
- [ ] Only create if custom queries needed
- [ ] Use `select()` and `exec()` for queries
- [ ] Use proper async/await patterns

### 5. API Routes (`app/api/v1/[entity].py`)

- [ ] Create router with proper prefix
- [ ] Add operation_id for each route
- [ ] Use `RoleChecker` dependency for permissions
- [ ] Convert service errors to `HTTPException`
- [ ] Return proper response models
- [ ] Use `Annotated` for dependency injection

### 6. Tests

- [ ] Unit tests for service layer business logic
- [ ] Integration tests for database operations
- [ ] Test fixture for entity creation
- [ ] 80%+ coverage required
- [ ] Use `pytest.mark.asyncio` for async tests

## Code Examples by Entity Type

### Versionable Entity Examples

- **Model**: [`backend/app/models/domain/user.py`](../../../../backend/app/models/domain/user.py) - User with bitemporal versioning
- **Schema**: [`backend/app/models/schemas/user.py`](../../../../backend/app/models/schemas/user.py)
- **Service**: [`backend/app/services/user_service.py`](../../../../backend/app/services/user_service.py)

### Branchable Entity Examples

- **Model**: [`backend/app/models/domain/cost_element.py`](../../../../backend/app/models/domain/cost_element.py) - Cost allocation with branching
- **Schema**: [`backend/app/models/schemas/cost_element.py`](../../../../backend/app/models/schemas/cost_element.py)
- **Service**: [`backend/app/services/cost_element_service.py`](../../../../backend/app/services/cost_element_service.py)

### Other Examples

- **WBE** (Branchable): [`backend/app/models/domain/wbe.py`](../../../../backend/app/models/domain/wbe.py)
- **Project** (Branchable): [`backend/app/models/domain/project.py`](../../../../backend/app/models/domain/project.py)
- **Department** (Versionable): [`backend/app/models/domain/department.py`](../../../../backend/app/models/domain/department.py)

## Common Pitfalls

### ❌ Using `Any` type

```python
# Bad
def process_data(data: Any) -> Any:
    return data

# Good
def process_data(data: ProjectCreate) -> Project:
    return Project(**data.model_dump())
```

### ❌ Accessing SQLAlchemy objects after session operations

```python
# Bad - May cause MissingGreenlet errors
wbe = await CreateVersionCommand(...).execute(session)
# ... some SQL operations ...
wbe_id = created_wbe.wbe_id  # Object may have expired

# Good - Capture IDs immediately
wbe = await CreateVersionCommand(...).execute(session)
wbe_id = wbe.wbe_id  # Capture ID before object expires
```

### ❌ Generating timestamps multiple times

```python
# Bad - May create empty ranges
await self._check_overlap(session, datetime.now(UTC), branch)
await self._close_version(session, version, datetime.now(UTC))

# Good - Generate once
timestamp = datetime.now(UTC)
await self._check_overlap(session, timestamp, branch)
await self._close_version(session, version, timestamp)
```

### ❌ Returning ORM rows from API

```python
# Bad
return results.scalars().all()

# Good
projects = results.scalars().all()
return [ProjectPublic.model_validate(p) for p in projects]
```

## Out of Scope

This skill does NOT:

- Handle frontend TypeScript types (use frontend-entity-dev skill)
- Create API route documentation (auto-generated via FastAPI)
- Manage database migrations (use Alembic directly)
- Implement authentication/authorization logic

## Quality Gates

Before completion, ensure:

- [ ] MyPy strict mode passes (zero errors)
- [ ] Ruff linting passes (zero errors)
- [ ] All tests pass (pytest)
- [ ] Test coverage ≥80%
- [ ] Docstrings on all public methods

## Related Documentation

- [Entity Classification Guide](../../../../docs/02-architecture/backend/contexts/evcs-core/entity-classification.md) - Full decision tree and examples
- [Backend Coding Standards](../../../../docs/02-architecture/backend/coding-standards.md) - Complete standards reference
- [EVCS Implementation Guide](../../../../docs/02-architecture/backend/contexts/evcs-core/evcs-implementation-guide.md) - EVCS patterns and recipes
