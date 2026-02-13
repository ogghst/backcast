# Request Analysis: WBE Parent Filter Pagination

**Date:** 2026-01-09  
**Analyst:** AI Assistant  
**Status:** 🔍 Analysis Phase

---

## Clarified Requirements

**User Request:** "The hierarchical filtering mode shall be implemented only when requested project_id, but when filtering by parent_wbe_id it shall be a simple list."

**Interpretation:**

Currently, the WBE endpoint (`GET /api/v1/wbes`) has two modes:

1. **Hierarchical Mode (No Pagination)**: Returns `Array<WBE>` when filtering by `project_id` OR `parent_wbe_id`
2. **General Listing Mode (Paginated)**: Returns `PaginatedResponse<WBE>` when no hierarchical filters are applied

**Proposed Change:**

- **Hierarchical Mode (No Pagination)**: Only when filtering by `project_id` alone
- **Parent Filter Mode (Paginated)**: When filtering by `parent_wbe_id` (with or without `project_id`), return `PaginatedResponse<WBE>`
- **General Listing Mode (Paginated)**: Remains unchanged

**Rationale for Change:**

The current assumption that filtering by `parent_wbe_id` always returns a bounded dataset (suitable for unpaginated arrays) may not hold true in large projects where:

- A single parent WBE might have hundreds of children
- Users need search/filter/sort capabilities within a parent's children
- UI components benefit from consistent pagination patterns

---

## Context Discovery Findings

### Product Scope

**Relevant User Stories:**

- WBE Management: Users need to browse, search, and filter WBEs within projects
- Hierarchical Navigation: Users navigate project → WBE → child WBEs → cost elements

**Business Requirements:**

- Support large-scale projects with thousands of WBEs
- Maintain performance for hierarchical queries
- Provide consistent UX patterns across entity lists

### Architecture Context

**Bounded Contexts Involved:**

- **Project & WBE Management** (Backend Context 5)
- **Frontend State & Data Management** (Frontend Context F1)

**Existing Patterns:**

- **Backend**: Hybrid pagination strategy in `backend/app/api/routes/wbes.py`
- **Frontend**: TanStack Query for server state, Ant Design Table for pagination
- **Coding Standards**: Backend as source of truth, strict typing, functional programming

**Current Implementation:**

```python
# backend/app/api/routes/wbes.py (lines 97-109)

# Handle hierarchical filtering (returns list, not paginated)
# Case 1: Specific parent (parsed_parent_id is set)
# Case 2: Root query (is_root_query is True)
if parsed_parent_id or is_root_query:
    return await service.get_by_parent(
        project_id=project_id,
        parent_wbe_id=parsed_parent_id,
        branch=branch,
    )

# Project filtering only (returns list, not paginated)
if project_id:
    return await service.get_by_project(project_id=project_id, branch=branch)
```

### Codebase Analysis

**Backend:**

- **API Route**: `backend/app/api/routes/wbes.py` - `read_wbes()` endpoint
- **Service**: `backend/app/services/wbe.py` - `WBEService.get_by_parent()`, `get_by_project()`, `get_wbes()`
- **Data Models**: `backend/app/models/domain/wbe.py` - WBE entity with `parent_wbe_id` field

**Frontend:**

- **API Client**: `frontend/src/api/generated/services/WbEsService.ts` - Auto-generated OpenAPI client
- **Components**:
  - `frontend/src/pages/wbes/WBEList.tsx` - Main WBE list page
  - `frontend/src/pages/wbes/WBEDetailPage.tsx` - WBE detail with child WBEs
  - `frontend/src/features/wbes/components/WBEModal.tsx` - Create/Edit modal
- **State Management**: TanStack Query hooks (not yet implemented for WBEs based on current iteration context)

**Current Usage:**

- Frontend does NOT currently use `parent_wbe_id` filter in API calls (grep search returned no results in hooks/API calls)
- The `parent_wbe_id` field is only used in forms and display logic
- This suggests the feature may not be actively used in production UI

---

## Solution Options

### Option 1: Simple Conditional Pagination (Recommended)

**Architecture & Design:**

- Modify `read_wbes()` endpoint to return `PaginatedResponse` when `parent_wbe_id` is provided
- Keep unpaginated array response only for `project_id` filtering (full project tree)
- Reuse existing `get_wbes()` service method with additional `parent_wbe_id` filter

**Implementation:**

