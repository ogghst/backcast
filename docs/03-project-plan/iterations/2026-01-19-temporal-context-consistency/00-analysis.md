# Analysis: Temporal and Branch Context Consistency

**Created:** 2026-01-19
**Request:** Ensure all write operations consistently implement temporal and branch context parameters according to API conventions

---

## Clarified Requirements

### Problem Statement

The API routes exhibit inconsistent implementation of temporal (`control_date`) and branch (`branch`) context parameters for write operations (POST, PUT, PATCH, DELETE). The API conventions documentation specifies these parameters should be part of request bodies for write operations, but current implementations mix query parameters and body fields, leading to confusion and inconsistency.

### Functional Requirements

1. **Consistent Parameter Location**: All write operation parameters (`branch`, `control_date`) MUST be in the request body for POST/PUT/PATCH operations
2. **DELETE Operation Handling**: DELETE operations cannot have a request body, so these parameters should remain as query parameters
3. **Schema Compliance**: All Create/Update schemas MUST include `branch` and `control_date` fields
4. **Route Implementation**: All write routes MUST extract these parameters from the request body (except DELETE)
5. **Breaking Change Acceptable**: No backward compatibility needed - deprecated routes should be replaced or removed

### Non-Functional Requirements

- **Maintainability**: Consistent patterns reduce cognitive load for developers
- **API Design**: Follow REST principles where query parameters modify GET operations and body data modifies write operations
- **Documentation**: API conventions document should accurately reflect implementation
- **Type Safety**: Pydantic schemas should enforce these fields at the type level

### Constraints

- **HTTP DELETE**: Cannot have a request body per HTTP/1.1 specification
- **Existing Schema Patterns**: ProjectCreate, ProjectUpdate, WBECreate, WBEUpdate, CostElementCreate, CostElementUpdate, ForecastCreate, ForecastUpdate already have these fields in body
- **Schedule Baseline**: Currently uses hardcoded values and missing schema fields

---

## Context Discovery

### Product Scope

**Relevant User Stories:**
- None directly - this is a technical debt/consistency improvement
- Impacts all API consumers working with versioned entities (Projects, WBEs, Cost Elements, Schedule Baselines, Forecasts)

**Business Requirements:**
- API consistency improves developer experience
- Reduces errors from parameter location confusion
- Aligns implementation with documented conventions

### Architecture Context

**Bounded Contexts Involved:**
- Change Order & Branching (core to this issue)
- Project & WBE Management
- Cost Element & Financial Tracking

**Existing Patterns to Follow:**
From API conventions (`docs/02-architecture/cross-cutting/api-conventions.md`):

| Parameter      | Location   | Type   | Default    | Description                                                                                 |
| -------------- | ---------- | ------ | ---------- | ------------------------------------------------------------------------------------------- |
| `branch`       | Query      | string | `"main"`   | The branch to read from or write to.                                                        |
| `mode`         | Query      | string | `"merged"` | **Branch Mode**: `merged` (include parent branch data) or `isolated` (current branch only). |
| `as_of`        | Query      | string | `null`     | **Read Context**: ISO 8601 timestamp for Time-Travel (historical view).                     |
| `control_date` | Body/Query | string | `null`     | **Write Context**: Effective date for the operation (affects `valid_time`).                 |

**Architectural Constraints:**
- EVCS bitemporal versioning system requires `branch` and `control_date` for all write operations
- TemporalService[T] generic service expects these parameters
- HTTP DELETE cannot have request body (RFC 7231)

### Codebase Analysis

**Backend - Existing Related APIs:**

#### Schemas - Already Have `branch` and `control_date` in Body ✅

1. **Project Schemas** (`backend/app/models/schemas/project.py`)
   - `ProjectCreate` (lines 23-37): Includes `branch` (default "main") and `control_date`
   - `ProjectUpdate` (lines 40-54): Includes `branch` (nullable) and `control_date`

2. **WBE Schemas** (`backend/app/models/schemas/wbe.py`)
   - `WBECreate` (lines 24-38): Includes `branch` (default "main") and `control_date`
   - `WBEUpdate` (lines 41-54): Includes `branch` (nullable) and `control_date`

3. **Cost Element Schemas** (`backend/app/models/schemas/cost_element.py`)
   - `CostElementCreate` (lines 19-35): Includes `branch` (default "main") and `control_date`
   - `CostElementUpdate` (lines 38-51): Includes `branch` (nullable) and `control_date`

