# API Response Patterns

**Last Updated:** 2026-01-08  
**Status:** Active

---

## Overview

This document describes the standard response patterns used across the API, particularly for list endpoints with server-side filtering, search, and sorting capabilities.

---

## Response Formats

### 1. Paginated Response (Standard)

**Used by:** Projects (general listing)

**Format:**

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

**When to use:**

- General list endpoints without hierarchical filters
- When pagination UI needs total count
- When server-side filtering/search/sorting is enabled

**Example:**

```http
GET /api/v1/projects?page=1&per_page=20&search=Alpha&filters=status:Active
```

**TypeScript Type:**

```typescript
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}
```

---

### 2. Array Response (Legacy/Hierarchical)

**Used by:** WBEs (hierarchical queries), Cost Elements (backward compatibility)

**Format:**

```json
[
  { "id": "...", "name": "..." },
  { "id": "...", "name": "..." }
]
```

**When to use:**

- Hierarchical queries (e.g., WBEs by project/parent)
- Backward compatibility with existing clients
- When total count is not needed

**Example:**

```http
GET /api/v1/wbes?project_id=abc123
GET /api/v1/cost-elements?wbe_id=xyz789
```

---

### 3. Hybrid Response (WBEs)

**Used by:** WBEs endpoint

**Behavior:**

- Returns **array** when hierarchical filters are used (projectId, parentWbeId)
- Returns **paginated object** when no hierarchical filters (general listing)

**Decision Logic:**

```python
if project_id or parent_wbe_id:
    return array  # Hierarchical query
else:
    return paginated_response  # General listing
```

**Frontend Handling:**

```typescript
const unwrapWBEResponse = <T>(res: T[] | { items: T[] }): T[] => {
  return Array.isArray(res) ? res : (res as { items: T[] }).items;
};
```

---

## Server-Side Filtering

### URL Format

**Filter String:** `column:value;column:value1,value2`

**Examples:**

```http
# Single filter
?filters=status:Active

# Multiple values (IN clause)
?filters=status:Active,Draft

# Multiple filters
?filters=status:Active;branch:main,dev

# Combined with search and sort
?search=Project&filters=status:Active&sort_field=name&sort_order=desc
```

### Supported Parameters

| Parameter    | Type   | Description               | Example                 |
| ------------ | ------ | ------------------------- | ----------------------- |
| `page`       | int    | Page number (1-indexed)   | `page=1`                |
| `per_page`   | int    | Items per page (1-100)    | `per_page=20`           |
| `search`     | string | Search term (code, name)  | `search=Alpha`          |
| `filters`    | string | Filter expression         | `filters=status:Active` |
| `sort_field` | string | Field to sort by          | `sort_field=name`       |
| `sort_order` | string | Sort direction (asc/desc) | `sort_order=desc`       |
| `branch`     | string | Branch name               | `branch=main`           |

### Whitelisted Filter Fields

**Projects:**

- `status`
- `code`
- `name`

**WBEs:**

- `level`
- `code`
- `name`

**Cost Elements:**

- `code`
- `name`

**Security Note:** Only whitelisted fields can be filtered. Attempting to filter on non-whitelisted fields will raise a `ValueError`.

---

## Frontend Integration Patterns

### Pattern 1: TanStack Query Hook with Pagination

**Use Case:** Projects, general WBE listing

```typescript
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

interface ServerSideParams {
  page?: number;
  per_page?: number;
  search?: string;
  filters?: string;
  sort_field?: string;
  sort_order?: "asc" | "desc";
  branch?: string;
}

const getProjectsPaginated = async (
  params?: ServerSideParams
): Promise<PaginatedResponse<ProjectRead>> => {
  return __request(OpenAPI, {
    method: "GET",
    url: "/api/v1/projects",
    query: {
      page: params?.page || 1,
      per_page: params?.per_page || 20,
      branch: params?.branch || "main",
      search: params?.search,
      filters: params?.filters,
      sort_field: params?.sort_field,
      sort_order: params?.sort_order,
    },
  });
};

// In hook
const res = await getProjectsPaginated(serverParams);
return unwrapResponse(res); // Returns items array
```

