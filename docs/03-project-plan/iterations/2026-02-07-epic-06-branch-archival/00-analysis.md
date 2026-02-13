# Analysis: Epic 6 - Branch Archival (E06-U08)

**Iteration:** 2026-02-07-epic-06-branch-archival
**Status:** 🏗️ In Progress

---

## 1. Requirements Clarification

**User Intent:**
Users need a way to "clean up" Change Order branches after they have been finalized (Merged/Implemented or Rejected). These branches should no longer appear in active branch lists but must remain accessible for historical reference and audit purposes (time-travel).

**Functional Requirements:**

- [ ] Ability to "archive" a Change Order branch.
- [ ] Archival should only be allowed for final states (`Implemented`, `Rejected`).
- [ ] Archived branches must NOT appear in standard branch lists (`get_branches`).
- [ ] Archived branches MUST be retrievable via time-travel queries (`get_branches_as_of`) or specific "include archived" flags if applicable (though time-travel is the primary audit mechanism).
- [ ] Archival should be a soft-delete operation on the `Branch` entity.

**Non-Functional Requirements:**

- **Auditability:** The action of archiving must be traceable (who, when).
- **Integrity:** Archiving the branch must not delete the actual Change Order entity or its history.

---

## 2. Context Discovery

### 2.1 Documentation & Codebase

- **`ChangeOrderService`**: Currently manages CO creation and Workflow.
- **`BranchService`**: Manages `Branch` entity. confirmed `TemporalService` base class, which supports `soft_delete`.
- **`Branch` Entity**: Has `deleted_at` field (via `VersionableMixin`).
- **`TemporalService`**: Base class for `BranchService`, provides `soft_delete` method which sets `deleted_at`.

### 2.2 Existing Patterns

- **Soft Delete**: `TemporalService.soft_delete` is the standard pattern for removing entities while keeping history.
- **Branching**: Change Orders have a 1:1 relationship with a `Branch` entity named `co-{code}`.

---

## 3. Solution Design

### Option 1: Explicit `archive` Method in `ChangeOrderService` (Recommended)

Add `archive_change_order_branch` to `ChangeOrderService`. This method encapsulates the business logic of validating the CO status before calling `BranchService.soft_delete`.

**Pros:**

- Encapsulates business rule (Status check) in the domain service (`ChangeOrderService`).
- Keeps `BranchService` generic.
- Clear intent in API.

**Cons:**

- Adds method to `ChangeOrderService`.

**Implementation:**

```python
async def archive_change_order_branch(self, change_order_id, actor_id):
    co = await self.get_current(change_order_id)
    if co.status not in ["Implemented", "Rejected"]:
        raise ValueError("Cannot archive active Change Order")
    
    branch_name = co.branch_name
    await self.branch_service.soft_delete(branch_name, ...)
```

### Option 2: Direct `BranchService.soft_delete` Call

Call `BranchService.soft_delete` directly from the API/Controller layer after checking CO status.

**Pros:**

- No new service method.

**Cons:**

- Leaks business logic (status check requirement) to API layer.
- Risk of bypassing the check.

### Option 3: "Archived" Status in Change Order

Add an `Archived` status to the Change Order workflow itself.

**Pros:**

- Visible in CO status.

**Cons:**

- Confuses "Lifecycle Status" (Approved/Rejected) with "Visibility Status" (Archived).
- A CO is "Implemented", that is its final lifecycle state. "Archived" is about the *hosting branch* visibility.

---

## 4. Recommendation

**I recommend Option 1.** It correctly places the business logic in the domain service and leverages the existing `soft_delete` mechanism of the `Branch` entity to achieve "archival" (hidden from active lists but available in history).

### Plan for Plan Phase

1. Implement `archive_change_order_branch` in `ChangeOrderService`.
2. Add integration test `test_change_order_branch_archive.py`.
