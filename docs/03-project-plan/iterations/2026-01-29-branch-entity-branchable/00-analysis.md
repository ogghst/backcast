# Analysis: Make Branch Entity Branchable

**Created:** 2026-01-29  
**Request:** Modify the Branch entity to be a branchable temporal entity, preventing architectural violations where users can create entities at a branch with a control date before the change order creation.

---

## Clarified Requirements

The Branch entity currently uses a simple entity pattern (`created_at/deleted_at`) but references ChangeOrder entities which are branchable temporal entities. This creates an architectural violation:

**Problem:** A user can create entities on a branch with a `control_date` that is _before_ the branch/change order was created, violating temporal consistency.

**Solution:** Make Branch a branchable entity with full bitemporal tracking (`valid_time`, `transaction_time`), ensuring temporal queries can properly validate that entities cannot exist on a branch before the branch itself exists.

### Functional Requirements

- Branch entity must support bitemporal versioning (`valid_time`, `transaction_time`)
- Branch must be queryable with time-travel (`as_of` parameter)
- Branch creation must respect `control_date` for temporal consistency
- Existing branch operations (lock/unlock) must remain functional
- Foreign key-like validation in services must check branch existence at `control_date`

### Non-Functional Requirements

- Maintain backward compatibility with existing branch queries
- No data loss during migration
- Tests must cover temporal boundary enforcement

### Constraints

- Branch uses composite PK `(name, project_id)` which must be preserved
- ChangeOrder already has `branch_name` referencing Branch
- Branch is project-scoped (same branch name can exist in different projects)
- Migration must handle existing data gracefully

---

## Context Discovery

### Product Scope

- **User Story:** Enable proper temporal validation of branch-entity relationships
- **Business Requirement:** Prevent data inconsistency where entities pre-date their containing branch

### Architecture Context

**Bounded Contexts:**

- **EVCS Core** - Temporal versioning and branching infrastructure
- **Change Order Management** - Workflow and branch lifecycle

**Existing Patterns:**

