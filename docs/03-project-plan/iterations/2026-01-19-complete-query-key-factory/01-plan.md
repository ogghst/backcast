# Plan: Complete Query Key Factory Adoption

**Created:** 2026-01-19
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 - Comprehensive Migration (all 11 files)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 - Comprehensive Migration
- **Architecture**: Centralized query key factory pattern with 100% adoption across all frontend hooks and components
- **Key Decisions**:
  - Extend `queryKeys.ts` factory with missing keys (users.me, verify impactAnalysis exists)
  - Migrate all 11 remaining files to use factory-generated keys
  - Keep `useCrud` and `useEntityHistory` as generic utilities but document their usage guidelines
  - Fix component-level cache invalidation bugs by using proper factory keys with Time Machine context

### Success Criteria

**Functional Criteria:**

- [ ] All 11 files use `queryKeys` factory for query key generation VERIFIED BY: Code inspection showing zero manual `queryKey: ["pattern"]` arrays
- [ ] Component-level mutation callbacks use factory keys with proper Time Machine context (branch, asOf, mode) VERIFIED BY: Code audit of mutation invalidation callbacks
- [ ] Time Machine context invalidations use factory `all` keys for proper cache clearing VERIFIED BY: Review of TimeMachineContext.tsx invalidation logic
- [ ] Specialized hooks (useImpactAnalysis, useWorkflowActions) use appropriate factory keys VERIFIED BY: Hook implementation review

**Technical Criteria:**

- [ ] TypeScript strict mode with zero errors VERIFIED BY: `npm run lint` and TypeScript compilation
- [ ] All existing tests pass (211+) VERIFIED BY: `npm test` and `npm run e2e`
- [ ] No breaking changes to API contracts VERIFIED BY: Running E2E test suite
- [ ] Query key structure consistency across all hooks VERIFIED BY: Global search for manual query keys returns zero results

**Business Criteria:**

- [ ] Cache-related bugs eliminated (no stale data after mutations) VERIFIED BY: Manual smoke testing of cost element CRUD, forecasts, and change orders
- [ ] Developer onboarding improved (single pattern to learn) VERIFIED BY: Documentation review

### Scope Boundaries

**In Scope:**

- Migration of 11 identified files to use `queryKeys` factory
- Extension of factory with missing keys (users.me, verification of impactAnalysis)
- Documentation updates for generic hooks (useCrud, useEntityHistory)
- Component-level cache invalidation fixes
- Time Machine context integration for versioned entities

**Out of Scope:**

- ESLint rule implementation (deferred to future iteration)
- API client generation changes
- Backend modifications
- New feature development
- Performance optimizations beyond cache consistency fixes

---

## Work Decomposition

