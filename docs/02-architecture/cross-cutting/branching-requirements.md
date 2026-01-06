# Branching and Versioning Requirements

**Last Updated:** 2025-12-29  
**Source:** PRD Section 8.4  
**Status:** Active

This document specifies the comprehensive branching and versioning architecture for the Backcast EVS system, enabling isolated work on change orders and complete entity history tracking.

---

## Overview

The system implements a Git-like branching and versioning architecture that supports:
- **Isolated Workspaces:** Change orders work in separate branches without affecting main production data
- **Complete History:** Immutable audit trail of all entity changes
- **Time Travel:** Reconstruct entity state at any historical point
- **Safe Experimentation:** Model change impacts before applying to production

---

## 1. Entity Versioning (Composite Identity)

### 1.1 Composite Primary Key Architecture

All entities support versioning through a unified mechanism based on **Composite Primary Key**:

**Head Tables:**
- Primary Key: `(id, branch)` for branch-enabled entities
- Purpose: Stable identity and current state pointers
- Example: `Project`, `WBE`, `CostElement`

**Version Tables:**
- Primary Key: `(head_id, valid_from)`
- Purpose: Immutable historical snapshots
- Fields: `valid_to`, `version`, `status`, `created_by_id`

### 1.2 Version Creation

When an entity is modified:
1. Close current version: `UPDATE SET valid_to = now() WHERE valid_to IS NULL`
2. Create new version record with updated data
3. Increment version number
4. Set `valid_from = now()`, `valid_to = NULL`

**Result:** Immutable audit trail within specific branch context

---

## 2. Branch-Enabled Entities

### 2.1 Branch Support

Branch-enabled entities maintain additional `branch` field identifying which branch the entity version belongs to.

**Entities with Branch Support:**
- WBE (Work Breakdown Element)
- CostElement
- Related financial data (costs, forecasts, earned values)

**Entities without Branch Support (Non-Branching):**
- User
- Department
- Project (parent level, not copied)

### 2.2 Branch Types

**Main Branch:**
- Name: `"main"`
- Purpose: Production branch with all approved, active project data
- Default: All operational reporting and EVM calculations use main branch
- Cannot be locked or deleted

**Change Order Branches:**
- Name format: `"co-{identifier}"`
- Purpose: Isolated branches for change order modifications
- Created: Automatically when change order is created
- Lifecycle: Can be locked, merged, or deleted

---

## 3. Branch Creation and Management

### 3.1 Branch Creation (Deep Copy)

When a change order branch is created:

**Process:**
1. Generate unique branch identifier: `co-{short_id}` from change order ID
2. Perform **Deep Copy** of Project and all WBEs from 'main' to new branch
3. Copy all active CostElements and related data
4. Maintain same logical IDs, but create distinct database rows

**Isolation:** Complete independence between branches

### 3.2 Supported Branch Operations

| Operation | Description | Authorization |
|-----------|-------------|---------------|
| **Create** | Deep copy from main | Project Manager |
| **List** | View all branches for project | Any authenticated user |
| **Lock** | Prevent modifications | Project Manager |
| **Unlock** | Re-enable modifications | Project Manager |
| **Delete** | Remove branch data | Admin only |
| **Merge** | Apply changes to main | Project Manager + approval |

---

## 4. Branch Context and Filtering

### 4.1 Composite Primary Key Enforcement

The system uses Composite PK `(id, branch)` to natively enforce branch context:

**Query Rules:**
- All queries for branch-enabled entities **MUST** include `branch` parameter
- No automatic fallback to main branch
- **Strict Isolation:** If entity not found in current branch, it doesn't exist in that context

**Example:**
```sql
-- Correct: Explicit branch filter
SELECT * FROM wbe WHERE id = 'uuid' AND branch = 'co-123';

-- Incorrect: Missing branch filter
SELECT * FROM wbe WHERE id = 'uuid';
```

### 4.2 Context Persistence

**Session-Based:**
- Branch selection is request-scoped
- Persisted per user session on backend
- Client doesn't need to restate branch on every request

**UI Integration:**
- Branch selector in application header
- All views automatically filter by selected branch
- Clear visual indicator of current branch context

---

## 5. Branch Isolation and Data Copying

### 5.1 Full Copy Isolation Strategy

**Initialization:**
- Upon branch creation, all relevant active entities copied from 'main' to new branch
- Each entity gets new version in new branch context
- Logical ID remains constant, but database row is distinct

**Modifications:**
- All updates, deletions, creations within branch affect **only that branch's data**
- Main branch remains completely untouched

**Independence:**
- Logical ID shared across branches (same WBE in main and branch)
- Physical database rows are separate (distinct composite PKs)

### 5.2 Version Lineage

