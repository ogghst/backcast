# PLAN Phase: Page-Level Adapters Refactoring

**Iteration:** 2026-01-09-page-level-adapters  
**Status:** 📝 Draft  
**Date:** 2026-01-09

---

## 1. Objective

Standardize the usage of `createResourceHooks` in page-level components by migrating from the legacy "User-named" adapter pattern to the modern "Named Methods" pattern (`list`, `create`, `update`, `delete`).

---

## 2. Scope

**In Scope:**

- Refactoring adapter objects in:
  - `UserList.tsx`
  - `DepartmentManagement.tsx`
  - `CostElementTypeManagement.tsx`
  - `CostElementManagement.tsx`

**Out of Scope:**

- Changing the actual logic within the adapter methods (just renaming keys).
- `WBEList.tsx` (confirmed already using `useWBEs` with named methods).
- `ProjectList.tsx` (confirmed already using `useProjects`).

---

## 3. Implementation Steps

### Step 1: User List

- Update `userApi` object keys in `frontend/src/pages/admin/UserList.tsx`.

### Step 2: Department Management

- Update `departmentApi` object keys in `frontend/src/pages/admin/DepartmentManagement.tsx`.

### Step 3: Cost Element Type Management

- Update `costElementTypeApi` object keys in `frontend/src/pages/admin/CostElementTypeManagement.tsx`.

### Step 4: Cost Element Management

- Update `costElementApi` object keys in `frontend/src/pages/financials/CostElementManagement.tsx`.

---

## 4. Verification Plan

### Automated Checks

- `tsc -b` should pass (ensuring the new object shapes satisfy `ApiMethods` type union in `useCrud.ts`).

### Manual Checks

- Verify `UserList` loads data.
- Verify `CostElementManagement` loads data (since it has complex custom logic).

---

## 5. Effort Estimation

- **Refactoring:** 30 mins
- **Verification:** 15 mins
- **Total:** 45 mins