### Task Breakdown

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ----- | ------ | ------------ | ---------------- | ---------- |
| 1 | Extend queryKeys factory with users.me key | `/home/nicola/dev/backcast_evs/frontend/src/api/queryKeys.ts` | None | Factory exports `queryKeys.users.me` key, TypeScript compiles without errors | Low |
| 2 | Verify queryKeys.changeOrders.impact() exists and is correctly structured | `/home/nicola/dev/backcast_evs/frontend/src/api/queryKeys.ts` | None | Factory has `impact: (id: string) => ["change-orders", id, "impact"]` pattern | Low |
| 3 | Migrate useAuth hook to use queryKeys.users.me | `/home/nicola/dev/backcast_evs/frontend/src/hooks/useAuth.ts` | Task 1 | Lines 29, 56 use `queryKeys.users.me` instead of `["currentUser"]`, auth flow works | Low |
| 4 | Migrate TimeMachineContext invalidations to use factory all keys | `/home/nicola/dev/backcast_evs/frontend/src/contexts/TimeMachineContext.tsx` | None | Lines 77-80 use `queryKeys.projects.all`, `queryKeys.wbes.all`, etc. | Low |
| 5 | Migrate useImpactAnalysis hook to use queryKeys.changeOrders.impact() | `/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/api/useImpactAnalysis.ts` | Task 2 | Line 27 uses `queryKeys.changeOrders.impact(changeOrderId)` with asOf context | Low |
| 6 | Migrate useWorkflowActions hook to use factory keys | `/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/hooks/useWorkflowActions.ts` | Task 2 | Lines 46-47, 56-57 use `queryKeys.changeOrders.all` and `queryKeys.projects.branches()` | Medium |
| 7 | Migrate OverviewTab invalidations to use factory keys | `/home/nicola/dev/backcast_evs/frontend/src/pages/cost-elements/tabs/OverviewTab.tsx` | Task 1 | Lines 38-47 use factory keys with proper Time Machine context parameters | Medium |
| 8 | Migrate ScheduleBaselinesTab invalidations to use factory keys | `/home/nicola/dev/backcast_evs/frontend/src/pages/cost-elements/tabs/ScheduleBaselinesTab.tsx` | None | Lines 58, 65, 72 use `queryKeys.scheduleBaselines.byCostElement()` | Low |
| 9 | Migrate ForecastsTab invalidations to use factory keys | `/home/nicola/dev/backcast_evs/frontend/src/pages/cost-elements/tabs/ForecastsTab.tsx` | None | Lines 61, 70 use `queryKeys.forecasts.byCostElement()` with branch context | Low |
| 10 | Migrate CostRegistrationsTab invalidations to use factory keys | `/home/nicola/dev/backcast_evs/frontend/src/pages/cost-elements/tabs/CostRegistrationsTab.tsx` | None | Lines 87, 97, 107 use `queryKeys.costRegistrations.budgetStatus()` | Low |
| 11 | Migrate ChangeOrderUnifiedPage invalidations to use factory keys | `/home/nicola/dev/backcast_evs/frontend/src/pages/change-orders/ChangeOrderUnifiedPage.tsx` | None | Line 168 uses `queryKeys.changeOrders.all` | Low |
| 12 | Add documentation header comments to useCrud and useEntityHistory | `/home/nicola/dev/backcast_evs/frontend/src/hooks/useCrud.ts`, `/home/nicola/dev/backcast_evs/frontend/src/hooks/useEntityHistory.ts` | None | Clear JSDoc comments explaining when to use these generic hooks vs factory keys | Low |
| 13 | Global code audit for any remaining manual query keys | All frontend source files | Tasks 1-12 | Zero instances of `queryKey: ["pattern"]` remain in codebase (except generics) | Low |
| 14 | Run full test suite and fix any regressions | All test files | Task 13 | All unit tests pass, all E2E tests pass, TypeScript zero errors | Medium |
| 15 | Manual smoke testing of affected user flows | N/A | Task 14 | Cost element CRUD, forecasts, change orders work without cache issues | Medium |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| ------------------- | ------- | --------- | ----------------- |
| All files use queryKeys factory | T-001 | Code inspection audit | Grep search for `queryKey: [` returns zero results in non-generic hooks |
| Component mutations use factory keys with context | T-002 | Code inspection of mutation callbacks | All `invalidateQueries` calls use factory keys with `branch`, `asOf`, `mode` params |
| Time Machine invalidations use factory all keys | T-003 | TimeMachineContext.tsx review | Invalidations use `queryKeys.{entity}.all` pattern |
| useAuth uses factory keys | T-004 | useAuth.ts code review | Query and invalidation use `queryKeys.users.me` |
| TypeScript zero errors | T-005 | Build verification | `npm run lint` and TypeScript compilation pass |
| All tests pass | T-006 | Test suite execution | `npm test` and `npm run e2e` show 211+ passing tests |
| No cache staleness bugs | T-007 | Manual smoke test | Mutations trigger proper cache refreshes across components |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: TASK-001
    name: "Extend queryKeys factory with users.me key"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: TASK-002
    name: "Verify queryKeys.changeOrders.impact() exists"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: TASK-003
    name: "Migrate useAuth hook to use queryKeys.users.me"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-001]

  - id: TASK-004
    name: "Migrate TimeMachineContext invalidations to use factory all keys"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: TASK-005
    name: "Migrate useImpactAnalysis hook to use queryKeys.changeOrders.impact()"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-002]

  - id: TASK-006
    name: "Migrate useWorkflowActions hook to use factory keys"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-002]

  - id: TASK-007
    name: "Migrate OverviewTab invalidations to use factory keys"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-001, TASK-004]

  - id: TASK-008
    name: "Migrate ScheduleBaselinesTab invalidations to use factory keys"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: TASK-009
    name: "Migrate ForecastsTab invalidations to use factory keys"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: TASK-010
    name: "Migrate CostRegistrationsTab invalidations to use factory keys"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: TASK-011
    name: "Migrate ChangeOrderUnifiedPage invalidations to use factory keys"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: TASK-012
    name: "Add documentation to useCrud and useEntityHistory"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: TASK-013
    name: "Global code audit for remaining manual query keys"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-001, TASK-002, TASK-003, TASK-004, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009, TASK-010, TASK-011, TASK-012]

  - id: TASK-014
    name: "Run full test suite and fix any regressions"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-013]

  - id: TASK-015
    name: "Manual smoke testing of affected user flows"
    agent: pdca-frontend-do-executor
    dependencies: [TASK-014]
