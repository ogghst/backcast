# Context: State Management & Data

**Last Updated:** 2026-04-14

## 1. Overview

This context governs how data flows through the application, distinguishing clearly between **Server State** (data owned by the backend) and **Client State** (UI state owned by the user session).

## 2. Technology Stack

- **Server State**: TanStack Query (React Query) v5
- **Client State**: Zustand v5 with Immer middleware
- **HTTP Client**: Axios

## 3. Architecture

### 3.1 Server State (TanStack Query)

We prefer **Server State** over generic global stores.

- **Pattern**: Custom hooks for every API resource (e.g., `useProjects`, `useUpdateProject`).
- **Caching**: Stale-while-revalidate strategy.
- **Optimistic Updates**: UI updates immediately before the server response confirms success (critical for "snappy" feel).
- **DevTools**: Enabled in development to debug cache states.

#### 3.1.1 Query Keys & Context Isolation

We strictly enforce a centralized Query Key factory to ensure cache consistency and type safety.

- **Factory**: All keys are defined in `src/api/queryKeys.ts` using `createQueryKeys`.
- **Naming**: Keys follow a kebab-case hierarchical structure (e.g., `['cost-elements', 'detail', id]`).
- **Context Isolation**: For branchable or temporal entities, the Query Key **MUST** include context parameters to prevent stale data when switching contexts.
  - **Wrong**: `['cost-elements', 'detail', id]` (Cached shared across branches)
  - **Correct**: `['cost-elements', 'detail', id, { branch: 'main', asOf: '2024-01-01' }]`

#### 3.1.2 Invalidation Strategy

Mutations must trigger invalidation not just for the modified entity but for **all dependent data**.

- **Example**: Creating a _Schedule Baseline_ affects _Planned Value_, which affects _Forecasts_ (EVM Metrics).
- **Rule**: A mutation hook should invalidate `queryKeys.forecasts.all` if it touches cost or schedule data.
- **Implementation**: Use the `queryKeys` factory for invalidations to match the query generation.

**Dependent Invalidation Patterns:**

| Primary Entity     | Dependent Entities                                     | Rationale                                           |
| ------------------ | ------------------------------------------------------ | --------------------------------------------------- |
| Cost Elements      | `forecasts.all`, `forecast_comparison`                 | Cost element changes affect EVM calculations        |
| Cost Registrations | `forecasts.all`, `forecast_comparison`, `budgetStatus` | Actual costs affect EVM metrics and budget tracking |
| Schedule Baselines | `forecasts.all`, `forecast_comparison`                 | Planned Value changes affect EVM calculations       |
| Change Orders      | `projects.*.branches`, `projects`                      | Branch creation/updates affect project branch lists |

**Implementation Example:**

```typescript
// In mutation onSuccess callback
onSuccess: (...args) => {
  // Invalidate the modified entity
  queryClient.invalidateQueries({
    queryKey: queryKeys.costElements.all,
  });

  // Invalidate dependent EVM data
  queryClient.invalidateQueries({
    queryKey: queryKeys.forecasts.all,
  });

  toast.success("Created successfully");
};
```

#### 3.1.3 Optimistic Updates

Optimistic updates are **required** for high-frequency user actions (e.g., renaming, status changes).

```typescript
// Example: useUpdateCostElement.ts
onMutate: async ({ id, data }) => {
  await queryClient.cancelQueries({ queryKey: queryKeys.costElements.detail(id) });
  const previous = queryClient.getQueryData(queryKeys.costElements.detail(id));
  queryClient.setQueryData(queryKeys.costElements.detail(id), (old: any) => ({ ...old, ...data }));
  return { previous };
},
onError: (err, vars, context) => {
    // Rollback
    queryClient.setQueryData(queryKeys.costElements.detail(vars.id), context.previous);
}
```

### 3.2 Client State (Zustand)

Used **only** for global UI state that persists across routes but isn't database data.

- **Examples**: Sidebar toggle state, User authentication token, Theme preference.
- **Why Zustand?**: Minimal boilerplate compared to Redux; better performance than Context API for frequent updates.

**Immer Middleware:**
All Zustand stores use the `immer` middleware for immutable state updates:

```typescript
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

export const useStore = create<State>()(
  immer((set) => ({
    items: [],
    addItem: (item) =>
      set((state) => {
        state.items.push(item); // Direct mutation (immer handles immutability)
      }),
  })),
);
```

