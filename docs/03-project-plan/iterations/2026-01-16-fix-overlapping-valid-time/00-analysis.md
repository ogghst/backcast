# Analysis: Fix Overlapping Valid Time Constraint (TD-058)

**Date:** 2026-01-16
**Status:** ✅ **APPROVED**
**Driver:** Technical Debt Register

---

## 1. Problem Statement

### 1.1 Context

As identified in **[TD-058] Overlapping valid_time Constraint**, the current Entity Version Control System (EVCS) implementation lacks a constraint to prevent overlapping `valid_time` ranges for the same entity (same `root_id` and branch).

### 1.2 Issue

When using the `control_date` parameter for time-travel updates (correcting history) or future scheduling, it is possible to create version nodes that have overlapping `valid_time` ranges.

**Example:**

- Version A: `valid_time = [2026-01-01, Infinity)`
- Update with `control_date=2026-02-01` creates Version B.
- If not handled correctly, we might end up with:
  - Version A: `valid_time = [2026-01-01, Infinity)` (Unclosed)
  - Version B: `valid_time = [2026-02-01, Infinity)`
- A query for `as_of=2026-03-01` would return **both** versions.

### 1.3 Impact

- Time-travel queries return incorrect/duplicate results.
- "Zombie" entities may appear.
- Data integrity potentially compromised.

---

## 2. Options

### Option 1: Application-Level Constraint (Selected)

Implement checks within `CreateVersionCommand` and `UpdateVersionCommand` to ensure that any new version's `valid_time` does not overlap with existing versions for the same `root_id` on the same branch.

**Pros:**

- Centralized logic in the core branching module.
- Database agnostic (mostly).
- Easier to implement complex temporal logic than pure SQL constraints (though PostgreSQL `EXCLUDE` constraints are powerful, they are complex with bitemporal data).

**Cons:**

- Potential race conditions if not inside a strict transaction with locking (Acceptable for now as updates are transactional).

### Option 2: Database Exclusion Constraint

Use PostgreSQL `EXCLUDE USING gist` constraint on the table.

**Pros:**

- Strongest guarantee.
  **Cons:**
- Requires significant schema migration.
- Complex to implement with bitemporal (valid_time + transaction_time) and branching logic (requires custom operator classes).

---

## 3. Selected Approach: Option 1

We will modify the core `Command` classes in the backend to strictly enforce non-overlapping ranges.

### Key Logic

1.  **Pre-write check**: Before inserting a new version, query for existing versions of the same `root_id` and branch.
2.  **Overlap Validation**: Ensure the new `valid_time` range does not overlap with any existing record's `valid_time`.
    - Note: Normally, an update _closes_ the previous version. The issue is when we insert a version "in the middle" or fail to close the predecessor correctly in complex scenarios. The logic must ensure proper chaining.
3.  **Safety Net**: Update query methods to use `DISTINCT ON` or similar mechanisms to handle legacy bad data if necessary, though the primary fix is preventing creation.

---

## 4. References

- [Technical Debt Register](../technical-debt-register.md)
- [Temporal Query Reference](../../../02-architecture/cross-cutting/temporal-query-reference.md)
