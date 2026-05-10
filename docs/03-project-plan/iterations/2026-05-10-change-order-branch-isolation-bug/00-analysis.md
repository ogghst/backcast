# Analysis: Change Order Branch Isolation Bug

**Created:** 2026-05-10
**Request:** Critical bug discovered during change order E2E testing - cost element edits applied to main branch instead of change order branch

---

## Clarified Requirements

### Problem Statement

When editing a cost element while viewing a change order branch (BR-CO-2026-016), the change was applied to the **main** branch instead of being forked to the change branch. This violates the EVCS core principle of branch isolation and breaks the change order workflow.

### Test Scenario

1. Created change order CO-2026-016 (Draft status)
2. Switched to change branch BR-CO-2026-016 via time machine panel
3. Navigated to cost element CE-CTRL-02 (PLC Programming, €45,000)
4. Edited budget from €45,000 to €55,000
5. Saved the change

**Expected:** Entity should be forked to BR-CO-2026-016 branch, main branch unchanged
**Actual:** Entity updated on main branch, no version created on BR-CO-2026-016

### Functional Requirements

- **BR-1:** All entity mutations (create, update, delete) MUST respect the current branch context from the Time Machine
- **BR-2:** When viewing a change order branch, edits to branchable entities MUST create versions on that branch
- **BR-3:** The system MUST support lazy branching - entities are forked only when modified, not proactively
- **BR-4:** Branch isolation MUST be enforced for all branchable entities (Cost Elements, WBEs, Projects, etc.)

### Non-Functional Requirements

- **NFR-1:** Maintain backward compatibility with existing API contracts
- **NFR-2:** Zero data corruption - changes must not silently apply to wrong branches
- **NFR-3:** Performance impact must be minimal (branch context is already available in frontend state)
- **NFR-4:** Solution must be consistent across all branchable entity types

### Constraints

- **Constraint-1:** Cannot change the backend API signature (branch is in request body, not query parameter for updates)
- **Constraint-2:** Frontend uses generated OpenAPI client - must work with existing service patterns
- **Constraint-3:** Must preserve the Time Machine's ability to switch branches for viewing only (read operations)

---

## Context Discovery

### Product Scope

- **Epic 6:** Branching & Change Order Management
- **User Story:** As a project manager, I want to edit project entities within a change order branch so that proposed changes are isolated from live data until approved
- **Business Rule:** Change Orders use lazy branching - entities are forked only when modified, not at CO creation
- **Business Rule:** Branch isolation is mandatory - changes on CO branches must not affect main until merge

### Architecture Context

**Bounded Contexts:**
- **EVCS Core:** Entity Versioning Control System with bitemporal tracking and branch isolation
- **Change Orders:** Workflow management for approving and merging changes
- **Time Machine:** UI component for navigating branches and time-travel

**Existing Patterns:**
- **BranchableService:** Base service class for entities supporting branching
- **Lazy Branching:** Entities forked only on first modification to branch
- **BranchableProtocol:** Protocol requiring `branch`, `parent_id`, and `merge_from_branch` fields

**Architectural Constraints:**
- Frontend uses TanStack Query for server state with query key-based cache isolation
- Branch context is stored in Zustand store (`useTimeMachineStore`)
- API uses OpenAPI-generated TypeScript client

### Codebase Analysis

**Backend:**

- **`/backend/app/api/routes/cost_elements.py`** (lines 209-228)
  - `update_cost_element` endpoint uses `element_in.branch or "main"` (line 218)
  - Backend correctly defaults to "main" if branch not provided in request body
  - Pattern is consistent across WBE and Project update endpoints

- **`/backend/app/services/cost_element_service.py`** (lines 287-451)
  - `update()` method extracts branch from schema: `target_branch = update_data.pop("branch", None) or branch or "main"` (line 302)
  - Lazy branching implemented: if entity not found on target branch, forks from main (lines 366-451)
  - Service correctly handles branching when branch parameter is provided

- **`/backend/app/services/wbe.py`** (lines 639-733)
  - `update_wbe()` correctly extracts branch from schema: `branch = wbe_in.branch or "main"` (line 669)
  - Uses branch for all operations including parent lookups and validation
  - Demonstrates correct pattern for branch context handling

**Frontend:**

- **`/frontend/src/stores/useTimeMachineStore.ts`** (all lines)
  - Manages per-project time machine settings (branch, as_of, mode)
  - `getSelectedBranch()` returns current branch for active project
  - Settings persisted to localStorage per project

- **`/frontend/src/contexts/TimeMachineContext.tsx`** (all lines)
  - Provides `branch`, `asOf`, and `mode` to component tree
  - `useTimeMachine()` hook for accessing context
  - `useTimeMachineParams()` returns API parameters object

- **`/frontend/src/hooks/useVersionedCrud.ts`** (lines 183-210) **← ROOT CAUSE**
  - `useList` and `useDetail` hooks correctly use `useTimeMachineParams()` for queries
  - `useUpdate`, `useCreate`, and `useDelete` hooks do NOT inject branch context
  - Mutation functions call API methods without adding current branch to request data