### Pattern 2: Response Unwrapping Helper

**Use Case:** All list endpoints

```typescript
/**
 * Helper to unwrap paginated response from API.
 * Backend may return either an array or { items: [...] } wrapper.
 */
const unwrapResponse = <T>(res: T[] | { items: T[] }): T[] => {
  return Array.isArray(res) ? res : (res as { items: T[] }).items;
};
```

### Pattern 3: Ant Design Table Params Conversion

**Use Case:** Converting Ant Design table state to server params

```typescript
const getPaginationParams = (params?: {
  pagination?: { current?: number; pageSize?: number };
  search?: string;
  filters?: Record<string, string[] | string>;
  sorter?: { field?: string; order?: "ascend" | "descend" };
}) => {
  const current = params?.pagination?.current || 1;
  const pageSize = params?.pagination?.pageSize || 20;

  // Convert Ant Design table filters to server format
  let filterString: string | undefined;
  if (params?.filters) {
    const filterParts: string[] = [];
    Object.entries(params.filters).forEach(([key, value]) => {
      if (value && value.length > 0) {
        const values = Array.isArray(value) ? value : [value];
        filterParts.push(`${key}:${values.join(",")}`);
      }
    });
    filterString = filterParts.length > 0 ? filterParts.join(";") : undefined;
  }

  // Convert Ant Design sorter to server format
  const sortField = params?.sorter?.field;
  const sortOrder = params?.sorter?.order === "descend" ? "desc" : "asc";

  return {
    page: current,
    per_page: pageSize,
    search: params?.search,
    filters: filterString,
    sort_field: sortField,
    sort_order: sortOrder,
  };
};
```

---

## Backend Implementation Patterns

### Pattern 1: Service Layer

**Signature:**

```python
async def get_entities(
    self,
    skip: int = 0,
    limit: int = 100,
    branch: str = "main",
    search: str | None = None,
    filters: str | None = None,
    sort_field: str | None = None,
    sort_order: str = "asc",
) -> tuple[list[Entity], int]:
    """Returns (items, total_count) tuple."""
```

**Implementation:**

```python
from app.core.filtering import FilterParser

# Base query
stmt = select(Entity).where(Entity.branch == branch)

# Apply search
if search:
    search_term = f"%{search}%"
    stmt = stmt.where(
        or_(
            Entity.code.ilike(search_term),
            Entity.name.ilike(search_term),
        )
    )

# Apply filters
if filters:
    allowed_fields = ["status", "code", "name"]
    parsed_filters = FilterParser.parse_filters(filters)
    filter_expressions = FilterParser.build_sqlalchemy_filters(
        Entity, parsed_filters, allowed_fields=allowed_fields
    )
    if filter_expressions:
        stmt = stmt.where(and_(*filter_expressions))

# Get total count
count_stmt = select(func.count()).select_from(stmt.subquery())
total = await session.scalar(count_stmt)

# Apply sorting
if sort_field:
    if not hasattr(Entity, sort_field):
        raise ValueError(f"Invalid sort field: {sort_field}")
    column = getattr(Entity, sort_field)
    stmt = stmt.order_by(column.desc() if sort_order == "desc" else column.asc())

# Apply pagination
stmt = stmt.offset(skip).limit(limit)

# Execute
result = await session.execute(stmt)
items = result.scalars().all()

return items, total
```

### Pattern 2: API Layer (Paginated Response)

```python
from app.models.schemas.common import PaginatedResponse

@router.get("", response_model=None)
async def read_entities(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = None,
    filters: str | None = None,
    sort_field: str | None = None,
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    service: EntityService = Depends(get_service),
) -> dict:
    skip = (page - 1) * per_page

    items, total = await service.get_entities(
        skip=skip,
        limit=per_page,
        search=search,
        filters=filters,
        sort_field=sort_field,
        sort_order=sort_order,
    )

    response = PaginatedResponse[EntityPublic](
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )

    return response.model_dump()
```

### Pattern 3: API Layer (Array Response - Backward Compatible)

