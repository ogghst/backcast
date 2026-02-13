# PLAN Phase: Frontend Architecture Cleanup

**Iteration:** Frontend Architecture Consistency & Robustness Improvement
**Start Date:** 2026-01-07
**Status:** 🟡 In Planning

---

## Phase 1: Context Analysis

### Documentation Review

**Architecture Documentation Analyzed:**
- `docs/02-architecture/frontend/contexts/01-core-architecture.md` - Core architecture patterns
- `docs/02-architecture/frontend/contexts/02-state-data.md` - State management patterns
- `docs/02-architecture/frontend/contexts/04-quality-testing.md` - Testing standards
- `docs/02-architecture/frontend/contexts/06-authentication.md` - Auth patterns
- `docs/02-architecture/02-technical-debt.md` - Existing technical debt

**Key Architecture Principles Identified:**
1. **Server State**: Use TanStack Query for all API data (NOT Zustand)
2. **Client State**: Use Zustand with `immer` middleware for all stores
3. **Feature-Based Structure**: Organize by domain in `src/features/`
4. **Type Safety**: No `any` allow-list, strict TypeScript
5. **Code Reuse**: Generic factories over duplicated implementations

### Codebase Analysis

**Files Analyzed:** 50+ frontend files

**Key Patterns Identified:**
- **State Management Mix:**
  - `useAuthStore`: Uses `persist` middleware (no `immer`) ❌
  - `useAppStore`, `useUserPreferencesStore`: Use `immer` middleware ✅
  - `useUserStore`: Stores API data (violates architecture) ❌

- **API Adapter Duplication:**
  - 7+ identical adapter patterns mapping generic names to actual services
  - Found in: `useProjects.ts`, `useWBEs.ts`, `UserList.tsx`, `DepartmentManagement.tsx`, `CostElementTypeManagement.tsx`, `CostElementManagement.tsx`, `WBEList.tsx`

- **History Hook Inconsistency:**
  - Generic `useEntityHistory` exists
  - Specific `useProjectHistory`, `useWBEHistory` also created
  - Some files use generic, others use specific

---

## Phase 2: Problem Definition

### 1. Problem Statement

**Primary Issues:**

1. **State Management Violation** (Critical)
   - `useUserStore` stores server state (users array, loading, error) in Zustand
   - Violates documented pattern: "Do not store API data in Zustand. Use useQuery"
   - Duplicates TanStack Query functionality
   - Loss of caching, background refetch, deduplication benefits

2. **Store Middleware Inconsistency** (High)
   - Documentation: "Do use immer middleware for all Zustand stores"
   - `useAuthStore` uses `persist` without `immer`
   - Other stores correctly use `immer`
   - Risk of accidental mutations in auth state

3. **API Adapter Code Duplication** (Medium)
   - 7+ identical adapter patterns (15-20 lines each)
   - Forces misleading method names (`getUsers` for departments, projects)
   - Maintenance burden: changes require updates in 7+ places

4. **Pagination Inconsistency** (Low)
   - Hardcoded limits: 10, 100, 1000 across different files
   - No centralized constant for dropdown pagination

**Why Important Now:**
- Each new entity adds more duplication
- Inconsistency confuses developers and violates DRY
- Technical debt accumulating faster than being resolved
- Architecture drift from documented standards

**Business Value:**
- Reduced maintenance cost (less duplicated code)
- Faster onboarding (consistent patterns)
- Fewer bugs (type safety, proper state management)
- Better performance (proper caching)

### 2. Success Criteria (Measurable)

**Functional Criteria:**
- [ ] `useUserStore` deleted; all users use TanStack Query directly
- [ ] `useAuthStore` refactored to use `immer` middleware
- [ ] `createResourceHooks` accepts named service methods (no adapters needed)
- [ ] All 7+ adapter usages migrated to new pattern
- [ ] Pagination constants centralized in single location
- [ ] History hooks standardized on `useEntityHistory`

**Technical Criteria:**
- [ ] No compilation errors (TypeScript strict mode)
- [ ] All tests pass (unit, integration, e2e)
- [ ] No new `any` type casts
- [ ] Code coverage maintained ≥80%
- [ ] Linting passes (ESLint zero errors)

**Business Criteria:**
- [ ] Reduced lines of code by ~150-200 lines
- [ ] All state management follows documented patterns
- [ ] New entity CRUD requires <30 lines of code (vs 50+ currently)

