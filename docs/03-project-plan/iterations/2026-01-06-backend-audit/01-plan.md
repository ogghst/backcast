# PLAN Phase: Backend Audit Gap Fix

**Date:** 2026-01-06
**Status:** Planning

## Phase 1: Context Analysis

### Problem Definition

The current EVCS architecture tracks _when_ data changed (Valid Time/Transaction Time) and _what_ changed (Versioned Rows), but fails to track _who_ changed it.

- `VersionableMixin` lacks a user identifier column.
- Services accept `actor_id` but do not pass it to the persistence layer in a meaningful way or the persistence layer drops it.
- This prevents auditability and accountability.

### Success Criteria

1.  **Schema Support:** `VersionableMixin` has a `created_by` (UUID) column, non-nullable (except perhaps for system initialization, but ideally strict).
2.  **Command Persistence:** `CreateVersionCommand`, `UpdateVersionCommand` and `SoftDeleteCommand` persist the `actor_id` into the `created_by` column of the _new_ version row.
3.  **Service Integration:** `TemporalService` (and subclasses like `ProjectService`) correctly pass the `actor_id` from the API layer to the Command layer.
4.  **Verification:** A test case explicitly verifies that after `create` and `update`, the `created_by` field matches the `actor_id`.

## Phase 3: Implementation Options

### Option A: `created_by` on Version (Immutable)

- **Concept:** Since every update creates a _new_ version row, we only need `created_by` on that row.
- **Semantics:** "Who created this specific version of the state?"
  - Initial Create: Version 1, created_by = User A.
  - Update: Version 2, created_by = User B.
- **Pros:** Simple, immutable suitable for EVCS.
- **Cons:** None.
- **Decision:** **Option A**.

### Option B: `created_by` and `updated_by`

- **Concept:** Add `updated_by` as well.
- **Analysis:** Since versions are immutable, `updated_by` would only be relevant if we allow updating metadata of a closed version (e.g. closing it). But the _new_ version captures the "Update" event. The "Closer" of the old version is implicitly the "Creator" of the new version.
- **Decision:** Redundant. Stick to Option A.

## Phase 4: Technical Design

### 1. Database Schema Changes (`app/models/mixins.py`)

Modify `VersionableMixin`:

```python
class VersionableMixin:
    # ... existing fields ...
    created_by: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)
    deleted_by: Mapped[UUID | None] = mapped_column(PG_UUID, nullable=True) # For Soft Delete
```

### 2. Command Updates (`app/core/versioning/commands.py`)

Update `VersionedCommandABC`:

- Add `actor_id: UUID` to `__init__`.

Update `CreateVersionCommand`:

- `__init__(..., actor_id: UUID, ...)`
- `execute(...) -> version.created_by = self.actor_id`

Update `UpdateVersionCommand`:

- `__init__(..., actor_id: UUID, ...)`
- `execute(...) -> new_version.created_by = self.actor_id`

Update `SoftDeleteCommand`:

- `__init__(..., actor_id: UUID, ...)`
- `execute(...) -> current.deleted_by = self.actor_id; current.soft_delete()`

### 3. Service Updates (`app/core/versioning/service.py`)

Update `TemporalService`:

- `create(..., actor_id: UUID, ...)` -> Pass to command
- `update(..., actor_id: UUID, ...)` -> Pass to command
- `soft_delete(..., actor_id: UUID)` -> Pass to command

### 4. Migration Strategy

1.  Generate Alembic migration.
2.  Provide default value (e.g., system user or simple uuid) for existing rows to satisfy `nullable=False` for `created_by`.

## Verification Plan

### Automated Tests

1.  **New Unit Test:** `tests/unit/core/versioning/test_audit.py`
    - Create a version -> Assert `created_by == actor_id`
    - Update a version -> Assert new `created_by == actor_id_2`
    - Soft delete -> Assert `deleted_by == actor_id_3`

## Phase 5: Risk Assessment

- **Risk:** Migration fails on existing constraints.
- **Mitigation:** Use a "System User" UUID for backfilling existing rows.

## Effort Estimation

- **Development:** 1-2 hours
- **Testing:** 0.5 hours