```python
@router.get("", response_model=list[EntityRead])
async def read_entities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    service: EntityService = Depends(get_service),
) -> Sequence[Entity]:
    # Service returns tuple, unpack and return only items
    items, _ = await service.get_entities(skip=skip, limit=limit)
    return items
```

---

## Migration Checklist

When adding server-side filtering to a new entity:

### Backend

- [ ] Update service `get_*` method signature
- [ ] Add search, filters, sort_field, sort_order parameters
- [ ] Change return type to `tuple[list[Entity], int]`
- [ ] Implement FilterParser integration
- [ ] Define `allowed_fields` whitelist
- [ ] Add database indexes for filtered columns
- [ ] Update API endpoint to handle paginated response
- [ ] Write unit tests (search, filter, sort, pagination)

### Frontend

- [ ] Update TanStack Query hook
- [ ] Add `PaginatedResponse` interface
- [ ] Create `getEntityPaginated` function
- [ ] Add `unwrapResponse` helper
- [ ] Update component to remove client-side filtering
- [ ] Change `sorter: (a, b) => ...` to `sorter: true`
- [ ] Remove `onFilter` functions
- [ ] Update `dataSource` to use raw data
- [ ] Test in browser

### Documentation

- [ ] Update API docstrings
- [ ] Add filter examples
- [ ] Update OpenAPI schema
- [ ] Document whitelisted fields

---

## Common Pitfalls

### 1. Forgetting to Unwrap Responses

**Problem:**

```typescript
const wbes = await WbEsService.getWbes(0, 1000);
wbes.forEach(...) // Error: forEach is not a function
```

**Solution:**

```typescript
const wbesRes = await WbEsService.getWbes(0, 1000);
const wbes = Array.isArray(wbesRes) ? wbesRes : wbesRes.items;
wbes.forEach(...) // Works!
```

### 2. Not Unpacking Tuple in API Layer

**Problem:**

```python
# Service returns tuple
return await service.get_entities(...)  # ResponseValidationError!
```

**Solution:**

```python
items, _ = await service.get_entities(...)
return items  # Works!
```

### 3. Client-Side Filtering on Server-Side Data

**Problem:**

```typescript
const filtered = useMemo(() => {
  return data.filter((item) => item.name.includes(search));
}, [data, search]);
```

**Solution:**

```typescript
// Remove useMemo - server handles filtering
// Just use raw data
dataSource={data || []}
```

---

## Performance Considerations

### Database Indexes

Always add indexes on filtered columns:

```python
# In Alembic migration
op.create_index('ix_entities_status', 'entities', ['status'])
op.create_index('ix_entities_name', 'entities', ['name'])
```

### Query Optimization

- Use single query for data + count (subquery)
- Apply filters before counting
- Use LIMIT/OFFSET for pagination
- Avoid N+1 queries with joins

### Caching

Consider caching for:

- Frequently accessed filter options
- Slow aggregation queries
- Static reference data

---

## Security

### SQL Injection Prevention

✅ **Safe:** Using FilterParser with SQLAlchemy ORM

```python
FilterParser.build_sqlalchemy_filters(Entity, filters, allowed_fields)
# Uses parameterized queries
```

❌ **Unsafe:** Raw SQL concatenation

```python
f"SELECT * FROM entities WHERE {filter_field} = '{filter_value}'"
# NEVER DO THIS!
```

### Field Whitelisting

Always define `allowed_fields`:

```python
allowed_fields = ["status", "code", "name"]
FilterParser.build_sqlalchemy_filters(
    Entity, parsed_filters, allowed_fields=allowed_fields
)
# Raises ValueError if invalid field
```

---

## Related Documentation

- [Coding Standards](../02-architecture/coding-standards.md)
- [FilterParser Implementation](../../backend/app/core/filtering.py)
- [PaginatedResponse Schema](../../backend/app/models/schemas/common.py)
- [Phase 2 Implementation](../03-project-plan/iterations/2026-01-08-table-harmonization/phase2/)

---

**Document Owner:** Backend Team  
**Review Cycle:** Quarterly  
**Last Review:** 2026-01-08