- [Entity Classification Guide](file:///home/nicola/dev/backcast_evs/docs/02-architecture/backend/contexts/evcs-core/entity-classification.md) defines Simple/Versionable/Branchable tiers
- [Temporal Query Reference](file:///home/nicola/dev/backcast_evs/docs/02-architecture/cross-cutting/temporal-query-reference.md) documents bitemporal query patterns
- All branchable entities use `EntityBase + VersionableMixin + BranchableMixin`

**Architectural Constraints:**

- Use `TemporalService._apply_bitemporal_filter()` for all time-travel queries
- Branch name must remain stable (cannot version the composite PK directly)

### Codebase Analysis

**Backend - Current State:**

- [Branch Model](file:///home/nicola/dev/backcast_evs/backend/app/models/domain/branch.py) - Simple entity with `created_at/deleted_at`
- [BranchService](file:///home/nicola/dev/backcast_evs/backend/app/services/branch_service.py) - Basic CRUD without temporal support
- [Branch Schema](file:///home/nicola/dev/backcast_evs/backend/app/models/schemas/branch.py) - API schema `BranchPublic`
- [Branch Migration](file:///home/nicola/dev/backcast_evs/backend/alembic/versions/XXXX_add_branches_table.py) - Original table creation

**Backend - Reference Implementations:**

- [ChangeOrder Model](file:///home/nicola/dev/backcast_evs/backend/app/models/domain/change_order.py) - Branchable entity pattern
- [Mixins](file:///home/nicola/dev/backcast_evs/backend/app/models/mixins.py) - `VersionableMixin`, `BranchableMixin`
- [BranchableService](file:///home/nicola/dev/backcast_evs/backend/app/core/branching/service.py) - Full temporal service

**Tests:**

- [test_branch_model.py](file:///home/nicola/dev/backcast_evs/backend/tests/unit/test_branch_model.py) - Basic unit tests
- [test_branch_service.py](file:///home/nicola/dev/backcast_evs/backend/tests/unit/test_branch_service.py) - Service tests
- [test_change_order_workflow_full_temporal.py](file:///home/nicola/dev/backcast_evs/backend/tests/integration/test_change_order_workflow_full_temporal.py) - Temporal workflow tests

---

## Solution Options

### Option 1: Full Branchable Entity Conversion

**Architecture & Design:**

Convert Branch from a simple entity to a branchable entity, following the established pattern (ChangeOrder, Project, WBE, etc.).

**Changes:**

1. **Branch Model:** Add `VersionableMixin`, `BranchableMixin`, replace `created_at` with temporal fields
2. **New BranchVersion Table:** Rename table to `branch_versions` (follows naming convention)
3. **BranchService:** Extend or replace with `BranchableService[Branch]`
4. **Migration:** Convert existing data to temporal format

**Trade-offs:**

| Aspect          | Assessment                                               |
| --------------- | -------------------------------------------------------- |
| Pros            | Full consistency with other entities, proper time-travel |
| Cons            | Significant refactor, composite PK complexity            |
| Complexity      | High                                                     |
| Maintainability | Good (follows established patterns)                      |
| Performance     | Same as other branchable entities                        |

---

### Option 2: Versionable Entity (Without Branching)

**Architecture & Design:**

Convert Branch to a versionable entity (bitemporal) but without branch field (since Branch _is_ the branch).

**Changes:**

1. **Branch Model:** Add `VersionableMixin` only (no `BranchableMixin`)
2. **BranchService:** Extend `TemporalService[Branch]`
3. **Migration:** Convert existing data to temporal format, keeping composite PK

**Trade-offs:**

| Aspect          | Assessment                                                   |
| --------------- | ------------------------------------------------------------ |
| Pros            | Simpler than full branchable, achieves temporal validation   |
| Cons            | New pattern (versionable with composite PK), less consistent |
| Complexity      | Medium                                                       |
| Maintainability | Fair (new pattern to document)                               |
| Performance     | Same as other versionable entities                           |

---

### Option 3: Hybrid - Temporal Fields without Versioning

**Architecture & Design:**

Add temporal fields (`valid_time`, `transaction_time`) to Branch without full version history (keep single-row-per-branch pattern).

**Changes:**

1. **Branch Model:** Add temporal columns, but updates modify in-place (like a "current snapshot" pattern)
2. **BranchService:** Add `as_of` filtering without full EVCS versioning
3. **Migration:** Add columns to existing table

**Trade-offs:**

| Aspect          | Assessment                                      |
| --------------- | ----------------------------------------------- |
| Pros            | Minimal change, solves immediate problem        |
| Cons            | Anti-pattern (temporal without true versioning) |
| Complexity      | Low                                             |
| Maintainability | Poor (inconsistent with architecture)           |
| Performance     | Best (no version history)                       |

---

## Comparison Summary

| Criteria           | Option 1: Branchable | Option 2: Versionable | Option 3: Hybrid |
| ------------------ | -------------------- | --------------------- | ---------------- |
| Development Effort | High (3-4 days)      | Medium (2-3 days)     | Low (1 day)      |
| Consistency        | Excellent            | Good                  | Poor             |
| Flexibility        | Full time-travel     | Full time-travel      | Limited          |
| Best For           | Long-term arch       | Pragmatic solution    | Quick fix        |

---

## Recommendation

**I recommend Option 2: Versionable Entity because:**

1. **Branch doesn't branch itself** - A Branch entity doesn't need to exist on multiple branches, it _is_ the branch
2. **Solves the core problem** - Bitemporal tracking enables temporal validation
3. **Simpler implementation** - No need for `BranchableMixin` complications with composite PK
4. **Pragmatic balance** - Less work than Option 1, architecturally sound unlike Option 3

**Alternative consideration:**

Choose Option 1 if there's a future requirement for "branch templates" or "branch cloning" that would need branch-level versioning. However, this seems unlikely given the current domain model.

---

## Decision Questions

1. **Branch Versioning Semantics:** When a branch is locked/unlocked, should this create a new version (full history) or update in-place (simpler)?

2. **Root ID Strategy:** Should we add a `branch_id` UUID as a root identifier (following `project_id`, `wbe_id` patterns) or continue using the composite PK `(name, project_id)` as the lookup key?

3. **Frontend Impact:** Are there branch-related frontend queries that would need `as_of` support?

---

## References

- [Temporal Query Reference](file:///home/nicola/dev/backcast_evs/docs/02-architecture/cross-cutting/temporal-query-reference.md)
- [Entity Classification Guide](file:///home/nicola/dev/backcast_evs/docs/02-architecture/backend/contexts/evcs-core/entity-classification.md)
- [ADR-005: Bitemporal Versioning](file:///home/nicola/dev/backcast_evs/docs/02-architecture/decisions/ADR-005-bitemporal-versioning.md)

---

## Decision (2026-01-29)

**Approved:** Option 2 - Versionable Entity

**Key Decisions:**

1. **Lock/unlock updates in-place** - No version history for lock state changes
2. **Add `branch_id` UUID** - Following existing entity patterns (`project_id`, `wbe_id`)
3. **Frontend BranchSelector** - Will support `as_of` temporal queries

**Next Phase:** [01-plan.md](01-plan.md)