### 3. Scope Definition

**In Scope:**
- Refactor `useAuthStore` to use `immer` middleware
- Delete `useUserStore` entirely; migrate to direct TanStack Query usage
- Refactor `createResourceHooks` to accept named methods
- Update all 7 adapter usages to new pattern
- Standardize history hooks on `useEntityHistory`
- Centralize pagination constants
- Update affected tests
- Update architecture documentation if needed

**Out of Scope:**
- Backend changes
- New features or functionality
- UI/UX redesigns
- Performance optimization beyond removing duplication
- Lazy loading of routes (already documented, not implemented)

---

## Phase 3: Implementation Options

### Option 1: Incremental Refactor (Recommended)

**Approach Summary:** Fix issues one at a time, ensuring tests pass at each step

**Design Patterns:**
- Maintain existing `createResourceHooks` signature
- Add overload for named methods
- Migrate adapters incrementally
- Preserve backward compatibility during migration

**Pros:**
- Lower risk (can stop if issues arise)
- Easier to review (smaller changes)
- Tests can verify each step
- Can ship partial improvements

**Cons:**
- Takes longer overall
- More commits/PRs
- Temporary mixed patterns

**Test Strategy Impact:** Tests updated incrementally; lower risk of breakage
**Risk Level:** Low
**Estimated Complexity:** Simple

---

### Option 2: Big Bang Refactor

**Approach Summary:** Change everything in one go; break compatibility

**Design Patterns:**
- Replace `createResourceHooks` signature entirely
- Delete old patterns without backward compatibility
- Force all files to update simultaneously

**Pros:**
- Cleaner final result
- No temporary mixed patterns
- Faster to complete (once started)

**Cons:**
- High risk (if something breaks, everything breaks)
- Harder to review (large PR)
- Tests may all fail simultaneously
- Rollback difficult

**Test Strategy Impact:** All tests may fail temporarily; require comprehensive fix
**Risk Level:** High
**Estimated Complexity:** Moderate

---

### Option 3: Defer to Next Sprint

**Approach Summary:** Document as technical debt, address in future iteration

**Design Patterns:**
- Add items to technical debt register
- Continue with current patterns for new features
- Schedule dedicated refactoring sprint

**Pros:**
- No immediate risk
- Can focus on features
- Plan for larger refactoring

**Cons:**
- Debt continues accumulating
- Each new feature adds more duplication
- Inconsistency confuses new developers
- Harder to refactor later (more code affected)

**Test Strategy Impact:** No impact
**Risk Level:** None (status quo)
**Estimated Complexity:** N/A

---

### Recommendation

**I recommend Option 1 (Incremental Refactor)** because:

1. **Low Risk:** Can verify each step with tests
2. **Pauses Possible:** Can stop after any completed step
3. **Learning Opportunity:** Team learns patterns through practice
4. **Code Review Friendly:** Smaller PRs easier to review
5. **Aligns with PDCA:** Continuous improvement approach

**Implementation Order:**
1. Centralize pagination constants (5 min, no risk)
2. Refactor `useAuthStore` to use `immer` (15 min, isolated)
3. Delete `useUserStore` and migrate usage (30 min, moderate risk)
4. Refactor `createResourceHooks` (1 hour, higher complexity)
5. Migrate all adapters to new pattern (1 hour, systematic)
6. Standardize history hooks (20 min, simple cleanup)
7. Update tests and documentation (30 min)

**Total Estimated Effort:** ~3-4 hours

> [!IMPORTANT] > **Human Decision Point**: Do you approve Option 1 (Incremental Refactor) with the proposed implementation order?

---

## Phase 4: Technical Design

### TDD Test Blueprint

**Unit Tests (isolated component behavior):**
1. Test `useAuthStore` with immer middleware (state updates, mutations)
2. Test new `createResourceHooks` with named methods
3. Test pagination constant exports

**Integration Tests (component interactions):**
1. Test UserList page with direct TanStack Query (no `useUserStore`)
2. Test ProjectList with new `createResourceHooks` pattern
3. Test auth state updates across components

**E2E Tests (critical user flows):**
1. User management CRUD flow (verify no `useUserStore` usage)
2. Auth persistence across page refreshes (verify `immer` works)

**Test Cases (ordered simplest to most complex):**

