# Analysis: TD-067 FK Constraint Refactoring (Phase 2)

**Status**: [DRAFT]
**Date**: 2026-02-23
**Author**: Antigravity (AI Architect)
**Iteration**: 2026-02-23-fk-refactoring-phase-2

## 1. Requirements Clarification

### 1.1 Intent

In a bitemporal system, root IDs (like `project_id`, `wbe_id`, `user_id`) are stable identifiers but are **not unique** at the database level because multiple versions of the same entity exist (one per row).

Standard PostgreSQL Foreign Key constraints require the target column to be UNIQUE or the PRIMARY KEY. Attempting to create an FK to a root ID in a bitemporal table is architecturally incorrect and often impossible or causes runtime errors if the database state contains multiple versions.

**Goal**: Complete the work started in the previous iteration by auditing and refactoring all remaining bitemporal entities to use **Application-Level Referential Integrity** instead of database FK constraints for relationships between versioned entities.

### 1.2 Requirements

- **Functional**:
  - Entity relationships must remain valid across version updates.
  - Queries must be able to resolve relationships based on root IDs at any point in time (`as_of`).
- **Technical**:
  - Remove invalid database FK constraints.
  - Maintain indexing on reference columns for performance.
  - Enforce integrity in the Service layer (validation on create/update).

## 2. Context Discovery

### 2.1 Audit Results

The following entities have been identified as having invalid database FK constraints pointing to non-unique root IDs:

| Entity             | Field                  | Target                          | Issue                               |
| :----------------- | :--------------------- | :------------------------------ | :---------------------------------- |
| `WBE`              | `project_id`           | `projects.project_id`           | Pointing to non-unique root ID      |
| `CostElement`      | `wbe_id`               | `wbes.wbe_id`                   | Pointing to non-unique root ID      |
| `CostElement`      | `cost_element_type_id` | `cost_element_types...`         | Pointing to non-unique root ID      |
| `Department`       | `manager_id`           | `users.user_id`                 | Pointing to non-unique Business Key |
| `CostElementType`  | `department_id`        | `departments.department_id`     | Pointing to non-unique root ID      |
| `CostRegistration` | `cost_element_id`      | `cost_elements.cost_element_id` | Pointing to non-unique root ID      |
| `ScheduleBaseline` | `cost_element_id`      | `cost_elements.cost_element_id` | Deprecated field with invalid FK    |
| `ProgressEntry`    | `cost_element_id`      | `cost_elements.cost_element_id` | Pointing to non-unique root ID      |

Entities already correctly implemented:

- `Branch.project_id` (No DB FK)
- `ChangeOrder.assigned_approver_id` (Fixed in Phase 1)
- `CostElement.schedule_baseline_id` (No DB FK)
- `CostElement.forecast_id` (No DB FK)

### 2.2 ADR Reference

This refactoring aligns with **ADR-005 (Bitemporal Versioning)** and established project patterns where referential integrity for temporal entities is managed in the application layer.

## 3. Solution Design

### Option 1: Standard Application-Level Integrity (Recommended)

Align all audited entities with the established pattern. Remove database constraints and rely on Service layer validation.

#### Technical Implementation

1. **Migration**:
   - Create a single Alembic migration that identifies and drops the FK constraints for all listed entities.
   - Keep the columns as `UUID` types with existing indexes.
2. **Models**:
   - Update SQLAlchemy models to remove the `ForeignKey` directive or update it to be "internal only" (if needed for relationships, though explicit joins are preferred in this architecture).
   - Add documentation comments to the models explaining the application-level enforcement.
3. **Services**:
   - Ensure `create` and `update` methods in relevant services (e.g., `WBEService`, `CostElementService`) validate the existence of the parent root ID.

#### Trade-offs

| Aspect              | Assessment                                                                             |
| :------------------ | :------------------------------------------------------------------------------------- |
| **Pros**            | • Architectural consistency<br>• Correct bitemporal semantics<br>• No DB schema errors |
| **Cons**            | • Risk of orphaned data if service layer validation is bypassed                        |
| **Complexity**      | Medium (due to volume of changes)                                                      |
| **Maintainability** | High (follows project standards)                                                       |

### Option 2: Database Triggers for Integrity

Implement custom triggers to check for existence of root IDs in parent tables.

#### Trade-offs

| Aspect         | Assessment                                                                             |
| :------------- | :------------------------------------------------------------------------------------- |
| **Pros**       | • Stronger DB-level enforcement                                                        |
| **Cons**       | • Opaque logic<br>• Maintenance burden<br>• Inconsistent with current project patterns |
| **Complexity** | High                                                                                   |

## 4. Recommendation

I recommend **Option 1**. It is the established pattern in this codebase (already applied to `Branch`, `ChangeOrder`, and leaf references in `CostElement`). It provides the best balance of correctness and maintainability for a bitemporal system.

## 5. Decision

**Selected Option**: Option 1
**Approved By**: [Pending User Approval]
**Date**: 2026-02-23
