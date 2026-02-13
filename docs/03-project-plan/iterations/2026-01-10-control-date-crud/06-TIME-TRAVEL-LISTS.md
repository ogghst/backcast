# Time-Travel List Query Support - Implementation Summary

**Date:** 2026-01-10
**Status:** ✅ COMPLETE

## Overview

Extended time-travel (as_of) query support to **all list endpoints** for Projects, WBEs, and Cost Elements. Users can now view the complete historical state of their data at any point in time, not just individual entity details.

## Problem Statement

Previously, only detail endpoints supported time-travel via the `as_of` parameter. List endpoints always returned current versions, which meant:

- Time Machine "time travel" only worked for viewing individual entity details
- List views always showed current data, even when a historical time was selected
- Users couldn't see what their project/WBE/cost element lists looked like at past dates

## Solution Applied

### Backend Changes

Applied a **consistent pattern** across all three entities (Projects, WBEs, Cost Elements):

#### 1. API Route Updates

Added `as_of` query parameter to all list endpoints:

```python
as_of: datetime | None = Query(
    None,
    description="Time travel: get [Entity] as of this timestamp (ISO 8601)",
)
```

**Files Modified:**

- `backend/app/api/routes/projects.py` - Added `as_of` to `read_projects()`
- `backend/app/api/routes/wbes.py` - Added `as_of` to `read_wbes()`
- `backend/app/api/routes/cost_elements.py` - Added `as_of` to `read_cost_elements()`

#### 2. Service Layer Updates

Updated all service methods to support time-travel filtering:

**Pattern Applied:**

```python
async def get_[entities](
    self,
    # ... existing params ...
    as_of: datetime | None = None,
) -> tuple[list[Entity], int]:
    # Base query
    stmt = select(Entity).where(
        Entity.branch == branch,
        cast(Any, Entity).deleted_at.is_(None),
    )

    # Apply time-travel filter
    if as_of:
        # Get version valid at as_of time
        stmt = stmt.where(
            cast(Any, Entity).valid_time.contains(as_of)
        )
    else:
        # Get current version (open upper bound)
        stmt = stmt.where(
            func.upper(cast(Any, Entity).valid_time).is_(None)
        )
```

**Files Modified:**

- `backend/app/services/project.py` - Updated `get_projects()`
- `backend/app/services/wbe.py` - Updated `get_wbes()` and `_get_base_stmt()` (for parent names)
- `backend/app/services/cost_element_service.py` - Updated `get_cost_elements()`

**Key Insight:** For WBEs, also updated `_get_base_stmt()` to support time-travel for parent name lookups, ensuring complete historical accuracy.

### Frontend Changes

Created **custom list hooks** that automatically inject `as_of` from the `TimeMachineContext`:

#### Pattern Applied:

```typescript
export const use[Entities] = (params?: Parameters<typeof baseHooks.useList>[0]) => {
  const { asOf } = useTimeMachineParams();

  return useQuery({
    queryKey: ["[entities]", params, { asOf }],
    queryFn: async () => {
      // Parse params...

      // Manual request to support as_of query param
      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/[entities]",
        query: {
          // ... pagination, filters, sorting ...
          as_of: asOf || undefined,
        },
      }) as Promise<PaginatedResponse<EntityRead>>;
    },
    ...params?.queryOptions,
  });
};
```

**Files Modified:**

- `frontend/src/features/projects/api/useProjects.ts` - Custom `useProjects` hook
- `frontend/src/features/wbes/api/useWBEs.ts` - Custom `useWBEs` hook
- `frontend/src/features/cost-elements/api/useCostElements.ts` - Custom `useCostElements` hook

## Testing

✅ **All backend tests passing** (13/13 tests for Projects + Cost Elements, 11/11 for WBEs)

- Existing CRUD tests continue to work (current version queries)
- `control_date` tests pass for create/update/delete operations
- Time-travel queries work correctly with pagination, filtering, and sorting

## Benefits

1. **Complete Historical View:** Users can now see entire lists as they appeared at any point in time
2. **Consistent UX:** Time Machine works uniformly across all entity types and views
3. **Audit Capabilities:** Managers can review project/WBE/cost element states at specific milestones
4. **Pattern Reuse:** Consistent implementation across all entities makes maintenance easier

## How It Works

### User Flow:

1. User selects a date in the Time Machine UI (e.g., "March 1, 2025")
2. `TimeMachineContext` stores the selected time as `asOf`
3. All list hooks (`useProjects`, `useWBEs`, `useCostElements`) automatically include `asOf` in API requests
4. Backend filters to versions that were valid at that time using `valid_time.contains(as_of)`
5. User sees the historical state of all lists and details

### Query Behavior:

**Without `as_of` (default):**

```sql
WHERE valid_time_upper IS NULL  -- Current version
```

**With `as_of`:**

```sql
WHERE valid_time @> '2025-03-01'::timestamp  -- Version at specific time
```

## Generalization & Code Reuse

The solution was **highly generalized** across all three entities:

- Same API parameter pattern
- Same service layer logic
- Same frontend hook structure
- Minimal code duplication

This makes it easy to add time-travel support to future entities by following the same pattern.

## Future Enhancements

Potential improvements:

1. Extract common time-travel filter logic into a base service method
2. Create a reusable frontend hook factory for time-travel lists
3. Add time-travel support for hierarchical queries (parent/child relationships)
4. Optimize queries with specialized indexes on `valid_time` ranges

## Related Documentation

- [Control Date CRUD Implementation](./2026-01-10-control-date-crud/)
- [Time Machine Context](../../../frontend/src/contexts/TimeMachineContext.tsx)
- [Bitemporal Versioning ADR](../../02-architecture/decisions/ADR-005-bitemporal-versioning.md)
