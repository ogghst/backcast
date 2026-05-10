# Plan: Change Order Branch Isolation Bug Fix

**Created:** 2026-05-10
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 - Inject Branch Context in useVersionedCrud Mutations

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option:** Option 1 - Inject Branch Context in useVersionedCrud Mutations
- **Architecture:** Modify the `useVersionedCrud` hook to automatically inject the current branch from `useTimeMachineParams()` into all mutation operations (create, update, delete)
- **Key Decisions:**
  - Centralized fix in single file (`useVersionedCrud.ts`)
  - Automatic branch injection - no developer awareness required
  - Explicit branch in data overrides Time Machine branch (for advanced use cases)
  - Default to "main" branch if no Time Machine context available
  - Maintain backward compatibility with existing API contracts

### Success Criteria

**Functional Criteria:**

- [ ] **SC1:** Editing a cost element while viewing a change order branch creates a version on that branch, not main VERIFIED BY: Integration test
- [ ] **SC2:** Main branch remains unchanged when editing on change order branch VERIFIED BY: Database verification test
- [ ] **SC3:** Same behavior applies to WBEs, Projects, and all branchable entities using useVersionedCrud VERIFIED BY: Unit tests
- [ ] **SC4:** Create operations on change branch create entities on that branch VERIFIED BY: Unit test
- [ ] **SC5:** Delete operations on change branch delete from that branch VERIFIED BY: Unit test
- [ ] **SC6:** Explicit branch in mutation data overrides Time Machine branch VERIFIED BY: Unit test
- [ ] **SC7:** No Time Machine context defaults to "main" branch VERIFIED BY: Unit test

**Technical Criteria:**

- [ ] **TC1:** Zero TypeScript errors - strict mode maintained VERIFIED BY: `npm run typecheck`
- [ ] **TC2:** Zero ESLint errors VERIFIED BY: `npm run lint`
- [ ] **TC3:** All existing tests continue to pass VERIFIED BY: `npm test`
- [ ] **TC4:** Test coverage ≥80% for useVersionedCrud hook VERIFIED BY: `npm run test:coverage`
- [ ] **TC5:** No breaking changes to component interfaces VERIFIED BY: Integration smoke test
- [ ] **TC6:** Performance impact <5ms per mutation VERIFIED BY: Manual timing test

**Business Criteria:**

- [ ] **BC1:** Change order workflow provides reliable branch isolation VERIFIED BY: E2E lifecycle test
- [ ] **BC2:** Project managers can confidently edit on change branches VERIFIED BY: User acceptance testing
- [ ] **BC3:** No risk of unintended data corruption on main branch VERIFIED BY: Database integrity checks

### Scope Boundaries

**In Scope:**

- Modify `useVersionedCrud.ts` to inject branch context in useCreate, useUpdate, useDelete
- Add unit tests for branch injection logic
- Add integration test for cost element update on change branch
- Update existing E2E test to verify branch isolation
- Documentation update in hook comments

**Out of Scope:**

- Backend API changes (backend correctly handles branch parameter)
- Changes to individual components using useVersionedCrud
- UI/UX changes to Time Machine panel
- Branch isolation for non-versioned entities (not applicable)
- Migration of existing data (no data migration needed)
- Schedule baseline fallback on change branches (separate issue)

---

## Work Decomposition

### Task Breakdown

| #   | Task                                                          | Files                                                      | Dependencies | Success Criteria                                                                  | Complexity |
| --- | ------------------------------------------------------------- | ---------------------------------------------------------- | ------------ | --------------------------------------------------------------------------------- | ---------- |
| 1   | Add branch injection to useUpdate hook in useVersionedCrud.ts | `frontend/src/hooks/useVersionedCrud.ts`                   | None         | Branch from useTimeMachineParams merged into update data; unit tests pass        | Low        |
| 2   | Add branch injection to useCreate hook in useVersionedCrud.ts | `frontend/src/hooks/useVersionedCrud.ts`                   | Task 1       | Branch from useTimeMachineParams merged into create data; unit tests pass        | Low        |
| 3   | Add branch injection to useDelete hook in useVersionedCrud.ts | `frontend/src/hooks/useVersionedCrud.ts`                   | Task 1       | Branch from useTimeMachineParams added to delete call; unit tests pass           | Low        |
| 4   | Add unit tests for branch injection logic                     | `frontend/src/hooks/useVersionedCrud.test.ts` (new file)   | Tasks 1-3    | All branch injection scenarios tested; coverage ≥80%                             | Medium     |
| 5   | Add integration test for cost element update on change branch | `frontend/src/hooks/__tests__/useVersionedCrud.integration.test.ts` | Tasks 1-3    | Test verifies entity forked to change branch, not main                            | Medium     |
| 6   | Run quality checks (typecheck, lint, test)                   | N/A                                                        | Tasks 1-5    | Zero TypeScript/ESLint errors; all tests pass                                     | Low        |
| 7   | Update E2E test to verify branch isolation                   | `CHANGE_ORDER_E2E_TEST_REPORT.md` (re-run test)            | Tasks 1-6    | E2E test confirms branch isolation working; no changes on main branch             | Medium     |