```

**Parallelization Notes:**
- **Level 0 (Immediate)**: TASK-001, TASK-002, TASK-004, TASK-008, TASK-009, TASK-010, TASK-011, TASK-012 can all run in parallel
- **Level 1**: TASK-003 (waits for TASK-001), TASK-005 (waits for TASK-002), TASK-006 (waits for TASK-002), TASK-007 (waits for TASK-001, TASK-004)
- **Level 2**: TASK-013 (waits for all migration tasks)
- **Level 3**: TASK-014 (waits for TASK-013)
- **Level 4**: TASK-015 (waits for TASK-014)

---

## Test Specification

### Test Hierarchy

```
├── Code Inspection Tests (automated via grep/ast-grep)
│   ├── Verify zero manual query keys in non-generic hooks
│   ├── Verify factory keys include Time Machine context for versioned entities
│   └── Verify all invalidations use factory pattern
├── Unit Tests (existing suite)
│   ├── Auth hook tests (useAuth.spec.ts)
│   ├── Time Machine context tests
│   └── Hook behavior tests
├── Integration Tests (existing E2E suite)
│   ├── Cost element CRUD with cache verification
│   ├── Forecast creation and updates
│   └── Change order workflow transitions
└── Manual Smoke Tests
    ├── Login/logout flow with cache clearing
    ├── Cost element edit with budget refresh
    ├── Forecast creation with EVM update
    └── Time Machine context switching
