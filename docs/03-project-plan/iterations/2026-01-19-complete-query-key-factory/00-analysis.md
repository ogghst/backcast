# Analysis: Complete Query Key Factory Adoption

**Created:** 2026-01-19
**Request:** Complete query key factory adoption across all frontend hooks

---

## 1. Requirements Clarification

### User Intent

The previous iteration (2026-01-18-refactor-tanstack-query) successfully migrated core versioned entity hooks to use the centralized `queryKeys` factory. However, a comprehensive audit reveals additional hooks, components, and utility functions that still use manual query key arrays instead of the factory pattern. The goal is to achieve **100% adoption** of the query key factory across the entire frontend codebase.

### Functional Requirements

1. **Identify ALL remaining manual query key usage**: Search the entire frontend codebase for patterns like `queryKey: ["entity-name", ...]`
2. **Classify findings by type**: Distinguish between versioned entities, non-versioned entities, derived/computed queries, and one-off queries
3. **Determine migration scope**: Decide which manual keys should be migrated to the factory vs. which are legitimately one-off
4. **Ensure consistency**: All query invalidations should use factory-generated keys
5. **Update documentation**: Document any new query key patterns added to the factory

### Non-Functional Requirements

1. **Type Safety**: Maintain TypeScript strict mode compliance
2. **Cache Coherency**: Ensure query key changes don't break cache invalidation
3. **Test Coverage**: All changes must maintain 80%+ test coverage
4. **Zero Downtime**: Changes should not introduce breaking changes to API calls

### Constraints

1. **Time Machine Context**: Versioned entity query keys MUST include `{ branch, asOf, mode }` context
2. **Existing Factory**: Must extend `/home/nicola/dev/backcast_evs/frontend/src/api/queryKeys.ts`, not replace it
3. **Backward Compatibility**: Cannot change query key structures for already-migrated hooks (would invalidate existing caches)

---

## 2. Context Discovery

### 2.1 Product Scope

- **Relevant User Stories**: N/A (technical debt iteration)
- **Business Requirements**: Improve code maintainability, prevent cache-related bugs, enforce architectural standards

### 2.2 Architecture Context

**Bounded Contexts Involved:**
- All frontend bounded contexts (projects, WBEs, cost elements, forecasts, change orders, etc.)

**Existing Patterns:**
- Centralized query key factory at `/home/nicola/dev/backcast_evs/frontend/src/api/queryKeys.ts`
- Version-aware hook factory at `/home/nicola/dev/backcast_evs/frontend/src/hooks/useVersionedCrud.ts`
- Time Machine context injection via `useTimeMachineParams()`

**Architectural Constraints:**
- Rule from `docs/02-architecture/frontend/contexts/02-state-data.md`:
  - "We strictly enforce a centralized Query Key factory"
  - "For branchable or temporal entities, the Query Key **MUST** include context parameters"
  - "Mutations must trigger invalidation not just for the modified entity but for **all dependent data**"

### 2.3 Codebase Analysis

#### Successfully Migrated (Previous Iteration)

The following hooks now use the `queryKeys` factory correctly:

1. **`/home/nicola/dev/backcast_evs/frontend/src/features/projects/api/useProjects.ts`**
   - Uses: `queryKeys.projects.list()`, `queryKeys.projects.detail()`, `queryKeys.projects.branches()`

2. **`/home/nicola/dev/backcast_evs/frontend/src/features/wbes/api/useWBEs.ts`**
   - Uses: `queryKeys.wbes.list()`, `queryKeys.wbes.detail()`, `queryKeys.wbes.breadcrumb()`

3. **`/home/nicola/dev/backcast_evs/frontend/src/features/cost-elements/api/useCostElements.ts`**
   - Uses: `queryKeys.costElements.list()`, `queryKeys.costElements.detail()`, `queryKeys.costElements.breadcrumb()`

4. **`/home/nicola/dev/backcast_evs/frontend/src/features/cost-registration/api/useCostRegistrations.ts`**
   - Uses: `queryKeys.costRegistrations.list()`, `queryKeys.costRegistrations.detail()`, `queryKeys.costRegistrations.budgetStatus()`, `queryKeys.costRegistrations.history()`

