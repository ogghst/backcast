# Analysis: Phase 2 -- Backend Dashboard Layout API

**Created:** 2026-04-05
**Request:** Backend persistence layer for dashboard layouts: database model, Pydantic schemas, service, API routes, Alembic migration, and frontend API hooks.

---

## Clarified Requirements

### Functional Requirements

- **Persist dashboard layouts** per user per project (with optional global layouts where `project_id` is null)
- **CRUD operations** on dashboard layouts via REST API with JWT authentication
- **Template system**: system-provided templates (`is_template = true`) that users can clone into personal dashboards
- **Default dashboard**: exactly one default layout per user per project (enforced via partial unique index)
- **Widget instances stored as JSONB** array within the layout row (embedded, not a separate table)
- **Frontend TanStack Query hooks** for all CRUD operations, following the existing `useEVMMetrics.ts` pattern

### Non-Functional Requirements

- Non-versioned entity (no EVCS, no bitemporal tracking, no branching)
- JWT authentication required on all endpoints
- JSONB column for widget instances to allow schema evolution without migrations
- Alembic migration for table creation

### Constraints

- Must use `SimpleEntityBase` + `SimpleService` pattern (non-versioned)
- Must follow existing API route conventions (operation_id, Depends injection, FastAPI router registration in `main.py`)
- Frontend hooks must use the generated OpenAPI client (`__request` + `OpenAPI` pattern)
- Must integrate with existing `queryKeys.ts` factory
- Depends on Phase 1 types being defined (widget type definitions)

---

## Context Discovery

### Product Scope

The widget system is documented in `docs/03-project-plan/iterations/2026-04-06-widget-system/` across three research documents (claude.md, perplexity.md, gemini.md). The system envisions composable dashboards where users assemble widget instances into named layouts, persist them per project, and share templates. Phase 2 specifically delivers the backend storage and API surface for this capability.

### Architecture Context

**Bounded contexts involved:** Dashboard/Widget composition (new bounded context, alongside existing Dashboard context which provides activity aggregation).

**Existing patterns to follow:**

1. **SimpleEntityBase** (`backend/app/core/base/base.py`): Abstract base providing `id` (UUID PK), `created_at`, `updated_at`. Inherited by `RefreshToken`, `ProjectMember`.
2. **SimpleService** (`backend/app/core/simple/service.py`): Generic CRUD with `get()`, `list_all()`, `create(**fields)`, `update(entity_id, **updates)`, `delete(entity_id)`. Uses command objects internally.
3. **API route pattern** (`backend/app/api/routes/project_members.py`, `dashboard.py`): Service instantiation via `Depends(get_db)`, auth via `Depends(get_current_active_user)`, Pydantic schema validation, `operation_id` on every endpoint.
4. **Pydantic schema pattern** (`backend/app/models/schemas/project_member.py`): `BaseModel` with `ConfigDict(from_attributes=True)`, separate Create/Update/Read schemas.
5. **Frontend hook pattern** (`frontend/src/features/evm/api/useEVMMetrics.ts`): Uses `__request(OpenAPI, {...})` directly, integrates `useTimeMachineParams()`, query keys from centralized factory.
6. **Query key factory** (`frontend/src/api/queryKeys.ts`): Hierarchical `createQueryKeys` structure with `all`, `lists()`, `list(params)`, `details()`, `detail(id)` pattern.

**Architectural constraints:**

- Single-server deployment (no Redis). In-memory only.
- No EVCS versioning for this entity type. Dashboard layouts are mutable documents.
- No RBAC beyond JWT auth (no `ProjectRoleChecker`) -- any authenticated user manages their own layouts.

### Codebase Analysis

**Backend:**

