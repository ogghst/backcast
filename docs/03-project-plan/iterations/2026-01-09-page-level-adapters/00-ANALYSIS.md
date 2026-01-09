# Analysis: Remaining Page-Level API Adapters (TD-017)

**Technical Debt Item:** TD-017  
**Severity:** Low  
**Estimated Effort:** 1 hour  
**Date:** 2026-01-09

---

## 1. Problem Statement

Several page-level components still use the "legacy adapter pattern" for `createResourceHooks`. This involves defining an ad-hoc object with method names like `getUsers`, `createUser`, `updateUser` (even for non-User entities), which are then passed to the hook factory.

This pattern:

1.  Violates strict semantic naming (calling everything "User").
2.  Relies on deprecated logic in `useCrud` (`isLegacy` check).
3.  Increases code duplication in page files.

**Affected Files:**

1.  `frontend/src/pages/admin/UserList.tsx`
2.  `frontend/src/pages/admin/DepartmentManagement.tsx`
3.  `frontend/src/pages/admin/CostElementTypeManagement.tsx`
4.  `frontend/src/pages/financials/CostElementManagement.tsx`
5.  (WBEList was mentioned in TD but appears resolved in `features/wbes/api/useWBEs.ts`)

---

## 2. Solution Design

Refactor the locally defined API adapter objects to use the standard **Named Methods** pattern supported by `createResourceHooks`.

**Migration Map:**

- `getUsers` -> `list`
- `getUser` -> `detail`
- `createUser` -> `create`
- `updateUser` -> `update`
- `deleteUser` -> `delete`

**Example (UserList.tsx):**

_Before:_

```typescript
const userApi = {
  getUsers: async (params) => { ... },
  getUser: (id) => ...,
  createUser: (data) => ...,
  // ...
};
```

_After:_

```typescript
const userApi = {
  list: async (params) => { ... },
  detail: (id) => ...,
  create: (data) => ...,
  // ...
};
```

The `createResourceHooks` utility automatically detects the pattern based on key presence.

---

## 3. Plan

1.  **Refactor `UserList.tsx`:** Rename keys in `userApi`.
2.  **Refactor `DepartmentManagement.tsx`:** Rename keys in `departmentApi`.
3.  **Refactor `CostElementTypeManagement.tsx`:** Rename keys in `costElementTypeApi`.
4.  **Refactor `CostElementManagement.tsx`:** Rename keys in `costElementApi`.
5.  **Verify:** Ensure `WBEList.tsx` is indeed correct (no action needed).
6.  **Test:** Manual verification of one list to ensure data still loads (demonstrating hook integration works).

---

## 4. Risks

- **Breaking Changes:** If `createResourceHooks` detection logic relies on exact types, changing keys might cause type errors if the signature doesn't perfectly match `NamedApiMethods`.
  - _Mitigation:_ The signatures are practically identical `(params) => Promise<T>`, so this risk is low.

---

**Status:** Approved for DO phase.