```

### Test Cases (Critical Path)

| Test ID | Test Name | Criterion | Type | Verification Method |
| ------- | --------- | --------- | ---- | ------------------- |
| T-001 | `test_manual_query_keys_absent_from_source` | All files use factory | Code Audit | Run `grep -r 'queryKey: \[' src/ --exclude-dir=generated` verify zero matches |
| T-002 | `test_useAuth_uses_factory_keys` | useAuth migration | Unit | Verify `queryKeys.users.me` in useAuth.ts lines 29, 56 |
| T-003 | `test_timeMachine_invalidations_use_factory` | TimeMachine migration | Code Review | Verify `queryKeys.{entity}.all` in TimeMachineContext.tsx |
| T-004 | `test_overview_tab_invalidations_include_context` | Component context | Code Review | Verify OverviewTab uses `queryKeys.costElements.detail(id, {branch, asOf})` |
| T-005 | `test_typescript_compilation_clean` | TypeScript strict | Build | `npm run lint` exits with code 0 |
| T-006 | `test_all_unit_tests_pass` | No regressions | Unit | `npm test` shows all tests passing |
| T-007 | `test_e2e_cost_element_crud_with_cache` | Cache coherency | E2E | `cost_elements_crud.spec.ts` passes |
| T-008 | `test_e2e_forecast_updates_refresh_cache` | Cache invalidation | E2E | `cost_element_forecast.spec.ts` passes |
| T-009 | `test_manual_smoke_test_login_flow` | Auth cache clearing | Manual | Login → verify user data loads → logout → verify cache cleared |
| T-010 | `test_manual_smoke_test_cost_element_edit` | Mutation refresh | Manual | Edit cost element → verify budget status updates without refresh |

### Test Infrastructure Needs

**Existing Fixtures (from `/home/nicola/dev/backcast_evs/frontend/tests/`):**
- E2E test setup in `tests/e2e/` with Playwright
- Auth fixtures for login/logout flows
- Database seeding for cost elements, projects, WBEs
- Time Machine test utilities

**No New Fixtures Required:**
- Migration is purely frontend refactoring
- Existing E2E tests provide adequate coverage
- Manual smoke tests supplement automated suite

**Mocking Requirements:**
- None (factory is pure functions, no external dependencies)

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --------- | ----------- | ---------- | ------ | ---------- |
| **Technical** | Query key structure changes could invalidate existing caches during migration | Medium | Medium | Factory already has correct structure; changes are mostly find-and-replace. Test in dev environment first. |
| **Technical** | Missing Time Machine context parameters in component invalidations could cause cache misses | High | High | Strict code review to ensure all versioned entity invalidations include `{branch, asOf, mode}` context. |
| **Integration** | E2E tests may fail if query keys don't match expected patterns | Low | Medium | Run E2E suite immediately after each component migration. Fix issues incrementally. |
| **Process** | Generic hooks (useCrud, useEntityHistory) might be misused after migration | Low | Low | Add clear JSDoc documentation explaining when to use factory keys vs generic hooks. |
| **Quality** | Incomplete migration leaving some manual query keys | Medium | Medium | TASK-013 performs global audit. Use grep/ast-grep to catch any missed instances. |

**High-Priority Risks:**
1. **Missing Time Machine context in component invalidations** - This is the most critical risk. Ensure all `queryKeys.costElements.detail()`, `queryKeys.costRegistrations.budgetStatus()`, etc. include the context object with `{branch, asOf, mode}`.

**Mitigation Strategy:**
- Code review checklist for all component migrations
- Automated grep script to find any remaining manual keys
- Incremental testing after each file migration

---

## Documentation References

### Required Reading

- **Coding Standards**: `/home/nicola/dev/backcast_evs/docs/00-meta/coding_standards.md`
- **Query Key Architecture**: `/home/nicola/dev/backcast_evs/docs/02-architecture/frontend/contexts/02-state-data.md`
  - Rule: "We strictly enforce a centralized Query Key factory"
  - Rule: "For branchable or temporal entities, the Query Key **MUST** include context parameters"
  - Rule: "Mutations must trigger invalidation not just for the modified entity but for **all dependent data**"
- **Previous Migration**: `/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-18-refactor-tanstack-query/00-analysis.md`

### Code References

**Factory Pattern (Current Implementation):**
- `/home/nicola/dev/backcast_evs/frontend/src/api/queryKeys.ts` - Query key factory

**Successfully Migrated Hooks (Reference Patterns):**
- `/home/nicola/dev/backcast_evs/frontend/src/features/projects/api/useProjects.ts` - Example: `queryKeys.projects.list(params)`
- `/home/nicola/dev/backcast_evs/frontend/src/features/cost-elements/api/useCostElements.ts` - Example: `queryKeys.costElements.detail(id, {branch, asOf})`
- `/home/nicola/dev/backcast_evs/frontend/src/features/cost-registration/api/useCostRegistrations.ts` - Example: `queryKeys.costRegistrations.budgetStatus(id, {asOf})`

**Files to Migrate:**
- `/home/nicola/dev/backcast_evs/frontend/src/hooks/useAuth.ts` - Lines 29, 56
- `/home/nicola/dev/backcast_evs/frontend/src/contexts/TimeMachineContext.tsx` - Lines 77-80
- `/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/api/useImpactAnalysis.ts` - Line 27
- `/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/hooks/useWorkflowActions.ts` - Lines 46-47, 56-57
- `/home/nicola/dev/backcast_evs/frontend/src/pages/cost-elements/tabs/OverviewTab.tsx` - Lines 38-47
- `/home/nicola/dev/backcast_evs/frontend/src/pages/cost-elements/tabs/ScheduleBaselinesTab.tsx` - Lines 58, 65, 72
- `/home/nicola/dev/backcast_evs/frontend/src/pages/cost-elements/tabs/ForecastsTab.tsx` - Lines 61, 70
- `/home/nicola/dev/backcast_evs/frontend/src/pages/cost-elements/tabs/CostRegistrationsTab.tsx` - Lines 87, 97, 107
- `/home/nicola/dev/backcast_evs/frontend/src/pages/change-orders/ChangeOrderUnifiedPage.tsx` - Line 168

**Generic Hooks (Document Only):**
- `/home/nicola/dev/backcast_evs/frontend/src/hooks/useCrud.ts` - Generic CRUD factory for non-versioned entities
- `/home/nicola/dev/backcast_evs/frontend/src/hooks/useEntityHistory.ts` - Generic history hook for any entity

**Test Coverage:**
- `/home/nicola/dev/backcast_evs/frontend/tests/e2e/cost_elements_crud.spec.ts` - Cost element E2E tests
- `/home/nicola/dev/backcast_evs/frontend/tests/e2e/cost_element_forecast.spec.ts` - Forecast E2E tests
- `/home/nicola/dev/backcast_evs/frontend/tests/e2e/time_machine.spec.ts` - Time Machine context tests

---

## Prerequisites

### Technical

- [x] Node.js dependencies installed (`npm install` completed)
- [x] Development environment running (`npm run dev` accessible)
- [x] Backend API available for testing
- [x] PostgreSQL database running

### Documentation

- [x] Analysis phase approved (Option 1: Comprehensive Migration)
- [x] Query key factory architecture reviewed
- [x] Previous migration patterns understood
- [x] Time Machine context integration requirements clear

### Development Environment

- [x] Frontend test suite runnable (`npm test`)
- [x] E2E tests runnable (`npm run e2e`)
- [x] TypeScript compilation working (`npm run lint`)
- [x] Git workspace clean (ready for new feature branch)

---

## Implementation Notes for DO Phase

### Key Patterns to Follow

**1. Versioned Entity Query Keys (with Time Machine context):**
```typescript
// CORRECT: Include context for versioned entities
queryKey: queryKeys.costElements.detail(id, { branch, asOf, mode })
queryKey: queryKeys.costRegistrations.budgetStatus(id, { asOf })
queryKey: queryKeys.forecasts.byCostElement(id, branch, { asOf })