4. **Forecast Schemas** (`backend/app/models/schemas/forecast.py`)
   - `ForecastCreate` (lines 21-35): Includes `branch` (default "main") and `control_date`
   - `ForecastUpdate` (lines 38-50): Includes `branch` (nullable) and `control_date`

#### Schemas - MISSING `branch` and `control_date` ❌

5. **Schedule Baseline Schemas** (`backend/app/models/schemas/schedule_baseline.py`)
   - `ScheduleBaselineCreate` (lines 39-50): **MISSING** `branch` and `control_date` fields
   - `ScheduleBaselineUpdate` (lines 53-60): **MISSING** `branch` and `control_date` fields

#### Routes - Implementation Issues

**1. Projects Route** (`backend/app/api/routes/projects.py`)
   - **DELETE** (lines 214-236): Uses `control_date` from QUERY parameter ❌
     ```python
     control_date: datetime | None = Query(
         None, description="Optional control date for deletion"
     )
     ```
   - **POST, PUT**: Correctly use body fields from schema ✅

**2. WBEs Route** (`backend/app/api/routes/wbes.py`)
   - **DELETE** (lines 267-287): Uses `control_date` from QUERY parameter ❌
     ```python
     control_date: datetime | None = Query(
         None, description="Optional control date for deletion"
     )
     ```
   - **POST, PUT**: Correctly use body fields from schema ✅

**3. Cost Elements Route** (`backend/app/api/routes/cost_elements.py`)
   - **DELETE** (lines 210-241): Uses `control_date` from QUERY parameter ❌
     ```python
     control_date: datetime | None = Query(
         None, description="Optional control date for deletion"
     )
     ```
   - **POST, PUT**: Correctly use body fields from schema ✅
   - **Note**: Forecast endpoints (lines 569-816) use query parameters for PUT/DELETE ❌

**4. Schedule Baselines Route** (`backend/app/api/routes/schedule_baselines.py`)
   - **POST** (lines 93-117): Hardcoded `branch="main"` and `control_date=None` ❌
     ```python
     return await service.create(
         create_schema=baseline_in,
         actor_id=current_user.user_id,
         branch="main",  # Always create on main first
         control_date=None,
     )
     ```
   - **PUT** (lines 160-193): Hardcoded `branch="main"` and `control_date=None` ❌
     ```python
     return await service.update(
         root_id=schedule_baseline_id,
         actor_id=current_user.user_id,
         branch="main",
         control_date=None,
         **update_data,
     )
     ```
   - **DELETE** (lines 196-227): Uses query parameters (acceptable for DELETE) ✅

**Data Models:**

All versioned entities inherit from `TemporalBase` which includes:
- `branch`: str
- `valid_time`: TSTZRANGE
- `transaction_time`: TSTZRANGE
- `deleted_at`: datetime | None

**Similar Patterns:**

The pattern established by Project, WBE, and CostElement schemas:
- Create schemas have `branch` with default "main" and optional `control_date`
- Update schemas have nullable `branch` and optional `control_date`
- Routes extract these from the request body via Pydantic validation

**Technical Debt:**

1. **TD-058**: Overlapping valid_time constraint (referenced in temporal-query-reference.md)
2. **Schedule Baseline**: Inconsistent with other versioned entities (hardcoded values)
3. **Forecast Endpoints**: Use query parameters for update operations (should use body)
4. **DELETE Operations**: Query parameter usage is technically correct but inconsistent with documented convention

### Frontend Impact Analysis

**Current Frontend Implementation:**

The frontend has **two distinct API patterns** for Schedule Baseline operations:

#### Pattern 1: Direct Schedule Baseline API (`frontend/src/features/schedule-baselines/api/useScheduleBaselines.ts`)

**Current State:**
- **CREATE** (`useCreateScheduleBaseline`, lines 200-240): Already includes `branch` in body payload
- **UPDATE** (`useUpdateScheduleBaseline`, lines 245-281): Does NOT pass `branch` or `control_date` to API
- **DELETE** (`useDeleteScheduleBaseline`, lines 286-318): Passes `branch` and `control_date` as query parameters (correct)
- **Generated Types** (`ScheduleBaselineCreate`, `ScheduleBaselineUpdate`): MISSING `branch` and `control_date` fields

