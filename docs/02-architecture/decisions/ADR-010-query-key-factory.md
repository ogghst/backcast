# ADR-010: Query Key Factory Pattern

**Status:** Accepted
**Date:** 2026-01-19
**Context:** Frontend State Management
**Deciders:** Frontend Team

---

## Context

The application uses TanStack Query (React Query) for server state management. React Query requires **query keys** to identify, cache, and invalidate data. Initially, query keys were constructed manually throughout the codebase:

```typescript
// Manual query keys (old pattern)
queryKey: ["cost-element", id]
queryKey: ["projects"]
queryKey: ["users", "me"]
```

This approach led to several problems:

1. **Cache Inconsistency**: Manual keys didn't match between queries and invalidations, causing stale data
2. **Time Machine Context**: Versioned entities require `{ branch, asOf, mode }` context, which was often forgotten
3. **Type Safety**: Manual string arrays had no type checking
4. **Refactoring Risk**: Changing key structures required finding all manual instances
5. **Developer Confusion**: No single source of truth for key patterns

### Specific Incidents

**Incident #1: OverviewTab Cache Bug**
- **Problem**: Cost element edits didn't refresh data in UI
- **Root Cause**: Manual key `["cost_element", id]` didn't match factory pattern `["cost-elements", "detail", id, context]`
- **Impact**: Users saw stale data after edits, requiring manual page refresh

**Incident #2: Time Machine Cross-Context Pollution**
- **Problem**: Switching to historical view showed current data
- **Root Cause**: Query keys missing `{ asOf }` context parameter
- **Impact**: Historical analysis showed incorrect data

---

## Decision

**Adopt a centralized query key factory pattern with strict enforcement.**

### Implementation

1. **Centralized Factory**: All query keys defined in `src/api/queryKeys.ts`

```typescript
export const queryKeys = {
  costElements: {
    all: ["cost-elements", "all"] as const,
    detail: (id: string, context?: TimeMachineContext) =>
      ["cost-elements", "detail", id, context] as const,
    breadcrumb: (id: string) => ["cost-elements", id, "breadcrumb"] as const,
  },
  // ... other entities
};
```

2. **Context Parameters**: Versioned entities include Time Machine context

```typescript
queryKeys.costElements.detail(id, { branch: "main", asOf: "2024-01-01" })
```

3. **ESLint Rule**: Custom rule prevents manual key construction

```typescript
// Rule: custom-rules/no-manual-query-keys
// Error: "Use query key factory instead of manual array construction"
queryKey: ["pattern"]  // ❌ ESLint error
queryKey: queryKeys.entity.method()  // ✅ Allowed
```

4. **Dependent Invalidation**: Mutations invalidate all related queries

```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: queryKeys.costElements.all });
  queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });
}
```

### Scope

**Versioned Entities** (require context):
- Cost Elements
- Work Breakdown Elements (WBEs)
- Forecasts
- Projects
- Schedule Baselines
- Change Orders

**Non-Versioned Entities** (no context):
- Users
- Departments
- Cost Element Types

**Exceptions** (may use manual keys):
- `useCrud.ts` (generic hook factory)
- `useEntityHistory.ts` (generic history hook)

---

## Alternatives Considered

### Alternative 1: Distributed Manual Keys (Status Quo)
**Pros:**
- No upfront migration cost
- Flexible for one-off patterns

**Cons:**
- Cache inconsistency bugs (Incidents #1, #2)
- No type safety
- Difficult to refactor
- **Rejected**: Ongoing maintenance cost too high

### Alternative 2: Runtime Key Registry
**Pros:**
- Dynamic key registration
- No compilation step

**Cons:**
- Runtime overhead
- No type safety
- Harder to debug
- **Rejected**: Performance and safety trade-offs unacceptable

### Alternative 3: Code Generator
**Pros:**
- Automatic from OpenAPI spec
- Always in sync with backend

**Cons:**
- Complex build pipeline
- Can't handle context parameters easily
- Less flexible for custom keys
- **Rejected**: Over-engineering for this use case

---

## Consequences

### Positive

1. **Cache Consistency**: All queries and invalidations use identical keys
2. **Type Safety**: Factory provides TypeScript autocomplete and type checking
3. **Developer Experience**: Single pattern to learn and follow
4. **Refactoring Safety**: Changing key structure updates all usages
5. **Context Isolation**: Time Machine context properly propagated
6. **Enforcement**: ESLint rule prevents violations

### Negative

1. **Migration Cost**: ~13 files required migration (completed in iteration 2026-01-19)
2. **Learning Curve**: New developers must learn factory pattern
3. **Boilerplate**: Adding new keys requires updating factory

### Mitigation

- **Documentation**: Comprehensive examples in `docs/02-architecture/frontend/contexts/02-state-data.md`
- **ESLint Rule**: Catches violations at compile time
- **Generic Hooks**: `useCrud` and `useEntityHistory` documented for appropriate use cases

---

## Implementation Status

**Completed** (2026-01-19):

- ✅ Centralized factory implemented in `src/api/queryKeys.ts`
- ✅ All 13 files migrated to factory pattern
- ✅ 5 cache bugs fixed in component-level invalidations
- ✅ Generic hooks documented with clear guidelines
- ✅ ESLint rule `custom-rules/no-manual-query-keys` implemented
- ✅ Zero manual query keys in production code
- ✅ All 211 tests passing with zero regressions

**Metrics:**

- **Files Migrated**: 13
- **Cache Bugs Fixed**: 5
- **Test Pass Rate**: 100% (211/211)
- **TypeScript Errors**: 0
- **ESLint Errors (src/)**: 0

---

## References

- **Implementation**: `frontend/src/api/queryKeys.ts`
- **State Management Architecture**: `docs/02-architecture/frontend/contexts/02-state-data.md`
- **Coding Standards**: `docs/02-architecture/coding-standards.md` (Section 4.4.1)
- **Iteration Report**: `docs/03-project-plan/iterations/2026-01-19-complete-query-key-factory/`
- **Related ADRs**:
  - [ADR-005: Bitemporal Versioning](./ADR-005-bitemporal-versioning.md) (Time Machine context)
  - [ADR-004: Quality Standards](./ADR-004-quality-standards.md) (Testing requirements)

---

## Related Decisions

This ADR complements:
- **ADR-005**: Provides query key structure for bitemporal entities
- **ADR-004**: Establishes testing requirements for cache behavior
- **Frontend Architecture**: State management strategy (TanStack Query)
