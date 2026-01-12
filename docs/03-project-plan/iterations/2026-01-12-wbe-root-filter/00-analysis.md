# Request Analysis: Restrict Project Detail WBEs to Level 1

## Clarified Requirements

1.  **User Intent**: content on the Project Detail page (the WBE list) should only show top-level WBEs (Level 1).
2.  **Current Behavior**: It likely shows all WBEs (flattened) or behaves inconsistently because the "root only" filter is not correctly applied in the backend for paginated queries.
3.  **Constraint**: The frontend explicitly requests `parentWbeId: "null"`. The backend must interpret this as "Filter where `parent_wbe_id` IS NULL".

## Context Discovery Findings

**Codebase Analysis:**

**Frontend (`ProjectDetailPage.tsx`)**:

- Calls `useWBEs({ projectId, parentWbeId: "null" })`.
- Expects a list of Root WBEs.

**Backend (`api/routes/wbes.py`)**:

- `read_wbes` detects `parent_wbe_id="null"` and sets `is_root_query = True`.
- However, it falls through to calls `service.get_wbes(...)` passing `parent_wbe_id=None`.
- `service.get_wbes` interprets `parent_wbe_id=None` as "No Filter" (return all WBEs).

**Backend (`services/wbe.py`)**:

- `get_wbes(...)` signature: `parent_wbe_id: UUID | None = None`.
- Logic: `if parent_wbe_id: stmt = stmt.where(WBE.parent_wbe_id == parent_wbe_id)`.
- There is no way to pass "NULL" to this method to filter for roots using the current signature.

---

## Solution Options

### Option 1: Explicit Root Filter Flag in Service (Recommended)

**Architecture & Design:**

- Modify `WBEService.get_wbes` to accept an `is_root: bool = False` or similar flag.
- Or verify if `parent_wbe_id` can be a sentinel.
- Let's use a cleaner approach: Update `get_wbes` to handle `parent_wbe_id` filtering more explicitly.
  - Argument: `parent_wbe_id: UUID | None | Literal[False] = False`. (False = no filter, None = Root, UUID = specific). defaulting to False (No filter).
  - Actually, `None` is the pythonic "default".
  - Better: Add `filter_by_parent: bool = False`. If True and `parent_wbe_id` is None -> Root. If True and `parent_wbe_id` is Set -> Child.
  - Or just `root_only: bool = False`.

**Implementation:**

- Update `WBEService.get_wbes` signature.
- Update `read_wbes` route to pass `root_only=is_root_query`.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | Explicit, type-safe, fixes the logic gap. |
| Cons | Changes service signature. |
| Complexity | Low. |

### Option 2: Use `filters` string

**Architecture & Design:**

- Frontend changes `useWBEs` to send `{ filters: { level: 1 } }` instead of `parentWbeId: "null"`.
- Backend `get_wbes` already handles filters.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | No backend changes needed immediately (if level filter works). |
| Cons | `parentWbeId` param in API becomes misleading (can't use it for root). Semantically "Level 1" is "Root", but `parent_id IS NULL` is the source of truth. |

### Option 3: Separate Route or Branching

**Architecture & Design:**

- In `read_wbes`, if `is_root_query` is True, call `service.get_by_parent(..., parent_wbe_id=None)`.
- This returns a `List`, skipping pagination logic.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | Uses existing working method (`get_by_parent`). |
| Cons | Returns unpaginated list (inconsistent with general list). |

---

## Comparison Summary

| Criteria           | Option 1 (Service Update) | Option 2 (Frontend Filter) | Option 3 (Unpaginated) |
| ------------------ | ------------------------- | -------------------------- | ---------------------- |
| Development Effort | Low                       | Low                        | Low                    |
| UX Quality         | High (Paginated)          | High                       | Medium (No pagination) |
| Robustness         | High                      | Medium                     | Medium                 |

## Recommendation

**I recommend Option 1.** Modifying `WBEService.get_wbes` to correctly handle "Root Only" filtering is the most robust solution. It fixes the semantic gap in the service layer.

**Proposed Signature Change:**
Change `parent_wbe_id` default behavior? No, that breaks existing calls.
New arg: `apply_parent_filter: bool = False`.
If `apply_parent_filter` is True:
`stmt = stmt.where(WBE.parent_wbe_id == parent_wbe_id)` (works for None too).
If `apply_parent_filter` is False:
Ignore `parent_wbe_id`.

In Route:
`apply_parent_filter = (parsed_parent_id is not None) or is_root_query`

## Questions for Decision

1.  Is it acceptable to update the `WBEService` signature? (Yes, internal code).

---

Created: 2026-01-12
