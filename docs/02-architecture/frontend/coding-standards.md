# Frontend Coding Standards (TypeScript/React)

**Scope:** Frontend, State Management, UI Components

---

## Type Safety (Non-Negotiable)

- **TypeScript strict mode** in `tsconfig.app.json`
- Never use `any` - use `unknown` or generics
- Types MUST match backend API schemas exactly
- Use `@/` path aliases for imports

---

## Documentation Standard (LLM-Optimized)

**All public functions and components MUST have JSDoc that explains intent and context.**

```typescript
/**
 * Calculate cumulative earned value from progress entries.
 *
 * Context: Used by EVM dashboard cards and forecast charts.
 * Integrates with Time Machine for bitemporal queries.
 *
 * @param entries - Progress entries with completion percentages
 * @param asOf - Control date for time-travel calculation
 * @returns Cumulative EV as number (sum of weighted progress)
 *
 * @example
 * const ev = calculateEarnedValue(entries, new Date('2026-01-15'));
 */
export function calculateEarnedValue(
  entries: ProgressEntry[],
  asOf: Date
): number { ... }
```

**Required elements:**

1. **One-line summary** - what it does
2. **Context** - why it exists, what uses it
3. **@param** - with business meaning
4. **@returns** - what the value represents
5. **@example** - when non-obvious

---

## Architecture Patterns

### State Management

| Type            | Tool            | Example                |
| --------------- | --------------- | ---------------------- |
| Server State    | TanStack Query  | API data, mutations    |
| Global UI State | Zustand         | Theme, sidebar         |
| Form State      | Ant Design Form | Validation, submission |

**Rule:** Never duplicate server state in Zustand.

### Data Fetching

```typescript
// ✅ Use query hooks - NEVER useEffect for fetching
const { data, isLoading } = useProjects({ branch, asOf });

if (isLoading) return <Spin />;
if (!data) return <Empty />;
return <ProjectTable projects={data} />;
```

### Query Keys

- ALL keys via `src/api/queryKeys.ts` factory
- Versioned entities MUST include `{ branch, asOf, mode }`
- Mutations MUST invalidate dependent queries

---

## Component Patterns

```typescript
/**
 * Display project summary with EVM metrics.
 *
 * Context: Used on project detail page. Shows budget vs actual.
 * Integrates with Can component for permission gating.
 */
function ProjectStats({ project }: { project: Project }) {
  const stats = useProjectStats(project);

  // Early returns for loading/error states
  if (!stats) return <Skeleton />;

  return (
    <Card title="Project Stats">
      <Statistic title="Budget" value={stats.budget} />
    </Card>
  );
}
```

**Structure:** Separate logic from view using custom hooks.

---

## Common Pitfalls

| Issue             | Wrong                     | Right                                  |
| ----------------- | ------------------------- | -------------------------------------- |
| Unknown data      | `data: any`               | `data: unknown` with type guard        |
| Testing           | `getByClassName`          | `getByRole` or `getByText`             |
| State duplication | Cache API data in Zustand | Use `useQuery` directly                |
| Toast testing     | Assert toast message      | Verify side effect (table update, URL) |

---

## Quality Gates

```bash
npm run lint         # ESLint
npm run type-check   # TypeScript
npm test             # Vitest (≥80% coverage)
npm run e2e          # Playwright for critical flows
```
