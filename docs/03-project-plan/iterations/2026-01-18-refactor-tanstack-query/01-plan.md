# Plan: Refactor TanStack Query Usage - Full Factory Implementation

**Created:** 2026-01-18
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 2 - Full Factory (implement factory and migrate all hooks at once)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 2 - Version-Aware Hook Factory with full migration
- **Architecture**: Create a new `createVersionedResourceHooks` factory that extends `useCrud.ts` with Time Machine context awareness
- **Key Decisions**:
  - Enforce centralized Query Key factory usage
  - Automatic context injection from `useTimeMachineParams()`
  - Context-aware optimistic updates
  - Dependent invalidation support for EVM data consistency
  - Migrate all versioned entity hooks at once: cost-elements, wbes, forecasts, projects, schedule-baselines

### Dependent Invalidation Patterns Analysis

Based on codebase exploration, the following dependent invalidation patterns were identified:

| Primary Entity | Dependent Entities | Rationale |
| -------------- | ------------------ | --------- |
| **Cost Elements** | `forecasts.all`, `forecast_comparison` | Cost element changes affect EVM calculations |
| **Cost Registrations** | `forecasts.all`, `forecast_comparison`, `budgetStatus` | Actual costs affect EVM metrics and budget tracking |
| **Schedule Baselines** | `forecasts.all`, `forecast_comparison` | Planned Value changes affect EVM calculations |
| **Forecasts** | (none identified) | Leaf node in dependency graph |
| **WBEs** | (none identified) | Hierarchical structure, no EVM impact |
| **Projects** | (none identified) | Root entity, branch management handled separately |
| **Change Orders** | `projects.*.branches`, `projects` | Branch creation/updates affect project branch lists |

**Critical Finding**: The pattern `["forecast_comparison"]` appears as a legacy key that should be migrated to `queryKeys.forecasts.comparison()`.

### Success Criteria

**Functional Criteria:**

- [ ] All versioned entity hooks use `queryKeys` factory for query key generation VERIFIED BY: Code review showing no manual key construction
- [ ] All query keys include context parameters `{ branch, asOf, mode }` VERIFIED BY: Unit tests verifying key structure
- [ ] Create/update/delete mutations trigger proper dependent invalidations VERIFIED BY: Integration tests
- [ ] Optimistic updates work correctly with context-aware keys VERIFIED BY: E2E tests
- [ ] Legacy `["forecast_comparison"]` key replaced with `queryKeys.forecasts.comparison()` VERIFIED BY: Grep search
- [ ] Cost element list query includes `asOf` parameter (fix current bug) VERIFIED BY: Manual testing

**Technical Criteria:**

- [ ] TypeScript strict mode with zero errors VERIFIED BY: `npm run lint` and `tsc --noEmit`
- [ ] Test coverage ≥80% for new factory code VERIFIED BY: `npm run test:coverage`
- [ ] All existing tests continue to pass VERIFIED BY: `npm test`
- [ ] Zero breaking changes to public API of hooks VERIFIED BY: TypeScript compilation check

**TDD Criteria:**

- [ ] Factory tests written before factory implementation VERIFIED BY: Git commit history
- [ ] Each hook migration includes test updates VERIFIED BY: Test file modifications
- [ ] Test coverage for context isolation scenarios VERIFIED BY: Coverage report
- [ ] Tests follow Arrange-Act-Assert pattern VERIFIED BY: Code review

### Scope Boundaries

**In Scope:**

- Create `src/hooks/useVersionedCrud.ts` factory
- Migrate `useCostElements` (fix missing `asOf` bug)
- Migrate `useWBEs` (currently ignores factory)
- Migrate `useForecasts` (currently ignores factory)
- Migrate `useProjects` (currently ignores factory)
- Migrate `useScheduleBaselines` (uses factory, verify correctness)
- Update all dependent invalidation patterns
- Replace legacy `["forecast_comparison"]` keys
- Unit tests for factory
- Integration tests for cache invalidation
- Update TypeScript types

**Out of Scope:**

- `useCostRegistrations` (already uses factory correctly, non-versioned)
- `useChangeOrders` (uses factory, specialized workflow)
- Backend API changes
- Database schema changes
- UI component refactoring (hooks maintain same API)
- Non-versioned entities (users, departments, cost element types)

---

## Work Decomposition

