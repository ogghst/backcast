# Coding Standards

**Last Updated:** 2026-01-08  
**Scope:** Backend (Python/FastAPI), Frontend (TypeScript/React), Common Patterns

This document consolidates coding principles for a robust, reliable, and maintainable codebase. It builds on established patterns from [ADR-004](decisions/ADR-004-quality-standards.md) and [Frontend Quality Standards](frontend/contexts/04-quality-testing.md).

---

## 1. Core Principles

### 1.1 Strict Typing (Zero Tolerance)

**Rule:** Never use `Any` (Python) or `any` (TypeScript). Always define explicit types/interfaces.

**Backend:**

```python
# ❌ Bad
def process_data(data: Any) -> Any:
    return data

# ✅ Good
def process_data(data: ProjectCreate) -> Project:
    return Project(**data.model_dump())
```

**Frontend:**

```typescript
// ❌ Bad
function formatProject(project: any): any {
  return project;
}

// ✅ Good
function formatProject(project: Project): FormattedProject {
  return { code: project.code, name: project.name };
}
```

**Enforcement:**

- Backend: MyPy strict mode (`disallow_any_explicit = True`)
- Frontend: TypeScript `"strict": true` with `noImplicitAny`

### 1.2 Source of Truth

**Backend Pydantic models are the single source of truth.** Frontend types must match API response structures perfectly.

**Process:**

1. Define Pydantic schemas in `backend/app/models/schemas/`
2. Generate TypeScript types from OpenAPI spec OR manually match
3. Validate response types in frontend services

**Example:**

```python
# Backend: Source of Truth
class ProjectPublic(BaseModel):
    project_id: UUID
    code: str
    name: str
    budget: Decimal
```

```typescript
// Frontend: Must Match Exactly
export interface Project {
  project_id: string; // UUID as string in JSON
  code: string;
  name: string;
  budget: string; // Decimal as string in JSON
}
```

### 1.3 Functional & Stateless

**Prefer pure functions. Isolate side effects.**

**Pure Function Characteristics:**

- Same input → Same output (deterministic)
- No side effects (no mutations, no I/O)
- Easier to test, reason about, and parallelize

**Example:**

```python
# ✅ Pure function
def calculate_variance(budget: Decimal, actual: Decimal) -> Decimal:
    return budget - actual

# ❌ Impure (side effect)
def log_variance(budget: Decimal, actual: Decimal) -> Decimal:
    variance = budget - actual
    logger.info(f"Variance: {variance}")  # Side effect: I/O
    return variance

# ✅ Isolate side effects
def calculate_and_log_variance(budget: Decimal, actual: Decimal) -> Decimal:
    variance = calculate_variance(budget, actual)  # Pure
    logger.info(f"Variance: {variance}")  # Side effect isolated
    return variance
```

**Frontend:**

```typescript
// ✅ Pure component logic
function useProjectStats(projects: Project[]) {
  return useMemo(() => {
    return projects.reduce((sum, p) => sum + parseFloat(p.budget), 0);
  }, [projects]);
}
```

### 1.4 Error Handling

**Fail gracefully. Use standard HTTP status codes.**

**HTTP Status Codes:**

- `200 OK` - Successful GET
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Validation error
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Business rule violation
- `500 Internal Server Error` - Unexpected error

See Section 2.4 for implementation patterns.

---

## 2. Common Principles

### 2.1 Type Safety (Non-Negotiable)

- **Backend:** MyPy strict mode, 100% type hint coverage
- **Frontend:** TypeScript strict mode (`tsconfig.app.json`)
- **Rationale:** Catch bugs at compile time, improve maintainability, enable safe refactoring

### 2.2 Code Quality Automation

- **Linting:** Ruff (backend), ESLint (frontend)
- **Formatting:** Ruff Format (backend), Prettier (frontend)
- **Pre-commit:** Hooks enforce quality before commit (Husky + lint-staged)
- **CI/CD:** Zero tolerance for linting/type errors in pipeline

### 2.3 Testing Strategy

**Coverage Requirements:**

- Minimum 80% overall coverage ([ADR-004](decisions/ADR-004-quality-standards.md))
- 100% coverage for critical paths (versioning, EVM calculations, auth)

**Test Types:**

1. **Unit Tests:** Pure logic (utils, hooks, services)
2. **Integration Tests:** Database operations, API interactions
3. **E2E Tests:** Critical user flows (CRUD, auth, navigation)

