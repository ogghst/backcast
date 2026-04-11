# Analysis: Automated Filter Types via OpenAPI (TD-014)

**Created:** 2026-04-11
**Request:** Automate frontend filter type generation from backend OpenAPI specification to eliminate manual synchronization drift.

---

## Clarified Requirements

### Problem Statement

Currently, frontend filter types (`frontend/src/types/filters.ts`) are manually maintained and synchronized with backend whitelists. This creates several issues:

1. **Drift Risk**: Manual synchronization is error-prone; backend whitelist changes may not be reflected in frontend types
2. **Duplication of Effort**: Filter fields are defined in 6+ backend services and must be manually duplicated in TypeScript
3. **Maintenance Burden**: Each new filterable entity requires updates in both backend and frontend
4. **Type Safety Gaps**: Mismatches between backend and frontend can cause runtime errors

### Functional Requirements

- Backend must expose filterable fields in OpenAPI specification
- Frontend client generation must consume OpenAPI metadata to generate TypeScript filter types
- Generated types must be compatible with existing `useTableParams` hook
- Solution must support existing filter patterns (single/multi-value, type coercion)
- Migration path must maintain backward compatibility

### Non-Functional Requirements

- **Type Safety**: Generated types must provide compile-time guarantees
- **Performance**: Client generation should complete in reasonable time (<10 seconds)
- **Maintainability**: Reduce long-term maintenance burden, not add complexity
- **Developer Experience**: Clear error messages when filters don't match backend whitelist
- **Zero Runtime Overhead**: Generated types should be compile-time only

### Constraints

- **OpenAPI Generator**: Currently using `openapi-typescript-codegen` (v0.29.0)
- **FastAPI Version**: Using latest FastAPI with automatic OpenAPI generation
- **Existing Patterns**: Must respect ADR-008 (Server-Side Filtering) architecture
- **Filter Security**: Must maintain field whitelisting for security (cannot expose all model fields)
- **Minimal Disruption**: Should not require major refactoring of existing components

---

## Context Discovery

### Product Scope

- **Relevant User Stories**: None explicitly documented; this is a technical debt/developer efficiency improvement
- **Business Requirements**: Improve developer productivity and reduce bugs from manual synchronization
- **Domain Context**: Affects all list views across Projects, WBEs, Cost Elements, Departments, Users, Change Orders

### Architecture Context

**Bounded Contexts Involved:**
- **Core API Layer**: OpenAPI specification generation
- **Frontend Type Generation**: Client code generation pipeline
- **Cross-Cutting Filtering**: Server-side filtering utility (ADR-008)

**Existing Patterns to Follow:**
- **ADR-008**: Server-side filtering with field whitelisting for security
- **API Conventions**: REST endpoints with `filters`, `search`, `sort_field`, `sort_order` query parameters
- **Type Generation**: Existing `npm run generate-client` workflow using `openapi-typescript-codegen`

**Architectural Constraints:**
- **FilterParser Security**: Field whitelisting is non-negotiable (prevents unauthorized filtering)
- **OpenAPI Schema**: FastAPI auto-generates schema; must work within this pattern
- **Type Safety**: Frontend uses TypeScript strict mode; generated types must be compatible

### Codebase Analysis

**Backend:**

**Existing Related APIs:**
- `backend/app/api/routes/projects.py` (line 38-83): GET endpoint with filters parameter
- `backend/app/api/routes/wbes.py`: Similar pattern
- `backend/app/api/routes/departments.py`: Similar pattern
- `backend/app/api/routes/cost_elements.py`: Similar pattern
- `backend/app/api/routes/change_orders.py`: Similar pattern
- `backend/app/api/routes/cost_element_types.py`: Similar pattern

**Data Models:**
- All entities use SQLAlchemy models with standard columns
- Filterable fields: typically `status`, `code`, `name`, `level`, `description`

**Backend Filter Implementation:**
- **FilterParser** (`backend/app/core/filtering.py`): Generic utility for parsing filter strings and building SQLAlchemy expressions
- **Field Whitelisting Pattern** (6 services):
  ```python
  # Example from projects.py line 137
  allowed_fields = ["status", "code", "name"]
  filter_expressions = FilterParser.build_sqlalchemy_filters(
      cast(Any, Project), parsed_filters, allowed_fields=allowed_fields
  )
  ```
