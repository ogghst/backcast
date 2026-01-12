# Request Analysis: Create WBE 'Level' Field Inference

## Clarified Requirements

1.  **Remove Manual Input**: The 'Level' field should be removed from the "Create WBE" form in the frontend.
2.  **Automatic Inference**: The system must automatically calculate the WBE level based on its parent:
    - If `parent_wbe_id` is null (Root WBE), `level` should be 1.
    - If `parent_wbe_id` is provided, `level` should be `parent.level + 1`.
3.  **Scope**: This primarily applies to WBE creation. However, changing a WBE's parent (update) implies a potential change in level, which should also be handled to maintain consistency.

## Context Discovery Findings

**Product Scope:**

- **Usability**: Simplifying data entry removes error-prone manual steps.
- **Data Integrity**: Ensures hierarchy levels are always consistent with the actual parent-child relationship.

**Architecture Context:**

- **Bounded Context**: `backend/app/services/wbe.py` manages WBE logic.
- **Pattern**: Service layer orchestrates business logic before persisting via Repositories/Commands.
- **Standard**: "Thin controllers, fat services" - logic should reside in `WBEService`.

**Codebase Analysis:**

**Backend:**

- `WBEService.create_wbe`: Currently takes `WBECreate` model and passes it to `CreateVersionCommand`. It does not perform level calculation.
- `WBE` Model (`backend/app/models/domain/wbe.py`): Has a `level` column.
- `Simple Query`: `WBEService` already has methods to fetch WBEs, making it easy to look up a parent.

**Frontend:**

- `WBEModal.tsx`: Currently includes a `Form.Item` for "level".
- `WBECreate` Type: Includes `level` as an optional field.

---

## Solution Options

### Option 1: Backend-Side Inference (Recommended)

**Architecture & Design:**

- **Frontend**: Remove the 'Level' field from `WBEModal`.
- **Backend**: Modify `WBEService.create_wbe` to intercept the creation request.
  - Check if `wbe_in.parent_wbe_id` is present.
  - If present, fetch the parent WBE to obtain its `level`.
  - Set `wbe_in.level = parent.level + 1`.
  - If not present, set `wbe_in.level = 1`.
- **Update Handling**: Similarly, in `WBEService.update_wbe`, if `parent_wbe_id` is being changed, recalculate the level.

**UX Design:**

- User sees one less field. Form is cleaner.
- "Level" is an implementation detail of the hierarchy that the user doesn't need to manually manage.

**Implementation:**

- `frontend/src/features/wbes/components/WBEModal.tsx`: Remove `level` InputNumber.
- `backend/app/services/wbe.py`: Update `create_wbe` and `update_wbe`.
  - Need to efficiently fetch parent level.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | Guarantees data consistency; simplifies frontend; robust against API usage. |
| Cons | Requires an extra database read (to fetch parent) during creation. |
| Complexity | Low. |
| Maintainability | High. Logic is centralized in the service. |
| Performance | Negligible impact (one indexed lookup). |

### Option 2: Frontend-Side Inference

**Architecture & Design:**

- **Frontend**: Calculate level before submission.
  - Requires `WBEModal` to know the parent's level. Currently it only receives `parentWbeId`.
  - would need to pass `parentLevel` prop to `WBEModal` or fetch it.
- **Backend**: No changes, trusts the frontend provided level.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | No extra DB read on backend (if parent data is already in frontend state). |
| Cons | Brittle; API consumers (scripts, other apps) might send wrong levels; "Business logic in UI". |
| Complexity | Medium (need to ensure parent data is available). |
| Maintainability | Lower. Logic is scattered. |

---

## Comparison Summary

| Criteria           | Option 1 (Backend)            | Option 2 (Frontend)                |
| ------------------ | ----------------------------- | ---------------------------------- |
| Development Effort | Low                           | Medium                             |
| UX Quality         | High                          | High                               |
| Data Integrity     | **Guaranteed**                | Vulnerable                         |
| Best For           | Robust, long-term correctness | Quick hacks (not recommended here) |

## Recommendation

**I recommend Option 1 (Backend-Side Inference) because:**

1.  It places business logic (hierarchy rules) in the Domain/Service layer where it belongs.
2.  It prevents data inconsistency if WBEs are created via API/scripts directly.
3.  It simplifies the frontend component by removing responsibility.
4.  The performance cost of one PK lookup is trivial.

## Questions for Decision

1.  Should we also handle **re-leveling** children if a WBE is moved (parent changed)? (Assumption: Yes, for the moved node itself. Recursive re-leveling of _descendants_ is a more complex operation typically handled in a separate "Move" action, but we should at least handle the immediate node's level on update).

---

Created: 2026-01-12
Links:

- `backend/app/services/wbe.py`
- `frontend/src/features/wbes/components/WBEModal.tsx`