### Task Breakdown

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ----- | ------ | ------------- | ---------------- | ---------- |
| 1 | **Create `useVersionedCrud` factory** | `frontend/src/hooks/useVersionedCrud.ts` | None | Factory compiles, exports typed interface, includes context injection | High |
| 2 | **Write factory unit tests** | `frontend/src/hooks/useVersionedCrud.test.ts` | Task 1 | Tests pass, cover context injection, query key generation, invalidation | Medium |
| 3 | **Migrate `useCostElements`** | `frontend/src/features/cost-elements/api/useCostElements.ts` | Tasks 1,2 | Uses factory, includes `asOf` in list query, all invalidations use factory | Medium |
| 4 | **Migrate `useWBEs`** | `frontend/src/features/wbes/api/useWBEs.ts` | Tasks 1,2 | Uses factory, all manual keys replaced | Low |
| 5 | **Migrate `useForecasts`** | `frontend/src/features/forecasts/api/useForecasts.ts` | Tasks 1,2 | Uses factory, replaces manual keys | Low |
| 6 | **Migrate `useProjects`** | `frontend/src/features/projects/api/useProjects.ts` | Tasks 1,2 | Uses factory, replaces manual keys | Low |
| 7 | **Verify `useScheduleBaselines`** | `frontend/src/features/schedule-baselines/api/useScheduleBaselines.ts` | Tasks 1,2 | Confirm factory usage correct, fix any issues | Low |
| 8 | **Replace legacy forecast_comparison keys** | All hook files with forecast invalidation | Tasks 3-7 | All `["forecast_comparison"]` replaced with `queryKeys.forecasts.comparison()` | Low |
| 9 | **Update dependent invalidations** | All migrated hooks | Tasks 3-8 | Document patterns in factory, ensure EVM data consistency | Medium |
| 10 | **Integration tests for cache invalidation** | `frontend/tests/integration/cache-invalidation.test.ts` | Tasks 1-9 | Tests verify proper cascade invalidation | Medium |
| 11 | **E2E test for context isolation** | `frontend/tests/e2e/time-machine-context.spec.ts` | Tasks 1-9 | Verify branch/asOf switches invalidate correctly | High |
| 12 | **Final verification & cleanup** | All modified files | Tasks 1-11 | Lint clean, tests pass, no manual keys remain | Low |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| ------------------- | ------- | --------- | ----------------- |
| Factory provides context injection | T-001 | `useVersionedCrud.test.ts` | Factory hook reads `{ branch, asOf, mode }` from TimeMachine context |
| Factory generates query keys via factory | T-002 | `useVersionedCrud.test.ts` | Query keys match `queryKeys[resource].*` pattern |
| Factory includes context in all keys | T-003 | `useVersionedCrud.test.ts` | All query keys contain `{ branch, asOf, mode }` |
| Cost elements list includes asOf | T-004 | `useCostElements.test.ts` | List query key contains `asOf` parameter |
| Dependent invalidation triggers | T-005 | `cache-invalidation.test.ts` | Cost element mutation invalidates `forecasts.all` |
| Optimistic updates with context | T-006 | `cache-invalidation.test.ts` | Update optimistically modifies correct context-isolated cache entry |
| Context isolation prevents stale data | T-007 | `time-machine-context.spec.ts` | Branch switch triggers refetch, no data leakage |
| Legacy keys replaced | T-008 | Code search | No `["forecast_comparison"]` strings in codebase |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests (frontend/src/hooks/)
│   ├── useVersionedCrud.test.ts
│   │   ├── Factory initialization
│   │   ├── Context injection from useTimeMachineParams
│   │   ├── Query key generation via queryKeys factory
│   │   ├── Mutation invalidation (create/update/delete)
│   │   └── Dependent invalidation support
│   └── Individual hook test updates
│       ├── useCostElements.test.ts
│       ├── useWBEs.test.ts
│       ├── useForecasts.test.ts
│       └── useProjects.test.ts
├── Integration Tests (frontend/tests/integration/)
│   └── cache-invalidation.test.ts
│       ├── Cost element CRUD → forecast invalidation
│       ├── Cost registration CRUD → forecast invalidation
│       ├── Schedule baseline CRUD → forecast invalidation
│       └── Context isolation (branch/asOf switches)
└── E2E Tests (frontend/tests/e2e/)
    └── time-machine-context.spec.ts
        ├── Branch switch invalidates all versioned queries
        ├── AsOf change invalidates temporal queries
        └── No cross-branch data leakage