**Test Naming:** `test_{feature}_{scenario}_{expected_outcome}`

Example: `test_project_create_with_duplicate_code_raises_error`

### 2.4 Documentation Standards

- **Docstrings:** All public functions/classes
- **Architecture Changes:** Document via ADRs in `docs/02-architecture/decisions/`
- **API Docs:** Auto-generated via FastAPI/OpenAPI
- **Comments:** Explain _why_, not _what_ (code is self-documenting)

---

## 3. Backend Standards (Python/FastAPI)

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

**Benefits:**

- Prevents implicit type coercion
- Catches type mismatches at validation time
- Ensures data integrity

**Prefer Pydantic models over raw dictionaries:**

```python
# ❌ Bad
def create_project(data: dict[str, Any]) -> Project:
    code = data.get("code")
    ...

# ✅ Good
def create_project(data: ProjectCreate) -> Project:
    code = data.code  # Type-safe access
    ...
```

### 3.2 Type Annotations (100% Coverage)

**Every function argument and return value MUST have type hints.**

**Required:**

```python
from uuid import UUID
from collections.abc import Sequence

async def get_projects(
    self,
    skip: int = 0,
    limit: int = 100,
    branch: str = "main"
) -> Sequence[Project]:
    """Get all projects with pagination."""
    ...
```

**SQLAlchemy Models:** Use `Mapped[]` for columns

```python
from sqlalchemy.orm import Mapped, mapped_column

class Project(TemporalBase):
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
```

**Use `typing.Annotated` for dependency injection:**

```python
from typing import Annotated
from fastapi import Depends

CurrentUser = Annotated[User, Depends(get_current_active_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]

@router.post("/projects")
async def create_project(
    project_in: ProjectCreate,
    current_user: CurrentUser,  # Clean, reusable
    session: DBSession,
) -> Project:
    ...
```

See: `backend/app/models/domain/project.py`

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

**FastAPI endpoints: Add summary and description for OpenAPI:**

```python
@router.post(
    "",
    response_model=ProjectPublic,
    summary="Create a new project",
    description="Creates a new project with the provided code, name, and budget. Requires project-create permission.",
)
async def create_project(...) -> Project:
    """Create a new project. Requires create permission."""
    ...
```

### 3.4 Service Layer Pattern

**Structure:** `TemporalService` for versioned entities, `SimpleService` for non-versioned

**Example:** `backend/app/services/cost_element_service.py`

**Key Principles:**

- Services orchestrate business logic
- Use command pattern for state changes (`CreateVersionCommand`, `UpdateVersionCommand`)
- Always pass `actor_id` for audit trail
- Return domain objects, not ORM rows

### 3.5 API Route Conventions

**Pattern:** See `backend/app/api/routes/projects.py`

```python
@router.post(
    "",
    response_model=ProjectPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_project",
    dependencies=[Depends(RoleChecker(required_permission="project-create"))],
)
async def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    service: ProjectService = Depends(get_project_service),
) -> Project:
    """Create a new project. Requires create permission."""
    try:
        existing = await service.get_by_code(project_in.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project with code '{project_in.code}' already exists",
            )

        return await service.create_project(
            project_in=project_in,
            actor_id=current_user.user_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
```

**Checklist:**

- ✅ `operation_id` for OpenAPI client generation
- ✅ RBAC via `RoleChecker` dependency
- ✅ Explicit status codes (`201`, `404`, etc.)
- ✅ Pydantic schemas for request/response (`ProjectCreate`, `ProjectPublic`)
- ✅ Proper exception handling with HTTP status codes
- ✅ Service dependency injection via `Depends()`

### 3.6 Error Handling

**Pattern:** Raise `ValueError` in services, convert to `HTTPException` in routes

```python
# Service Layer
async def update_project(...) -> Project:
    current = await self.get_by_root_id(project_id)
    if not current:
        raise ValueError(f"Project {project_id} not found")
    ...

# API Layer
@router.put("/{project_id}", ...)
async def update_project(...) -> Project:
    try:
        return await service.update_project(...)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
```

### 3.7 Testing Standards

**Fixtures:** See `backend/tests/conftest.py`

**Pytest Patterns:**