**Within Branch:**
- Entity has version history within its branch
- `version` field increments per modification
- `parent_version_id` links to previous version in same branch

**Cross-Branch:**
- No direct version linkage between branches
- Merge operation creates new versions in target branch

---

## 6. Branch Comparison

### 6.1 Comparison Capabilities

The system provides comprehensive comparison between any branch and main (or between any two branches):

**Detected Changes:**
- **Created Entities:** New WBEs or CostElements added in branch
- **Updated Entities:** Modified entities with field-level differences
- **Deleted Entities:** Soft-deleted entities in branch
- **Financial Impact:** Summary of budget, revenue, forecast changes

**Output:**
- Change summary: counts of created/updated/deleted
- Detailed diff: field-level changes for each entity
- Financial summary: total budget impact, revenue changes

### 6.2 Comparison API

**Endpoints:**
```
GET /api/v1/projects/{id}/branches/{branch}/compare
GET /api/v1/projects/{id}/branches/{branch1}/compare/{branch2}
```

**Response Format:**
```json
{
  "summary": {
    "created_count": 5,
    "updated_count": 12,
    "deleted_count": 2
  },
  "created": [{entity}],
  "updated": [{entity, changes: {field: {old, new}}}],
  "deleted": [{entity}],
  "financial_impact": {
    "budget_delta": 50000,
    "revenue_delta": 0
  }
}
```

---

## 7. Branch Merging

### 7.1 Merge Operation

When change order is approved and implemented, merge branch into main:

**Atomic Process:**
1. Validate: Check for conflicts, verify branch not locked
2. **Create new versions** in main branch for all modified entities
3. **Apply all changes:** creates, updates, deletes from branch to main
4. **Preserve history:** Previous main branch versions retained
5. **Handle relationships:** Ensure WBE-CostElement hierarchies maintained
6. **Mark merged:** Set all branch entities with `status="merged"`
7. **Notify:** Generate notifications to stakeholders

**Atomicity:** All-or-nothing operation. Either all changes applied successfully, or operation fails with no changes to main.

### 7.2 Merge Preview

Before confirming merge:
- Show complete comparison (as in section 6)
- Display financial impact summary
- List all entities that will be modified in main
- Require explicit user confirmation

### 7.3 Merge Validation

**Pre-Merge Checks:**
- Branch not locked
- No concurrent modifications to main entities
- All required approvals obtained
- Change order status = "approved"

**Conflict Detection:**
- Identify if same entity modified in both main and branch since branch creation
- Present conflict resolution options to user

---

## 8. Branch Locking

### 8.1 Lock Mechanism

**Purpose:** Prevent modifications when branch should be read-only (e.g., under review)

**Rules:**
- Only applicable to change order branches (main cannot be locked)
- Includes reason for locking with timestamp and user
- Prevents all modification operations (create, update, delete)
- Allows read-only access to locked branch data

**Lock Record:**
```json
{
  "branch": "co-123",
  "locked": true,
  "locked_at": "2025-01-15T10:30:00Z",
  "locked_by": "user-uuid",
  "lock_reason": "Under review by finance department"
}
```

### 8.2 Lock Operations

| Operation | Authorization | Effect |
|-----------|---------------|--------|
| **Lock** | Project Manager, Admin | Prevents all writes |
| **Unlock** | Project Manager, Admin | Re-enables writes |
| **Check Status** | Any user | View lock state |

**UI Indication:**
- Lock status visible in branch selector
- Visual indicator (lock icon) when branch is locked
- Modification attempts show meaningful error message

---

## 9. Version History and Time Machine

### 9.1 Time Travel Queries

The system provides robust capabilities to view project state at any past point in time.

**Query Pattern:**
```sql
SELECT * FROM entity_version
WHERE head_id = 'entity-id'
  AND branch = 'target-branch'
  AND valid_from <= 'target-timestamp'
  AND (valid_to > 'target-timestamp' OR valid_to IS NULL)
```

**Simplified by Composite PK:** Time machine queries are range queries on specific branch partition.

### 9.2 Supported Time Travel Scenarios

**T1 (Active History):**
- Viewing active state of entity at past date
- Entity currently active, retrieve past version

**T2 (Deleted Head):**
- Viewing entity at past date when it was active, even if currently deleted
- Handles soft-deleted entities

**T3 (Deleted Past):**
- Correctly showing "no data" for dates when entity was effectively deleted
- Returns null for periods where entity didn't exist

**T4 (Cross-Branch):**
- Viewing history of specific change order branch independent of main
- Each branch has separate version timeline

**T5 (Reactivation Gap):**
- Correctly handling gaps where entity was deleted and later restored
- Multiple validity ranges for same logical entity

---

## 10. Entity Lifecycle Operations