### Test-to-Requirement Traceability

| Acceptance Criterion      | Test ID | Test File                                            | Expected Behavior                                                                                     |
| ------------------------- | ------- | ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| SC1: Cost element edit on change branch creates version on that branch | T-001   | `frontend/src/hooks/__tests__/useVersionedCrud.integration.test.ts` | When updating cost element on BR-CO-2026-016, new version created on that branch, not main             |
| SC2: Main branch unchanged when editing on change branch | T-002   | `frontend/src/hooks/__tests__/useVersionedCrud.integration.test.ts` | After update on change branch, main branch version has same valid_time range as before               |
| SC3: Behavior consistent across all branchable entities | T-003   | `frontend/src/hooks/useVersionedCrud.test.ts`        | Unit tests verify branch injection for create, update, delete operations                              |
| SC4: Create operations respect branch context | T-004   | `frontend/src/hooks/useVersionedCrud.test.ts`        | Creating entity while viewing change branch adds entity to that branch                                |
| SC5: Delete operations respect branch context | T-005   | `frontend/src/hooks/useVersionedCrud.test.ts`        | Deleting entity while viewing change branch deletes from that branch                                  |
| SC6: Explicit branch override works | T-006   | `frontend/src/hooks/useVersionedCrud.test.ts`        | When data includes branch field, it overrides Time Machine branch                                     |
| SC7: No context defaults to main | T-007   | `frontend/src/hooks/useVersionedCrud.test.ts`        | When no Time Machine context, mutation defaults to "main" branch                                      |
| TC1-TC5: Quality gates    | T-008   | CI pipeline                                         | typecheck, lint, and test commands all pass with zero errors                                         |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests (frontend/src/hooks/useVersionedCrud.test.ts)
│   ├── Happy path tests
│   │   ├── useUpdate injects branch from Time Machine
│   │   ├── useCreate injects branch from Time Machine
│   │   └── useDelete injects branch from Time Machine
│   ├── Edge cases and boundaries
│   │   ├── Explicit branch in data overrides Time Machine branch
│   │   ├── No Time Machine context defaults to "main"
│   │   └── Empty branch string defaults to "main"
│   └── Error handling
│       └── Invalid branch name handled by backend
├── Integration Tests (frontend/src/hooks/__tests__/useVersionedCrud.integration.test.ts)
│   ├── Cost element update on change branch
│   │   ├── Entity forked to change branch
│   │   └── Main branch unchanged
│   └── WBE update on change branch
│       └── Lazy branching applied correctly
└── E2E Tests (CHANGE_ORDER_E2E_TEST_REPORT.md - re-run)
    └── Full change order lifecycle with branch isolation