```python
@pytest.mark.asyncio
async def test_create_project_success(session: AsyncSession, admin_user: User):
    """Should create project with valid data."""
    service = ProjectService(session)

    project = await service.create_project(
        project_in=ProjectCreate(code="TEST-001", name="Test Project"),
        actor_id=admin_user.user_id,
    )

    assert project.code == "TEST-001"
    assert project.created_by == admin_user.user_id
```

**Test Isolation:** Use fresh `session` fixture, no shared state between tests

---

## 4. Frontend Standards (TypeScript/React)

### 4.1 TypeScript Configuration

**Strict Mode:** `tsconfig.app.json` enforces:

```json
{
  "strict": true,
  "noUnusedLocals": true,
  "noUnusedParameters": true,
  "noFallthroughCasesInSwitch": true
}
```

**Path Aliases:** Use `@/` for imports

```typescript
import { ProjectsService } from "@/api/services/projects";
```

### 4.2 Component Structure

**Principle: Separate Logic from View**

```typescript
// ✅ Good: Logic in custom hook, view in component

// hooks/useProjectStats.ts
function useProjectStats(projects: Project[]) {
  return useMemo(() => {
    const total = projects.reduce((sum, p) => sum + parseFloat(p.budget), 0);
    const count = projects.length;
    return { total, count, average: total / count };
  }, [projects]);
}

// components/ProjectStats.tsx
function ProjectStats({ projects }: { projects: Project[] }) {
  const stats = useProjectStats(projects);

  return (
    <div>
      <p>Total: €{stats.total}</p>
      <p>Average: €{stats.average}</p>
    </div>
  );
}
```

### 4.3 Component Organization

**Pattern:** Feature-based organization

```
frontend/src/
├── features/
│   ├── projects/
│   │   ├── components/
│   │   │   ├── ProjectList.tsx
│   │   │   └── ProjectModal.tsx
│   │   ├── hooks/
│   │   │   └── useProjects.ts
│   │   └── types.ts
```

**Naming Conventions:**

- Components: PascalCase (`ProjectList.tsx`)
- Hooks: camelCase with `use` prefix (`useProjects.ts`)
- Types: PascalCase interfaces/types (`Project`, `ProjectCreate`)

### 4.4 Data Fetching Pattern

**Rule: Use TanStack Query for ALL server state. NEVER use `useEffect` for data fetching.**

**❌ Bad:**

```typescript
function ProjectList() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Don't do this!
    ProjectsService.getProjects().then((data) => {
      setProjects(data);
      setLoading(false);
    });
  }, []);

  // No loading states, error handling, caching, refetching...
}
```

**✅ Good:** Use `createResourceHooks` from `@/hooks/useCrud.ts`

```typescript
// Direct pattern (recommended)
const { useList, useCreate, useUpdate, useDelete } = createResourceHooks(
  "projects",
  {
    list: ProjectsService.getProjects,
    detail: ProjectsService.getProject,
    create: ProjectsService.createProject,
    update: ProjectsService.updateProject,
    delete: ProjectsService.deleteProject,
  }
);

// Usage in component
function ProjectList() {
  const { data: projects, isLoading } = useList();
  const createMutation = useCreate();

  if (isLoading) return <Spin />;

  return (
    <StandardTable
      data={projects}
      columns={columns}
      onCreate={(data) => createMutation.mutate(data)}
    />
  );
}
```

See: `frontend/src/hooks/useCrud.ts` for full pattern

### 4.5 State Management

**Global State:** Zustand for stores (`@/stores/`)

**Server State:** TanStack Query (React Query)

**Form State:** Ant Design Form hooks

**Rule:** Never duplicate server state in Zustand (use React Query)

### 4.6 Error Handling

**Error Boundaries:** Wrap app in `<ErrorBoundary>` (see `frontend/src/components/ErrorBoundary.tsx`)

```tsx
<ErrorBoundary>
  <App />
</ErrorBoundary>
```

**User Feedback:** Use `toast.error()` for mutations (built into `useCrud` hooks)

**Network Errors:** Handled by React Query with retry logic

### 4.7 Component Best Practices

**Code Style: Early returns to avoid deep nesting**

