# WBE Root Filter Iteration Review

## Summary

Fixed the issue where querying for Root WBEs (parent_id=null) was not working because the backend service was ignoring `None` values for `parent_wbe_id`.

## Changes Implemented

- **Backend Service**: Updated `WBEService.get_wbes` to accept an `apply_parent_filter` boolean flag. This forces the SQL query to include `WHERE parent_wbe_id IS [value]`, even if `[value]` is `None` (for root items).
- **Backend API**: Updated `read_wbes` route to calculate `apply_parent_filter` based on whether `parent_wbe_id` was explicitly provided (including as string "null").
- **Tests**: Added `test_get_wbes_param_filter` to verify Root-only, Child-only, and All-items queries.

## Results

- **Queries for Root WBEs** (`parent_wbe_id=null`) now correctly return only Level 1 items.
- **Queries for Child WBEs** (`parent_wbe_id=UUID`) work as expected.
- **Unfiltered queries** return all items (subject to pagination).

## Artifacts

- `docs/03-project-plan/iterations/2026-01-12-wbe-root-filter/00-analysis.md`
- `docs/03-project-plan/iterations/2026-01-12-wbe-root-filter/01-plan.md`