5. **`/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/api/useChangeOrders.ts`**
   - Uses: `queryKeys.changeOrders.list()`, `queryKeys.changeOrders.detail()`

6. **`/home/nicola/dev/backcast_evs/frontend/src/features/forecasts/api/useForecasts.ts`**
   - Uses: `queryKeys.forecasts.list()`, `queryKeys.forecasts.detail()`, `queryKeys.forecasts.comparison()`, `queryKeys.forecasts.byCostElement()`

7. **`/home/nicola/dev/backcast_evs/frontend/src/features/schedule-baselines/api/useScheduleBaselines.ts`**
   - Uses: `queryKeys.scheduleBaselines.list()`, `queryKeys.scheduleBaselines.detail()`, `queryKeys.scheduleBaselines.pv()`, `queryKeys.scheduleBaselines.history()`

8. **`/home/nicola/dev/backcast_evs/frontend/src/features/schedule-baselines/api/useCostElementScheduleBaseline.ts`**
   - Uses: `queryKeys.scheduleBaselines.byCostElement()`

#### Remaining Manual Query Key Usage

**Priority 1: Core Infrastructure Hooks (High Impact)**

1. **`/home/nicola/dev/backcast_evs/frontend/src/hooks/useAuth.ts`**
   - Line 29: `queryKey: ["currentUser"]`
   - Line 56: `queryKey: ["currentUser"]` (invalidation)
   - **Type**: Non-versioned entity (authentication)
   - **Recommendation**: Add `queryKeys.users.me` to factory

2. **`/home/nicola/dev/backcast_evs/frontend/src/contexts/TimeMachineContext.tsx`**
   - Line 77-80: Manual invalidation keys `["projects"]`, `["wbes"]`, `["cost-elements"]`, `["cost-element-types"]`
   - **Type**: Global invalidation handler
   - **Recommendation**: Use factory's `all` keys for proper invalidation

3. **`/home/nicola/dev/backcast_evs/frontend/src/hooks/useCrud.ts`**
   - Line 70: `queryKey: [queryKey, "list", filters]`
   - Line 87: `queryKey: [queryKey, "detail", id]`
   - Lines 114-116: Manual invalidation with `[key]`
   - **Type**: Generic factory for non-versioned entities
   - **Recommendation**: Keep as-is (intended for simple CRUD), but document usage guidelines

4. **`/home/nicola/dev/backcast_evs/frontend/src/hooks/useEntityHistory.ts`**
   - Line 43: `queryKey: [resource, entityId, "history"]`
   - **Type**: Generic history hook for any entity
   - **Recommendation**: Use factory's history keys if available, or keep generic for flexibility

**Priority 2: Specialized Hooks (Medium Impact)**

5. **`/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/api/useImpactAnalysis.ts`**
   - Line 27: `queryKey: ["impact-analysis", changeOrderId, branchName, { asOf }]`
   - **Type**: Derived/computed query (change order impact)
   - **Recommendation**: Add `queryKeys.changeOrders.impact()` to factory (already defined!)

6. **`/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/hooks/useWorkflowActions.ts`**
   - Line 46: `queryKey: ["change-orders"]`
   - Line 47: `queryKey: ["branches"]` (should use factory)
   - Line 56: `queryKey: ["change-orders"]`
   - Line 57: `queryKey: ["branches"]` (should use factory)
   - **Type**: Workflow mutation hook
   - **Recommendation**: Use `queryKeys.changeOrders.all` and `queryKeys.projects.branches()`

**Priority 3: Component-Level Invalidation (Low Impact)**