```

### Test Cases

| Test ID | Test Name                                                         | Criterion | Type          | Expected Result                                                                                                               |
| ------- | ----------------------------------------------------------------- | --------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| T-001   | `test_useUpdate_injects_branch_from_time_machine`                 | SC3       | Unit          | useUpdate mutation includes branch from useTimeMachineParams in request data                                                  |
| T-002   | `test_useCreate_injects_branch_from_time_machine`                 | SC4       | Unit          | useCreate mutation includes branch from useTimeMachineParams in request data                                                  |
| T-003   | `test_useDelete_injects_branch_from_time_machine`                 | SC5       | Unit          | useDelete mutation includes branch from useTimeMachineParams in API call                                                      |
| T-004   | `test_explicit_branch_in_data_overrides_time_machine`             | SC6       | Unit          | When mutation data includes branch field, it takes precedence over Time Machine branch                                       |
| T-005   | `test_no_time_machine_context_defaults_to_main`                   | SC7       | Unit          | When no Time Machine context available, mutation defaults to "main" branch                                                    |
| T-006   | `test_cost_element_update_on_change_branch_forks_entity`          | SC1       | Integration   | PUT request to cost element while viewing BR-CO-2026-016 creates version on that branch, not main                             |
| T-007   | `test_cost_element_update_on_change_branch_preserves_main`        | SC2       | Integration   | After update on BR-CO-2026-016, main branch cost element has unchanged valid_time range                                       |
| T-008   | `test_wbe_update_on_change_branch_lazy_branching`                 | SC3       | Integration   | WBE update on change branch triggers lazy forking - entity copied to branch then modified                                     |
| T-009   | `test_change_order_edit_workflow_branch_isolation`                | BC1       | E2E           | Full workflow: create CO, switch branch, edit cost element, verify forked to branch, verify main unchanged                    |
| T-010   | `test_all_quality_checks_pass`                                   | TC1-TC5   | Quality Gate  | npm run typecheck, npm run lint, npm test all pass with zero errors                                                           |

### Test Infrastructure Needs

**Fixtures needed:**
- Mock Time Machine context with specific branch
- Mock API service methods
- Mock QueryClient for cache invalidation verification

**Mocks/stubs:**
- `@tanstack/react-query` useQueryClient, useMutation
- Time Machine context (useTimeMachineParams)
- API service methods (CostElementsService, etc.)

**Database state:**
- Test project with change order BR-CO-2026-016
- Cost element CE-CTRL-02 on main branch
- WBE on main branch for lazy branching test

---

## Risk Assessment

| Risk Type   | Description                                                                                       | Probability | Impact      | Mitigation                                                                                                                                                                          |
| ----------- | ------------------------------------------------------------------------------------------------- | ----------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Technical   | TypeScript generic type constraints may prevent branch injection for some entity types           | Low         | Medium      | Use type assertions sparingly; verify with typecheck; test with multiple entity types (CostElement, WBE, Project)                                                                    |
| Integration | Existing components may rely on mutations NOT injecting branch (unintended behavior)            | Medium      | High        | Review components using useVersionedCrud; add migration guide if needed; ensure backward compatibility via explicit branch override                                                    |
| Performance | Additional hook call (useTimeMachineParams) on every mutation may impact render performance      | Low         | Low         | useTimeMachineParams uses useMemo; negligible overhead (<5ms per mutation); verify with manual timing test                                                                           |
| Testing     | Integration tests may require complex database setup (change order, branch, entities)            | Medium      | Medium      | Use existing test project CO-E2E-ROBOT; reuse test fixtures from previous E2E test; create dedicated test database state                                                             |
| Regression  | Fix may break existing workflows that depend on mutations defaulting to main branch              | Medium      | High        | Explicit branch override allows existing behavior; run full test suite before and after; monitor production for unexpected branch usage patterns                                     |
| Edge Case   | Delete operations may use query parameters instead of body, requiring different injection pattern | Low         | Medium      | Verify delete API signature; if uses query params, add branch to query string instead of body; test specifically for delete operation                                               |

---

## Documentation References

### Required Reading

- **Coding Standards:** `docs/02-architecture/coding-standards.md`
- **EVCS Entity Classification:** `docs/02-architecture/backend/contexts/evcs-core/entity-classification.md`
- **ADR-005: Bitemporal Versioning:** `docs/02-architecture/decisions/ADR-005-bitemporal-versioning.md`
- **Change Order Workflow Guide:** `docs/05-user-guide/change-order-workflow-guide.md`

### Code References

- **Backend pattern (correct implementation):** `/backend/app/services/wbe.py` (lines 639-733) - Shows correct branch parameter handling in `update_wbe()`
- **Frontend Time Machine Store:** `/frontend/src/stores/useTimeMachineStore.ts` - Source of truth for branch context
- **Frontend Time Machine Context:** `/frontend/src/contexts/TimeMachineContext.tsx` - useTimeMachineParams hook implementation
- **Test pattern:** `/frontend/src/stores/useTimeMachineStore.test.ts` - Example of testing Time Machine context

---

## Prerequisites

### Technical

- [x] Analysis phase approved
- [ ] Backend services running (port 8020)
- [ ] Frontend dev server running (port 5173)
- [ ] PostgreSQL container running (backcast-postgres-1)
- [ ] Test project CO-E2E-ROBOT exists with change order BR-CO-2026-016
- [ ] Test users available (pm@backcast.org, admin@backcast.org)
- [ ] Dependencies installed: `npm install --legacy-peer-deps` completed

### Documentation

- [x] Analysis phase approved (Option 1 selected)
- [x] Architecture docs reviewed (EVCS branching pattern)
- [ ] E2E test report reviewed (understands current bug behavior)

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: FE-001
    name: "Add branch injection to useUpdate hook"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-002
    name: "Add branch injection to useCreate hook"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-003
    name: "Add branch injection to useDelete hook"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-004
    name: "Add unit tests for branch injection logic"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002, FE-003]

  - id: FE-005
    name: "Add integration test for cost element update on change branch"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002, FE-003]

  - id: FE-006
    name: "Run quality checks (typecheck, lint, test)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-004, FE-005]

  - id: FE-007
    name: "Re-run E2E test to verify branch isolation fix"
    agent: pdca-frontend-do-executor
    dependencies: [FE-006]
```

