# Analysis: TD-067 FK Constraint: Business Key vs Primary Key in Temporal Entities

**Status**: [DRAFT]
**Date**: 2026-02-07
**Author**: Antigravity (Backend Developer)
**Iteration**: 2026-02-07-td-067-fk-business-keys

## 1. Requirements Clarification

### 1.1 Intent

The objective is to fix a data integrity and logical defect in the `ChangeOrder` entity where the `assigned_approver_id` field has a database Foreign Key constraint referencing `users.id` (the **Version ID** of a user).

In a bitemporal system, `users.id` changes every time a user is updated (e.g., changing email, role, or even correcting a typo). If a Change Order links to a specific *Version ID*, the assignment becomes "stuck" to that historical version of the user. If the user profile is updated, the link points to a "stale" or "deleted" version, potentially breaking queries that look for "Current assignments for User X".

**Goal**: Ensure `ChangeOrder.assigned_approver_id` references the stable `users.user_id` (**Business Key**) so that assignments persist across user profile updates, while adhering to the system's bitemporal architecture patterns.

### 1.2 Requirements

- **Functional**:
  - `ChangeOrder` assignments must remain valid when the assigned `User` is updated.
  - Retrieving a Change Order should resolve the *current* state of the assigned approver (or the state *as_of* the query time).
  - Queries for "My Assignments" must work regardless of whether my user profile has changed since assignment.
- **Context/Constraint**:
  - `users` table is bitemporal (multiple rows per `user_id`).
  - Postgres Foreign Key constraints require the target column(s) to be Unique.
  - `users.user_id` is **NOT Unique** in the database (it allows multiple versions).
  - Therefore, a standard database FK constraint to `users.user_id` is **impossible**.

## 2. Context Discovery

### 2.1 Codebase Analysis

- **`ChangeOrder` Entity**:
  - Defined in `backend/app/models/domain/change_order.py`.
  - Field: `assigned_approver_id`.
  - Current Migration (`20260203_add_approval_matrix_fields.py`): Explicitly adds `op.create_foreign_key(..., ['assigned_approver_id'], ['id'])`.
  - **Defect confirmed**: It points to `users.id`.

- **Pattern Comparison**:
  - **`WBE` Entity**: References `projects.project_id`. **No FK Constraint** exists in DB (confirmed in `48c88d1ddf9c...py`).
  - **`CostElement` Entity**: References `wbe_id` and `cost_element_type_id`. Comments in `b2c3d4e5f6g7...py` explicitly state: *"No FK constraints... because in a bitemporal system, these are root IDs... Referential integrity is enforced at the application level."*
  - **`CostElementType`**: References `department_id`. Comment: *"No FK constraint... enforced at application level."*

### 2.2 Conclusion

The `ChangeOrder` FK constraint is an anomaly that violates the established architectural pattern for bitemporal entities in this codebase. The `users` table functions exactly like `projects` or `wbes` (bitemporal), so it cannot support a standard FK to its root ID.

## 3. Solution Design

### Option 1: Standard Application-Level Integrity (Recommended)

Align `ChangeOrder` with the existing pattern used by `WBE` and `CostElement`. Remove the database constraint and enforce integrity via the Service layer.

#### Structure

- **Database**:
  - Drop `fk_change_orders_assigned_approver`.
  - Migrate data: Update `assigned_approver_id` to store `users.user_id` (Business Key) instead of `users.id` (Version ID).
  - No new FK constraint added.
  - Index on `assigned_approver_id` remains for performance.
- **Backend**:
  - Update `ChangeOrder` model to clarify `assigned_approver_id` semantics.
  - Ensure `ChangeOrderService` validates existence of `user_id` during assignment (e.g., `user_service.exists(user_id)`).

#### Technical Implementation

- **Migration**:

    ```python
    def upgrade():
        # 1. Drop Constraint
        op.drop_constraint('fk_change_orders_assigned_approver', 'change_orders', type_='foreignkey')
        
        # 2. Data Migration (ID -> User_ID)
        # Note: Requires temporary column or careful update using join
        op.execute("""
            UPDATE change_orders 
            SET assigned_approver_id = users.user_id 
            FROM users 
            WHERE change_orders.assigned_approver_id = users.id
        """)
    ```

- **Service Layer**:
  - `ChangeOrderService.create/update`: Verify `assigned_approver_id` corresponds to a valid `User` (using `UserService`).

#### Trade-offs

| Aspect | Assessment |
| :--- | :--- |
| **Pros** | • Fixed the defect completely<br>• Fully consistent with existing architecture (WBE, CostElement)<br>• Zero performance overhead on writes (no DB FK check) |
| **Cons** | • Loss of database-enforced referential integrity (possible to have orphaned IDs if app logic fails)<br>• Requires data migration |
| **Complexity** | Low |
| **Maintainability** | High (Standard pattern) |

### Option 2: Integrity via Database Triggers

Implement the "logical" Foreign Key using PostgreSQL Triggers.

#### Structure

- **Database**:
  - Same migration as Option 1 (Drop FK, Data Migration).
  - Create a `BEFORE INSERT OR UPDATE` trigger on `change_orders`.
  - Trigger function checks if `exists(select 1 from users where user_id = new.assigned_approver_id)`.

#### Technical Implementation

- **Migration**:
  - Add `Op.execute` to create PL/pgSQL function and Trigger.

#### Trade-offs

| Aspect | Assessment |
| :--- | :--- |
| **Pros** | • Enforces integrity at Database level (safer than App level)<br>• Fixes the user update issue |
| **Cons** | • Introduces "Hidden logic" in triggers (harder to debug/maintain)<br>• Performance cost on every insert/update<br>• Deviates from project pattern (we don't use triggers elsewhere for this) |
| **Complexity** | Medium |
| **Maintainability** | Fair (Triggers can be opaque) |

### Option 3: Logic Patch (Status Quo + Band-aid)

Keep the invalid FK to `users.id`, but add logic to "Chase updates".

#### Structure

- **Backend Only**:
  - When a `User` is updated (new `id` generated), trigger a background job to find all `ChangeOrders` assigned to the *old* `id` and update them to the *new* `id`.

#### Trade-offs

| Aspect | Assessment |
| :--- | :--- |
| **Pros** | • No schema changes<br>• Keeps strict DB references to specific versions (if audit requires knowing *exactly which version* was assigned) |
| **Cons** | • Heavy complexity: Race conditions, distributed transaction issues<br>• "Chasing pointers" is a known anti-pattern<br>• Does not solve the fundamental query issue easily |
| **Complexity** | High |
| **Maintainability** | Poor |

## 4. Recommendation

**I recommend Option 1: Standard Application-Level Integrity.**

**Rationale:**

1. **Consistency**: It aligns `ChangeOrder` with `WBE`, `CostElement`, and `CostElementType` which already use this pattern successfully.
2. **Correctness**: It solves the "Stale Identity" problem by referencing the stable Business Key (`user_id`).
3. **Simplicity**: It avoids complex database triggers or fragile "pointer logic". The slight risk of broken references is mitigated by Service-level validation, which is standard in this architecture.

**Plan of Action:**

1. Create migration to drop FK and update data.
2. Update code documentation to reflect strict bitemporal linking rules.

## 5. Decision

**Selected Option:** Option 1 (Standard Application-Level Integrity)

**Approved By:** User
**Date:** 2026-02-07

**Rationale:**

- Best alignment with existing bitemporal architecture (WBE, CostElement).
- Solves the business problem of stable assignments.
- Lowest long-term maintenance cost.