7. **`/home/nicola/dev/backcast_evs/frontend/src/pages/cost-elements/tabs/OverviewTab.tsx`**
   - Line 38: `queryKey: ["cost_element", costElement.cost_element_id]` (inconsistent with factory)
   - Line 41: `queryKey: ["cost_element_breadcrumb", costElement.cost_element_id]` (should use factory)
   - Line 44: `queryKey: ["budget_status", costElement.cost_element_id]` (should use factory)
   - Line 47: `queryKey: ["forecasts"]` (should use factory)
   - **Type**: Component-level mutation callback
   - **Recommendation**: Use factory keys: `queryKeys.costElements.detail()`, `queryKeys.costElements.breadcrumb()`, `queryKeys.costRegistrations.budgetStatus()`, `queryKeys.forecasts.all`

8. **`/home/nicola/dev/backcast_evs/frontend/src/pages/cost-elements/tabs/ScheduleBaselinesTab.tsx`**
   - Lines 58, 65, 72: `queryKey: ["cost_element_schedule_baseline"]`
   - **Type**: Component-level mutation callback
   - **Recommendation**: Use `queryKeys.scheduleBaselines.byCostElement()`

9. **`/home/nicola/dev/backcast_evs/frontend/src/pages/cost-elements/tabs/ForecastsTab.tsx`**
   - Lines 61, 70: `queryKey: ["cost_element_forecast", costElement.cost_element_id]`
   - **Type**: Component-level mutation callback
   - **Recommendation**: Use `queryKeys.forecasts.byCostElement()`

10. **`/home/nicola/dev/backcast_evs/frontend/src/pages/cost-elements/tabs/CostRegistrationsTab.tsx`**
    - Lines 87, 97, 107: `queryKey: ["budget_status", costElement.cost_element_id]`
    - **Type**: Component-level mutation callback
    - **Recommendation**: Use `queryKeys.costRegistrations.budgetStatus()`

11. **`/home/nicola/dev/backcast_evs/frontend/src/pages/projects/change-orders/ChangeOrderUnifiedPage.tsx`**
    - Line 168: `queryKey: ["change-orders"]`
    - **Type**: Component-level mutation callback
    - **Recommendation**: Use `queryKeys.changeOrders.all`

#### Summary of Findings

| Category | Count | Files | Migration Priority |
|----------|-------|-------|-------------------|
| Core Infrastructure | 4 | useAuth, TimeMachineContext, useCrud, useEntityHistory | High |
| Specialized Hooks | 2 | useImpactAnalysis, useWorkflowActions | Medium |
| Component-Level | 5 | OverviewTab, ScheduleBaselinesTab, ForecastsTab, CostRegistrationsTab, ChangeOrderUnifiedPage | Low |
| **Total** | **11** | | |

---

## 3. Solution Options

### Option 1: Comprehensive Migration (Recommended)

Migrate ALL identified manual query keys to use the factory pattern.

**Scope:**

1. **Add missing factory keys** to `/home/nicola/dev/backcast_evs/frontend/src/api/queryKeys.ts`:
   - `queryKeys.users.me` for current user query
   - Ensure `queryKeys.changeOrders.impact()` exists (already defined!)

2. **Migrate core infrastructure**:
   - Update `useAuth` to use `queryKeys.users.me`
   - Update `TimeMachineContext` to use factory `all` keys
   - Document `useCrud` usage guidelines (keep generic)

3. **Migrate specialized hooks**:
   - Update `useImpactAnalysis` to use `queryKeys.changeOrders.impact()`
   - Update `useWorkflowActions` to use `queryKeys.changeOrders.all` and `queryKeys.projects.branches()`

4. **Migrate component-level invalidations**:
   - Update all tab components to use factory keys in mutation callbacks

**Implementation Details:**

```typescript
// 1. Add to queryKeys.ts
users: {
  all: null as QueryKey,
  list: null as QueryKey,
  detail: (id: string) => ["users", "detail", id] as const,
  me: null as QueryKey,  // ADD THIS
},
```

```typescript
// 2. Update useAuth.ts
useQuery<UserPublic>({
  queryKey: queryKeys.users.me,  // CHANGED FROM ["currentUser"]
  queryFn: getCurrentUser,
  // ...
})

// In login mutation
queryClient.invalidateQueries({ queryKey: queryKeys.users.me });  // CHANGED
```

