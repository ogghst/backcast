# Backend Coding Standards (Python/FastAPI)

**Last Updated:** 2026-01-19
**Scope:** Backend (Python/FastAPI), Database, EVCS Core

This document consolidates coding principles for a robust, reliable, and maintainable backend.

---

## 1. Core Principles

### 1.1 Strict Typing (Zero Tolerance)

**Rule:** Never use `Any`. Always define explicit types/interfaces.

```python
# ❌ Bad
def process_data(data: Any) -> Any:
    return data

# ✅ Good
def process_data(data: ProjectCreate) -> Project:
    return Project(**data.model_dump())
```

**Enforcement:** MyPy strict mode (`disallow_any_explicit = True`)

### 1.2 Source of Truth

**Backend Pydantic models are the single source of truth.**

**Process:**

1. Define Pydantic schemas in `backend/app/models/schemas/`
2. Frontend types must match these schemas exactly

### 1.3 Functional & Stateless

**Prefer pure functions. Isolate side effects.**

```python
# ✅ Pure function
def calculate_variance(budget: Decimal, actual: Decimal) -> Decimal:
    return budget - actual

# ✅ Isolate side effects
def calculate_and_log_variance(budget: Decimal, actual: Decimal) -> Decimal:
    variance = calculate_variance(budget, actual)  # Pure
    logger.info(f"Variance: {variance}")  # Side effect isolated
    return variance
```

### 1.4 API Response Patterns

**Standardize on server-side processing for scalability.**

**Rules:**

- Use `FilterParser` for all list endpoints.
- Whitelist allowed filter fields explicitly.
- Return `PaginatedResponse` for general listings.
- Unpack service tuples `(items, total)` in the API layer.
- Never concatenate raw SQL; use SQLAlchemy abstractions.

See [API Response Patterns](../cross-cutting/api-response-evcs-implementation-guide.md) for detailed implementation guides.

---

## 2. Common Principles

### 2.1 Type Safety (Non-Negotiable)

- **Standard:** MyPy strict mode, 100% type hint coverage
- **Rationale:** Catch bugs at compile time, enable safe refactoring

### 2.2 Code Quality Automation

- **Linting:** Ruff
- **Formatting:** Ruff Format
- **Pre-commit:** Hooks enforce quality before commit

### 2.3 Testing Strategy

**Coverage Requirements:**

- Minimum 80% overall coverage
- 100% coverage for critical paths (versioning, EVM calculations, auth)

**Test Types:**

1. **Unit Tests:** Pure logic (utils, services)
2. **Integration Tests:** Database operations, API interactions

### 2.4 Documentation

- **Docstrings:** Google-style docstrings for all public functions/classes
- **API Docs:** Auto-generated via FastAPI/OpenAPI

---

## 3. Backend Standards

### 3.1 Pydantic V2 Strict Mode

**Use `ConfigDict(strict=True)` for all schemas:**

```python
from pydantic import BaseModel, ConfigDict

class ProjectCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    code: str
    name: str
    budget: Decimal
```

**Prefer Pydantic models over raw dictionaries.**

### 3.2 Type Annotations (100% Coverage)

**Every function argument and return value MUST have type hints.**

**SQLAlchemy Models:** Use `Mapped[]` for columns

```python
class Project(TemporalBase):
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
```

**Use `typing.Annotated` for dependency injection:**

```python
CurrentUser = Annotated[User, Depends(get_current_active_user)]

@router.post("/projects")
async def create_project(
    project_in: ProjectCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> Project:
    ...
```

### 3.3 Documentation Requirements

**Google-style docstrings for complex logic:**

```python
async def calculate_earned_value(
    project_id: UUID,
    as_of: datetime,
) -> Decimal:
    """Calculate earned value for a project at a specific point in time.

    Args:
        project_id: The unique identifier of the project
        as_of: The timestamp for time-travel calculation

    Returns:
        The earned value amount as a Decimal

    Raises:
        ValueError: If project not found or calculation fails
    """
    ...
```

### 3.4 Service Layer Pattern

**Structure:** `TemporalService` for versioned entities, `SimpleService` for non-versioned

**Key Principles:**

- Services orchestrate business logic
- Use command pattern for state changes
- Always pass `actor_id` for audit trail
- Return domain objects, not ORM rows

### 3.5 API Route Conventions

**Example Pattern:**

```python
@router.post(
    "",
    response_model=ProjectPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_project",
    dependencies=[Depends(RoleChecker(required_permission="project-create"))],
)
async def create_project(...) -> Project:
    """Create a new project. Requires create permission."""
    try:
        return await service.create_project(...)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
```

### 3.6 Error Handling

**Pattern:** Raise `ValueError` in services, convert to `HTTPException` in routes

### 3.7 Testing Standards

**Pytest Patterns:**

```python
@pytest.mark.asyncio
async def test_create_project_success(session: AsyncSession, admin_user: User):
    """Should create project with valid data."""
    service = ProjectService(session)
    project = await service.create_project(...)
    assert project.code == "TEST-001"
```

**Test Isolation:** Use fresh `session` fixture, no shared state between tests

---

## 4. Architecture Patterns

### 4.1 EVCS (Entity Version Control System)

**Core Concepts:**

- **Bitemporal:** Track `valid_time` and `transaction_time`
- **Immutability:** Append-only
- **Branching:** Support branch isolation
- **Soft Delete:** `deleted_at` timestamp

**ADR:** [ADR-005: Bitemporal Versioning](../decisions/ADR-005-bitemporal-versioning.md)

### 4.2 Command Pattern

**State Changes:** Use command objects (`CreateVersionCommand`, `UpdateVersionCommand`)

**ADR:** [ADR-003: Command Pattern](../decisions/ADR-003-command-pattern.md)

### 4.3 RBAC (Role-Based Access Control)

**Backend:** `RoleChecker` dependency

**ADR:** [ADR-007: RBAC Service](../decisions/ADR-007-rbac-service.md)

---

## 5. Quality Gates

### 5.1 Pre-commit

```bash
ruff check app tests --fix
mypy app --strict
```

### 5.2 CI Pipeline

- ✅ Type check (MyPy)
- ✅ Linting (Ruff)
- ✅ Unit tests (pytest)
- ✅ Test coverage ≥80%

---

## 6. Common Pitfalls

❌ **Returning ORM rows instead of domain objects**

```python
# Bad
return results.scalars().all()

# Good
projects = results.scalars().all()
return [ProjectPublic.model_validate(p) for p in projects]
```

❌ **Not using snake_case for field names**

Use `project_id`, not `projectId`.
