# Analysis: Epic 6 - Branch Archival UI (E06-U08 Finalization)

**Created:** 2026-02-24
**Request:** identify next task to complete story e06-u08 and start a pdca iteration using analysis-prompt.md

---

## Clarified Requirements

The backend `ChangeOrderService` already implements the `archive_change_order_branch()` method (from epic-06-branch-archival iteration), which soft-deletes a Change Order branch after it is "Implemented" or "Rejected". However, this capability is currently unavailable to users. The next required step involves exposing this functionality via a REST API endpoint and crafting the frontend interactions to trigger the archival safely with proper updates to the UI states.

### Functional Requirements

- Complete the backend loop by exposing `POST /api/v1/change-orders/{change_order_id}/archive`.
- Re-generate the frontend API client.
- Add a new React Query mutation `useArchiveChangeOrder`.
- Provide a user interface allowing authorized users to archive eligible (Implemented/Rejected) Change Orders.

### Non-Functional Requirements

- User confirmation is required before archival.
- The UI should react properly once the operation is complete (e.g., removing the item from active scope or triggering query invalidation).

### Constraints

- The backend `archive_change_order_branch` strictly filters for "Implemented" and "Rejected" types; UI components must similarly disable elements when state conditions do not match.

---

## Context Discovery

### Product Scope

- Relevant user stories: E06-U08 - Delete/Archive Branches.
- Business requirements: Old branches or rejected drafts clutter the active application landscape. Users need a reliable way to hide them without losing audit records.

### Architecture Context

- Bounded contexts involved: Evcs-Core (Branching) and Change Order Workflow.
- Existing patterns to follow: Ant Design Popconfirm modals and strict use of custom `useMutation` hooks decoupled from components. Backend endpoints usually apply dependency injection to wrap service calls.

### Codebase Analysis

**Backend:**

- Existing related APIs: `backend/app/api/routes/change_orders.py` has route endpoints but misses `archive`.
- Similar patterns: The branch merge mutation (`/merge`) functions similarly as a POST command.

**Frontend:**

- Comparable components: We have `ChangeOrderList.tsx` for visualizing tables and `WorkflowActions.tsx`/`WorkflowButtons.tsx` in the detail view for triggering workflow changes.
- State management: `TanStack React Query` handles cache; `useChangeOrders` invalidations should clear the list immediately upon archival.

---

## Solution Options

### Option 1: Action Menu in Change Orders List

**Architecture & Design:**
Add a dropdown menu (or icon) in the Action column within the `ChangeOrderList.tsx` table.

**UX Design:**
The user views all active change orders in the table. Rows that refer to "Implemented" or "Rejected" COs display an "Archive" icon button. Clicking triggers a confirmation modal. Once confirmed, the row naturally disappears as the data un-renders.

**Implementation:**

- Edit `ChangeOrderList.tsx`'s column definition (`ProjectList.columns.tsx` equivalent if refactored, otherwise inline).
- Add `useArchiveChangeOrder` hook.
- Implement the POST endpoint in FastAPI.

**Trade-offs:**

| Aspect          | Assessment                                                                     |
| --------------- | ------------------------------------------------------------------------------ |
| Pros            | Fast execution without navigating to details. Good for bulk visual management. |
| Cons            | Can crowd the action columns.                                                  |
| Complexity      | Low                                                                            |
| Maintainability | Good                                                                           |
| Performance     | Normal                                                                         |

---

### Option 2: Action Button within Change Order Detail Page

**Architecture & Design:**
Place the archive action exclusively inside `ChangeOrderDetail.tsx` under the top header actions (e.g., inside `WorkflowActions.tsx`).

**UX Design:**
The user opens a completed Change Order. Beside the workflow status, a "Archive Branch" button appears. When clicked, it asks for confirmation. Doing so redirects the user back to the change orders list.

**Implementation:**

- Add button and standard Ant Design `Modal.confirm` in `WorkflowActions.tsx`.
- Include the React Router `useNavigate` to redirect to `/change-orders` upon success.

**Trade-offs:**

| Aspect          | Assessment                                                                             |
| --------------- | -------------------------------------------------------------------------------------- |
| Pros            | Cleaner list view. Intention matches the single-entity focus of the detail page.       |
| Cons            | Forces the user to click into each Change order simply to archive them piece by piece. |
| Complexity      | Low                                                                                    |
| Maintainability | Good                                                                                   |
| Performance     | Normal                                                                                 |

---

### Option 3: Combined Approach (List Context Menu + Detail Action)

**Architecture & Design:**
Implement both Option 1 and Option 2 using a shared, abstracted sub-component.

**UX Design:**
Allows fluid archival either directly from the list, or from within the details page for ultimate flexibility.

**Implementation:**

- Create an abstracted `<ArchiveChangeOrderButton />` component that accepts `changeOrderId`, `status`, and `onSuccess` callback.
- Embed in both table and detail page.

**Trade-offs:**

| Aspect          | Assessment                                                         |
| --------------- | ------------------------------------------------------------------ |
| Pros            | Best user experience for varied workflows. Follows DRY principles. |
| Cons            | Slightly more initial setup.                                       |
| Complexity      | Medium                                                             |
| Maintainability | Excellent                                                          |
| Performance     | Normal                                                             |

---

## Comparison Summary

| Criteria           | Option 1 (List Area) | Option 2 (Detail Area)           | Option 3 (Both)     |
| ------------------ | -------------------- | -------------------------------- | ------------------- |
| Development Effort | 2 hrs                | 2 hrs                            | 3 hrs               |
| UX Quality         | Good                 | Fair                             | Excellent           |
| Flexibility        | High                 | Low                              | High                |
| Best For           | Bulk cleanup         | Auditing an item then closing it | Complete experience |

---

## Recommendation

**I recommend Option 3 because:** Creating a reusable `<ArchiveChangeOrderButton />` solves the need for maintaining both single view actions and list-view quick actions, while keeping the API hook code and modal confirmation safely encapsulated. It requires nominally more effort, but fulfills our objective cleanly.

---

## Decision Questions

1. Do you agree with moving forward with Option 3 (creating a shared button for both list and detail views)?
2. The current backend logic strictly throws a ValueError if an active CO is archived. Do you want to hide the button entirely if the UI hasn't reached an end-state ("Implemented" / "Rejected"), or show it disabled?

---

## References

- [EVCS Core Temporal Documentation](../../02-architecture/cross-cutting/temporal-query-reference.md)
- [Story E06-U08 Epic documentation](./../../iterations/2026-02-07-epic-06-branch-archival/COMPLETION_SUMMARY.md)