- **No Existing OpenAPI Extensions**: Current OpenAPI spec has no `x-*` custom extensions

**Frontend:**

**Comparable Components:**
- `frontend/src/hooks/useTableParams.ts`: Generic hook for table params with filters
- `frontend/src/components/common/StandardTable.tsx`: Reusable table component
- 6 list components using filter types: `ProjectList.tsx`, `WBEList.tsx`, `CostElementManagement.tsx`, `UserList.tsx`, `DepartmentManagement.tsx`, `CostElementTypeManagement.tsx`

**State Management:**
- **URL-Based State**: Filters stored in URL search params (`?filters=status:active;code:PROJ1`)
- **Ant Design Table Integration**: Filters use `FilterValue` type from `antd/es/table/interface`
- **Type Pattern**: `Filterable<T, K extends keyof T>` where K is union of allowed field names

**Current Filter Types** (`frontend/src/types/filters.ts`):
```typescript
// Manual definitions duplicated from backend
export type ProjectFilters = Filterable<ProjectRead, "status" | "code" | "name">;
export type WBEFilters = Filterable<WBERead, "code" | "name" | "level">;
export type CostElementFilters = Filterable<CostElementRead, "code" | "name">;
// ... 6 total filter types
```

**Import Pattern:**
```typescript
import { ProjectFilters } from "@/types/filters";
useTableParams<Project, ProjectFilters>();
```

**Client Generation** (`frontend/package.json`):
```json
"generate-client": "openapi --input ../backend/openapi.json --output ./src/api/generated --client axios"
```

**Key Finding**: `openapi-typescript-codegen` does not natively support generating custom types from OpenAPI extensions. It generates API client methods and basic types from schemas, but does not have a plugin system for custom type generation.

---

## Solution Options

### Option 1: OpenAPI Extension + Post-Processing Generator

**Architecture & Design:**

1. **Backend Enhancement**:
   - Add `openapi_extra` parameter to route decorators with `x-filterable-fields` extension
   - Create a helper decorator or mixin to reduce boilerplate
   - Example:
     ```python
     @router.get("",
         openapi_extra={
             "x-filterable-fields": ["status", "code", "name"]
         }
     )
     async def read_projects(...):
     ```

2. **Post-Processing Script**:
   - Create a Node.js script that runs after `openapi-typescript-codegen`
   - Parse `openapi.json` to extract `x-filterable-fields` from each endpoint
   - Map operation IDs (e.g., `get_projects`) to entity names (e.g., `Project`)
   - Generate `filters.ts` with type-safe filter interfaces
   - Integrate into `npm run generate-client` as a sequential step

3. **Type Generation Pattern**:
   ```typescript
   // Generated from OpenAPI metadata
   export interface ProjectFilters {
     status?: FilterValue;
     code?: FilterValue;
     name?: FilterValue;
   }
   ```

**UX Design:**

- No user-visible changes
- Developers run `npm run generate-client` after backend changes
- TypeScript compile errors if filters don't match backend

**Implementation:**

- **Backend Changes**: Minimal (decorator updates to 6 endpoints)
- **Frontend Changes**:
  - New script: `scripts/generate-filter-types.mjs`
  - Update `package.json`: `"generate-client": "... && node scripts/generate-filter-types.mjs"`
  - Update `filters.ts`: Re-export from generated file for backward compatibility
  - Eventually remove manual type definitions

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | • Automatic synchronization<br>• Single source of truth<br>• Maintains security whitelist<br>• Clear separation of concerns<br>• Minimal runtime overhead |
| Cons            | • Requires post-processing script<br>• Adds npm script dependency<br>• Boilerplate on backend decorators<br>• OpenAPI extension is non-standard |
| Complexity      | Medium                    |
| Maintainability | Good (script is isolated) |
| Performance     | Fast (<2s for generation) |

---

### Option 2: Model-Based Schema Annotation

**Architecture & Design:**

1. **Backend Enhancement**:
   - Annotate Pydantic schemas with `json_schema_extra` to mark filterable fields
   - Example:
     ```python
     class ProjectRead(BaseModel):
         status: str = Field(..., json_schema_extra={"filterable": True})
         code: str = Field(..., json_schema_extra={"filterable": True})
         name: str = Field(..., json_schema_extra={"filterable": True})
     ```
   - Create a custom FastAPI route handler that inspects schemas and adds `x-filterable-fields` to OpenAPI

