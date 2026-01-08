# ADR-008: Server-Side Filtering, Search, and Sorting

**Status:** Accepted  
**Date:** 2026-01-08  
**Context:** [Phase 2 Implementation](../../03-project-plan/iterations/2026-01-08-table-harmonization/phase2/)

---

## Context and Problem Statement

As the dataset grows beyond 1,000 records, client-side filtering and sorting in the frontend (the "Phase 1" approach) become performance bottlenecks. It causes high memory usage, slow UI response times, and prevents "true" global search because the frontend only sees the subset of data it has loaded.

We needed a scalable solution to handle thousands (or millions) of records while maintaining the high-quality user experience established in Phase 1.

## Decision Research

1. **Client-side filtering**: Fast for small datasets, but doesn't scale. Requires loading all data upfront.
2. **Post-processing in Backend**: Better, but still inefficient as it fetches everything from the DB.
3. **Database-level filtering (WHERE/ORDER BY)**: Most scalable. Leverages indexes.
4. **GraphQL**: Flexible, but requires significant setup and changes to existing REST endpoints.

## Decision Outcome

We decided to implement **Database-level filtering, search, and sorting** integrated into our existing REST API via a generic `FilterParser` utility.

### Key Implementation Details

1. **Backend Integration**:

   - Created a generic `FilterParser` in `app/core/filtering.py` to convert URL query parameters into SQLAlchemy `WHERE` clauses.
   - Enhanced Service layer to support search (code/name ILIKE), multiple filters (IN clauses), and dynamic sorting.
   - Standardized API response format using `PaginatedResponse[T]` schema.

2. **Frontend Integration**:

   - Updated `useTableParams` and TanStack Query hooks to pass pagination, filter, and sort parameters to the backend.
   - Implemented response unwrapping to handle the new `{items, total}` format while keeping the UI components clean.

3. **Performance Optimization**:

   - Added database indexes on frequently filtered/searched columns (`status`, `name`, `code`, `level`).
   - Implemented single-query execution for both data and total count (via subqueries/CTE).

4. **Security**:
   - Implemented **Field Whitelisting** to prevent unauthorized filtering on internal or sensitive columns.
   - Secured against SQL injection by using SQLAlchemy's parameterized query engine exclusively.

## Consequences

### Positive

- **Scalability**: Handles unlimited record counts efficiently.
- **Global Search**: Search works across the entire database, not just the currently loaded records.
- **Reduced Client Load**: Frontend only processes one page of data at a time.
- **Consistency**: The `FilterParser` provides a standard way to implement filtering across all entities.

### Negative

- **API Complexity**: Response format changed from simple array to paginated object.
- **Frontend Complexity**: Components must handle pagination and server-side table states.
- **Boilerplate**: Each service needs to explicitly whitelist and apply filters.

## Pros and Cons of the Options

### Option 1: Database-level Filtering (Chosen)

- **Pros**: Most scalable, prevents SQL injection, minimal network overhead.
- **Cons**: Requires database indexes for performance.

### Option 2: Server-side post-processing

- **Pros**: Easier to implement (no SQL knowledge needed in parser).
- **Cons**: Still fetches all records from DB to memory; doesn't solve DB-to-Backend bottleneck.

## References

- [API Response Patterns](../cross-cutting/api-response-patterns.md)
- [Coding Standards](../coding-standards.md)
- [Phase 2 Final Summary](../../03-project-plan/iterations/2026-01-08-table-harmonization/phase2/FINAL-SUMMARY.md)
