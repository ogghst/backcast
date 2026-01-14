# Request Analysis & Solution Design: Frontend Filter Type Safety

**Technical Debt Item:** TD-014  
**Severity:** Medium  
**Estimated Effort:** 3 hours  
**Date:** 2026-01-09  
**Author:** AI Assistant

---

## Request Summary

Address technical debt item **TD-014**: Frontend filter types currently use `Record<string, any>` instead of strict typing based on entity schemas. This violates the project's core principle of **zero tolerance for `any` types** and creates potential runtime errors.

---

## Clarified Requirements

### Functional Requirements

1. **Eliminate `any` types** from filter-related code in the frontend
2. **Type-safe filter definitions** for each entity (Project, WBE, CostElement, etc.)
3. **Compile-time validation** of filter field names and value types
4. **Backend-frontend alignment** ensuring filter types match API contracts

### Non-Functional Requirements

1. **Maintainability:** Filter types should be easy to update when entity schemas change
2. **Developer Experience:** TypeScript should provide autocomplete for filter fields
3. **Backward Compatibility:** No breaking changes to existing components
4. **Performance:** Zero runtime overhead

### Constraints

1. **Zero `any` tolerance:** Per coding standards (section 1.1)
2. **Backend as source of truth:** Types must align with Pydantic schemas
3. **Existing patterns:** Must integrate with `useTableParams` hook and `FilterParser`
4. **Timeline:** 3-hour implementation window

---

## Context Discovery Findings

### Product Scope

**Relevant User Stories:**

- Users need to filter entity lists (projects, WBEs, cost elements) by various fields
- Administrators configure which fields are filterable
- Developers need type safety when building filter UIs

**Business Requirements:**

- Server-side filtering for performance (established in Phase 2 work)
- Security via field whitelisting (see `FilterParser` backend implementation)
- Consistent UX across all entity tables

### Architecture Context

**Bounded Contexts Involved:**

- Frontend: `features/projects`, `pages/wbes`, `pages/financials`
- Cross-Cutting: `hooks/useTableParams.ts`, API client layer
- Backend: `app/core/filtering.py` (FilterParser)

**Existing Patterns:**