**Files Affected:**
1. `frontend/src/features/schedule-baselines/api/useScheduleBaselines.ts`
2. `frontend/src/api/generated/models/ScheduleBaselineCreate.ts` (generated, will need regeneration)
3. `frontend/src/api/generated/models/ScheduleBaselineUpdate.ts` (generated, will need regeneration)
4. `frontend/src/api/generated/services/ScheduleBaselinesService.ts` (generated, will need regeneration)

#### Pattern 2: Nested Cost Element Schedule Baseline API (`frontend/src/features/schedule-baselines/api/useCostElementScheduleBaseline.ts`)

**Current State:**
- **CREATE** (`useCreateCostElementScheduleBaseline`, lines 104-172): Passes `branch` as QUERY parameter, `control_date` in body
- **UPDATE** (`useUpdateCostElementScheduleBaseline`, lines 181-243): Passes `branch` as QUERY parameter, `control_date` in body
- **DELETE** (`useDeleteCostElementScheduleBaseline`, lines 252-308): Passes `branch` and `control_date` as QUERY parameters
- **Modal Component** (`ScheduleBaselineModal.tsx`): Does not pass `branch` or `control_date` when creating/updating

**Files Affected:**
1. `frontend/src/features/schedule-baselines/api/useCostElementScheduleBaseline.ts`
2. `frontend/src/features/schedule-baselines/components/ScheduleBaselineModal.tsx`
3. `frontend/src/api/generated/services/CostElementsService.ts` (generated, will need regeneration)

**Impact Summary:**

| API Pattern | Operation | Current Implementation | Required Change |
|------------|-----------|------------------------|-----------------|
| Direct API | CREATE | `branch` in body (already correct) | Add `control_date` to body, regenerate types |
| Direct API | UPDATE | No `branch`/`control_date` | Add both to body, regenerate types |
| Direct API | DELETE | Query params (correct) | No change |
| Nested API | CREATE | `branch` in query, `control_date` in body | Move `branch` to body |
| Nested API | UPDATE | `branch` in query, `control_date` in body | Move `branch` to body |
| Nested API | DELETE | Query params (correct) | No change |

**Frontend Changes Required:**

1. **Regenerate OpenAPI Client** (`npm run generate-client`)
   - Backend schema changes will auto-generate updated TypeScript types
   - `ScheduleBaselineCreate` will include `branch` and `control_date`
   - `ScheduleBaselineUpdate` will include `branch` and `control_date`

2. **Update Direct API Hooks** (`useScheduleBaselines.ts`)
   - **CREATE**: Already correct, but needs to add `control_date` from TimeMachine context
   - **UPDATE**: Add `branch` and `control_date` to payload
   - No changes needed for DELETE

3. **Update Nested API Hooks** (`useCostElementScheduleBaseline.ts`)
   - **CREATE**: Move `branch` from query params to body, add `control_date` to body
   - **UPDATE**: Move `branch` from query params to body, keep `control_date` in body
   - No changes needed for DELETE

4. **Update Modal Component** (`ScheduleBaselineModal.tsx`)
   - No explicit changes needed (hooks handle the data)
   - Will benefit from regenerated types

5. **Update Query Types**
   - Domain types in both hook files need to match new generated types
   - Add `branch?: string` and `control_date?: string` to `ScheduleBaselineCreate` and `ScheduleBaselineUpdate` interfaces

**Breaking Change Impact:**

Since the frontend is the only API consumer (confirmed in requirements), breaking changes are acceptable:

- **Components**: `ScheduleBaselineModal.tsx` - No direct API calls, uses hooks
- **Pages**: `CostElementDetailPage.tsx`, `ScheduleBaselinesTab.tsx` - Use hooks, no direct impact
- **Hooks**: Will need updates to match new API signatures
- **Generated Client**: Will need regeneration after backend changes

**Testing Requirements:**

1. **Unit Tests** (`useCostElementScheduleBaseline.test.ts` exists)
   - Update test mocks to include `branch` and `control_date` in request bodies
   - Verify query params no longer include `branch` for POST/PUT

2. **Integration Tests**
   - Test CREATE with `branch` in body
   - Test UPDATE with both `branch` and `control_date` in body
   - Test DELETE with query params (no change)

3. **E2E Tests** (Playwright)
   - Verify modal form submission works with new API
   - Test branch switching during baseline creation
   - Verify time-travel context (`control_date`) propagation

