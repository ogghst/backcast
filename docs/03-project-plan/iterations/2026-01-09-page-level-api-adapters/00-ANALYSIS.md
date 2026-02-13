# Analysis: TD-017 Remaining Page-Level API Adapters

## Request Analysis

The user wants to implement **TD-017**, which involves migrating the remaining page-level API adapters to the standardized named-methods pattern used in `useProjects.ts` and `useWBEs.ts`.

**Clarified Requirements:**

1.  **Refactor**: Remove inline `const resourceApi = { getUsers: ..., getUser: ... }` usage in 5 files.
2.  **Standardize**: Use `createResourceHooks` with the `{ list, detail, create, update, delete }` object interface.
3.  **Preserve Logic**: Ensure custom filtering, sorting, and pagination logic (especially for complex pages like `CostElementManagement`) is preserved or cleanly extracted.
4.  **Files to Update**:
    - `frontend/src/pages/admin/UserList.tsx`
    - `frontend/src/pages/admin/DepartmentManagement.tsx`
    - `frontend/src/pages/admin/CostElementTypeManagement.tsx`
    - `frontend/src/pages/financials/CostElementManagement.tsx`
    - `frontend/src/pages/wbes/WBEList.tsx` (Wait, this one seems to use `useWBEs` hook already, need to check if it has local adapter too?)

**Correction on WBEList.tsx**:
Looking at `frontend/src/pages/wbes/WBEList.tsx` (Step 342), it imports `useWBEs` from `@/features/wbes/api/useWBEs`. It **does not** define a local adapter. It seems TD-017 description might be slightly outdated or referring to `useWBEs.ts` itself (which is already done as per Step 360).
**Conclusion**: `WBEList.tsx` is already clean. We only need to focus on the 4 admin/financial pages that define local `const resourceApi`.

## Context Discovery

**Existing Pattern (Antipattern to Fix):**

```typescript
const departmentApi = {
  getUsers: async (params) => { ... }, // Legacy name 'getUsers' for everything!
  getUser: ...,
  createUser: ...,
  // ...
};
const { useList } = createResourceHooks(..., departmentApi);
```

**Target Pattern (Standard):**

```typescript
// Best Practice: Define hooks in features/[feature]/api/use[Resource].ts
export const { useList, ... } = createResourceHooks("resource", {
  list: async (params) => { ... },
  detail: Service.get,
  create: Service.create,
  update: Service.update,
  delete: Service.delete,
});
```

**Files to Refactor & Strategy:**

1.  **`UserList.tsx`**:

    - Has explicit `userApi` object.
    - Has `getUsers` method handling `UsersService.getUsers(0, 100000)` (client-side pagination).
    - **Action**: Create `features/users/api/useUsers.ts` (if not exists) or inline the new pattern if we want to keep it simple for now (but feature folder is better).
    - _Better approach:_ Move logic to `features/users/api/useUsers.ts`.

2.  **`DepartmentManagement.tsx`**:

    - Has `departmentApi`.
    - Complex `getUsers` (legacy name) with manual filter parsing.
    - **Action**: Create `features/departments/api/useDepartments.ts`.

3.  **`CostElementTypeManagement.tsx`**:

    - Has `costElementTypeApi`.
    - Manual filter parsing.
    - **Action**: Create `features/cost-element-types/api/useCostElementTypes.ts`.

4.  **`CostElementManagement.tsx`**:
    - Has `costElementApi`.
    - Very complex `getUsers` handling branch, composite IDs, wbe filters.
    - **Action**: Create `features/cost-elements/api/useCostElements.ts`.

## Implementation Plan

1.  **Create Feature Hooks**:

    - `frontend/src/features/users/api/useUsers.ts`
    - `frontend/src/features/departments/api/useDepartments.ts`
    - `frontend/src/features/cost-element-types/api/useCostElementTypes.ts`
    - `frontend/src/features/cost-elements/api/useCostElements.ts`

2.  **Migrate Logic**:

    - Copy the `getUsers` (list) logic from the page files to the `list` method in the new hook files.
    - Map `createUser` -> `create`, `updateUser` -> `update`, etc.
    - Ensure types are correct.

3.  **Update Pages**:
    - Import the new hooks.
    - Remove the local adapter code.

## Trade-offs

- **Pros**: Consistency, reusability (can use hooks elsewhere), cleaner page components.
- **Cons**: Slight indirection (logic moved to separate file).
- **Complexity**: Low/Medium (copy-paste + refactor).

## Recommendation

Proceed with Option 1: **Extract to Feature Hooks**. This aligns with `useProjects` and `useWBEs` and cleans up the "Page" components to focus on UI.