```python
# backend/app/api/routes/wbes.py

# Project filtering only (returns list, not paginated) - UNCHANGED
if project_id and not parent_wbe_id:
    return await service.get_by_project(project_id=project_id, branch=branch)

# Parent filtering (returns paginated response) - NEW
if parent_wbe_id or is_root_query:
    skip = (page - 1) * per_page
    wbes, total = await service.get_wbes(
        skip=skip,
        limit=per_page,
        branch=branch,
        parent_wbe_id=parsed_parent_id,
        project_id=project_id,  # Optional additional filter
        search=search,
        filters=filters,
        sort_field=sort_field,
        sort_order=sort_order,
    )
    # Return paginated response...
```

**Service Changes:**

```python
# backend/app/services/wbe.py

async def get_wbes(
    self,
    skip: int = 0,
    limit: int = 100000,
    branch: str = "main",
    parent_wbe_id: UUID | None = None,  # NEW parameter
    project_id: UUID | None = None,      # NEW parameter
    search: str | None = None,
    filters: str | None = None,
    sort_field: str | None = None,
    sort_order: str = "asc",
) -> tuple[list[WBE], int]:
    """Get WBEs with pagination, search, and filters."""

    # Build base query
    conditions = [
        WBE.branch == branch,
        func.upper(cast(Any, WBE).valid_time).is_(None),
        cast(Any, WBE).deleted_at.is_(None),
    ]

    # Add parent filter if provided
    if parent_wbe_id is not None:
        conditions.append(WBE.parent_wbe_id == parent_wbe_id)

    # Add project filter if provided
    if project_id is not None:
        conditions.append(WBE.project_id == project_id)

    # ... rest of existing logic
```

**Trade-offs:**

| Aspect              | Assessment                                                                                                                                                      |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pros**            | - Minimal code changes<br>- Reuses existing pagination infrastructure<br>- Consistent API response format<br>- Supports search/filter/sort on parent's children |
| **Cons**            | - Breaking change for any frontend code using `parent_wbe_id` filter (currently none found)<br>- Slightly more complex endpoint logic                           |
| **Complexity**      | **Low** - ~30 lines of code changes                                                                                                                             |
| **Maintainability** | **Good** - Follows existing patterns, reduces special cases                                                                                                     |
| **Performance**     | **Excellent** - Pagination reduces payload size, indexed queries remain fast                                                                                    |

**Frontend Impact:**

- **OpenAPI Client**: Auto-regenerate to reflect new response type
- **Type Safety**: TypeScript will enforce correct handling of `PaginatedResponse` vs `Array`
- **No Breaking Changes**: Since `parent_wbe_id` filter is not currently used in frontend

---

### Option 2: Separate Endpoint for Parent Filtering

**Architecture & Design:**

- Create new endpoint: `GET /api/v1/wbes/by-parent/{parent_wbe_id}`
- Keep existing `GET /api/v1/wbes` logic unchanged
- Dedicated endpoint always returns `PaginatedResponse`

**Implementation:**

```python
# backend/app/api/routes/wbes.py

@router.get(
    "/by-parent/{parent_wbe_id}",
    response_model=None,  # PaginatedResponse[WBEPublic]
    operation_id="get_wbes_by_parent",
    dependencies=[Depends(RoleChecker(required_permission="wbe-read"))],
)
async def read_wbes_by_parent(
    parent_wbe_id: str,  # Can be UUID or "null" for root
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1),
    project_id: UUID | None = Query(None),
    branch: str = Query("main"),
    search: str | None = Query(None),
    sort_field: str | None = Query(None),
    sort_order: str = Query("asc"),
    service: WBEService = Depends(get_wbe_service),
) -> dict[str, Any]:
    """Get WBEs by parent with pagination."""
    # ... implementation
```

**Trade-offs:**

| Aspect              | Assessment                                                                                                                                  |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pros**            | - No breaking changes to existing endpoint<br>- Clear separation of concerns<br>- Explicit API contract                                     |
| **Cons**            | - Code duplication between endpoints<br>- More endpoints to maintain<br>- Inconsistent with REST conventions (filter should be query param) |
| **Complexity**      | **Medium** - ~60 lines of new code + tests                                                                                                  |
| **Maintainability** | **Fair** - More code to maintain, potential drift between endpoints                                                                         |
| **Performance**     | **Excellent** - Same as Option 1                                                                                                            |