```

### Test Cases (first 8)

| Test ID | Test Name | Criterion | Type | Expected Result |
| ------- | --------- | --------- | ---- | --------------- |
| T-001 | `test_factory_hooks_inject_context_from_time_machine` | AC: Factory provides context injection | Unit | Factory hook reads `{ branch, asOf, mode }` and includes in query keys |
| T-002 | `test_factory_uses_query_keys_factory` | AC: Factory generates query keys via factory | Unit | Query keys match structure from `queryKeys[resource].*()` |
| T-003 | `test_factory_includes_context_in_all_keys` | AC: Factory includes context in all keys | Unit | List, detail, and mutation keys all contain context params |
| T-004 | `test_cost_elements_list_includes_as_of` | AC: Cost elements list includes asOf | Unit | List query key contains `asOf` parameter (fixes current bug) |
| T-005 | `test_cost_element_create_invalidates_forecasts` | AC: Dependent invalidation triggers | Integration | Creating cost element triggers `forecasts.all` invalidation |
| T-006 | `test_optimistic_update_with_context_isolation` | AC: Optimistic updates with context | Integration | Update modifies correct cache entry for current branch/asOf |
| T-007 | `test_branch_switch_invalidate_versioned_queries` | AC: Context isolation prevents stale data | E2E | Switching branch refetches all versioned entity data |
| T-008 | `test_no_legacy_forecast_comparison_keys` | AC: Legacy keys replaced | Unit | Search confirms no `["forecast_comparison"]` strings exist |

### Test Infrastructure Needs

- **Fixtures needed**:
  - `mockQueryClient` - TanStack Query mock with controlled cache
  - `mockTimeMachineContext` - Wrapper providing controlled `{ branch, asOf, mode }`
  - `mockQueryKeys` - Spied queryKeys factory for verification
- **Mocks/stubs**:
  - API service methods (CostElementsService, etc.)
  - TimeMachineContext
  - QueryClient invalidation/prefetch methods
- **Database state**: Not applicable (frontend-only refactor)

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --------- | ----------- | ----------- | ------ | ---------- |
| **Technical** | Factory generic types become complex and hard to maintain | Medium | Medium | Keep generics simple, document thoroughly, add comprehensive type tests |
| **Technical** | Context injection breaks existing hook consumers | Low | High | Maintain backward-compatible hook signatures, add integration tests |
| **Integration** | Dependent invalidation patterns missed, causing stale EVM data | Medium | High | Document all patterns in factory config, add integration tests |
| **Integration** | Optimistic updates corrupt cache with wrong context | Low | High | Add unit tests for onMutate/onError with context variations |
| **Process** | TDD discipline breaks down under refactor complexity | Medium | Low | Use todo tracking, enforce RED-GREEN-REFACTOR, pair review |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph for Parallel Execution
tasks:
  # Foundation Phase - Must run first
  - id: FE-001
    name: "Create useVersionedCrud factory"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-002
    name: "Write factory unit tests"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  # Migration Phase - Can run in parallel after factory
  - id: FE-003
    name: "Migrate useCostElements hook"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002]

  - id: FE-004
    name: "Migrate useWBEs hook"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002]

  - id: FE-005
    name: "Migrate useForecasts hook"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002]

  - id: FE-006
    name: "Migrate useProjects hook"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002]

  - id: FE-007
    name: "Verify useScheduleBaselines hook"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002]

  # Cleanup Phase - Must wait for migrations
  - id: FE-008
    name: "Replace legacy forecast_comparison keys"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003, FE-004, FE-005, FE-006, FE-007]

  - id: FE-009
    name: "Update dependent invalidation patterns"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003, FE-004, FE-005, FE-006, FE-007]

  # Verification Phase - Must wait for cleanup
  - id: FE-010
    name: "Write integration tests for cache invalidation"
    agent: pdca-frontend-do-executor
    dependencies: [FE-008, FE-009]

  - id: FE-011
    name: "Write E2E test for context isolation"
    agent: pdca-frontend-do-executor
    dependencies: [FE-008, FE-009]

  # Final Phase - Must wait for verification
  - id: FE-012
    name: "Final verification and cleanup"
    agent: pdca-frontend-do-executor
    dependencies: [FE-010, FE-011]
```

**Execution Strategy**:
- **Level 0** (FE-001): Create factory - single thread
- **Level 1** (FE-002): Write factory tests - single thread
- **Level 2** (FE-003 to FE-007): Migrate 5 hooks in parallel - 5 threads
- **Level 3** (FE-008, FE-009): Cleanup tasks - 2 threads
- **Level 4** (FE-010, FE-011): Write tests - 2 threads
- **Level 5** (FE-012): Final verification - single thread

---

## Documentation References

### Required Reading

- **Architecture**: `docs/02-architecture/frontend/contexts/02-state-data.md`
  - Query Key factory rules
  - Context isolation requirements
  - Invalidation strategy guidelines
- **Coding Standards**: `docs/00-meta/coding_standards.md`
- **Analysis Output**: `docs/03-project-plan/iterations/2026-01-18-refactor-tanstack-query/00-analysis.md`

### Code References

