# Analysis: Refactor TanStack Query Usage

## 1. Requirements Clarification

### User Intent

The user wants to fix the compliance issues identified in the TanStack Query usage verification. The goal is to align the frontend code with the architecture guidelines specified in `docs/02-architecture/frontend/contexts/02-state-data.md`.

### Functional Requirements

1. **Strict Compliance**: Use `src/api/queryKeys.ts` factory for all query keys.
2. **Context Isolation**: Ensure all query keys for versioned entities include `{ branch, asOf }` context.
3. **Key Consistency**: Ensure that read hooks and mutation hooks (optimistic updates) use the exact same key generation logic to ensure proper cache updates.
4. **Fix Functional Bugs**: Correct the missing `asOf` in `useCostElements` list query.

## 2. Context Discovery

### 2.1 Documentation Review

- **`docs/02-architecture/frontend/contexts/02-state-data.md`**:
  - **Rule**: "We strictly enforce a centralized Query Key factory".
  - **Rule**: "For branchable or temporal entities, the Query Key **MUST** include context parameters".
  - **Rule**: "Mutations must trigger invalidation not just for the modified entity but for **all dependent data**".

### 2.2 Codebase Analysis

- **`src/api/queryKeys.ts`**: Correctly defines the factory pattern.
- **`useCostElements.ts`**:
  - Uses factory but incorrectly (misses `asOf` in list key).
  - Optimistic updates miss context in detail key.
- **`useWBEs.ts`, `useForecasts.ts`, `useProjects.ts`**:
  - Completely ignore the factory.
  - Manually construct keys like `["wbes", params, { asOf... }]` instead of `queryKeys.wbes.list(params)`.
  - This makes the system brittle; if the factory changes, these hooks won't update.

## 3. Solution Design

### Options

#### Option 1: Manual Incremental Refactor

Refactor each hook file one by one to use the `queryKeys` factory.

- **Implementation Details**:
  1. Update `useCostElements.ts`: Fix list key, fix optimistic update key.
  2. Update `useWBEs.ts`: Replace manual keys with `queryKeys.wbes.*`.
  3. Update `useForecasts.ts`: Replace manual keys with `queryKeys.forecasts.*`.
  4. Update `useProjects.ts`: Replace manual keys with `queryKeys.projects.*`.
- **Pros**: Low risk, straightforward, fixes immediate violations.
- **Cons**: Repetitive manual work, doesn't prevent future violations, no enforcement mechanism.

#### Option 2: Version-Aware Hook Factory (Recommended)

Create a new `createVersionedResourceHooks` factory that extends `useCrud.ts` with Time Machine context awareness and enforces the Query Key factory pattern.

##### Architecture Design

**Factory Signature**:

```typescript
createVersionedResourceHooks<T, TCreate, TUpdate>(
  resourceName: string,
  queryKeyFactory: QueryKeyFactoryMethods,
  apiMethods: VersionedApiMethods<T, TCreate, TUpdate>,
  options?: VersionedHookOptions
)
```

**Key Features**:

1. **Automatic Context Injection**: Reads `{ branch, asOf, mode }` from `useTimeMachineParams()` and includes them in all query keys.
2. **Query Key Factory Integration**: Uses the centralized `queryKeys` factory methods instead of manual string arrays.
3. **Optimistic Updates**: Provides opt-in optimistic update support with correct context-aware key matching.
4. **Invalidation Cascade**: Supports dependent invalidation (e.g., `forecasts.all` when cost data changes).
5. **Type Safety**: Full TypeScript generics for compile-time correctness.

##### Implementation Plan

1. **Create `src/hooks/useVersionedCrud.ts`**:
    - Extends the pattern from `useCrud.ts`
    - Integrates `useTimeMachineParams()` for context
    - Uses query key factory methods instead of raw strings
    - Injects `control_date` into mutation payloads

2. **Refactor existing hooks to use the factory**:
    - `useCostElements.ts` → Uses `createVersionedResourceHooks("cost-elements", queryKeys.costElements, {...})`
    - `useWBEs.ts` → Uses factory
    - `useForecasts.ts` → Uses factory
    - `useProjects.ts` → Uses factory
    - `useScheduleBaselines.ts` → Uses factory

3. **Benefits over Option 1**:
    - **Prevents Future Violations**: New resources must use the factory to get Time Machine support
    - **DRY Principle**: All versioned CRUD logic in one place
    - **Consistent Behavior**: Every hook gets the same context handling, invalidation logic, toast messages
    - **Easier Testing**: Test the factory once instead of each hook

##### Trade-offs Analysis

| Aspect              | Assessment                                                                                                   |
| :------------------ | :----------------------------------------------------------------------------------------------------------- |
| **Pros**            | Enforces compliance by design, prevents regressions, reduces boilerplate, improves long-term maintainability |
| **Cons**            | Requires upfront design work, moderate refactor complexity                                                   |
| **Complexity**      | Medium (one-time factory creation, then simple refactors)                                                    |
| **Maintainability** | Excellent (violations become compile errors, single source of truth)                                         |
| **Performance**     | Same as Option 1 (fixes cache misses) + future-proof                                                         |

#### Option 3: Hybrid Approach

Implement Option 2 factory but only migrate critical hooks (`useCostElements`, `useForecasts`) initially, leaving others for gradual migration.

- **Pros**: Lower initial effort, validates factory design with real usage
- **Cons**: Temporary inconsistency in codebase, still requires full migration eventually

## 4. Recommendation & Decision

### Comparison Summary

| Criteria                  | Option 1 (Manual) | Option 2 (Factory)               | Option 3 (Hybrid) |
| :------------------------ | :---------------- | :------------------------------- | :---------------- |
| Development Effort        | Low               | Medium (upfront), Low (per-hook) | Medium            |
| Long-term Maintainability | Fair              | Excellent                        | Good              |
| Prevents Future Issues    | No                | Yes                              | Partially         |
| Risk                      | Low               | Medium                           | Medium            |
| Best For                  | Quick fix         | Scalable architecture            | Cautious rollout  |

### Recommendation

**I recommend Option 2 (Version-Aware Hook Factory)** because:

1. **Architectural Alignment**: The project already uses factories (`createQueryKeys`, `createResourceHooks`). This extends the pattern consistently.
2. **Enforcement by Design**: The factory makes violations impossible—if a hook needs Time Machine support, it must use the factory, which enforces the Query Key pattern.
3. **ROI**: Medium upfront cost, but high long-term value. Every new versioned resource gets correct implementation "for free".
4. **Tested Pattern**: Similar to existing `useCrud.ts`, proven to work in this codebase.

### Alternative Consideration

If the team prefers to validate the factory design first, **Option 3 (Hybrid)** is acceptable: implement the factory and migrate `useCostElements` + `useForecasts` first, then expand to others after validation.

### Questions for Decision

1. Should we implement Option 2 fully, or start with Option 3 (hybrid) to validate the factory design?
2. Are there specific invalidation patterns (beyond `forecasts.all`) that the factory should handle by default?