// INCORRECT: Missing context
queryKey: queryKeys.costElements.detail(id)
```

**2. Non-Versioned Entity Query Keys:**
```typescript
// CORRECT: No context needed
queryKey: queryKeys.users.me
queryKey: queryKeys.departments.all
```

**3. Global Invalidation (Time Machine context changes):**
```typescript
// CORRECT: Use factory's all keys
queryClient.invalidateQueries({ queryKey: queryKeys.projects.all })
queryClient.invalidateQueries({ queryKey: queryKeys.wbes.all })
queryClient.invalidateQueries({ queryKey: queryKeys.costElements.all })

// INCORRECT: Manual arrays
queryClient.invalidateQueries({ queryKey: ["projects"] })
```

**4. Component-Level Mutation Invalidation:**
```typescript
// CORRECT: Include all dependent queries with context
const onSuccess = () => {
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
};
```

### Verification Command for DO Phase

After completing all migrations, run this command to verify success:

```bash
# Should return zero results (except for generated files and generic hooks)
grep -r 'queryKey: \[' frontend/src/ --include='*.ts' --include='*.tsx' | grep -v 'generated' | grep -v 'useCrud' | grep -v 'useEntityHistory'
```

Expected output: Empty (no matches)

---

## Success Metrics

### Quantitative Metrics

- **0**: Number of manual query keys in non-generic hooks
- **11**: Number of files migrated to factory pattern
- **211+**: Number of passing tests (no regressions)
- **0**: TypeScript errors
- **100%**: Query key factory adoption rate

### Qualitative Metrics

- All cache invalidation bugs eliminated
- Consistent query key pattern across entire codebase
- Improved developer experience (single pattern to learn)
- Better cache coherency in Time Machine context switching

---

## Next Steps (DO Phase)

The DO phase should execute tasks in the order specified in the dependency graph:

1. **Start with factory extensions** (TASK-001, TASK-002) - foundation for all migrations
2. **Migrate core infrastructure** (TASK-003, TASK-004) - high impact, enables component migrations
3. **Migrate specialized hooks** (TASK-005, TASK-006) - medium priority
4. **Migrate component invalidations** (TASK-007 through TASK-011) - can run in parallel
5. **Document generic hooks** (TASK-012) - prevent future misuse
6. **Global audit** (TASK-013) - verify completeness
7. **Test suite** (TASK-014) - catch regressions
8. **Manual smoke test** (TASK-015) - final verification

**Estimated Total Time**: 4-6 hours (matches analysis estimate)