---

## Definition of Done

This iteration is complete when:

1. **Code Implementation:**
   - [ ] All three mutation hooks (useUpdate, useCreate, useDelete) inject branch context
   - [ ] Branch injection follows correct pattern (merge with Time Machine params)
   - [ ] Explicit branch in data overrides Time Machine branch
   - [ ] No Time Machine context defaults to "main" branch

2. **Testing:**
   - [ ] All unit tests pass (T-001 through T-008)
   - [ ] Integration tests pass (T-006 through T-008)
   - [ ] E2E test passes (T-009)
   - [ ] Test coverage ≥80% for useVersionedCrud hook
   - [ ] No regression in existing test suite

3. **Quality Gates:**
   - [ ] Zero TypeScript errors (`npm run typecheck`)
   - [ ] Zero ESLint errors (`npm run lint`)
   - [ ] All tests pass (`npm test`)
   - [ ] Manual timing test shows <5ms overhead per mutation

4. **Documentation:**
   - [ ] Hook comments updated to document branch injection behavior
   - [ ] Analysis document linked to implementation
   - [ ] Test report updated with pass/fail results

5. **Verification:**
   - [ ] Manual testing confirms branch isolation working
   - [ ] Database verification shows entities forked to correct branches
   - [ ] No unintended changes to main branch
   - [ ] Time Machine panel continues working correctly

---

## Implementation Notes

### Code Pattern for Branch Injection

**For useUpdate and useCreate (body-based mutations):**

```typescript
const useUpdate = (mutationOptions?) => {
  const queryClient = useQueryClient();
  const { branch } = useTimeMachineParams(); // Get current branch

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TUpdate }) => {
      if (!apiMethods.update) {
        throw new Error("update method not implemented");
      }
      // Merge Time Machine branch into request data
      // Explicit branch in data takes precedence
      const requestData = { ...data, branch: data.branch || branch };
      return apiMethods.update(id, requestData);
    },
    // ... rest of mutation logic
  });
};
```

**For useDelete (query parameter-based mutations):**

Note: Verify if delete uses body or query params. If query params:

```typescript
const useDelete = (mutationOptions?) => {
  const queryClient = useQueryClient();
  const { branch } = useTimeMachineParams();

  return useMutation({
    mutationFn: (id: string) => {
      if (!apiMethods.delete) {
        throw new Error("delete method not implemented");
      }
      // Add branch to query parameters or body based on API signature
      return apiMethods.delete(id, { branch });
    },
    // ... rest of mutation logic
  });
};
```

### Edge Cases to Handle

1. **Explicit Branch Override:**
   - If `data.branch` is explicitly set, use that value (allows advanced use cases)
   - Pattern: `data.branch || branch`

2. **No Project Context:**
   - If `useTimeMachineParams()` returns no context, default to "main"
   - Pattern: `branch || "main"`

3. **Empty Branch String:**
   - Treat empty string as "main"
   - Pattern: `branch || "main"` (empty string is falsy)

4. **Delete Operation Signature:**
   - Verify if delete accepts branch in query params or body
   - Check generated API client signature
   - Adjust injection pattern accordingly

5. **Type Safety:**
   - Ensure `TUpdate` and `TCreate` generics allow optional `branch` field
   - Use type assertion if needed: `data.branch || branch as string`

---

## Success Metrics

**Before Fix (Baseline):**
- E2E Test 3: FAILED - Branch isolation not working
- Cost element updated on main branch instead of change branch
- Main branch corrupted during change order workflow

**After Fix (Target):**
- E2E Test 3: PASSED - Branch isolation working
- Cost element forked to BR-CO-2026-016 branch
- Main branch unchanged during change order workflow
- All unit tests passing with ≥80% coverage
- Zero quality gate failures

**Measurable Impact:**
- Branch isolation reliability: 0% → 100%
- Risk of data corruption: HIGH → NONE
- Change order workflow: BROKEN → FUNCTIONAL