**Combining Immer with Persist Middleware:**

When using both `immer` and `persist` middleware, the correct order is `immer(persist(...))`:

```typescript
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { persist } from "zustand/middleware";

export const useAuthStore = create<State>()(
  immer(
    persist(
      (set, get) => ({
        // ... store implementation
      }),
      {
        name: "auth-storage",
        partialize: (state) => ({ token: state.token }),
      },
    ),
  ),
);
```

**Important:** Always wrap `persist` with `immer`, not the other way around. This ensures immer's draft state API works correctly with persisted state.

**Benefits:**

- Cleaner, more readable code (no spread operators)
- Prevents accidental mutations
- Easier to work with nested objects/arrays
- Type-safe draft mutations

---

### 3.3 API Layer

- **Client**: Single Axios instance (`src/api/client.ts`) handles:
  - Base URL configuration.
  - Auth token injection (Interceptors).
  - Global error handling (401 redirects).
- **Standardization**: All API calls must return typed responses matching Backend Pydantic schemas.

### 3.4 CRUD Hook Factories

We provide two distinct factories for generating CRUD hooks, enforcing separation between simple data and versioned application state.

#### 3.4.1 Versioned Entities (`createVersionedResourceHooks`)

**Used for**: Entities that support Time Machine (branches, history, time-travel).

- **Entities**: Projects, WBEs, Cost Elements, Forecasts, Change Orders.
- **Path**: `src/hooks/useVersionedCrud.ts`

This factory automatically injects `TimeMachineContext` ({ `branch`, `asOf`, `mode` }) into all query keys and API calls.

```typescript
import { createVersionedResourceHooks } from "@/hooks/useVersionedCrud";
import { queryKeys } from "@/api/queryKeys"; // Must use factory!
import { CostElementsService } from "@/api/generated";

export const {
  useList: useCostElements,
  useDetail: useCostElement,
  useCreate: useCreateCostElement,
  useUpdate: useUpdateCostElement,
  useDelete: useDeleteCostElement,
} = createVersionedResourceHooks(
  "cost-elements",
  queryKeys.costElements, // Pass the specific sub-factory
  {
    list: CostElementsService.getCostElements,
    detail: CostElementsService.getCostElement,
    create: CostElementsService.createCostElement,
    update: CostElementsService.updateCostElement,
    delete: CostElementsService.deleteCostElement,
  },
  {
    // Auto-invalidate dependent data (e.g., Forecasts depend on Cost Elements)
    invalidation: {
      create: [queryKeys.forecasts.all],
      update: [queryKeys.forecasts.all],
      delete: [queryKeys.forecasts.all],
    },
  },
);
```

#### 3.4.2 Simple Entities (`createResourceHooks`)

**Used for**: Global settings or non-temporal resources.

- **Entities**: Users, Departments, Cost Element Types.
- **Path**: `src/hooks/useCrud.ts`

**Warning**: Do NOT use this for versioned entities, as it creates query keys WITHOUT context, leading thereto potential data leakage across branches.

```typescript
import { createResourceHooks } from "@/hooks/useCrud";
import { UsersService } from "@/api/generated";

export const { useList: useUsers } = createResourceHooks("users", {
  list: UsersService.getUsers,
  detail: UsersService.getUser,
});
```

---

## 4. Implementation Guidelines

- **Do not** store API data in Zustand. Use `useQuery`.
- **Do not** use `useEffect` for data fetching.
- **Do** type all API responses.
- **Do** use immer middleware for all Zustand stores.
- **Do** use draft mutations (direct assignments) within immer `set` callbacks.
- **Do** use named methods pattern with hook factories for new code.
- **Do** use `createVersionedResourceHooks` for any entity that supports branching or history.
- **Do** include `{ branch, asOf }` in Query Keys for all versioned entities if manually constructing queries.

---

## 5. Query Key Factory Best Practices

### 5.1 Centralized Factory Usage

**Rule:** All query keys MUST be defined in `src/api/queryKeys.ts` using the centralized factory.

**Structure:**
The factory matches the domain structure of the application.

