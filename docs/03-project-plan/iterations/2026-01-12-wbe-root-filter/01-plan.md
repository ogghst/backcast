# Implementation Plan: WBE Root Filter

## Goal

Restrict the Project Detail WBE list to only Level 1 (Root) WBEs by fixing the backend filtering logic.

## Steps

### 1. Backend Changes

- [ ] **Modify `WBEService.get_wbes`**:
  - Add `apply_parent_filter: bool = False` argument.
  - Update logic:
    ```python
    if apply_parent_filter:
        stmt = stmt.where(WBE.parent_wbe_id == parent_wbe_id)
    ```
  - Check call sites to ensure no regression.
- [ ] **Modify `api/routes/wbes.py`**:
  - In `read_wbes`, determine `apply_parent_filter`.
  - `apply_parent_filter = (parsed_parent_id is not None) or is_root_query`
  - Pass this flag to `service.get_wbes`.

### 2. Verification

- [ ] **Test**: Verify `GET /api/v1/wbes?parent_wbe_id=null` returns only root elements.
- [ ] **Test**: Verify `GET /api/v1/wbes` (no params) still returns all elements (or defaults).
- [ ] **Frontend**: Verify Project Detail page shows only Level 1 items.
