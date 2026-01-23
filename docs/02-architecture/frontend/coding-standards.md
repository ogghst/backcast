# Frontend Coding Standards (TypeScript/React)

**Last Updated:** 2026-01-23
**Scope:** Frontend (TypeScript/React), State Management, Validation

This document consolidates coding principles for a robust, reliable, and maintainable frontend codebase.

---

## 1. Core Principles

### 1.1 Strict Typing (Zero Tolerance)

**Rule:** Never use `any`. Always define explicit types/interfaces.

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

**Enforcement:** TypeScript `"strict": true` with `noImplicitAny`.

### 1.2 Source of Truth

**Frontend types must match Backend API response structures perfectly.**

**Process:**

1. Generate TypeScript types from OpenAPI spec OR manually match
2. Validate response types in frontend services

### 1.3 Functional & Stateless

**Pure Component Logic:**

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

See Section 4.6 for implementation.

---

## 2. Common Principles

### 2.1 Type Safety (Non-Negotiable)

- **Standard:** TypeScript strict mode (`tsconfig.app.json`)
- **Rationale:** Catch bugs at compile time, improve maintainability

### 2.2 Code Quality Automation

- **Linting:** ESLint
- **Formatting:** Prettier
- **Pre-commit:** Hooks enforce quality before commit

### 2.3 Testing Strategy

**Coverage Requirements:**

- Minimum 80% overall coverage
- 100% coverage for critical paths

**Test Types:**

1. **Unit Tests:** Pure logic (hooks, utils)
2. **E2E Tests:** Critical user flows (CRUD, auth, navigation)

### 2.4 Documentation

- **Comments:** Explain _why_, not _what_
- **Technical Debt:** Document pre-existing quality issues in the Technical Debt Register before adding new code
  - See: `docs/03-project-plan/technical-debt-register.md`
  - Document severity, estimated effort, and target resolution date

---

## 3. Frontend Standards

### 3.1 TypeScript Configuration

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

### 3.2 Component Structure

**Principle: Separate Logic from View (Custom Hooks)**

```typescript
// hooks/useProjectStats.ts
function useProjectStats(projects: Project[]) { ... }

// components/ProjectStats.tsx
function ProjectStats({ projects }: { projects: Project[] }) {
  const stats = useProjectStats(projects);
  ...
}
```

### 3.3 Component Organization

**Pattern:** Feature-based organization (`features/`)

```
frontend/src/
├── features/
│   ├── projects/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── types.ts
```

### 3.4 Data Fetching Pattern

**Rule: Use TanStack Query for ALL server state. NEVER use `useEffect` for data fetching.**

**Pattern:** Use `createResourceHooks` or centralized factories.

```typescript
const { useList, useCreate } = createResourceHooks("projects", { ... });

function ProjectList() {
  const { data: projects, isLoading } = useList();
  if (isLoading) return <Spin />;
  ...
}
```

#### 3.4.1 Query Key Factory Pattern

**Rule: ALL query keys MUST use the centralized factory in `src/api/queryKeys.ts`.**

**Context Isolation:** Versioned entities MUST include `{ branch, asOf, mode }`.

**Dependent Query Invalidation:** Mutations MUST invalidate all dependent queries (e.g., creating a cost element invalidates forecasts).

Seee [State Management Context](../frontend/contexts/02-state-data.md).

### 3.5 State Management

- **Global State:** Zustand (UI state only)
- **Server State:** TanStack Query
- **Form State:** Ant Design Form hooks

**Rule:** Never duplicate server state in Zustand.

### 3.6 Error Handling

- **Error Boundaries:** Wrap app in `<ErrorBoundary>`
- **User Feedback:** Use `toast.error()` for mutations
- **Network Errors:** Handled by React Query retry logic

### 3.7 Component Best Practices

**Code Style: Early returns to avoid deep nesting.**

```typescript
if (isLoading) return <Spin />;
if (!data) return <NotFound />;
return <ProjectView project={data} />;
```

### 3.8 Declarative Patterns

Prefer declarative components (`<Spin>`, `<Result>`, `<Can>`).

### 3.9 Testing Standards

**Unit/Integration:** Vitest + React Testing Library

```typescript
describe("ProjectList", () => {
  it("should render project table", () => {
    render(<ProjectList />);
    expect(screen.getByRole("table")).toBeInTheDocument();
  });
});
```

**E2E:** Playwright

- Test user behavior
- Use distinct test attributes or roles

---

## 4. Architecture Patterns

### 4.1 RBAC (Frontend)

**Usage:** `<Can>` component

```tsx
<Can permission="project-create">
  <Button onClick={handleCreate}>Add Project</Button>
</Can>
```

### 4.2 Navigation Patterns

**Entity Detail Page Navigation:** Use URL-driven tabs with nested routes.

1. **Layout Wrapper:** Renders `PageNavigation` and `<Outlet />`
2. **Nested Routes:** Configure children in router
3. **Benefits:** Shareable URLs, SEO, clean state

---

## 5. Quality Gates

### 5.1 Pre-commit

**Required checks before committing:**

```bash
# Run ESLint with auto-fix
npm run lint

# Type check
npm run type-check

# Run tests
npm test
```

**Pre-commit Hooks (Recommended):**

Configure pre-commit hooks to enforce quality automatically:

```json
// .husky/pre-commit
npm run lint-staged
```

```json
// package.json - lint-staged configuration
"lint-staged": {
  "src/**/*.{ts,tsx}": [
    "eslint --fix",
    "tsc-files --noEmit"
  ]
}
```

**Rationale:** Pre-commit hooks prevent linting errors from accumulating and reduce manual cleanup effort. (See TD-062 and TD-066 in Technical Debt Register)

### 5.2 CI Pipeline

- ✅ Type check (TypeScript)
- ✅ Linting (ESLint) - Gate on modified files only
- ✅ Unit tests (Vitest)
- ✅ Test coverage ≥80%
- ✅ E2E tests (Playwright) for critical paths

**ESLint Policy:**

- **New files:** Must pass ESLint with zero errors
- **Modified files:** Must not introduce new ESLint errors
- **Pre-existing debt:** Incrementally fix during feature work (see TD-066)

### 5.3 Code Review Checklist

When reviewing pull requests, verify:

- [ ] No `any` types (use `unknown` or generics instead)
- [ ] No unused variables or imports
- [ ] ESLint passes on modified files
- [ ] TypeScript strict mode compliance
- [ ] Tests added for new logic
- [ ] Coverage maintained ≥80%

---

## 6. Common Pitfalls

❌ **Using `any` type**
Avoid `any` at all costs. Use `unknown` for truly unknown types, or generics. The codebase has 130+ `any` type errors (TD-066) - do not add to this debt.

```typescript
// ❌ Bad
function process(data: any) { ... }

// ✅ Good - use unknown for truly unknown data
function process(data: unknown) {
  if (isValidData(data)) {
    return data as ProcessedData;
  }
  throw new Error('Invalid data');
}

// ✅ Good - use generics
function process<T extends Data>(data: T): ProcessedData { ... }
```

❌ **Testing implementation details**
Use `getByRole`, not class names or implementation details.

❌ **Asserting transient toast messages in E2E**
Verify side effects (table data, URL change), not transient UI.

❌ **Duplicating server state in Zustand**
Use `useQuery` hooks directly in components.

❌ **Skipping pre-commit hooks**
Always run `npm run lint` before committing. Pre-commit hooks prevent accumulation of technical debt.