```typescript
// ❌ Bad: Deep nesting
function ProjectDetail({ id }: { id: string }) {
  const { data, isLoading } = useProjects.useDetail(id);

  if (data) {
    if (data.budget > 0) {
      if (data.wbes && data.wbes.length > 0) {
        return <ProjectView project={data} />;
      } else {
        return <EmptyWBEs />;
      }
    } else {
      return <NoBudget />;
    }
  } else if (isLoading) {
    return <Spin />;
  } else {
    return <NotFound />;
  }
}

// ✅ Good: Early returns
function ProjectDetail({ id }: { id: string }) {
  const { data, isLoading } = useProjects.useDetail(id);

  if (isLoading) return <Spin />;
  if (!data) return <NotFound />;
  if (data.budget <= 0) return <NoBudget />;
  if (!data.wbes?.length) return <EmptyWBEs />;

  return <ProjectView project={data} />;
}
```

### 4.8 Declarative Patterns

**Prefer Declarative Patterns:**

- Use Ant Design `<Result>` for empty states
- Use `<Spin>` for loading states
- Use `<Can>` wrapper for RBAC (see `frontend/src/components/Can.tsx`)

**Example:**

```tsx
function ProjectList() {
  const { data, isLoading } = useProjects.useList();

  if (isLoading) return <Spin />;
  if (!data?.length) return <Result title="No projects found" />;

  return <StandardTable data={data} columns={columns} />;
}
```

### 4.9 Testing Standards

**Unit/Integration:** Vitest + React Testing Library

**Pattern:**

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