- `SimpleEntityBase` at `backend/app/core/base/base.py:34` -- provides `id`, `created_at`, `updated_at`
- `SimpleService` at `backend/app/core/simple/service.py` -- generic CRUD
- `SimpleCreateCommand`, `SimpleUpdateCommand`, `SimpleDeleteCommand` at `backend/app/core/simple/commands.py` -- command objects
- `ProjectMember` at `backend/app/models/domain/project_member.py` -- best reference for a `SimpleEntityBase` model with FK constraints and `UniqueConstraint`
- `RefreshToken` at `backend/app/models/domain/refresh_token.py` -- reference for `SimpleEntityBase` with indexed columns
- `DashboardService` at `backend/app/services/dashboard_service.py` -- existing dashboard service (activity aggregation, different concern)
- `dashboard.py` route at `backend/app/api/routes/dashboard.py` -- existing dashboard route with auth pattern
- Router registration in `backend/app/main.py:274` -- existing pattern for new router inclusion
- `__init__.py` at `backend/app/api/routes/__init__.py` -- must add new route module

**Frontend:**

- `queryKeys.ts` at `frontend/src/api/queryKeys.ts` -- centralized key factory, must add `dashboardLayouts` section
- `useEVMMetrics.ts` at `frontend/src/features/evm/api/useEVMMetrics.ts` -- pattern for API hooks using `__request(OpenAPI, ...)`
- Frontend API generated client at `frontend/src/api/generated/` -- OpenAPI types auto-generated

**Key observation:** No existing codebase entity extends `SimpleService` with custom query methods. The current `SimpleService` only provides basic `list_all()` with offset/limit pagination. The request requires `get_for_user_project()` and `get_templates()`, which means the service class will need custom methods beyond the generic base.

---

## Solution Options

### Option 1: Straightforward SimpleService Extension (As Requested)

**Architecture & Design:**

Follow the request as stated: a new domain model inheriting `SimpleEntityBase`, a service class extending `SimpleService[DashboardLayout]` with custom query methods, a REST route module, and frontend hooks. The service adds `get_for_user_project()`, `get_templates()`, `save()` (upsert), `clone_template()`, and `seed_templates()`.

**UX Design:**

Not directly user-facing. This is a backend API that enables the frontend dashboard composition UX in later phases.

**Implementation:**

- Create `backend/app/models/domain/dashboard_layout.py` inheriting `SimpleEntityBase`
- Create `backend/app/models/schemas/dashboard_layout.py` with Pydantic schemas
- Create `backend/app/services/dashboard_layout_service.py` extending `SimpleService`
- Create `backend/app/api/routes/dashboard_layouts.py` with 7 endpoints
- Create Alembic migration for `dashboard_layouts` table
- Add `dashboardLayouts` section to `frontend/src/api/queryKeys.ts`
- Create `frontend/src/features/dashboard/api/useDashboardLayouts.ts` with 5 hooks
- Register router in `backend/app/main.py`

**Trade-offs:**

| Aspect          | Assessment                                                    |
| --------------- | ------------------------------------------------------------- |
| Pros            | Follows established patterns exactly; low learning curve; minimal new abstractions |
| Cons            | `SimpleService.list_all()` returns unfiltered results; service must override/extend significantly for user-scoped queries; upsert logic requires custom SQL or application-level check-then-insert |
| Complexity      | Low-Medium                                                    |
| Maintainability | Good -- follows existing patterns, familiar to any team member |
| Performance     | Adequate for single-server deployment. JSONB column allows efficient widget storage. Partial unique index prevents duplicate defaults at DB level. |

---

### Option 2: Separate Widget Instances Table (Normalized)

**Architecture & Design:**

Instead of storing widget instances as a JSONB array embedded in the layout row, normalize into two tables: `dashboard_layouts` (metadata) and `dashboard_widgets` (one row per widget instance). The widget rows store `widget_type_id`, `layout_position` (x, y, w, h as separate columns or a composite), and `config` as JSONB.

**UX Design:**

Same as Option 1 (not user-facing).

**Implementation:**

- Two domain models instead of one
- Two sets of schemas
- Service manages both entities with transactional consistency
- More complex Alembic migration (two tables, FK between them)
- API remains identical externally (layout endpoints return widgets embedded)
- Slightly more complex frontend hooks (no change in interface)

**Trade-offs:**

| Aspect          | Assessment                                                    |
| --------------- | ------------------------------------------------------------- |
| Pros            | Queryable individual widgets; can index widget type; easier to count widgets by type; cleaner data model if widgets grow complex |
| Cons            | Over-engineering for current needs; N+1 query risk; every layout fetch requires JOIN; migration complexity; the widget schema is unstable and likely to change frequently -- each change requires a migration |
| Complexity      | Medium-High                                                   |
| Maintainability | Fair -- more tables to maintain, but cleaner normalization     |
| Performance     | Slightly worse for reads (JOIN required), better for analytical queries on widgets |