1. **Pagination Constants Export**
   - Test: `DROPDOWN_PAGE_SIZE` equals 1000
   - Test: `TABLE_PAGE_SIZE` equals 10
   - Test: Constants are immutable (`as const`)

2. **useAuthStore Immer Migration**
   - Test: `setUser` updates state immutably
   - Test: `logout` clears all state using draft mutation
   - Test: `setToken` with immer doesn't mutate previous state

3. **createResourceHooks Named Methods**
   - Test: Factory accepts `{ list, detail, create, update, delete }`
   - Test: Returned hooks work with named methods
   - Test: Type inference works correctly

4. **UserList without useUserStore**
   - Test: Page renders with TanStack Query
   - Test: CRUD operations work
   - Test: Loading/error states handled

### Implementation Strategy

**High-Level Approach:**
1. Start with zero-risk changes (pagination constants)
2. Move to isolated changes (useAuthStore)
3. Tackle higher-complexity items (createResourceHooks refactor)
4. Migrate usages systematically
5. Clean up and document

**Key Technologies/Patterns:**
- Zustand with `immer` middleware
- TanStack Query for server state
- Generic TypeScript types
- Factory pattern for hooks

**Integration Points:**
- All list pages using `createResourceHooks`
- All auth components using `useAuthStore`
- All modals and forms

**Component Breakdown:**
```
frontend/src/
├── constants/
│   └── pagination.ts (NEW)
├── hooks/
│   └── useCrud.ts (MODIFY - add named methods support)
├── stores/
│   ├── useAuthStore.ts (MODIFY - add immer)
│   └── useUserStore.ts (DELETE)
└── [All adapter files] (MODIFY - remove adapters, use named methods)
```

---

## Phase 5: Risk Assessment

### Risks and Mitigations

| Risk Type | Description | Probability | Impact | Mitigation Strategy |
|-----------|-------------|-------------|--------|---------------------|
| **Technical** | Breaking auth flow with immer migration | Low | High | Comprehensive auth tests; verify persist still works |
| **Technical** | Type inference breaks with new factory signature | Medium | Medium | Use TypeScript strict mode; test with each entity type |
| **Schedule** | Underestimated effort for adapter migration | Medium | Low | Can pause after any entity; others unaffected |
| **Integration** | Existing e2e tests fail | Low | Medium | Run e2e after each change; fix failures immediately |
| **Integration** | New pattern incompatible with some edge case | Low | Low | Keep old pattern as fallback during migration |

---

## Phase 6: Effort Estimation

### Time Breakdown

- **Pagination Constants:** 5 min (create file, add imports)
- **useAuthStore Immer Migration:** 15 min (add immer, update actions, test)
- **Delete useUserStore:** 30 min (migrate UserList, update tests, delete file)
- **createResourceHooks Refactor:** 1 hour (new signature, types, tests)
- **Migrate Adapters (7 files):** 1 hour (~8-10 min each)
- **Standardize History Hooks:** 20 min (remove specific hooks, update imports)
- **Update Tests:** 30 min (fix broken imports, add new tests)
- **Documentation:** 15 min (update architecture if needed)

**Total Estimated Effort:** ~3-4 hours

### Story Points Estimate: 5 points

**Rationale:**
- Low to moderate complexity
- Well-defined scope
- Clear success criteria
- Low risk with incremental approach

### Prerequisites

**Must Complete First:**
- None (standalone refactoring)

**Documentation Updates Needed:**
- Possibly update `docs/02-architecture/frontend/contexts/02-state-data.md` if patterns change
- Update code examples in architecture docs

**Infrastructure Needed:**
- None (uses existing tooling)

---

## Output Summary

**File Created:** `docs/03-project-plan/iterations/2026-01-07-frontend-architecture-cleanup/01-plan.md`

**Approval Status:** ⏳ Pending Human Approval

**Date Created:** 2026-01-07

**Related Documents:**
- Architecture Documentation: `docs/02-architecture/frontend/`
- Technical Debt Register: `docs/03-project-plan/technical-debt-register.md`
- Analysis Findings: See conversation history for detailed findings

**Next Steps After Approval:**
1. Create `02-do.md` for implementation tracking
2. Begin with pagination constants (zero-risk warmup)
3. Proceed with useAuthStore immer migration
4. Continue through implementation order