2. **Schema Inspection Utility**:
   - Utility function to extract filterable fields from schema definitions
   - Runs at application startup to populate OpenAPI extensions automatically

3. **Frontend Generation**: Same post-processing approach as Option 1

**UX Design:**

- No user-visible changes
- Developers mark fields as filterable in schema definitions
- More declarative than decorator approach

**Implementation:**

- **Backend Changes**:
  - Update 6 Pydantic schemas with field annotations
  - Create utility to auto-generate OpenAPI extensions from schema metadata
  - Integrate into FastAPI app customization
- **Frontend Changes**: Same as Option 1

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | • Declarative field marking<br>• Closer to schema definition<br>• Single source of truth at model level<br>• Easier to see which fields are filterable |
| Cons            | • Schema pollution (mixing API and filtering concerns)<br>• More invasive schema changes<br>• Harder to customize per-endpoint<br>• Requires custom FastAPI openapi() override |
| Complexity      | Medium-High               |
| Maintainability | Fair (schema changes ripple) |
| Performance     | Fast (startup inspection)  |

---

### Option 3: Defer - Maintain Manual Sync with Documentation

**Architecture & Design:**

- Keep current manual approach
- Add documentation/comment reminders to update both backend and frontend
- Create a checklist in PR template for filter changes
- Add TypeScript tests to verify filter types match backend responses

**UX Design:**

- No changes to user or developer experience
- Relies on developer discipline

**Implementation:**

- Add comment blocks in service methods:
  ```python
  # FILTER_SYNC: If you change allowed_fields, update frontend/src/types/filters.ts
  allowed_fields = ["status", "code", "name"]
  ```
- Add frontend tests that call API and verify filter fields work
- Update PR template with filter sync checklist

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | • Zero implementation cost<br>• No new dependencies<br>• Maintains simplicity<br>• No backend changes needed |
| Cons            | • Manual sync still required<br>• Drift will still occur<br>• No type safety guarantee<br>• Developer burden remains |
| Complexity      | Low                       |
| Maintainability | Poor (manual process)     |
| Performance     | N/A (no runtime impact)   |

---

## Comparison Summary

| Criteria           | Option 1 (OpenAPI Extension + Post-Process) | Option 2 (Model-Based Schema Annotation) | Option 3 (Defer/Manual) |
| ------------------ | ------------------------------------------ | ---------------------------------------- | ----------------------- |
| Development Effort | 2-3 days                                   | 3-4 days                                 | 0 days (current state)  |
| UX Quality         | High (automatic sync)                      | High (automatic sync)                    | Low (manual sync)       |
| Flexibility        | High (per-endpoint control)                | Medium (schema-level only)               | N/A                     |
| Type Safety        | High (generated types)                     | High (generated types)                   | Low (manual types)      |
| Maintenance        | Low (after initial setup)                  | Medium (schema changes)                  | High (continuous sync)  |
| Best For           | Long-term scalability                      | Strongly-typed schemas                   | Short-term projects     |

---

## Recommendation

**I recommend Option 1 (OpenAPI Extension + Post-Processing) because:**

1. **Separation of Concerns**: Keeps filtering metadata at the API layer where it belongs, not mixed into schema definitions
2. **Per-Endpoint Flexibility**: Allows different filter sets for different endpoints (e.g., simplified filters for public vs admin endpoints)
3. **Minimal Invasion**: Requires only decorator changes, not schema refactoring
4. **Standard Pattern**: OpenAPI extensions are a documented pattern for vendor-specific metadata
5. **Isolated Complexity**: Post-processing script is self-contained and can be tested independently
6. **Maintainability**: Once set up, requires no manual intervention—regenerating client code updates filters automatically
7. **ADR-008 Alignment**: Respects the existing server-side filtering architecture without changes

**Alternative consideration:** Choose Option 2 if you prefer schema-driven design and want filterable fields to be part of the contract definition. This is better if you already use Pydantic schemas extensively for documentation and validation.

**When to choose Option 3:** Only if you have very limited development bandwidth or if the project is short-lived with few expected changes to filterable fields.