---

### Option 3: Hybrid -- JSONB with Generated Column for Type Indexing

**Architecture & Design:**

Same single-table layout as Option 1, but add a PostgreSQL generated column or GIN index on the `widgets` JSONB column to enable efficient querying by widget type without full normalization. The service includes a `get_by_widget_type()` method for future use.

**UX Design:**

Same as Option 1.

**Implementation:**

- Same model as Option 1, plus a GIN index on the `widgets` JSONB column
- Same service with an additional query method
- Migration includes `CREATE INDEX ... USING GIN (widgets)` statement
- Future-proofing for widget-type-based queries

**Trade-offs:**

| Aspect          | Assessment                                                    |
| --------------- | ------------------------------------------------------------- |
| Pros            | Preserves JSONB flexibility; adds query capability for widget types; minimal additional complexity; PostgreSQL JSONB indexing is mature and performant |
| Cons            | Slightly more complex migration; the GIN index may be premature optimization if widget-type queries are never needed |
| Complexity      | Medium                                                        |
| Maintainability | Good -- single table, flexible schema, indexed when needed    |
| Performance     | Good for both reads (single row fetch) and future widget-type queries |

---

## Comparison Summary

| Criteria           | Option 1: Straightforward    | Option 2: Normalized          | Option 3: Hybrid JSONB+GIN    |
| ------------------ | ---------------------------- | ----------------------------- | ----------------------------- |
| Development Effort | 2-3 days                     | 4-5 days                      | 2.5-3 days                    |
| Schema Flexibility | High (JSONB absorbs changes) | Low (migration per change)    | High (JSONB + indexed)        |
| Query Capability   | Basic (row-level only)       | Full relational               | Good (JSONB operators + GIN)  |
| Best For           | Current needs, rapid delivery | Complex widget relationships  | Balanced flexibility + query  |

---

## Recommendation

**I recommend Option 1 (Straightforward SimpleService Extension) because:** the JSONB-embedded widget array is the correct design choice for this phase. Widget instances are owned exclusively by their parent layout -- there is no cross-layout widget sharing, no need to query widgets independently, and the widget schema is intentionally unstable (it will evolve as new widget types are added). JSONB absorbs schema changes without migrations. The GIN index in Option 3 is premature -- there is no known requirement to query "all dashboards containing widget type X." When that requirement materializes, adding a GIN index is a single migration with zero code changes.

**Alternative consideration:** Choose Option 3 if you anticipate needing to query across layouts by widget type within the next 2-3 iterations. The cost difference is one index definition in the migration.

---

## Specific Adjustments to the Request

After analyzing the codebase, I recommend the following adjustments to the original request:

### 1. Remove `dashboard_id` Column

The request specifies both `id` (UUID PK) and `dashboard_id` (UUID, indexed). Every existing `SimpleEntityBase` model uses `id` as the sole UUID PK. Adding a second UUID identifier is inconsistent with the codebase. If a "root ID" concept is needed (for future versioning), that belongs in a `TemporalBase` model, not a `SimpleEntityBase`. Recommendation: use `id` only.

### 2. FK Constraints on `user_id` and `project_id`

The request says `user_id (UUID FK -> users)` and `project_id (UUID FK -> projects)`. However, examining the codebase:

- `ProjectMember.user_id` references `users.user_id` (the root ID, not `users.id`)
- `ProjectMember.project_id` references `projects.project_id` (the root ID, not `projects.id`)
- The `users` table uses `user_id` as a non-unique indexed column (multiple versions per user)
- The `projects` table uses `project_id` similarly

A FK to `users.user_id` would fail because it is not unique. The existing pattern in `ProjectMember` uses `ForeignKey("users.user_id", ondelete="CASCADE")`, but this works only because the `users` table happens to have a unique constraint on `user_id` for current versions via partial index. Verify the actual constraint before adding FKs. Alternatively, follow the `RefreshToken` pattern: store the ID without a DB-level FK constraint, enforce integrity at the application level, and add a comment explaining why.