1. **Filter String Format:** `column:value1,value2;column2:value3` (documented in [API Response Patterns](file:///home/nicola/dev/backcast_evs/docs/02-architecture/cross-cutting/api-response-evcs-implementation-guide.md))
2. **WhitelistPolicy:** Backend explicitly defines `allowed_fields` per entity
3. **Type Safety Standard:** Strict TypeScript mode, no `any` types ([Coding Standards](file:///home/nicola/dev/backcast_evs/docs/02-architecture/coding-standards.md) section 1.1)

**Current Violations:**

```typescript
// ❌ Current Implementation (useTableParams.ts:9)
filters?: Record<string, FilterValue | null>;

// ❌ Current Implementation (useTableParams.ts:14)
<T extends object = Record<string, unknown>>()

// ❌ Current Implementation (api-response-evcs-implementation-guide.md:242)
filters?: Record<string, string[] | string>;
```

### Codebase Analysis

#### Backend

**Whitelisted Filter Fields (per entity):**

```python
# Projects (backend/app/services/project_service.py)
allowed_fields = ["status", "code", "name"]

# WBEs (backend/app/services/wbe_service.py)
allowed_fields = ["level", "code", "name"]

# Cost Elements (backend/app/services/cost_element_service.py)
allowed_fields = ["code", "name"]
```

**Pydantic Schemas (Source of Truth):**

- `backend/app/models/schemas/project.py`: `ProjectRead`
- `backend/app/models/schemas/wbe.py`: `WBERead`
- `backend/app/models/schemas/cost_element.py`: `CostElementRead`

#### Frontend

**Current Usage Locations (grep results):**

- `hooks/useTableParams.ts` (core implementation)
- `features/projects/components/ProjectList.tsx`
- `pages/wbes/WBEList.tsx`
- `pages/admin/UserList.tsx`
- `pages/admin/DepartmentManagement.tsx`
- `pages/admin/CostElementTypeManagement.tsx`
- `pages/financials/CostElementManagement.tsx`

**Comparable Patterns:**

- `useCrud.ts` uses generic types for entities: `<T>`
- Entity types already defined in `api/generated/models/`
- OpenAPI generation provides base types, but not filter-specific types

**State Management:**

- `useTableParams` manages URL params for filters
- Ant Design `FilterValue` type: `(Key | boolean)[] | null`
- No current type mapping between entity fields and filter values

---

## Solution Options

### Option 1: Generic Filter Interface with Mapped Types

**Architecture & Design:**

Create a generic `Filterable<T>` mapped type that extracts filterable fields from entity types:

```typescript
// types/filters.ts
type FilterableValue = string | string[];

type Filterable<T, AllowedFields extends keyof T> = {
  [K in AllowedFields]?: FilterableValue;
};

// Entity-specific filter types
interface ProjectFilters
  extends Filterable<ProjectRead, "status" | "code" | "name"> {}
interface WBEFilters extends Filterable<WBERead, "level" | "code" | "name"> {}
interface CostElementFilters
  extends Filterable<CostElementRead, "code" | "name"> {}
```

**Generic Hook Signature:**

```typescript
export const useTableParams = <
  TEntity extends object,
  TFilters extends Record<string, FilterableValue> = Record<string, FilterableValue>
>() => {
  // ... implementation
  tableParams: {
    filters?: TFilters;
    // ... other params
  }
}
```

**Usage in Components:**

```typescript
// ProjectList.tsx
const { tableParams, handleTableChange } = useTableParams<
  ProjectRead,
  ProjectFilters
>();
//                                                          ^^^^^^^^^^^  ^^^^^^^^^^^^^^
//                                                          Entity type  Filter type

// TypeScript now validates:
tableParams.filters?.status; // ✅ Valid
tableParams.filters?.invalidField; // ❌ Compile error
```

**UX Design:**

- No UX impact - internal type safety only
- Developers get autocomplete when building filter UIs
- Compile-time errors prevent typos in filter field names

**Technical Implementation:**

1. Create `frontend/src/types/filters.ts`:
   - Define `Filterable<T, AllowedFields>` mapped type
   - Export entity-specific filter interfaces
2. Update `useTableParams.ts`:
   - Add `TFilters` generic parameter
   - Type `filters` property with `TFilters`
   - Maintain backward compatibility with default type
3. Update 7 component files:
   - Add explicit type parameters to `useTableParams<TEntity, TFilters>()`

**Trade-offs:**

| Aspect              | Assessment                                                                                                                                                                                       |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Pros**            | ✅ Full type safety at compile time<br>✅ Autocomplete for filter fields<br>✅ Catches typos before runtime<br>✅ Aligns with coding standards<br>✅ Backward compatible (default generic types) |
| **Cons**            | ❌ Requires manual maintenance of `AllowedFields` unions<br>❌ Doesn't auto-sync with backend whitelist<br>❌ Requires updating 7 component files                                                |
| **Complexity**      | **Medium** - TypeScript mapped types, generic constraints                                                                                                                                        |
| **Maintainability** | **Good** - Clear separation of concerns, easy to extend                                                                                                                                          |
| **Performance**     | **Excellent** - Zero runtime cost, compile-time only                                                                                                                                             |

---

### Option 2: OpenAPI Code Generation Enhancement

**Architecture & Design:**

Extend the OpenAPI code generation pipeline to emit filter type definitions alongside entity types:

```typescript
// Generated from OpenAPI spec
export interface ProjectReadFilters {
  status?: string | string[];
  code?: string | string[];
  name?: string | string[];
}

export interface WBEReadFilters {
  level?: string | string[];
  code?: string | string[];
  name?: string | string[];
}
```

**Backend Enhancement:**

Add filter schema metadata to OpenAPI spec:

```python
# In route definitions
@router.get("", response_model=PaginatedResponse[ProjectPublic])
async def read_projects(
    filters: str | None = Query(None, description="Filterable fields: status, code, name")
):
    ...
```

**Frontend Tooling:**

Create custom OpenAPI transformer to parse `allowed_fields` from backend and generate corresponding TypeScript interfaces.

**UX Design:**

- Same as Option 1 (no UX impact)
- Stronger developer confidence via automated sync

**Technical Implementation:**

1. **Backend:**
   - Add `x-filterable-fields` OpenAPI extension to endpoints
   - Document allowed fields in OpenAPI schema
2. **Frontend:**
   - Create `scripts/generate-filter-types.ts`
   - Parse OpenAPI spec, extract filterable fields
   - Generate `api/generated/filters/*.ts`
3. **Integration:**
   - Update `useTableParams` to use generated types
   - Update components to use generated filter types

**Trade-offs:**

| Aspect              | Assessment                                                                                                                                               |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pros**            | ✅ Auto-syncs with backend whitelist<br>✅ Single source of truth (OpenAPI spec)<br>✅ No manual maintenance<br>✅ Scalable to new entities              |
| **Cons**            | ❌ Requires backend OpenAPI schema changes<br>❌ More complex tooling setup<br>❌ Adds build step dependency<br>❌ Harder to debug when generation fails |
| **Complexity**      | **High** - OpenAPI extension, custom code generator                                                                                                      |
| **Maintainability** | **Excellent** - Fully automated, no drift risk                                                                                                           |
| **Performance**     | **Excellent** - Zero runtime cost                                                                                                                        |

---

### Option 3: Runtime Validation with Zod

**Architecture & Design:**

Use Zod schemas to define and validate filter types at runtime:

```typescript
import { z } from "zod";

const ProjectFiltersSchema = z
  .object({
    status: z.union([z.string(), z.array(z.string())]).optional(),
    code: z.union([z.string(), z.array(z.string())]).optional(),
    name: z.union([z.string(), z.array(z.string())]).optional(),
  })
  .strict(); // Reject unknown fields

type ProjectFilters = z.infer<typeof ProjectFiltersSchema>;
```

**Runtime Validation:**

```typescript
export const useTableParams = <
  TEntity extends object,
  TFilters extends z.ZodType
>(
  filterSchema?: TFilters
) => {
  const parseFilters = (rawFilters: unknown) => {
    if (!filterSchema) return rawFilters;

    try {
      return filterSchema.parse(rawFilters);
    } catch (error) {
      console.error("Invalid filter:", error);
      return {};
    }
  };

  // ...
};
```

**UX Design:**

- Filters that fail validation are silently dropped
- Optional: Show toast notification for invalid filters
- Prevents malformed URL params from breaking the app

**Technical Implementation:**

1. Install Zod: `npm install zod`
2. Create `frontend/src/schemas/filters.ts`:
   - Define Zod schemas for each entity's filters
3. Update `useTableParams.ts`:
   - Add optional `filterSchema` parameter
   - Validate filters before applying
4. Update components:
   - Pass filter schema to `useTableParams`

**Trade-offs:**

| Aspect              | Assessment                                                                                                                                                   |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Pros**            | ✅ Runtime validation catches URL manipulation<br>✅ Self-documenting schemas<br>✅ Can provide better error messages<br>✅ Type inference from schemas      |
| **Cons**            | ❌ Adds runtime overhead<br>❌ Increases bundle size (+~10KB gzipped)<br>❌ Still requires manual schema maintenance<br>❌ Overkill for internal type safety |
| **Complexity**      | **Medium** - Zod schemas, error handling                                                                                                                     |
| **Maintainability** | **Good** - Schemas are self-documenting                                                                                                                      |
| **Performance**     | **Fair** - Runtime validation on every filter change                                                                                                         |

---

## Comparison Summary

| Criteria               | Option 1: Mapped Types  | Option 2: OpenAPI Gen      | Option 3: Zod Validation     |
| ---------------------- | ----------------------- | -------------------------- | ---------------------------- |
| **Development Effort** | 2-3 hours               | 4-5 hours                  | 2-3 hours                    |
| **Type Safety**        | ✅ Compile-time         | ✅ Compile-time            | ✅ Compile + Runtime         |
| **Maintainability**    | 🟡 Manual updates       | ✅ Auto-synced             | 🟡 Manual schemas            |
| **Performance**        | ✅ Zero overhead        | ✅ Zero overhead           | 🟡 Runtime validation        |
| **Complexity**         | 🟡 Medium               | 🔴 High                    | 🟡 Medium                    |
| **Backend Sync**       | ❌ Manual               | ✅ Automated               | ❌ Manual                    |
| **Dev Experience**     | ✅ Good autocomplete    | ✅ Great autocomplete      | ✅ Good + runtime safety     |
| **Best For**           | Quick wins, small teams | Large teams, many entities | User-facing input validation |

---

## Recommendation

**I recommend Option 1: Generic Filter Interface with Mapped Types**

### Rationale

1. **Meets 3-hour constraint:** Can be implemented and tested within the allocated time
2. **Zero runtime cost:** Aligns with performance standards
3. **Immediate value:** Provides type safety across all 7 usage locations
4. **Low risk:** Backward compatible, no build pipeline changes
5. **Evolutionary path:** Can migrate to Option 2 later if backend sync becomes a pain point

### Alternative Consideration

**Choose Option 2 (OpenAPI Generation) if:**

- The project grows to 10+ filterable entities
- Backend whitelist changes frequently
- Team size increases (manual sync becomes error-prone)
- Already planning OpenAPI enhancement work

**Avoid Option 3 (Zod) for this use case:**

- Filter params are controlled by the app (not user input)
- Runtime validation overhead doesn't justify the benefit
- Save Zod for form validation and external API responses

---

## Questions for Decision

1. **Scope:** Should we also address **TD-015 (useTableParams generic types)** in the same iteration, or keep them separate?

   - **Impact:** If combined, effort increases to 4 hours but achieves complete type safety in one pass

2. **Migration Strategy:** Should we update all 7 components immediately, or phase the migration?

   - **Recommendation:** Update all at once to prevent partial adoption and confusion

3. **Documentation:** Should we update the [API Response Patterns](file:///home/nicola/dev/backcast_evs/docs/02-architecture/cross-cutting/api-response-evcs-implementation-guide.md) doc as part of this work?

   - **Recommendation:** Yes - update the "Frontend Integration Patterns" section with type-safe examples

4. **Future-Proofing:** Should we create a migration path document for Option 2 (OpenAPI generation)?
   - **Benefit:** Helps make informed decision if whitelist maintenance becomes burdensome

---

## Next Steps (If Approved)

1. **PLAN Phase:** Create detailed implementation plan with file-by-file changes
2. **DO Phase:** Implement solution, run tests, verify type checking
3. **CHECK Phase:** Browser testing, E2E test validation, documentation update
4. **ACT Phase:** Update sprint backlog, mark TD-014 as complete, identify follow-up improvements

---

**Status:** ✅ Analysis Complete - Awaiting User Decision  
**Related Debt:** TD-015 (useTableParams Type Safety)
**Blocking:** None  
**Blocked By:** None
