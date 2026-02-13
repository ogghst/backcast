---
name: frontend-state-dev
description: Manage frontend state data following TanStack Query + Zustand patterns with context isolation for versioned entities. Use when implementing data fetching, state management, query keys, CRUD hooks, or when user mentions "state", "cache", "query", "fetch", or "store".
allowed-tools: [AskUserQuestion, Read, Write, Edit, Glob, Grep]
---

# Frontend State Management Skill

Guides implementation of frontend state following the Backcast EVS architecture: **TanStack Query** for server state, **Zustand + Immer** for client state, with strict context isolation for versioned entities.

## Quick Start

When implementing state for a new entity:

1. **Determine Entity Type** - Is it Versioned (Time Machine) or Simple?
2. **Add Query Keys** - Define in `frontend/src/api/queryKeys.ts`
3. **Create CRUD Hooks** - Use factory: `createVersionedResourceHooks` or `createResourceHooks`
4. **Configure Dependent Invalidation** - Add EVM/forecasts dependencies if needed
5. **Write Component** - Use hooks with proper context parameters

## Entity Type Decision Guide

| Question                         | Versioned (Time Machine) | Simple                     |
| -------------------------------- | ------------------------ | -------------------------- |
| Need branch isolation?           | Yes                      | No                         |
| Need history/audit trail?        | Yes                      | No                         |
| Supports time-travel (asOf)?     | Yes                      | No                         |
| User-editable data?              | Usually Yes              | Usually No                 |
| Examples                         | Projects, WBEs, Cost Elements, Change Orders, Forecasts | Users, Departments, Cost Element Types, Config |

### Hook Factory Selection

```text
Does entity support Time Machine (branch/asOf)?
├─ Yes → createVersionedResourceHooks() (useVersionedCrud.ts)
│       - Auto-injects { branch, asOf, mode } into query keys
│       - Context isolation prevents stale data
│       - Use for: Projects, WBEs, Cost Elements, Change Orders, Forecasts
└─ No → createResourceHooks() (useCrud.ts)
        - No context injection
        - Use for: Users, Departments, Cost Element Types, System Config
```

## Implementation Checklist

### 1. Query Keys (`frontend/src/api/queryKeys.ts`)

- [ ] Add entity to `queryKeys` factory with kebab-case naming
- [ ] Include `context?: any` parameter for versioned entities
- [ ] Define `all`, `lists()`, `list()`, `details()`, `detail(id, context?)`
- [ ] Add domain-specific keys (e.g., `breadcrumb`, `evmMetrics`, `history`)

See example: [frontend/src/api/queryKeys.ts](../../../../frontend/src/api/queryKeys.ts)

### 2. CRUD Hooks (`frontend/src/features/[domain]/hooks/use[Entity].ts`)

- [ ] Use `createVersionedResourceHooks` for versioned entities
- [ ] Use `createResourceHooks` for simple entities
- [ ] Pass query key factory sub-key (e.g., `queryKeys.costElements`)
- [ ] Configure dependent invalidations
- [ ] Export named hooks: `use[Entity]s`, `use[Entity]`, `useCreate[Entity]`, etc.

See factory: [frontend/src/hooks/useVersionedCrud.ts](../../../../frontend/src/hooks/useVersionedCrud.ts)

### 3. Dependent Invalidation Configuration

Mutations must invalidate ALL dependent data to prevent stale EVM metrics.

| Primary Entity      | Dependent Invalidations                               | Query Key Pattern                 |
| ------------------- | ----------------------------------------------------- | --------------------------------- |
| Cost Elements       | `forecasts.all`                                       | `queryKeys.forecasts.all`         |
| Cost Registrations  | `forecasts.all`, `budgetStatus`                       | Both keys                         |
| Schedule Baselines  | `forecasts.all`                                       | `queryKeys.forecasts.all`         |
| Progress Entries    | `forecasts.all`, `evm.metrics`, `evm.timeSeries`      | All EVM-related keys              |
| Change Orders       | `projects.branches(projectId)`, `projects`            | Branch selectors + project lists  |

See: [State Management > Dependent Invalidation Strategy](../../../../docs/02-architecture/frontend/contexts/02-state-data.md)

### 4. Component Usage

- [ ] Use `useTimeMachineParams()` to get context for versioned entities
- [ ] Pass hooks to components (no manual fetching in useEffect)
- [ ] Handle loading/error states properly
- [ ] Use `enabled` option for conditional queries

## Context Isolation Rules

### Why Context Isolation Matters

Without context parameters, query keys are shared across branches/time periods:

- Switching branches shows stale data from previous branch
- Time-traveling shows incorrect historical state
- Changes in one branch affect UI in other branches

