# Implementation Plan: WBE Level Inference

## Goal

Remove manual "Level" input from WBE creation/editing and automatically infer it from the parent WBE's level in the backend.

## Steps

### 1. Frontend Changes

- [ ] **Modify `WBEModal.tsx`**:
  - Remove the `Form.Item` for "Level".
  - Ensure clean form submission without the level field.

### 2. Backend Changes

- [ ] **Update `WBEService.create_wbe`**:
  - Before creating the command, check if `wbe_in.parent_wbe_id` is set.
  - If set, fetch the parent WBE to get its `level`.
  - calculate `new_level = parent.level + 1`.
  - If `parent_wbe_id` is None, `new_level = 1`.
  - Inject `level` into the `CreateVersionCommand`.
- [ ] **Update `WBEService.update_wbe`**:
  - check if `wbe_in.parent_wbe_id` is present (meaning it's being changed).
  - If changed, fetch new parent and recalculate level.
  - If changed to None, set level to 1.
  - Add `level` to `UpdateVersionCommand` arguments.

### 3. Verification

- [ ] Restart backend (if needed for code reload, though dev server should handle it).
- [ ] Test creating a root WBE (should be level 1).
- [ ] Test creating a child WBE (should be parent level + 1).
- [ ] Test moving a WBE (updating parent) adjusts the level.
