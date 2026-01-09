# Implementation Plan: Frontend Type Safety (TD-014 & TD-015)

**Iteration:** 2026-01-09-frontend-filter-type-safety  
**Status:** 🟡 Awaiting Final Review  
**Date:** 2026-01-09  
**Approver:** USER

---

## 1. Problem Statement

### 1.1 The Issue

The frontend currently uses loosely typed structures for table parameters and filters. Specifically:

- **TD-014:** Filters use `Record<string, any>`, violating the "Zero Tolerance for `any`" principle ([Coding Standards](file:///home/nicola/dev/backcast_evs/docs/02-architecture/coding-standards.md) 1.1).
- **TD-015:** The `useTableParams` hook uses generic objects instead of strictly typed entity interfaces, leading to potential runtime errors and poor developer experience (missing autocomplete).

### 1.2 Impact

- **Maintenance Risk:** Refactoring entity fields is dangerous as the compiler doesn't catch mismatched filter keys.
- **Developer Friction:** Developers must manually verify filter keys against backend whitelists.
- **Runtime Errors:** Typos in filter strings cause 400 errors from the backend.

---

## 2. Success Criteria (Measurable)

### 2.1 Technical Criteria

- [ ] `useTableParams` hook signature requires generic type parameters for the entity and its filters.
- [ ] `Record<string, any>` is replaced with explicit interface-based typing.
- [ ] TypeScript compiler (`tsc`) passes without `any` violations in affected files.
- [ ] Autocomplete works for filter fields in `ProjectList`, `WBEList`, etc.

### 2.2 Functional Criteria

- [ ] Existing pagination, search, and filtering functionality remains fully operational across all 7 pages.
- [ ] URL parameter synchronization (filters in URL) works exactly as before.

### 2.3 Documentation Criteria

- [ ] [API Response Patterns](file:///home/nicola/dev/backcast_evs/docs/02-architecture/cross-cutting/api-response-patterns.md) updated with type-safe examples.
- [ ] Migration path for future OpenAPI automation documented.

---

## 3. Scope Definition

### In Scope

- Refactoring `useTableParams.ts` hook for strict generic typing.
- Creating a new centralized typing system for filterable fields.
- Updating all 7 component/page files using the hook.
- Updating `api-response-patterns.md`.
- Creating the migration path documentation.

### Out of Scope

- Automated OpenAPI code generation (deferred as per analysis decision).
- Backend changes to `FilterParser`.
- Changes to non-table components.

---

## 4. Implementation Approach (Approved: Option 1)

### 4.1 Technical Design

We will use **TypeScript Mapped Types** and **Generic Constraints** to enforce type safety.

#### 1. Filter Type Definition Pattern

We will define a generic `Filterable<T, K>` type that maps entity fields to standard filter values.

#### 2. Hook Refactoring

`useTableParams` will be updated to:

```typescript
export const useTableParams = <
  TEntity extends object,
  TFilters extends Record<string, FilterValue | null> = Record<string, FilterValue | null>
>() => { ... }
```

### 4.2 Component Breakdown

| Task ID    | Description                 | Component/File                                 |
| ---------- | --------------------------- | ---------------------------------------------- |
| **CORE-1** | Define core filter types    | `src/types/filters.ts`                         |
| **CORE-2** | Refactor hook with generics | `src/hooks/useTableParams.ts`                  |
| **DOC-1**  | Update architecture docs    | `docs/02-architecture/...`                     |
| **COMP-1** | Migrate Projects            | `features/projects/components/ProjectList.tsx` |
| **COMP-2** | Migrate WBEs                | `pages/wbes/WBEList.tsx`                       |
| **COMP-3** | Migrate Users               | `pages/admin/UserList.tsx`                     |
| **COMP-4** | Migrate Departments         | `pages/admin/DepartmentManagement.tsx`         |
| **COMP-5** | Migrate Cost Types          | `pages/admin/CostElementTypeManagement.tsx`    |
| **COMP-6** | Migrate Cost Elements       | `pages/financials/CostElementManagement.tsx`   |

---

## 5. TDD Test Blueprint

### Unit Tests (`useTableParams.test.tsx`)

1. **Validate Type Constraints:** Verify that strictly typed filters prevent invalid key access (compile-time).
2. **Regression Test:** Ensure URL parsing still correctly handles `key:val1,val2` format.
3. **State Change:** Verify `handleTableChange` updates the URL with correctly formatted filter strings.

### Integration/Manual Tests

1. **Project Table:** Open `/projects`, apply status filter, verify API request has correct `filters` param.
2. **WBE Table:** Open `/projects/:id`, verify hierarchy still works with new types.

---

## 6. Risks and Mitigations

| Risk Type  | Description                                          | Probability | Impact | Mitigation                                                                     |
| ---------- | ---------------------------------------------------- | ----------- | ------ | ------------------------------------------------------------------------------ |
| Technical  | Type mismatch between frontend and backend whitelist | Medium      | Medium | Maintain centralized `src/types/filters.ts` to match backend `allowed_fields`. |
| Regression | Broken URL parsing for complex filters               | Low         | High   | Comprehensive unit tests for `useTableParams`.                                 |
| Schedule   | Manual update of 7 files takes longer than estimated | Low         | Low    | Pattern is repetitive; first component will act as a template.                 |

---

## 7. Effort Estimation

- **Development (Core):** 1.0 hour
- **Component Migration:** 1.5 hours
- **Testing & Documentation:** 1.0 hour
- **Total:** 3.5 hours

---

## 8. Prerequisites

1. Approved [Analysis](./00-ANALYSIS.md).
2. Backup of current `api-response-patterns.md`.

---

## 9. Migration Path (Future OpenAPI)

To transition to automated filter types in the future:

1. **Model Tagging:** Tag Pydantic models with `Field(json_schema_extra={"filterable": True})`.
2. **Schema Middleware:** Modify FastAPI's `custom_openapi` to extract these tags into an `x-filterable` array per schema.
3. **Frontend Generator:** Update the OpenAPI generator to create `Filter` interfaces based on these `x-filterable` arrays.

---

**Approval Status:** 🟡 Pending User Approval to proceed to **DO Phase**.