### Correct vs Incorrect Query Keys

```text
❌ WRONG - Manual key construction WITHOUT context
  queryKey: ["cost-elements", id]  // Shared across ALL branches!

❌ WRONG - Factory WITHOUT context
  queryKey: queryKeys.costElements.detail(id)  // Missing context!

✅ CORRECT - Factory WITH context from TimeMachineContext
  const { branch, asOf } = useTimeMachineParams();
  queryKey: queryKeys.costElements.detail(id, { branch, asOf })

✅ CORRECT - Using createVersionedResourceHooks (auto-injects context)
  const { data } = useCostElement(id);  // Context auto-injected
```

### Context Object Structure

The context object comes from `useTimeMachineParams()`:

```text
{
  branch: string;      // 'main', 'feature-branch', etc.
  asOf?: string;       // ISO timestamp or undefined for current
  mode: 'merged' | 'isolated';  // Query mode
}
```

## Optimistic Updates

Optimistic updates are **required** for high-frequency user actions (renaming, status changes).

See pattern: [State Management > Optimistic Updates](../../../../docs/02-architecture/frontend/contexts/02-state-data.md)

## Zustand Stores (Client State)

Use Zustand **only** for global UI state, not API data.

### When to Use Zustand

| Use Case           | Example State          |
| ------------------ | ---------------------- |
| Authentication     | `{ token, user }`      |
| UI Preferences     | `{ sidebarOpen, theme }` |
| Modal/Drawer State | `{ isOpen, content }`  |
| Form Draft State   | `{ drafts: {} }`       |

### Zustand + Immer Pattern

```text
immer(persist(...))  // Always wrap persist with immer
```

See examples in: [State Management > Client State](../../../../docs/02-architecture/frontend/contexts/02-state-data.md)

## Common Pitfalls

### ❌ Storing API Data in Zustand

API data should use TanStack Query hooks, not Zustand stores.

### ❌ Using useEffect for Data Fetching

```text
❌ useEffect(() => { fetchCostElements().then(setData); }, []);
✅ const { data } = useCostElements();
```

### ❌ Missing Context in Query Keys

```text
❌ detail: (id: string) => ["cost-elements", "detail", id] as const
✅ detail: (id: string, context?: any) => ["cost-elements", "detail", id, context] as const
```

### ❌ Incomplete Dependent Invalidation

```text
❌ Only invalidates the entity itself (missing forecasts!)
✅ Invalidates entity + dependent EVM data
```

### ❌ Using createResourceHooks for Versioned Entities

```text
❌ createResourceHooks("cost-elements", {...})  // No context injection
✅ createVersionedResourceHooks("cost-elements", queryKeys.costElements, {...})
```

## Quality Gates

Before completion, ensure:

- [ ] Query keys use centralized factory (`queryKeys.ts`)
- [ ] Versioned entities include `context?: any` parameter
- [ ] Correct hook factory used (versioned vs simple)
- [ ] Dependent invalidations configured for EVM-related entities
- [ ] No API data stored in Zustand stores
- [ ] No manual data fetching with useEffect
- [ ] Optimistic updates for high-frequency actions
- [ ] TypeScript strict mode passes (zero errors)
- [ ] ESLint passes (zero errors)

## Code References

| Concept              | File                                                      |
| -------------------- | --------------------------------------------------------- |
| Query Key Factory    | [frontend/src/api/queryKeys.ts](../../../../frontend/src/api/queryKeys.ts) |
| Versioned Hooks      | [frontend/src/hooks/useVersionedCrud.ts](../../../../frontend/src/hooks/useVersionedCrud.ts) |
| Simple Hooks         | [frontend/src/hooks/useCrud.ts](../../../../frontend/src/hooks/useCrud.ts) |
| Time Machine Context | [frontend/src/contexts/TimeMachineContext.tsx](../../../../frontend/src/contexts/TimeMachineContext.tsx) |
| API Client           | [frontend/src/api/client.ts](../../../../frontend/src/api/client.ts) |

## Related Documentation

- [State Management Architecture](../../../../docs/02-architecture/frontend/contexts/02-state-data.md) - Complete state management guide
- [Frontend Coding Standards](../../../../docs/02-architecture/frontend/coding-standards.md) - Frontend standards reference
- [Time Machine Context](../../../../docs/02-architecture/frontend/contexts/01-time-machine.md) - Time travel and branching

## Out of Scope

This skill does NOT:

- Create backend entities or API endpoints (use backend-entity-dev skill)
- Handle React component structure and props (use frontend-developer agent)
- Manage database migrations or backend schemas
- Implement authentication/authorization logic