---

## Decision Questions

1. **Priority Trade-off**: How important is developer productivity vs. implementation time? If urgent features are pending, consider deferring (Option 3) with a plan to revisit.

2. **Schema Philosophy**: Does the team prefer API-layer configuration (Option 1) or schema-driven development (Option 2)?

3. **Testing Requirements**: Should we add integration tests that verify the generated filter types match the backend OpenAPI spec? This would catch drift at the CI/CD level.

4. **Migration Timeline**: Should this be a hard cutover (replace all filter types at once) or gradual (migrate one entity at a time)? Gradual migration reduces risk.

---

## Implementation Plan (If Option 1 Approved)

### Phase 1: Backend Enhancement (1 day)

**Tasks:**
1. Create helper function/decorator to add `x-filterable-fields` to endpoints
2. Update 6 service routes with the decorator:
   - `projects.py`: `["status", "code", "name"]`
   - `wbes.py`: `["level", "code", "name"]`
   - `departments.py`: `["code", "name"]`
   - `cost_elements.py`: `["code", "name"]`
   - `change_orders.py`: `["status", "code", "title"]`
   - `cost_element_types.py`: `["code", "name"]`
3. Regenerate `openapi.json` to verify extensions are present
4. Add unit test for OpenAPI extension generation

**Success Criteria:**
- `openapi.json` contains `x-filterable-fields` for all list endpoints
- Format: `["/api/v1/projects"].get["x-filterable-fields"] = ["status", "code", "name"]`

### Phase 2: Frontend Generator (1 day)

**Tasks:**
1. Create `scripts/generate-filter-types.mjs`:
   - Load `backend/openapi.json`
   - Extract `x-filterable-fields` by operation ID
   - Map operation IDs to TypeScript entity names
   - Generate `api/generated/filters.ts`
2. Update `package.json`: Modify `generate-client` script to run post-processor
3. Generate initial `filters.ts` and verify types
4. Add unit test for generator script

**Success Criteria:**
- Running `npm run generate-client` produces valid TypeScript filter types
- Generated types compile without errors
- Generated types match manual definitions

### Phase 3: Frontend Migration (0.5 day)

**Tasks:**
1. Update `frontend/src/types/filters.ts` to re-export from generated file
2. Update imports in 6 list components (or keep using `@/types/filters` for compatibility)
3. Run TypeScript compiler to verify no errors
4. Test all list views in development environment

**Success Criteria:**
- No TypeScript errors
- All list views function correctly
- Filters work as expected in UI

### Phase 4: Documentation & Cleanup (0.5 day)

**Tasks:**
1. Update migration doc with implementation details
2. Add developer guide: "How to add new filterable fields"
3. Remove manual type definitions from `filters.ts`
4. Add CI/CD check: ensure `openapi.json` is up to date

**Success Criteria:**
- Documentation is complete
- Manual types are removed
- CI/CD prevents drift

**Total Estimated Time: 3 days**

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| ---- | ---------- | ------ | ---------- |
| OpenAPI extension breaks other tools | Low | Medium | Test with existing client generation workflow |
| Generator script has bugs | Medium | Medium | Comprehensive unit tests; manual verification |
| Operation ID to entity mapping fails | Low | High | Use consistent naming convention; add fallbacks |
| TypeScript compilation errors | Medium | Low | Incremental migration; keep manual types as fallback |
| Backend performance impact | Very Low | Very Low | Extensions are metadata only; no runtime impact |

---

## References

- **Migration Plan**: [`docs/02-architecture/cross-cutting/automated-filter-types-migration.md`](../../02-architecture/cross-cutting/automated-filter-types-migration.md)
- **ADR-008**: Server-Side Filtering [`docs/02-architecture/decisions/ADR-008-server-side-filtering.md`](../../02-architecture/decisions/ADR-008-server-side-filtering.md)
- **Backend Filtering**: `backend/app/core/filtering.py`
- **Frontend Filter Types**: `frontend/src/types/filters.ts`
- **Client Generation**: `frontend/package.json` (line 15)
- **Service Examples**:
  - `backend/app/services/project.py` (line 137)
  - `backend/app/services/department.py` (line 75)
  - `backend/app/services/wbe.py` (line 410)