- **`/frontend/src/api/generated/services/CostElementsService.ts`** (lines 128-144)
  - Generated `updateCostElement(costElementId, requestBody)` method
  - Sends request body as-is without modifying it
  - No branch context injection at service layer

- **`/frontend/src/api/generated/models/CostElementUpdate.ts`** (all lines)
  - Schema includes optional `branch` field (line 17)
  - Documented as "Branch name for update (defaults to current branch)"
  - Frontend not populating this field from Time Machine context

---

## Solution Options

### Option 1: Inject Branch Context in useVersionedCrud Mutations (Recommended)

**Architecture & Design:**

Modify the `useVersionedCrud` hook to automatically inject the current branch from `useTimeMachineParams()` into all mutation operations. The hook will merge the Time Machine context with user-provided data before sending to the API.

**UX Design:**

- No changes to UI components
- Branch context automatically applied when user edits data while viewing a change order branch
- Transparent to end users - works as expected

**Implementation:**

1. Modify `useUpdate`, `useCreate`, and `useDelete` in `useVersionedCrud.ts`
2. Each mutation hook calls `useTimeMachineParams()` to get current branch
3. Merge branch into request data: `{ ...data, branch: currentBranch }`
4. For mutations that accept query parameters (delete), add branch to query string
5. Ensure branch field doesn't override user-provided branch (if explicitly set)

**Key Technical Details:**

- Use `useTimeMachineParams()` inside mutation hooks
- Merge strategy: Time Machine branch is default, user-provided branch overrides
- Handle different mutation signatures (body vs query parameters)
- Maintain type safety with TypeScript generics

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | • Fixes root cause centrally <br>• Consistent behavior across all entities <br>• No changes to individual components <br>• Follows DRY principle <br>• Automatic - no developer awareness needed |
| Cons            | • May hide branch context from developers <br>• Could complicate explicit branch operations <br>• Requires careful merge logic to handle edge cases |
| Complexity      | Low - isolated to one file |
| Maintainability | Excellent - single source of truth |
| Performance     | No impact - hook already exists |

---

### Option 2: Manual Branch Injection in Component Layer

**Architecture & Design:**

Add branch context manually in each component that performs mutations. Components would call `useTimeMachineParams()` and merge branch into mutation data.

**UX Design:**

- Same as Option 1 for end users
- More verbose component code

**Implementation:**

1. Each component using mutations calls `useTimeMachineParams()`
2. Manually merge branch into mutation data:
   ```typescript
   const { branch } = useTimeMachineParams();
   const { mutate } = useUpdateCostElement();
   mutate({ id, data: { ...updateData, branch } });
   ```
3. Update all cost element, WBE, and project forms/editors

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | • Explicit branch handling <br>• Easy to understand data flow <br>• Flexible for edge cases |
| Cons            | • High developer burden <br>• Error-prone - easy to forget <br>• Violates DRY principle <br>• Inconsistent application likely <br>• Difficult to enforce across team |
| Complexity      | High - touches many components |
| Maintainability | Poor - scatter-shot changes |
| Performance     | No impact |

---

### Option 3: Backend Branch Context Inference

**Architecture & Design:**

Modify backend to infer branch from a custom header or previous query context, eliminating the need for frontend to send branch in mutation body.

**UX Design:**

- Same as Option 1 for end users
- Simplified frontend code

**Implementation:**

1. Add middleware to store branch context from previous GET requests
2. On mutation requests, check if branch was previously queried for that entity
3. Use inferred branch if not provided in request body
4. Fallback to "main" if no context available

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | • Cleaner API contracts <br>• Automatic branch inference <br>• Works with existing frontend code |
| Cons            | • Complex state management on backend <br>• Relies on request ordering assumptions <br>• Difficult to test and debug <br>• May fail in load-balanced scenarios <br>• Violates stateless REST principles |
| Complexity      | Very High - middleware + session state |
| Maintainability | Poor - implicit behavior, hard to debug |
| Performance     | Potential overhead from session tracking |

---

## Comparison Summary

| Criteria           | Option 1 (Hook Injection) | Option 2 (Manual) | Option 3 (Backend Inference) |
| ------------------ | ------------------------- | ----------------- | ---------------------------- |
| Development Effort | Low (1 file, ~30 lines)   | High (20+ files)  | Very High (middleware + services) |
| UX Quality         | Excellent (transparent)    | Excellent         | Excellent                    |
| Flexibility        | High (override possible)   | Very High         | Low                          |
| Maintainability    | Excellent (centralized)    | Poor (scattered)  | Poor (complex implicit logic) |
| Test Coverage      | Easy (unit tests on hook)  | Difficult (many components) | Very Difficult (integration only) |
| Best For           | **Production systems**     | Prototypes        | Proof of concepts only       |

---

## Recommendation

**I recommend Option 1 (Inject Branch Context in useVersionedCrud Mutations)** because:

1. **Root Cause Fix:** Addresses the issue at its source - the hook that's supposed to provide version-aware CRUD operations
2. **Consistency:** Query operations already use Time Machine context; mutations should too
3. **Minimal Changes:** Single file change (`useVersionedCrud.ts`) fixes all entities
4. **Developer Experience:** Automatic behavior - no need to remember to add branch parameter
5. **Maintainability:** Centralized logic, easy to test and debug
6. **Architectural Alignment:** Follows the existing pattern of Time Machine context propagation
7. **Type Safety:** Preserves TypeScript generics and type checking

**Alternative consideration:** Choose Option 2 only if you need explicit control over branch selection in specific components (e.g., cross-branch operations or admin tools). For standard change order workflows, Option 1 is superior.

---

## Decision Questions

1. **Override Behavior:** Should developers be able to explicitly override the Time Machine branch in mutations? (Recommended: Yes, for advanced use cases like admin tools)

2. **Backward Compatibility:** Should we maintain support for mutations that don't provide a branch field? (Recommended: Yes, default to current Time Machine branch, fallback to "main" if no project context)

3. **Validation:** Should we add backend validation to reject mutations without branch context when a change order branch is active? (Recommended: No, would break existing clients; rely on frontend default instead)

4. **Testing Scope:** Should this fix include automated E2E tests for branch isolation? (Recommended: Yes, add regression tests to prevent this bug from recurring)

5. **Migration Strategy:** Should we update existing components to explicitly rely on Time Machine branch injection? (Recommended: No, the hook injection should be transparent; components continue to work as-is)

---

## Success Criteria

- [ ] SC1: Editing a cost element while viewing a change order branch creates a version on that branch
- [ ] SC2: Main branch remains unchanged when editing on change order branch
- [ ] SC3: Same behavior applies to WBEs, Projects, and all branchable entities
- [ ] SC4: No breaking changes to existing API contracts or component interfaces
- [ ] SC5: Zero data corruption - all mutations respect Time Machine branch context
- [ ] SC6: E2E tests pass for change order edit workflow
- [ ] SC7: Unit tests cover branch injection in mutation hooks

---

## Implementation Notes

### Files to Modify

**Primary Change:**
- `/frontend/src/hooks/useVersionedCrud.ts` - Add branch injection to `useUpdate`, `useCreate`, `useDelete`

**Tests:**
- `/frontend/src/hooks/useVersionedCrud.test.ts` - Add tests for branch injection
- New E2E test: Change order branch isolation

### Code Pattern for Branch Injection

```typescript
const useUpdate = (mutationOptions?) => {
  const queryClient = useQueryClient();
  const { branch } = useTimeMachineParams(); // Get current branch

  return useMutation({
    mutationFn: ({ id, data }) => {
      // Merge Time Machine branch into request data
      const requestData = { ...data, branch };
      return apiMethods.update(id, requestData);
    },
    // ... rest of mutation logic
  });
};
```

### Edge Cases to Handle

1. **Explicit Branch Override:** If data already contains `branch`, should it override Time Machine branch?
   - Decision: Yes, explicit branch in data takes precedence (advanced use cases)

2. **No Project Context:** What if Time Machine has no current project?
   - Decision: Default to "main" branch (current behavior)

3. **Delete Operations:** DELETE uses query parameters, not request body
   - Decision: Add branch to query parameters in `useDelete` hook

4. **Create Operations:** New entities should respect current branch
   - Decision: Inject branch into create data

---

## References

### Architecture Documentation

- [Entity Classification Guide](/home/nicola/dev/backcast/docs/02-architecture/backend/contexts/evcs-core/entity-classification.md)
- [Change Order Workflow Guide](/home/nicola/dev/backcast/docs/05-user-guide/change-order-workflow-guide.md)
- [EVCS Core Architecture](/home/nicola/dev/backcast/docs/02-architecture/backend/contexts/evcs-core/)

### Code References

- **Backend Cost Element Service:** `/home/nicola/dev/backcast/backend/app/services/cost_element_service.py` (lines 287-451)
- **Backend WBE Service:** `/home/nicola/dev/backcast/backend/app/services/wbe.py` (lines 639-733)
- **Frontend Time Machine Store:** `/home/nicola/dev/backcast/frontend/src/stores/useTimeMachineStore.ts`
- **Frontend Time Machine Context:** `/home/nicola/dev/backcast/frontend/src/contexts/TimeMachineContext.tsx`
- **Frontend Versioned CRUD Hook:** `/home/nicola/dev/backcast/frontend/src/hooks/useVersionedCrud.ts`

### Related Iterations

- [Branching Implementation (2026-01-12)](/home/nicola/dev/backcast/docs/03-project-plan/iterations/2026-01-12-branching-implementation/)
- [Change Order Workflow Integration (2026-02-05)](/home/nicola/dev/backcast/docs/03-project-plan/iterations/2026-02-05-change-order-workflow-integration/)

### ADRs

- [ADR-005: Bitemporal Versioning](/home/nicola/dev/backcast/docs/02-architecture/decisions/ADR-005-bitemporal-versioning.md)
- [ADR-006: Protocol-Based Type System](/home/nicola/dev/backcast/docs/02-architecture/decisions/ADR-006-protocol-based-type-system.md)