---

### Option 3: Hybrid with Threshold-Based Pagination

**Architecture & Design:**

- Keep current logic but add intelligent pagination based on result count
- If `parent_wbe_id` filter returns < 100 items, return unpaginated array
- If ≥ 100 items, return `PaginatedResponse`
- Frontend must handle both response types

**Implementation:**

```python
# backend/app/api/routes/wbes.py

if parsed_parent_id or is_root_query:
    # First, get count
    count = await service.get_children_count(
        wbe_id=parsed_parent_id,
        branch=branch
    )

    # If small dataset, return unpaginated
    if count < 100:
        return await service.get_by_parent(...)

    # Otherwise, paginate
    skip = (page - 1) * per_page
    wbes, total = await service.get_wbes(...)
    return PaginatedResponse(...)
```

**Trade-offs:**

| Aspect              | Assessment                                                                                                                                                           |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pros**            | - Optimizes for common case (small child sets)<br>- Backward compatible for small datasets                                                                           |
| **Cons**            | - **Inconsistent API contract** (response type varies)<br>- Frontend must handle both types<br>- Extra database query for count<br>- Violates type safety principles |
| **Complexity**      | **High** - Complex logic, frontend type handling                                                                                                                     |
| **Maintainability** | **Poor** - Unpredictable behavior, hard to test                                                                                                                      |
| **Performance**     | **Good** - Extra count query overhead                                                                                                                                |

**❌ Not Recommended** - Violates coding standards (strict typing, predictable APIs)

---

## Comparison Summary

| Criteria               | Option 1: Conditional Pagination | Option 2: Separate Endpoint   | Option 3: Threshold-Based         |
| ---------------------- | -------------------------------- | ----------------------------- | --------------------------------- |
| **Development Effort** | 1-2 hours                        | 2-3 hours                     | 3-4 hours                         |
| **Code Complexity**    | Low                              | Medium                        | High                              |
| **Type Safety**        | ✅ Excellent                     | ✅ Excellent                  | ❌ Poor (union types)             |
| **API Consistency**    | ✅ Good (REST conventions)       | ⚠️ Fair (more endpoints)      | ❌ Poor (unpredictable)           |
| **Maintainability**    | ✅ Good                          | ⚠️ Fair                       | ❌ Poor                           |
| **Breaking Changes**   | ⚠️ Yes (unused feature)          | ✅ No                         | ⚠️ Partial                        |
| **Best For**           | Standard pagination needs        | Strict backward compatibility | Dynamic datasets (not applicable) |

---

## Recommendation

**I recommend Option 1: Simple Conditional Pagination** because:

1. **Aligns with Coding Standards**:

   - Strict typing (single response type per filter mode)
   - Backend as source of truth
   - Predictable API contracts

2. **Minimal Risk**:

   - Frontend currently does NOT use `parent_wbe_id` filter (verified via grep search)
   - No breaking changes to production code

3. **Future-Proof**:

   - Supports large-scale projects with many child WBEs
   - Enables search/filter/sort on parent's children
   - Consistent with other paginated endpoints (projects, cost elements)

4. **Low Effort**:
   - ~30 lines of code changes
   - Reuses existing `get_wbes()` infrastructure
   - 1-2 hours implementation + testing

**Alternative Consideration:**

Choose **Option 2** only if:

- There's hidden production code using `parent_wbe_id` filter that wasn't found in grep search
- Strict backward compatibility is required for external API consumers

---

## Questions for Decision

1. **Backward Compatibility**: Are there any external API consumers or undocumented frontend code using the `parent_wbe_id` filter that would break with Option 1?

2. **Performance Requirements**: What is the expected maximum number of child WBEs under a single parent? (This validates the need for pagination)

3. **Frontend Impact**: Should we proactively implement frontend hooks for `parent_wbe_id` filtering, or wait for a specific use case?

4. **Timeline**: Is this change blocking any current work, or can it be scheduled for the next sprint?

---

## Next Steps

If **Option 1** is approved:

1. Create iteration folder: `docs/03-project-plan/iterations/2026-01-09-wbe-parent-filter-pagination/`
2. Move to **PLAN** phase:
   - Detailed implementation plan
   - Test strategy (unit, integration, E2E)
   - Migration guide for OpenAPI client regeneration
3. Estimated completion: 1-2 hours (backend) + 0.5 hours (testing)