describe("ProjectList", () => {
  it("should render project table", () => {
    render(<ProjectList />);
    expect(screen.getByRole("table")).toBeInTheDocument();
  });
});
```

**E2E:** Playwright (see `frontend/tests/e2e/projects_crud.spec.ts`)

**Key Principles:**

- Test user behavior, not implementation details
- Use `getByRole`, `getByLabel` over `getByTestId`
- Wait for modal close/data refresh, avoid toast assertions
- Use unique identifiers (timestamps) for test data

**E2E Pattern:**

```typescript
test("should create project", async ({ page }) => {
  await page.goto("/projects");

  // Wait for page load
  await expect(page.locator(".ant-table-wrapper")).toBeVisible();

  // Create
  await page.getByRole("button", { name: "Add Project" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();

  const projectCode = `E2E-${Date.now()}`;
  await page.getByLabel("Project Code").fill(projectCode);
  await page.getByRole("button", { name: "Create" }).click();

  // Verify via data in table, not toast
  await expect(page.locator(".ant-modal-content")).not.toBeVisible();
  await expect(page.locator(`text=${projectCode}`)).toBeVisible();
});
```

---

## 5. Development Process

### 5.1 Think First

**Before writing code, outline the plan:**

1. What problem are we solving?
2. What are the inputs and outputs?
3. What are the edge cases?
4. What dependencies exist?

**Example Planning Comment:**

```python
# Plan: Implement project variance calculation
# Input: project_id (UUID), as_of (datetime)
# Output: VarianceReport (budget vs actual)
# Edge cases:
#   - Project not found → 404
#   - No cost elements → variance = budget
#   - Time travel to before project start → use initial budget
# Dependencies: ProjectService, CostElementService
```

### 5.2 Interface First

**Define Pydantic models (backend) or interfaces (frontend) BEFORE implementation.**

**Backend Example:**

```python
# 1. Define schemas first
class VarianceReportCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    project_id: UUID
    as_of: datetime

class VarianceReport(BaseModel):
    project_id: UUID
    budget: Decimal
    actual: Decimal
    variance: Decimal
    percent_deviation: Decimal

# 2. Then implement service
class VarianceService:
    async def calculate_variance(
        self,
        request: VarianceReportCreate
    ) -> VarianceReport:
        ...
```

**Frontend Example:**

```typescript
// 1. Define types first
interface VarianceReportRequest {
  project_id: string;
  as_of: string; // ISO datetime
}

interface VarianceReport {
  project_id: string;
  budget: string;
  actual: string;
  variance: string;
  percent_deviation: string;
}

// 2. Then implement hook
function useVarianceReport(request: VarianceReportRequest) {
  return useQuery(...);
}
```

### 5.3 Validation

**Ensure code compiles before committing:**

**Backend:**

```bash
mypy app --strict
pytest tests/ --no-cov  # Quick smoke test
```

**Frontend:**

```bash
tsc --noEmit
npm run lint
vitest run  # Unit tests
```

---

## 6. Architecture Patterns

### 6.1 EVCS (Entity Version Control System)

**Core Concepts:**

- **Bitemporal:** Track `valid_time` (business) and `transaction_time` (system)
- **Immutability:** Append-only, updates create new versions
- **Branching:** All versioned entities support branch isolation
- **Soft Delete:** Use `deleted_at` timestamp, not hard deletes

**Implementation:** `backend/app/core/versioning/service.py` (TemporalService)

**ADR:** [ADR-005: Bitemporal Versioning](decisions/ADR-005-bitemporal-versioning.md)

### 6.2 Command Pattern

**State Changes:** Use command objects for create/update/delete

**Example:** See `backend/app/services/cost_element_service.py`

```python
class CostElementUpdateCommand(UpdateVersionCommand):
    def __init__(self, entity_class, root_id, actor_id, branch="main", **updates):
        super().__init__(entity_class, root_id, actor_id, **updates)
        self.branch = branch

    async def _get_current(self, session: AsyncSession):
        # Custom logic to filter by branch
        ...
```

**ADR:** [ADR-003: Command Pattern](decisions/ADR-003-command-pattern.md)

### 6.3 RBAC (Role-Based Access Control)

**Backend:** `RoleChecker` dependency

```python
dependencies=[Depends(RoleChecker(required_permission="project-create"))]
```

**Frontend:** `<Can>` component

```tsx
<Can permission="project-create">
  <Button onClick={handleCreate}>Add Project</Button>
</Can>
```

**ADR:** [ADR-007: RBAC Service](decisions/ADR-007-rbac-service.md)

---

## 7. Quality Gates

### 7.1 Pre-commit

**Backend:**

```bash
ruff check app tests --fix
mypy app --strict
```

**Frontend:**

```bash
eslint --fix src/**/*.{ts,tsx}
tsc-files --noEmit  # Type check staged files only
```

### 7.2 CI Pipeline

**Required Checks:**

- ✅ Type check (MyPy/TypeScript)
- ✅ Linting (Ruff/ESLint)
- ✅ Unit tests (pytest/Vitest)
- ✅ Test coverage ≥80%

**Optional (Recommended):**

- E2E tests (Playwright)
- Security scan (Bandit, npm audit)

### 7.3 Metrics

| Metric                   | Target | Tool         |
| ------------------------ | ------ | ------------ |
| Type Coverage            | 100%   | MyPy         |
| Test Coverage (Backend)  | ≥80%   | pytest-cov   |
| Test Coverage (Frontend) | ≥80%   | Vitest       |
| Linting Errors           | 0      | Ruff, ESLint |
| API Response Time        | <200ms | FastAPI logs |

---

## 8. Common Pitfalls

### 8.1 Backend

❌ **Returning ORM rows instead of domain objects**

```python
# Bad
results = await session.execute(select(Project))
return results.scalars().all()  # Returns Row objects

# Good
results = await session.execute(select(Project))
projects = results.scalars().all()
return [ProjectPublic.model_validate(p) for p in projects]
```

❌ **Not using snake_case for field names**

```python
# Derive root field name correctly
# Project -> project_id (not projectId)
```

See: `backend/app/core/versioning/service.py` (`_get_root_field_name`)

### 8.2 Frontend

❌ **Testing implementation details**

```typescript
// Bad
expect(wrapper.find(".modal-class")).toBeTruthy();

// Good
expect(screen.getByRole("dialog")).toBeVisible();
```

❌ **Asserting transient toast messages in E2E**

```typescript
// Bad (race condition)
await expect(page.locator("text=Created successfully")).toBeVisible();

// Good (verify data in table)
await expect(page.locator(".ant-modal-content")).not.toBeVisible();
await expect(page.locator(`text=${projectCode}`)).toBeVisible();
```

❌ **Duplicating server state in Zustand**

```typescript
// Bad: Projects in Zustand store
const useProjectStore = create((set) => ({
  projects: [],
  setProjects: (projects) => set({ projects }),
}));

// Good: Use React Query
const { data: projects } = useProjects.useList();
```

---

## 9. References

- [ADR-004: Quality Standards](decisions/ADR-004-quality-standards.md)
- [Frontend Quality & Testing](frontend/contexts/04-quality-testing.md)
- [System Map](00-system-map.md)
- [Backend EVCS Core](backend/contexts/evcs-core/architecture.md)