---

## Solution Options

### Option 1: Full Body Parameter Consistency (Recommended)

**Architecture & Design:**

Move ALL write operation parameters (`branch`, `control_date`) to request bodies for POST/PUT/PATCH operations. Keep DELETE operations using query parameters (as HTTP DELETE cannot have a body).

**Schema Changes:**
- Add `branch` and `control_date` to `ScheduleBaselineCreate` and `ScheduleBaselineUpdate`
- All Create/Update schemas now have consistent fields

**Route Changes:**
- Extract `branch` and `control_date` from request body in POST/PUT/PATCH
- DELETE routes continue using query parameters (with updated documentation)
- Remove all hardcoded values

**Service Layer:**
- No changes required - already expects these parameters

**UX Design:**

**API Consumer Experience:**
- Consistent parameter location across all write operations
- Clear separation: query params for filtering/context, body for data + metadata
- DELETE operations remain intuitive (query params only)

**Example Usage:**

```python
# CREATE - All in body
POST /api/v1/schedule-baselines
{
  "name": "Q1 2026 Baseline",
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-03-31T23:59:59Z",
  "progression_type": "LINEAR",
  "branch": "main",
  "control_date": "2026-01-19T10:00:00Z"
}

# UPDATE - All in body
PUT /api/v1/schedule-baselines/{id}
{
  "name": "Q1 2026 Baseline (Revised)",
  "end_date": "2026-04-15T23:59:59Z",
  "branch": "main",
  "control_date": "2026-01-19T10:00:00Z"
}

# DELETE - Query params only (HTTP constraint)
DELETE /api/v1/schedule-baselines/{id}?branch=main&control_date=2026-01-19T10:00:00Z
```

**Implementation:**

**Key Files to Modify:**

1. **Schema Updates** (`backend/app/models/schemas/schedule_baseline.py`):
   ```python
   class ScheduleBaselineCreate(ScheduleBaselineBase):
       schedule_baseline_id: UUID | None = Field(None, exclude=True)
       branch: str = Field("main", description="Branch name for creation")
       control_date: datetime | None = Field(
           None, description="Optional control date for creation"
       )

   class ScheduleBaselineUpdate(BaseModel):
       # ... existing fields ...
       branch: str | None = Field(None, description="Branch name for update")
       control_date: datetime | None = Field(None, description="Control date")
   ```

2. **Route Updates** (`backend/app/api/routes/schedule_baselines.py`):
   ```python
   @router.post("")
   async def create_schedule_baseline(
       baseline_in: ScheduleBaselineCreate,  # Now includes branch/control_date
       service: ScheduleBaselineService = Depends(get_schedule_baseline_service),
   ) -> ScheduleBaseline:
       return await service.create(
           create_schema=baseline_in,
           actor_id=current_user.user_id,
           branch=baseline_in.branch,  # From body
           control_date=baseline_in.control_date,  # From body
       )
   ```

3. **Nested Schedule Baseline Routes** (`cost_elements.py` lines 348-466):
   - Update to accept dict with branch/control_date
   - Extract and pass to service

4. **Documentation Updates**:
   - Clarify DELETE exception in API conventions
   - Update all endpoint examples

**Potential Technical Challenges:**

- **Breaking Change**: Frontend API calls need to be updated to match new signatures
- **Generated Client**: Must regenerate OpenAPI types after backend changes

**Frontend Changes:**

1. **Regenerate OpenAPI Client**
   ```bash
   cd frontend && npm run generate-client
   ```
   - `ScheduleBaselineCreate` will include `branch` and `control_date`
   - `ScheduleBaselineUpdate` will include `branch` and `control_date`
   - Generated service methods will expect these in body

2. **Update Direct API Hooks** (`useScheduleBaselines.ts`)
   ```typescript
   // CREATE - Already mostly correct, just add control_date
   export const useCreateScheduleBaseline = () => {
     const { asOf } = useTimeMachineParams();
     return useMutation({
       mutationFn: (data: CreateWithBranch) => {
         const { branch, ...rest } = data;
         const payload: ScheduleBaselineCreate = {
           ...rest,
           branch: branch || "main",
           control_date: asOf || undefined,  // ADD THIS
         };
         return ScheduleBaselinesService.createScheduleBaseline(payload);
       },
     });
   };

   // UPDATE - Add branch and control_date
   export const useUpdateScheduleBaseline = () => {
     const { asOf } = useTimeMachineParams();
     return useMutation({
       mutationFn: ({ id, data }: { id: string; data: UpdateWithBranch }) => {
         const { branch, ...rest } = data;
         const payload: ScheduleBaselineUpdate = {
           ...rest,
           branch: branch || "main",  // ADD THIS
           control_date: asOf || undefined,  // ADD THIS
         };
         return ScheduleBaselinesService.updateScheduleBaseline(id, payload);
       },
     });
   };
   ```

