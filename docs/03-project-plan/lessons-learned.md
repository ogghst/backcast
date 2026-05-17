# Lessons Learned

**Last Updated:** 2026-05-17

This document captures key learnings from project iterations to improve future development practices.

---

## Table of Contents

- [Backend Development](#backend-development)
- [Frontend Development](#frontend-development)
- [Testing](#testing)
- [Architecture & Design](#architecture--design)
- [Process & Workflow](#process--workflow)

---

## Backend Development

### Delegation Pattern for High-Risk Migrations

**Iteration:** Unified RBAC Refactoring (2026-05-10)

**Problem:** Replacing all route-level RBAC checkers in a big-bang change is high-risk and could break all 17 route files simultaneously.

**Learning:** Using a delegation pattern (existing checkers delegate to new service first, fallback to legacy) preserves backward compatibility while achieving the same effect with zero-risk rollout.

**Solution:**

```python
# RoleChecker.__call__ delegates to unified first
try:
    set_unified_rbac_session(session)
    unified_service = get_unified_rbac_service()
    # ... unified check ...
except Exception:
    logger.warning("Unified RBAC check failed, falling back to legacy")
    # Fallback: try legacy RBAC service
```

**Best Practice:** For service-level migrations, prefer delegation over replacement. Add logging for fallback triggers to monitor production health before removing legacy code.

---

### N+1 Query Pattern in API Enrichment

**Iteration:** Unified RBAC Refactoring (2026-05-10)

**Problem:** The `list_assignments` endpoint executed individual DB queries per assignment to enrich role names (N+1 pattern).

**Learning:** When enriching a list response with related data, batch the lookups using a single query with `IN` clause instead of individual queries per item.

**Solution:**

```python
# Collect unique IDs, single batch query, map results
role_ids = {a.role_id for a in assignments}
role_result = await session.execute(
    select(RBACRole.id, RBACRole.name).where(RBACRole.id.in_(role_ids))
)
role_name_map = {row[0]: row[1] for row in role_result.all()}
```

**Best Practice:** After writing any list endpoint with enrichment, verify the query pattern is batched, not per-item.

---

### Type Casting in Generic Filters

**Iteration:** E2E Test Stabilization (2026-01-09)

**Problem:** PostgreSQL strictly enforces type matching. Comparing `integer = varchar` causes SQL errors.

**Learning:** When building generic filtering systems, always validate and cast filter values against the database schema types.

**Solution:**

```python
# Inspect SQLAlchemy column metadata
col_type = column.type.python_type

# Cast values appropriately
if col_type is int:
    casted_values = [int(v) for v in values]
elif col_type is bool:
    casted_values = [parse_bool(v) for v in values]
```

**Best Practice:** Use SQLAlchemy's type system to automatically handle type conversions in generic code.

---

### API Response Consistency

**Iteration:** Server-Side Filtering (2026-01-08)

**Problem:** Some endpoints returned arrays, others returned `PaginatedResponse`, causing frontend confusion.

**Learning:** Consistent API response structures are critical for maintainability.

**Solution:** Standardize all list endpoints to return `PaginatedResponse`:

```python
{
  "items": [...],
  "total": 100,
  "page": 1,
  "per_page": 20
}
```

**Best Practice:** Document response formats in OpenAPI schema and enforce consistency through code generation.

---

## Frontend Development

### Search Parameter Integration

**Iteration:** E2E Test Stabilization (2026-01-09)

**Problem:** Search UI existed but search term wasn't being passed to API calls.

**Learning:** When adding server-side features, verify the entire data flow from UI → Hook → API → Backend.

**Solution:** Ensure all query parameters from `useTableParams` are included in API calls:

```typescript
const queryParams = {
  pagination: tableParams.pagination,
  sortField: tableParams.sortField,
  sortOrder: tableParams.sortOrder,
  filters: tableParams.filters,
  search: tableParams.search, // Don't forget this!
  branch: currentBranch,
};
```

**Best Practice:** Create integration tests that verify UI actions trigger correct API calls.

---

### Type Safety in Generic Hooks

**Iteration:** E2E Test Stabilization (2026-01-09)

**Problem:** `useTableParams` and filter types use `Record<string, any>`, losing type safety.

**Learning:** Generic hooks should accept type parameters to maintain compile-time safety.

**Recommendation:** Refactor to:

```typescript
export const useTableParams<T extends object>() => {
  // Type-safe filters based on T
}
```

**Best Practice:** Use TypeScript generics extensively in reusable hooks and utilities.

---

## Testing

### E2E Test Pagination Awareness

**Iteration:** E2E Test Stabilization (2026-01-09)

**Problem:** Tests assumed newly created items would appear on page 1, but pagination pushed them to later pages.

**Learning:** E2E tests must be resilient to data pollution from concurrent/previous test runs.

**Solution:** Use search to isolate test data before asserting visibility:

```typescript
// Instead of assuming item is on page 1
await expect(page.locator(`text=${itemName}`)).toBeVisible();

// Use search to find it
await searchInput.fill(itemName);
await waitForSearchResponse();
await expect(page.locator(`text=${itemName}`)).toBeVisible();
```

**Best Practice:** Design tests to be independent of database state and pagination.

---

### Dropdown Stability in E2E Tests

**Iteration:** E2E Test Stabilization (2026-01-09)

**Problem:** Clicking dropdown items immediately after opening caused "element detached" errors.

**Learning:** Ant Design dropdowns need time to render and attach to DOM.

**Solution:**

```typescript
await page.click("#dropdown-trigger");
await page.waitForSelector(".ant-select-dropdown", { state: "visible" });
await page.waitForTimeout(300); // Small delay for stability
await page.click(".ant-select-item");
```

**Best Practice:** Always wait for dropdowns/modals to be fully rendered before interacting.

---

### Test Data Isolation

**Iteration:** E2E Test Stabilization (2026-01-09)

**Problem:** E2E tests share database state, causing occasional flakiness.

**Learning:** Shared state between tests is a major source of flakiness.

**Recommendation:** Implement one of:

1. Database transactions with rollback after each test
2. Test data cleanup hooks
3. Separate test databases per worker

**Best Practice:** Design tests to be fully isolated and order-independent.

---

## Architecture & Design

### Dual Config File Divergence Prevention

**Iteration:** RBAC Seeding Fix (2026-05-10)

**Problem:** Two JSON files (`seed/rbac_roles.json` for database seeding and `config/rbac.json` for runtime RBAC policy) diverged silently over multiple iterations. Role names, permission sets, and even entire roles differed between the files, causing `seed_all()` to produce a database state that did not match what the runtime RBAC service expected.

**Learning:** When two configuration files serve overlapping purposes (seeding vs. runtime), divergence is inevitable without an automated enforcement mechanism. Manual synchronization is insufficient because each file is edited independently during different iterations.

**Solution:**

- Synchronized both files to contain structurally identical role and permission definitions
- Added a CI-sync test (`test_rbac_config_sync.py`) that parses both JSON files and asserts identical role names and permission sets, failing the build if they diverge

```python
# CI-sync test prevents future divergence
def test_same_permissions_per_role():
    for role_name in seed_roles:
        assert sorted(seed_roles[role_name]["permissions"]) == sorted(config_roles[role_name]["permissions"])
```

**Best Practice:** When two config files share structural data, add a CI-sync test immediately -- not after the first divergence incident. The test should compare the structural content (not comments or descriptions) and run on every PR.

---

### Generic vs. Specific Implementations

**Iteration:** Multiple iterations

**Learning:** Generic implementations (like `FilterParser`) need robust error handling and type safety.

**Best Practice:**

- Provide clear error messages for edge cases
- Use type introspection when possible
- Fallback gracefully when types can't be determined
- Document supported types and limitations

---

### Server-Side vs. Client-Side Processing

**Iteration:** Server-Side Filtering (2026-01-08)

**Learning:** Moving filtering/sorting/pagination to server improves performance but requires careful coordination.

**Checklist for Server-Side Features:**

- [ ] Backend implements feature correctly
- [ ] Frontend passes parameters correctly
- [ ] API response format is documented
- [ ] Frontend handles response correctly
- [ ] Tests verify end-to-end flow
- [ ] Error handling is robust

**Best Practice:** Implement server-side features incrementally, testing each layer.

---

## Architecture & Design (continued)

### Sequential Tool Execution as Default

**Iteration:** Sequential Tool Execution (2026-05-17)

**Problem:** LangGraph's default `ToolNode` executes multiple tool calls via `asyncio.gather`, which causes DB pool exhaustion (31 leaked connections observed) and race conditions (TOCTOU in revenue allocation validation) when tools share an async database session.

**Learning:** When tool functions share mutable state (database sessions, file handles, external connections), parallel execution is unsafe. Sequential execution must be enforced at the dispatch layer, not just via model hints.

**Solution:**

Two-layer defense-in-depth:
1. **Model hint:** `parallel_tool_calls=False` in `bind_tools` -- tells the LLM to emit one tool call at a time
2. **Dispatch enforcement:** `SequentialToolNode` overrides `_afunc` to use a for-loop instead of `asyncio.gather`

```python
# SequentialToolNode._afunc replaces asyncio.gather with for-loop
outputs = []
for call, tool_runtime in zip(tool_calls, tool_runtimes, strict=False):
    result = await self._arun_one(call, input_type, tool_runtime)
    outputs.append(result)
```

For third-party factories that hardcode `ToolNode` instantiation (e.g., `langchain_create_agent`), a global monkey-patch with idempotent guard ensures all instances use sequential execution.

**Best Practice:** Default to sequential execution for any tool system that shares mutable state. Use defense-in-depth: a model hint as the first layer, dispatch enforcement as the second. Log a WARNING when the enforcement layer catches a multi-call batch (canary for model hint failure).

---

### Testing Code with Module-Level Side Effects

**Iteration:** Sequential Tool Execution (2026-05-17)

**Problem:** A test using `caplog` to assert WARNING logs passed in isolation but failed when `agent_service.py` was imported first. The module-level import triggered `patch_tool_node_for_sequential_execution()` which emitted an INFO log, contaminating the `caplog` assertion count.

**Learning:** `caplog` captures ALL log records at the configured level from ALL loggers during the test. When the code under test has module-level side effects (logging, monkey-patching, global state), `caplog` assertions become fragile across test boundaries.

**Solution:**

Prefer `unittest.mock.patch` over `caplog` when testing code with module-level side effects:

```python
# Instead of caplog (captures everything):
# with caplog.at_level(logging.WARNING):
#     ...
# assert "expected message" in caplog.text

# Use mock.patch (isolated to specific logger):
with unittest.mock.patch("app.ai.tools.sequential_tool_node.logger") as mock_logger:
    # ... exercise code ...
    mock_logger.warning.assert_called_once_with(
        "SequentialToolNode: executing %d tool calls sequentially ...", ...
    )
```

**Best Practice:** When module-level side effects exist (common with monkey-patches, global state, or import-time initialization), use `unittest.mock.patch` on the specific logger to isolate test assertions. Reserve `caplog` for testing pure functions without import-time side effects.

---

## Process & Workflow

### PDCA Documentation

**Iteration:** All iterations

**Learning:** Structured PDCA documentation prevents context loss and improves iteration quality.

**Best Practice:**

- **PLAN:** Analyze problem, define approach
- **DO:** Document implementation details
- **CHECK:** Verify results, capture learnings
- **ACT:** Update debt register, plan next steps

**Benefit:** Future developers can understand decisions and avoid repeating mistakes.

---

### Test-Driven Debugging

**Iteration:** E2E Test Stabilization (2026-01-09)

**Learning:** Running tests after each change provides immediate feedback and prevents regressions.

**Best Practice:**

1. Reproduce issue with failing test
2. Make minimal fix
3. Run tests to verify
4. Refactor if needed
5. Run tests again

**Benefit:** Confidence in changes, faster debugging cycles.

---

### Legacy Code Cleanup

**Iteration:** E2E Test Stabilization (2026-01-09)

**Learning:** Removing duplicate/outdated tests improves maintainability.

**Best Practice:**

- Regularly review test suite for duplication
- Remove tests that no longer add value
- Consolidate similar tests
- Keep test count manageable

**Benefit:** Faster test runs, easier maintenance.

---

## Summary Statistics

| Category              | Lessons | Iterations |
| --------------------- | ------- | ---------- |
| Backend Development   | 4       | 3          |
| Frontend Development  | 2       | 2          |
| Testing               | 4       | 2          |
| Architecture & Design | 5       | 5          |
| Process & Workflow    | 3       | 4          |

**Total Lessons Captured:** 18
**Most Common Category:** Architecture & Design

---

## Next Review

**Date:** 2026-06-01
**Focus:** Review new lessons from upcoming iterations