```typescript
// src/api/queryKeys.ts
export const queryKeys = createQueryKeys("backcast-evs", {
  // Versioned Entity with Context
  costElements: {
    all: null as QueryKey,
    // Context is REQUIRED for details to ensure isolation
    detail: (id: string, context?: any) =>
      ["cost-elements", "detail", id, context] as const,
    // Dependent metrics
    evmMetrics: (id: string, context?: any) =>
      ["cost-elements", "evm", id, context] as const,
  },

  // Simple Entity
  users: {
    detail: (id: string) => ["users", "detail", id] as const,
  },
});
```

### 5.2 Context Isolation for Versioned Entities

**Rule:** All versioned entity query keys MUST include context parameters to prevent stale data when switching contexts.

**Context Object:**
The `context` object typically comes from `useTimeMachineParams()` and contains:

- `branch`: string (e.g., 'main', 'feature-1')
- `asOf`: string | undefined (ISO timestamp)
- `mode`: string ('merged' | 'isolated')

**Correct Usage:**

```typescript
// ✅ CORRECT - Use factory with properties from TimeMachineContext
const { branch, asOf } = useTimeMachineParams();

useQuery({
  queryKey: queryKeys.costElements.detail(id, { branch, asOf }),
  queryFn: () => fetchCostElement(id, branch, asOf),
});
```

**Incorrect Usage:**

```typescript
// ❌ WRONG - Manual key construction
useQuery({
  queryKey: ["cost-elements", id], // Will show same data across all branches!
  queryFn: ...
});
```

### 5.3 Invalidation Chains

When mutating data, you must consider the "ripple effect" of changes.

| Mutation                | Direct Invalidation        | Dependent Invalidation                                     |
| ----------------------- | -------------------------- | ---------------------------------------------------------- |
| **Create Cost Element** | `costElements.all`         | `forecasts.all` (New element needs forecast)               |
| **Update Schedule**     | `scheduleBaselines.detail` | `forecasts.all` (PV changes affect SV/SPI)                 |
| **Register Cost**       | `costRegistrations.all`    | `budgetStatus`, `forecasts.all` (AC changes affect CV/CPI) |

These invalidations should be configured in the `createVersionedResourceHooks` options or manually in `onSuccess` handlers.

---

## 6. Migration Patterns

### 6.1 Migrating to Query Key Factory

When migrating existing code to use the query key factory:

1. **Add query key methods to factory** (if not already present):

   ```typescript
   // In src/api/queryKeys.ts
   breadcrumbs: (id: string) => ["resource", id, "breadcrumb"] as const,
   ```

2. **Update hook to use factory**:

   ```typescript
   // Before
   queryKey: ["resource", id, "breadcrumb"];

   // After
   queryKey: queryKeys.resource.breadcrumb(id);
   ```

3. **Update all invalidations**:

   ```typescript
   // Before
   queryClient.invalidateQueries({ queryKey: ["resource"] });

   // After
   queryClient.invalidateQueries({ queryKey: queryKeys.resource.all });
   ```

4. **Add tests** for cache behavior (integration tests for invalidation, E2E for context isolation)

### 6.2 Special Cases

**Change Orders:** While change orders are versioned entities, they have specialized workflow requirements (branch creation, merge operations). Ensure invalidations include `queryKeys.projects.branches(projectId)` to keep branch selectors up-to-date.

**Breadcrumbs:** Navigation breadcrumbs don't require context isolation (they're hierarchical, not temporal), but should still use the factory for consistency.

---

## 7. Common Pitfalls

### 7.1 Missing Context in Query Keys

**Problem:** Query keys without context parameters cache data across branches/time periods.

**Solution:** Always include `{ branch, asOf, mode }` in query keys for versioned entities.

### 7.2 Incomplete Dependent Invalidation

**Problem:** Mutations don't invalidate dependent queries, causing stale EVM data.

**Solution:** Document dependent entity relationships and add invalidations in `onSuccess` callbacks.

### 7.3 Manual Key Construction

**Problem:** Manual query keys scattered across codebases make refactoring difficult.

**Solution:** Always use `queryKeys` factory; add new keys to factory if missing.

---

## 8. Performance Considerations

### 8.1 Cache Efficiency

- **Context isolation** prevents cache pollution when switching branches
- **Dependent invalidation** ensures EVM data stays consistent
- **Optimistic updates** improve perceived performance for user actions

### 8.2 Monitoring

- Use TanStack Query DevTools in development to inspect cache state
- Monitor cache hit/miss ratios in production
- Set up performance budgets for query execution time