### 10.1 Standard Operations with Versioning

**Create:**
- Creates new head entity with `version=1`
- Creates initial version with `status="active"`
- Sets `valid_from=now()`, `valid_to=NULL`

**Update:**
- Closes current version (`valid_to=now()`)
- Creates new version with updated data
- Increments version number
- Preserves all previous versions

**Soft Delete:**
- Creates new version with `status="deleted"`
- Preserves all previous versions for recovery
- Entity remains queryable in historical views

**Restore:**
- Creates new version with `status="active"`
- Based on most recent deleted version
- New version number, new validity range

**Hard Delete:**
- Permanently removes all versions of entity
- Only allowed for already soft-deleted entities
- Requires administrative privileges
- Cannot be undone

### 10.2 Version Sequence Integrity

**Guarantees:**
- Version numbers sequential within branch
- No gaps in version sequence
- `valid_from` of version N+1 = `valid_to` of version N
- Complete audit trail preserved

---

## 11. Query Filtering and Default Behavior

### 11.1 Automatic Filtering

**Active Status Filtering:**
- Default queries return only `status="active"` entities
- Override with `include_deleted=true` parameter

**Latest Version Filtering:**
- When multiple versions exist, return only latest (where `valid_to IS NULL`)
- Override with specific timestamp for time travel

**Branch Filtering:**
- For branch-enabled entities, automatic filter by current branch context
- Must be explicitly specified in query or from session context

**Combined Filtering Example:**
```sql
-- Default query behavior
SELECT *
FROM wbe_version wv
JOIN wbe w ON (wv.head_id = w.id AND wv.branch = w.branch)
WHERE w.branch = 'co-123'  -- from session context
  AND wv.valid_to IS NULL   -- latest version
  AND wv.status = 'active'  -- only active
```

### 11.2 Override Capabilities

For administrative and reporting operations:
- Access deleted entities: `include_deleted=true`
- Access allversions: `all_versions=true`
- Access specific timestamp: `as_of_date=YYYY-MM-DD`
- Cross-branch queries: Explicitly specify multiple branches

---

## 12. Merged View Service

### 12.1 Purpose

Display entities from both main and branch in unified view, clearly indicating change status.

### 12.2 Change Status Indicators

| Status | Meaning | Display |
|--------|---------|---------|
| **Unchanged** | Exists in both, identical data | Grey/default styling |
| **Created** | Exists only in branch | Green highlight, "NEW" badge |
| **Updated** | Modified in branch | Yellow highlight, "MODIFIED" badge |
| **Deleted** | Exists in main, deleted in branch | Red strikethrough, "DELETED" badge |

### 12.3 Implementation

**Algorithm:**
1. Fetch all entities from main branch
2. Fetch all entities from target branch
3. For each logical ID:
   - If in both: Compare data, mark as unchanged/updated
   - If only in branch: Mark as created
   - If only in main: Mark as deleted

**Use Cases:**
- Change order impact review before merge
- Branch comparison UI
- Approval workflow visualization

---

## 13. Performance Considerations

### 13.1 Indexing Strategy

**Required Indexes:**
```sql
-- Head tables
CREATE INDEX idx_head_branch ON wbe(id, branch);

-- Version tables
CREATE INDEX idx_version_lookup ON wbe_version(head_id, branch, valid_from);
CREATE INDEX idx_version_active ON wbe_version(head_id, branch, valid_to) WHERE valid_to IS NULL;
CREATE INDEX idx_version_time_travel ON wbe_version(head_id, branch, valid_from, valid_to);
```

### 13.2 Query Optimization

**Best Practices:**
- Always include branch in WHERE clause
- Use covering indexes for common queries
- Partition large tables by branch
- Use `EXPLAIN ANALYZE` for slow queries

---

## 14. Security and Authorization

### 14.1 Branch Access Control

| Role | Main Branch | Change Order Branches |
|------|-------------|----------------------|
| Admin | Full access | Full access, can delete |
| Project Manager | Full access | Create, lock, merge, view |
| Department Manager | Read assigned cost elements | Read only |
| Viewer | Read summary data | No access |

### 14.2 Branch Operations Authorization Matrix

| Operation | Required Role | Additional Checks |
|-----------|---------------|-------------------|
| Create Branch | Project Manager | Change order exists |
| Lock Branch | Project Manager | Branch not main |
| Unlock Branch | Project Manager | User locked it or Admin |
| Merge Branch | Project Manager | Change order approved |
| Delete Branch | Admin | Branch not main, not merged |

---

**See Also:**
- [Functional Requirements](functional-requirements.md) - Complete system capabilities
- [EVM Requirements](evm-requirements.md) - EVM calculations in branch context
- [Glossary](glossary.md) - Branching terminology definitions