```typescript
// 3. Update TimeMachineContext.tsx
const invalidateQueries = useCallback(() => {
  queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
  queryClient.invalidateQueries({ queryKey: queryKeys.wbes.all });
  queryClient.invalidateQueries({ queryKey: queryKeys.costElements.all });
  queryClient.invalidateQueries({ queryKey: queryKeys.costElementTypes.all });
}, [queryClient]);
```

```typescript
// 4. Update component invalidations (example from OverviewTab)
queryClient.invalidateQueries({
  queryKey: queryKeys.costElements.detail(costElement.cost_element_id, { branch, asOf })
});
queryClient.invalidateQueries({
  queryKey: queryKeys.costElements.breadcrumb(costElement.cost_element_id)
});
queryClient.invalidateQueries({
  queryKey: queryKeys.costRegistrations.budgetStatus(costElement.cost_element_id, { asOf })
});
queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });
```

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| **Pros** | 100% factory adoption, eliminates all inconsistencies, prevents future cache bugs, aligns with architecture standards |
| **Cons** | Moderate effort (11 files), requires careful testing of invalidation cascades |
| **Complexity** | Medium (mostly find-and-replace with context parameter fixes) |
| **Maintainability** | Excellent (single source of truth for all query keys) |
| **Performance** | No impact (same cache behavior, just consistent key generation) |

---

### Option 2: Tiered Migration (Infrastructure Only)

Migrate only core infrastructure and specialized hooks, leave component-level manual keys for future refactors.

**Scope:**
- Migrate items 1-6 from the findings above (infrastructure + specialized hooks)
- Leave component-level invalidations (items 7-11) as-is
- Add TODO comments in component files for future cleanup

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| **Pros** | Lower effort (6 files vs 11), fixes highest-impact issues, provides factory examples for components |
| **Cons** | Incomplete adoption, component-level bugs still possible, technical debt remains |
| **Complexity** | Low-Medium |
| **Maintainability** | Good (core is consistent, but components still inconsistent) |
| **Performance** | No impact |

---

### Option 3: Documentation + Linting Rule

Keep existing code, add documentation, and implement an ESLint rule to enforce factory usage for NEW code.

**Scope:**
- Document `useCrud` vs `queryKeys` factory usage guidelines
- Add ESLint rule: `no-manual-query-keys` (custom rule to detect `queryKey: ["pattern"]`)
- Allow existing manual keys (grandfather clause)
- Enforce factory usage only for new code

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| **Pros** | Zero refactoring risk, prevents future violations, minimal effort |
| **Cons** | Doesn't fix existing inconsistencies, cache bugs remain, two patterns in codebase |
| **Complexity** | Low (one-time lint rule setup) |
| **Maintainability** | Fair (prevents new issues but old issues remain) |
| **Performance** | No impact |

---

## 4. Comparison Summary

| Criteria | Option 1 (Comprehensive) | Option 2 (Tiered) | Option 3 (Linting Only) |
|----------|-------------------------|-------------------|-------------------------|
| Development Effort | Medium (11 files, ~4-6 hours) | Low-Medium (6 files, ~2-3 hours) | Low (~2 hours for lint rule) |
| Long-term Maintainability | Excellent (100% consistent) | Good (core consistent, components inconsistent) | Fair (old code inconsistent, new code consistent) |
| Prevents Cache Bugs | Yes (all fixed) | Partially (core fixed, components still risky) | No (existing bugs remain) |
| Risk | Medium (more changes = more test coverage needed) | Low (fewer changes) | Very Low (no production code changes) |
| Alignment with Architecture | Full alignment | Partial alignment | Future alignment only |
| Best For | Production-ready codebase, high standards | Quick wins, risk-averse teams | Minimal refactoring budget |

---

## 5. Recommendation

**I recommend Option 1 (Comprehensive Migration)** because:

1. **Architectural Alignment**: The project has already established a pattern of strict factory enforcement (see previous iteration). Partial adoption would be inconsistent with this standard.

2. **Low Risk, High Value**: The changes are mostly find-and-replace operations with well-defined factory equivalents. The effort is moderate (~4-6 hours) but the value is permanent elimination of an entire class of cache-related bugs.