Recommendation: Add FK constraints only if the target columns are uniquely constrained. Otherwise, use application-level validation with indexed columns (matching the `RefreshToken.user_root_id` pattern).

### 3. `save()` Method Name and Upsert Semantics

The request specifies `save()` with "upsert" semantics. However, `SimpleService` already has `create()` and `update()` as separate methods. Adding a `save()` that does both introduces ambiguity. The existing codebase pattern is explicit create vs. update in the API layer (POST vs. PUT). Recommendation: keep the POST endpoint as explicit create and the PUT endpoint as explicit update. Remove the `save()` upsert method. The frontend can determine whether to POST (new layout) or PUT (existing layout) based on whether `id` is present.

### 4. `seed_templates()` Belongs in a Startup/Lifecycle Hook, Not the Service

Seeding templates is a one-time initialization concern. If it lives in the service, it will be called manually or from an API endpoint. Recommendation: implement `seed_templates()` as a standalone function called during app startup (in the `lifespan` context manager in `main.py`), or defer it to a future iteration. For Phase 2, focus on the CRUD surface and template cloning.

### 5. `clone_template()` Should Be in the Service, Not the Route

The request correctly places `clone_template()` as a service method with a `POST /dashboard-layouts/{id}/clone` endpoint. This is appropriate.

### 6. No TimeMachineParams Integration Needed

The request says frontend hooks should follow the `useEVMMetrics.ts` pattern "with TimeMachineParams integration." However, dashboard layouts are non-versioned entities with no temporal semantics. TimeMachineParams (branch, asOf, mode) are meaningless for layout persistence. Recommendation: do not integrate TimeMachineParams. Hooks should accept simple query parameters (`projectId`, `id`) only.

### 7. Missing: Ownership Validation in API Routes

The API routes as specified require JWT auth but do not enforce that a user can only access/modify their own layouts. Any authenticated user could fetch or modify any layout by ID. Recommendation: add `user_id` filtering in the service layer. The `get_for_user_project()` method already scopes by user, but `GET /{id}`, `PUT /{id}`, and `DELETE /{id}` must verify that the layout belongs to `current_user.user_id`.

---

## Decision Questions

1. **Should templates be editable by users, or are they system-managed (seed-only)?** If templates should only be seeded by admins and cloned by users, the API should reject mutations on template layouts. If users can create templates, the `is_template` flag needs an ownership model.

2. **What should happen when a user deletes their default layout?** The partial unique index allows only one default per user/project. If the default is deleted, should the system automatically promote another layout, or leave the user without a default?

3. **Should the `widgets` JSONB column have a schema constraint (CHECK or validation trigger), or should validation happen only at the application layer (Pydantic)?** JSONB is schemaless by default. Application-level validation via Pydantic is simpler and more maintainable, but offers no protection against direct database edits.

---

## References

- `backend/app/core/base/base.py` -- SimpleEntityBase definition
- `backend/app/core/simple/service.py` -- SimpleService generic CRUD
- `backend/app/core/simple/commands.py` -- SimpleCreateCommand, SimpleUpdateCommand, SimpleDeleteCommand
- `backend/app/models/domain/project_member.py` -- Reference SimpleEntityBase model with FK + UniqueConstraint
- `backend/app/models/domain/refresh_token.py` -- Reference SimpleEntityBase model with indexed columns
- `backend/app/models/protocols.py` -- SimpleEntityProtocol definition
- `backend/app/api/routes/dashboard.py` -- Existing dashboard route with auth pattern
- `backend/app/api/routes/project_members.py` -- Reference route with RBAC
- `backend/app/services/dashboard_service.py` -- Existing dashboard service (different concern)
- `backend/app/main.py` -- Router registration
- `backend/app/models/schemas/project_member.py` -- Reference Pydantic schema pattern
- `frontend/src/api/queryKeys.ts` -- Query key factory
- `frontend/src/features/evm/api/useEVMMetrics.ts` -- Reference frontend hook pattern
- `docs/03-project-plan/iterations/2026-04-06-widget-system/claude.md` -- Widget system research (Phase analysis)
- `docs/02-architecture/cross-cutting/api-conventions.md` -- REST API conventions