3. **Update Nested API Hooks** (`useCostElementScheduleBaseline.ts`)
   ```typescript
   // CREATE - Move branch from query to body
   export const useCreateCostElementScheduleBaseline = () => {
     const { asOf } = useTimeMachineParams();
     return useMutation({
       mutationFn: async ({ costElementId, branch, ...data }) => {
         const payload = {
           ...data,
           branch: branch || "main",  // MOVE FROM QUERY TO BODY
           control_date: asOf || null,
         };
         return await __request(OpenAPI, {
           method: "POST",
           url: `/api/v1/cost-elements/${costElementId}/schedule-baseline`,
           // REMOVE: query: { branch: branch || "main" },
           body: payload,
         });
       },
     });
   };

   // UPDATE - Move branch from query to body
   export const useUpdateCostElementScheduleBaseline = () => {
     const { asOf } = useTimeMachineParams();
     return useMutation({
       mutationFn: async ({ costElementId, baselineId, data, branch }) => {
         const payload = {
           ...data,
           branch: branch || "main",  // MOVE FROM QUERY TO BODY
           control_date: asOf || null,
         };
         return await __request(OpenAPI, {
           method: "PUT",
           url: `/api/v1/cost-elements/${costElementId}/schedule-baseline/${baselineId}`,
           // REMOVE: query: { branch: branch || "main" },
           body: payload,
         });
       },
     });
   };
   ```

4. **Update Domain Types**
   - Add `branch?: string` and `control_date?: string` to local TypeScript interfaces
   - These will match the regenerated OpenAPI types

**Testing Approach:**

1. Unit tests for schema validation
2. Integration tests for each endpoint
3. Verify default values work correctly
4. Test time-travel scenarios with `control_date`
5. Test branch isolation

**Trade-offs:**

| Aspect          | Assessment                                                 |
| --------------- | ---------------------------------------------------------- |
| Pros            | - Complete consistency across all write operations<br>- Clear API design (body for writes, query for reads)<br>- Type-safe via Pydantic<br>- Easier to document and understand<br>- Breaking changes acceptable (frontend is only consumer) |
| Cons            | - Frontend changes required (hooks and generated client)<br>- DELETE remains exception (HTTP constraint)<br>- Requires OpenAPI regeneration |
| Complexity      | **Low** - Mostly mechanical changes to schemas and routes |
| Maintainability | **Excellent** - Consistent pattern reduces cognitive load |
| Performance     | **No impact** - Same data, different location |
| Frontend Effort | **Low** (1-2 hours) - Update 2 hook files, regenerate types |

---

### Option 2: Query Parameters for All Write Operations

**Architecture & Design:**

Move ALL `branch` and `control_date` to query parameters for consistency, including POST/PUT/PATCH operations. Remove from request bodies entirely.

**Schema Changes:**
- Remove `branch` and `control_date` from all Create/Update schemas
- Keep only in service layer

**Route Changes:**
- All write operations use query parameters
- Consistent with DELETE operations

**UX Design:**

**API Consumer Experience:**
- All context parameters in query string
- Request body contains only business data
- Consistent across all HTTP methods

**Example Usage:**

```python
# CREATE
POST /api/v1/schedule-baselines?branch=main&control_date=2026-01-19T10:00:00Z
{
  "name": "Q1 2026 Baseline",
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-03-31T23:59:59Z",
  "progression_type": "LINEAR"
}
```

**Frontend Changes:**

1. **Regenerate OpenAPI Client**
   - `ScheduleBaselineCreate` will NOT include `branch` or `control_date`
   - `ScheduleBaselineUpdate` will NOT include `branch` or `control_date`
   - Generated service methods will accept these as query parameters