- **Factory Pattern**: `frontend/src/hooks/useCrud.ts` (existing createResourceHooks to extend)
- **Query Key Factory**: `frontend/src/api/queryKeys.ts` (must use for all keys)
- **Time Machine Context**: `frontend/src/contexts/TimeMachineContext.tsx` (useTimeMachineParams source)
- **Current Implementation** (bugs to fix):
  - `frontend/src/features/cost-elements/api/useCostElements.ts` (line 47-51: missing asOf in list)
  - `frontend/src/features/wbes/api/useWBEs.ts` (line 48: manual key)
  - `frontend/src/features/forecasts/api/useForecasts.ts` (line 41: manual key)
- **Dependent Invalidation Examples**:
  - `frontend/src/features/cost-elements/api/useCostElements.ts` (lines 149-150, 227-228)
  - `frontend/src/features/cost-registration/api/useCostRegistrations.ts` (lines 170-171)
  - `frontend/src/features/schedule-baselines/api/useScheduleBaselines.ts` (lines 230-231)

---

## Prerequisites

### Technical

- [x] Node.js 18+ installed
- [x] Frontend dependencies installed (`npm install` in `frontend/`)
- [x] TanStack Query v5 available
- [x] TypeScript strict mode enabled
- [x] Vitest testing framework configured
- [x] Playwright E2E testing configured

### Documentation

- [x] Analysis phase approved
- [x] Architecture docs reviewed (`02-state-data.md`)
- [x] Existing factory pattern understood (`useCrud.ts`)
- [x] Dependent invalidation patterns catalogued

### Environment

- [x] Feature branch created: `E05-U01-register-actual-costs-against-cost-elements`
- [x] Git status clean (only expected modified files)
- [x] Access to all feature directories

---

## Factory Design Specification

### Core Interface

```typescript
interface VersionedHookOptions {
  // Dependent invalidations to trigger on mutations
  invalidation?: {
    create?: QueryKey[];
    update?: QueryKey[];
    delete?: QueryKey[];
  };
  // Enable optimistic updates
  optimisticUpdates?: boolean;
  // Custom toast messages
  toastMessages?: {
    create?: string;
    update?: string;
    delete?: string;
  };
}

interface VersionedApiMethods<T, TCreate, TUpdate> {
  list: (params: any) => Promise<T[]>;
  detail: (id: string, context: any) => Promise<T>;
  create: (data: TCreate) => Promise<T>;
  update: (id: string, data: TUpdate) => Promise<T>;
  delete: (id: string) => Promise<void>;
}

function createVersionedResourceHooks<T, TCreate, TUpdate>(
  resourceName: keyof QueryKeyType,
  queryKeyFactory: QueryKeyFactoryMethods,
  apiMethods: VersionedApiMethods<T, TCreate, TUpdate>,
  options?: VersionedHookOptions
): {
  useList: (params?: any) => UseQueryResult<T[]>;
  useDetail: (id: string) => UseQueryResult<T>;
  useCreate: (opts?) => UseMutationResult<T, Error, TCreate>;
  useUpdate: (opts?) => UseMutationResult<T, Error, {id: string; data: TUpdate}>;
  useDelete: (opts?) => UseMutationResult<void, Error, string>;
}
```

### Context Injection Pattern

```typescript
const { branch, asOf, mode } = useTimeMachineParams();

// All query keys automatically include context:
queryKey: queryKeyFactory.list(params, { branch, asOf, mode })
queryKey: queryKeyFactory.detail(id, { branch, asOf, mode })
```

### Dependent Invalidation Configuration

```typescript
// Example: Cost Elements
const options: VersionedHookOptions = {
  invalidation: {
    create: [queryKeys.forecasts.all],
    update: [queryKeys.forecasts.all],
    delete: [queryKeys.forecasts.all],
  },
};

// Example: Schedule Baselines
const options: VersionedHookOptions = {
  invalidation: {
    create: [queryKeys.forecasts.all],
    update: [queryKeys.forecasts.all],
    delete: [queryKeys.forecasts.all],
  },
};
```

---

## Key Principles

1. **Define WHAT, not HOW**: This plan specifies test requirements and success criteria, not implementation code
2. **Measurable**: All success criteria are objectively verifiable via tests, linting, or code review
3. **Sequential**: Tasks ordered with clear dependencies (factory → migrate → verify)
4. **Traceable**: Every requirement maps to specific test specifications
5. **Actionable**: Each task is clear enough for DO phase execution with defined deliverables

---

## Output Notes

This plan drives the DO phase implementation. Tests are **specified** here but will be **implemented** in DO phase following RED-GREEN-REFACTOR TDD discipline. The task dependency graph enables parallel execution of independent migrations after the factory foundation is complete.
