# Context: State Management & Data

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

### 3.3 API Layer

- **Client**: Single Axios instance (`src/api/client.ts`) handles:
  - Base URL configuration.
  - Auth token injection (Interceptors).
  - Global error handling (401 redirects).
- **Standardization**: All API calls must return typed responses matching Backend Pydantic schemas.

### 3.4 CRUD Hook Factory

The `createResourceHooks` factory in `src/hooks/useCrud.ts` provides a consistent pattern for CRUD operations. It supports two patterns:

**Named Methods Pattern (Recommended):**

Direct usage of service methods without adapters:

```typescript
import { createResourceHooks } from "@/hooks/useCrud";
import { ProjectsService } from "@/api/generated";

export const {
  useList: useProjects,
  useDetail: useProject,
  useCreate: useCreateProject,
  useUpdate: useUpdateProject,
  useDelete: useDeleteProject,
} = createResourceHooks("projects", {
  list: ProjectsService.getProjects,
  detail: ProjectsService.getProject,
  create: ProjectsService.createProject,
  update: ProjectsService.updateProject,
  delete: ProjectsService.deleteProject,
});
```

**Legacy Adapter Pattern (Backward Compatible):**

For existing code using adapters:

```typescript
const adapter = {
  getUsers: (params) => ProjectsService.getProjects(...),
  getUser: (id) => ProjectsService.getProject(id),
  createUser: (data) => ProjectsService.createProject(data),
  updateUser: (id, data) => ProjectsService.updateProject(id, data),
  deleteUser: (id) => ProjectsService.deleteProject(id),
};
const { useList } = createResourceHooks("projects", adapter);
```

The factory automatically detects which pattern you're using and routes accordingly.

---

## 4. Implementation Guidelines

- **Do not** store API data in Zustand. Use `useQuery`.
- **Do not** use `useEffect` for data fetching.
- **Do** type all API responses.
- **Do** use immer middleware for all Zustand stores.
- **Do** use draft mutations (direct assignments) within immer `set` callbacks.
- **Do** use named methods pattern with `createResourceHooks` for new code.
- **Do** include `{ branch, asOf }` in Query Keys for all versioned entities.
- **Do** wrap `persist` middleware with `immer` when combining them.