2. **Update Direct API Hooks** (`useScheduleBaselines.ts`)
   ```typescript
   // CREATE - Pass branch and control_date as query params
   export const useCreateScheduleBaseline = () => {
     const { asOf, branch: tmBranch } = useTimeMachineParams();
     return useMutation({
       mutationFn: (data: ScheduleBaselineCreate) => {
         // NOTE: Generated service will expect branch as query param
         return ScheduleBaselinesService.createScheduleBaseline(
           data,
           tmBranch || "main",  // branch as query param
           asOf || undefined,   // control_date as query param
         );
       },
     });
   };

   // UPDATE - Pass branch and control_date as query params
   export const useUpdateScheduleBaseline = () => {
     const { asOf, branch: tmBranch } = useTimeMachineParams();
     return useMutation({
       mutationFn: ({ id, data }: { id: string; data: ScheduleBaselineUpdate }) => {
         return ScheduleBaselinesService.updateScheduleBaseline(
           id,
           data,
           tmBranch || "main",  // branch as query param
           asOf || undefined,   // control_date as query param
         );
       },
     });
   };
   ```

3. **Update Nested API Hooks** (`useCostElementScheduleBaseline.ts`)
   ```typescript
   // CREATE - Already correct, just add control_date
   export const useCreateCostElementScheduleBaseline = () => {
     const { asOf } = useTimeMachineParams();
     return useMutation({
       mutationFn: async ({ costElementId, branch, ...data }) => {
         const payload = {
           ...data,
           // No branch or control_date in body
         };
         return await __request(OpenAPI, {
           method: "POST",
           url: `/api/v1/cost-elements/${costElementId}/schedule-baseline`,
           query: {
             branch: branch || "main",
             control_date: asOf || undefined,  // ADD THIS
           },
           body: payload,
         });
       },
     });
   };

   // UPDATE - Add control_date to query
   export const useUpdateCostElementScheduleBaseline = () => {
     const { asOf } = useTimeMachineParams();
     return useMutation({
       mutationFn: async ({ costElementId, baselineId, data, branch }) => {
         const payload = {
           ...data,
           // No branch or control_date in body
         };
         return await __request(OpenAPI, {
           method: "PUT",
           url: `/api/v1/cost-elements/${costElementId}/schedule-baseline/${baselineId}`,
           query: {
             branch: branch || "main",
             control_date: asOf || undefined,  // ADD THIS
           },
           body: payload,
         });
       },
     });
   };
   ```

4. **Update Domain Types**
   - Remove `branch` and `control_date` from local TypeScript interfaces
   - These will match the regenerated OpenAPI types

**Trade-offs:**

| Aspect          | Assessment                                                 |
| --------------- | ---------------------------------------------------------- |
| Pros            | - Consistent across all operations including DELETE<br>- Clear separation: query = context, body = data<br>- No breaking change for DELETE<br>- Minimal frontend changes (nested API already close) |
| Cons            | - Reverses existing pattern (Projects/WBEs/CostElements already use body)<br>- Less type-safe (query params not in Pydantic schemas)<br>- Longer URLs<br>- Harder to document in OpenAPI<br>- Requires updating 4 other entities to match |
| Complexity      | **Medium** - Requires removing fields from existing schemas AND updating Project/WBE/CostElement/Forecast |
| Maintainability | **Fair** - Works, but less type-safe than body approach |
| Performance     | **No impact** - Same data transmission |
| Frontend Effort | **Low** (1 hour) - Nested API already uses query for branch, just add control_date |

---

## Comparison Summary

| Criteria           | Option 1: Full Body       | Option 2: Query Params      |
| ------------------ | ------------------------- | -------------------------- |
| Backend Effort     | Low (2-3 hours)           | Medium (5-6 hours)         |
| Frontend Effort    | Low (1-2 hours)           | Low (1 hour)               |
| Breaking Changes   | Yes (acceptable)          | Yes (reverses existing)    |
| Type Safety        | Excellent (Pydantic)      | Poor (query params only)   |
| Consistency        | High (matches existing)   | Medium (requires updates to 4 other entities) |
| Migration Path     | Complete pattern          | Requires updating Project/WBE/CostElement/Forecast |
| Best For           | Long-term maintainability | Query-heavy APIs           |

---

## Recommendation

**I recommend Option 1: Full Body Parameter Consistency** because:

1. **Type Safety**: Pydantic schemas enforce validation at the type level, catching errors before they reach the service layer
2. **Existing Pattern**: Projects, WBEs, CostElements, and Forecasts already use this pattern - we're completing the pattern, not establishing a new one
3. **API Design Clarity**: Clear separation of concerns - query parameters for filtering/read context, request body for data + write metadata
4. **Documentation**: Easier to document in OpenAPI when parameters are in schemas
5. **Long-term Maintainability**: Consistent patterns reduce cognitive load for future developers
6. **Breaking Changes Acceptable**: Frontend is the only API consumer, so breaking changes are acceptable
7. **Minimal Frontend Effort**: Only 2 hook files need updates, and generated client regeneration is automatic

**Implementation Priority:**

1. **Phase 1** (Backend - High Priority): Fix Schedule Baseline schemas and routes
   - Add `branch` and `control_date` to `ScheduleBaselineCreate` and `ScheduleBaselineUpdate`
   - Update schedule baseline routes to use body parameters
   - Update nested schedule baseline endpoints in cost_elements.py

2. **Phase 2** (Backend - Medium Priority): Update forecast endpoints
   - Move `branch` and `control_date` from query to body for PUT operations
   - Keep DELETE using query parameters

3. **Phase 3** (Frontend - Medium Priority): Update frontend to match new API
   - Regenerate OpenAPI client (`npm run generate-client`)
   - Update `useScheduleBaselines.ts` to add `control_date` from TimeMachine context
   - Update `useCostElementScheduleBaseline.ts` to move `branch` from query to body
   - Update unit tests to match new request payloads

4. **Phase 4** (Documentation): Update API conventions
   - Clarify that DELETE operations use query parameters due to HTTP constraints
   - Document the pattern: "Write context (branch, control_date) goes in request body for POST/PUT/PATCH, query parameters for DELETE"

**Alternative consideration:** Choose Option 2 (Query Params) if you want all context parameters in query strings for a more REST API style, but this requires updating 4 other entities and loses type safety.

---

## Decision Questions

1. **Frontend Update Timeline**: How quickly can the frontend be updated to use body parameters instead of query parameters for Schedule Baseline operations?

2. **DELETE Operation Preference**: Should we update the API conventions documentation to explicitly call out DELETE as an exception (using query parameters due to HTTP constraints), or is the current documentation acceptable?

3. **Schedule Baseline Creation**: Should schedule baselines be creatable in non-main branches immediately, or should we enforce "create on main first, then branch" as the current hardcoded implementation suggests?

---

## Approved Decision

**Date:** 2026-01-19

**Selected Option:** **Option 1: Full Body Parameter Consistency**

**Decision Details:**
- All write operation parameters (`branch`, `control_date`) will be in request bodies for POST/PUT/PATCH
- DELETE operations will continue using query parameters (HTTP constraint)
- Schedule baselines **can be created in any branch** (not restricted to main)
- Breaking changes are **acceptable** - frontend is the only API consumer

**Rationale:**
- Completes the existing pattern established by Projects, WBEs, and CostElements
- Provides type safety via Pydantic schemas
- Clear API design: body for writes, query for filtering
- Best long-term maintainability
- Minimal frontend effort (2 hook files, auto-regenerated types)

**Implementation Plan:**
1. Backend: Update Schedule Baseline schemas and routes
2. Backend: Update forecast endpoints (optional, Phase 2)
3. Frontend: Regenerate OpenAPI client and update hooks
4. Documentation: Update API conventions document

**Breaking Change Impact:**
- Frontend files affected:
  - `frontend/src/features/schedule-baselines/api/useScheduleBaselines.ts`
  - `frontend/src/features/schedule-baselines/api/useCostElementScheduleBaseline.ts`
  - `frontend/src/api/generated/*` (auto-regenerated)
- Estimated frontend effort: 1-2 hours
- No external API consumers impacted

---

## References

- [API Conventions](../../02-architecture/cross-cutting/api-conventions.md) - Current specification
- [Temporal Query Reference](../../02-architecture/cross-cutting/temporal-query-reference.md) - Bitemporal system reference
- [ADR-005: Bitemporal Versioning](../../02-architecture/decisions/ADR-005-bitemporal-versioning.md) - Architecture decision
- [Schedule Baseline Schemas](../../../backend/app/models/schemas/schedule_baseline.py) - Current schema definitions
- [Schedule Baseline Routes](../../../backend/app/api/routes/schedule_baselines.py) - Current route implementations