3. **Component-Level Bugs ARE Real Bugs**: The component-level manual invalidations (Priority 3) are not just "cosmetic" - they can cause real cache inconsistencies. For example:
   - `OverviewTab` line 38 uses `["cost_element", id]` but the factory uses `["cost-elements", "detail", id, context]` - **these won't match!**
   - This means updates to cost elements might not trigger cache invalidations properly.

4. **Completeness**: Achieving 100% factory adoption means future developers only need to learn one pattern. It eliminates cognitive load and reduces onboarding time.

5. **Test Coverage**: The existing test suite provides good coverage. Component-level changes can be verified with the existing E2E tests (`cost_element_forecast.spec.ts` already exists).

### Implementation Checklist

**Phase 1: Factory Extensions** (30 minutes)
- [ ] Add `queryKeys.users.me` to factory
- [ ] Verify `queryKeys.changeOrders.impact()` exists

**Phase 2: Core Infrastructure** (1.5 hours)
- [ ] Update `useAuth.ts` to use `queryKeys.users.me`
- [ ] Update `TimeMachineContext.tsx` to use factory `all` keys
- [ ] Document `useCrud.ts` usage guidelines (keep as-is)

**Phase 3: Specialized Hooks** (1 hour)
- [ ] Update `useImpactAnalysis.ts` to use `queryKeys.changeOrders.impact()`
- [ ] Update `useWorkflowActions.ts` to use factory keys

**Phase 4: Component-Level** (2 hours)
- [ ] Update `OverviewTab.tsx` invalidations
- [ ] Update `ScheduleBaselinesTab.tsx` invalidations
- [ ] Update `ForecastsTab.tsx` invalidations
- [ ] Update `CostRegistrationsTab.tsx` invalidations
- [ ] Update `ChangeOrderUnifiedPage.tsx` invalidations

**Phase 5: Testing** (30 minutes)
- [ ] Run unit tests: `npm test`
- [ ] Run E2E tests: `npm run e2e`
- [ ] Manual smoke test of cost element CRUD, change orders, forecasts

### Alternative Consideration

**If the team is risk-averse or time-constrained**, Option 2 (Tiered Migration) is acceptable:
- Migrate infrastructure + specialized hooks first
- Tag component files with `TODO: Migrate to queryKeys factory`
- Schedule component cleanup for a future iteration
- **However**, this should be explicitly documented as technical debt, not a permanent state.

---

## 6. Decision Questions

1. **Should we proceed with comprehensive migration (Option 1) or start with tiered (Option 2)?**
   - Consider: Team's risk tolerance, iteration timeline, test coverage confidence

2. **For `useEntityHistory.ts`, should we use factory history keys or keep it generic?**
   - Generic: `[resource, entityId, "history"]` works for any entity
   - Factory: Would need to call different factory methods based on resource type
   - **Recommendation**: Keep generic (it's a utility hook by design)

3. **Should we add an ESLint rule to prevent future manual query keys, even after migration?**
   - Pros: Prevents regressions, enforces standard
   - Cons: Custom rule maintenance overhead
   - **Recommendation**: Yes, after migration is complete

---

## 7. References

**Architecture Documentation:**
- `/home/nicola/dev/backcast_evs/docs/02-architecture/frontend/contexts/02-state-data.md` - Query key standards
- `/home/nicola/dev/backcast_evs/frontend/src/api/queryKeys.ts` - Current factory definitions

**Previous Work:**
- `/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-18-refactor-tanstack-query/00-analysis.md` - Previous migration analysis

**Implementation Files:**
- `/home/nicola/dev/backcast_evs/frontend/src/hooks/useVersionedCrud.ts` - Version-aware hook factory
- `/home/nicola/dev/backcast_evs/frontend/src/contexts/TimeMachineContext.tsx` - Time Machine context provider

**Test Files:**
- `/home/nicola/dev/backcast_evs/frontend/tests/e2e/cost_element_forecast.spec.ts` - E2E test coverage
