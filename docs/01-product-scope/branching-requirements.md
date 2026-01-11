# Branching Requirements

**Last Updated:** 2026-01-07
**Status:** Active
**Related:** [ADR-005: Bitemporal Versioning](../02-architecture/decisions/ADR-005-bitemporal-versioning.md) | [EVCS Core Architecture](../02-architecture/backend/contexts/evcs-core/architecture.md)

---

## Overview

The Backcast EVS branching system provides Git-like versioning capabilities for all business entities. This enables isolated development of change orders, impact analysis before approval, and complete audit trails of all modifications.

---

## Branch Types

### Main Branch

- **Name:** `main`
- **Purpose:** Production state of all entities
- **Characteristics:**
  - Single canonical version of each entity
  - Read/write for authorized users
  - Source for creating new branches
  - Target for approved change order merges

### Change Order Branches

- **Naming Convention:** `co-{change_order_id}`
  - Example: `co-abc123-def456` for change order with ID `abc123-def456`
- **Purpose:** Isolated workspace for developing change orders
- **Characteristics:**
  - Created as deep copy of `main` at creation time
  - Independent modifications don't affect `main`
  - Can be compared to `main` for impact analysis
  - Merged back to `main` upon approval
  - Deleted/archived after successful merge

---

## Entity Versioning Model

### Single-Table Bitemporal Pattern

Each versioned entity uses a single table storing all version snapshots:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique version identifier (PK) |
| `{entity}_id` | UUID | Stable entity root ID |
| `valid_time` | TSTZRANGE | Business validity period |
| `transaction_time` | TSTZRANGE | System recording period |
| `deleted_at` | TIMESTAMPTZ | Soft delete timestamp |
| `branch` | VARCHAR(80) | Branch name |
| `parent_id` | UUID | Previous version ID (DAG) |
| `merge_from_branch` | VARCHAR(80) | Merge source tracking |

### Bitemporal Tracking

- **Valid Time:** When the data was/is effective in the real world
- **Transaction Time:** When the record was created/modified in the database

This dual-time tracking enables:
- Time-travel queries to any past state
- Complete audit trail of all changes
- Correction of errors without losing history

---

## Branch Operations

### 1. Create Branch

**Purpose:** Create isolated workspace for change order development

**Operation:**
- Deep copy of current `main` state to new branch
- All entities cloned with new version IDs
- Parent relationships preserved
- Branch metadata stamped on all versions

**Implementation Status:** 🔴 API endpoint not implemented - Service layer only

**API Endpoint (Not Implemented):**
```
POST /api/v1/branches
{
  "change_order_id": "abc123-def456",
  "source_branch": "main",
  "new_branch": "co-abc123-def456"
}
```

**Service Method (Available):**
```python
BranchableService.create_branch(
    root_id=UUID,
    new_branch="co-abc123-def456",
    from_branch="main"
)
```

**Trigger:** Automatic when change order is created (planned)

---

### 2. Modify in Branch

**Purpose:** Make changes without affecting production

**Operation:**
- Updates create new versions on the branch only
- Main branch remains untouched
- Version chain (parent_id) maintained within branch
- All modifications tracked with audit info

**Implementation Status:** ✅ Implemented via branch query parameter

**API Endpoint:**
```
PUT /api/v1/projects/{project_id}?branch=co-abc123-def456
{...updates...}
```

**Service Method:**
```python
BranchableService.update(
    root_id=UUID,
    updates={...},
    branch="co-abc123-def456"
)
```

**Isolation:** Repository layer enforces branch separation

---

### 3. Compare Branches

**Purpose:** Impact analysis before change order approval

**Operation:**
- Compare current versions between branches
- Identify added, modified, deleted entities
- Calculate budget/cost variances
- Generate comparison report

**Implementation Status:** 🔴 Not implemented

**API Endpoint (Planned):**
```
GET /api/v1/branches/compare?source=co-abc123-def456&target=main
```

**Comparison Types:**
- Entity-level: Which entities changed
- Field-level: Which fields changed
- Aggregate-level: Budget totals, cost allocations
- Variance: EVM metric differences

**Output Formats:**
- JSON (API response)
- PDF (export for review)
- HTML (side-by-side view)

---

### 4. Merge Branch

**Purpose:** Apply approved change order to production

**Operation:**
- Close current versions on target branch
- Clone source versions to target branch
- Stamp with `merge_from_branch` for traceability
- Preserve merge history in version chain

**Implementation Status:** 🔴 API endpoint not implemented - Service layer only

**API Endpoint (Not Implemented):**
```
POST /api/v1/branches/merge
{
  "source_branch": "co-abc123-def456",
  "target_branch": "main"
}
```

**Service Method (Available):**
```python
BranchableService.merge_branch(
    root_id=UUID,
    source_branch="co-abc123-def456",
    target_branch="main"
)
```

**Merge Strategy:** Overwrite (source replaces target)

**Conflict Resolution:**
- Automatic: Source branch wins
- Manual: Future enhancement for three-way merge

**Post-Merge:**
- Source branch locked (planned)
- Audit trail updated
- Notifications sent (planned)

---

### 5. Lock/Unlock Branch

**Purpose:** Prevent modifications during review or after merge

**Operation:**
- Set branch status to locked/unlocked
- Enforced at repository layer
- Visual indicators in UI

**Implementation Status:** 🔴 Not implemented

**API Endpoint (Planned):**
```
PUT /api/v1/branches/{branch_name}/lock
{ "locked": true }
```

**RBAC:** Only approvers can lock/unlock branches

---

### 6. Delete/Archive Branch

**Purpose:** Cleanup after successful change order

**Operation:**
- Soft delete branch metadata
- Archive option preserves history
- Confirmation required

**Implementation Status:** 🔴 Not implemented

**API Endpoint (Planned):**
```
DELETE /api/v1/branches/{branch_name}
```

**Constraints:**
- Cannot delete `main` branch
- Cannot delete active branches
- Must have merge confirmation

---

## Entity Classification

### Decision Tree

```
Need version history?
├─ No → SimpleEntityProtocol (created_at, updated_at)
│         └─ Use for: Config, preferences, transient data
└─ Yes → Need branching?
          ├─ No → VersionableProtocol (valid_time, transaction_time)
          │        └─ Use for: Audit logs, immutable records
          └─ Yes → BranchableProtocol (adds branch, parent_id)
                   └─ Use for: Projects, WBEs, Cost Elements
```

### Branchable Entities

| Entity | Branchable | Reason |
|--------|------------|--------|
| Project | Yes | Change orders affect project scope |
| WBE | Yes | Inherits from project |
| Cost Element | Yes | Budget allocations change with COs |
| Schedule Registration | Yes | Baseline adjustments |
| Cost Registration | Yes | Actual costs tracked in COs |
| Forecast | Yes | EAC updates in isolation |

### Non-Branchable Entities

| Entity | Protocol | Reason |
|--------|----------|--------|
| User | Versionable | Audit trail needed, no CO workflow |
| Department | Versionable | Organizational structure with history tracking |
| Cost Element Type | Versionable | Reference data with change history |

---

## Time Travel Queries

### Control Date

The system supports querying entity state at any past point in time:

**API:**
```
GET /api/v1/projects/{project_id}?control_date=2025-12-01
```

**Service:**
```python
TemporalService.get_as_of(
    root_id=UUID,
    as_of_date=datetime(2025, 12, 1),
    branch="main"
)
```

**Use Cases:**
- Historical reporting
- Audit investigations
- "What did we know on this date?" analysis

---

## Audit Trail

### Version History

Every entity maintains complete version history:

- **Who:** User ID from auth context
- **When:** `transaction_time.lower` (SQL-side timestamp)
- **What:** Field differences between versions
- **Why:** Change order ID or manual entry

**API Endpoint:**
```
GET /api/v1/{entity}/{id}/history
```

**Response:**
```json
[
  {
    "version_id": "uuid",
    "valid_from": "2025-01-01T00:00:00Z",
    "created_at": "2025-01-01T10:30:00Z",
    "created_by": "user-uuid",
    "changes": {
      "budget": {"from": 100000, "to": 120000},
      "description": {"from": "Old", "to": "New"}
    },
    "branch": "main",
    "change_order_id": null
  }
]
```

---

## Soft Delete

### Deletion Model

- **Soft Delete:** Set `deleted_at` timestamp (reversible)
- **Hard Delete:** Not used for versioned entities
- **Cascade:** Child entities soft deleted when parent deleted

**Operations:**
- `soft_delete(root_id, branch)` - Mark as deleted
- `undelete(root_id, branch)` - Restore deleted entity
- `get_current()` - Excludes deleted by default

**Use Cases:**
- Accidental deletion recovery
- Cancelled change orders (keep audit trail)
- Project closure (preserve data)

---

## Branch Isolation Rules

### Repository Layer Enforcement

1. **Query Filtering:**
   - Always include branch condition
   - Default to user's selected branch from session
   - Join with user preferences if needed

2. **Write Validation:**
   - Check branch status (locked branches reject writes)
   - Verify parent exists on same branch
   - Validate foreign keys within branch context

3. **Merge Safety:**
   - Validate target branch not locked
   - Check for concurrent modifications
   - Atomic transaction for all entity merges

---

## UI Integration

### Branch Selector

**Location:** Application header (near user menu)

**Behavior:**
- Persistent per user session
- Dropdown lists all accessible branches
- Visual status indicators (🟢 active, 🔒 locked, ✅ merged)
- Default: `main`

**API:**
```
PUT /api/v1/user/session/branch
{ "branch": "co-abc123-def456" }
```

### Time Machine Control

**Location:** Application header (left of branch selector)

**Behavior:**
- Date picker for historical view
- Defaults to current date
- All queries filtered by control date
- Shows "Viewing as of: {date}" when set

**API:**
```
PUT /api/v1/user/session/control-date
{ "control_date": "2025-12-01" }
```

---

## Performance Considerations

### Indexing Strategy

```sql
-- GIST indexes for range queries (time travel)
CREATE INDEX ix_entity_valid_gist ON entity_versions USING GIST (valid_time);
CREATE INDEX ix_entity_tx_gist ON entity_versions USING GIST (transaction_time);

-- B-tree indexes for branch filtering
CREATE INDEX ix_entity_branch ON entity_versions (branch);
CREATE INDEX ix_entity_root ON entity_versions (entity_id);

-- Partial unique index: one current version per entity per branch
CREATE UNIQUE INDEX uq_entity_current_branch
ON entity_versions (entity_id, branch)
WHERE upper(valid_time) IS NULL
  AND upper(transaction_time) IS NULL
  AND deleted_at IS NULL;
```

### Query Performance Targets

| Operation | Target |
|-----------|--------|
| Get current version | <100ms |
| Time-travel query | <200ms |
| Branch comparison | <500ms |
| Merge operation | <2s |

---

## Security & Access Control

### RBAC Integration

| Role | Create Branch | Modify Branch | Merge | Delete |
|------|---------------|--------------|-------|--------|
| System Administrator | All | All | All | All |
| Project Manager | Own projects | Own projects | Own projects | Own projects |
| Department Manager | Read only | Read only | No | No |
| Project Controller | Read only | Read only | No | No |

### Branch-Level Permissions

- Users can only access branches for their assigned projects
- Cross-branch access requires explicit authorization
- Audit log tracks all branch operations

---

## Testing Strategy

### Unit Tests

- Command execution (create, update, merge, revert)
- Service method behavior
- Protocol compliance

### Integration Tests

- Branch creation and cloning
- Multi-entity operations
- Concurrent modification handling

### E2E Tests

- Change order workflow (create → modify → compare → merge)
- Branch switching in UI
- Time travel queries

---

## Migration Path

### From Dual-Table (ADR-002) to Single-Table (ADR-005)

For entities using the legacy dual-table pattern:

1. Create new single table with `TSTZRANGE` columns
2. Migrate data:
   - `valid_from` → `lower(valid_time)`
   - `valid_to` → `upper(valid_time)`
   - Head table → current versions
3. Update commands to generic pattern
4. Update services to extend `BranchableService[T]`
5. Drop old head/version tables

---

## Future Enhancements

### Planned Features

- [ ] Three-way merge with conflict resolution UI
- [ ] Branch rebasing
- [ ] Cherry-pick specific changes
- [ ] Branch permissions per user
- [ ] Merge preview before commit
- [ ] Automatic conflict detection
- [ ] Branch templates for common change types

### Under Consideration

- [ ] Distributed version control (multi-system sync)
- [ ] Branch dependencies (CO requires other CO)
- [ ] Nested branches (branches of branches)
- [ ] Change request workflow integration

---

## See Also

- [Functional Requirements: Change Order Management](functional-requirements.md#5-change-order-management)
- [EVM Requirements: Branch Context](evm-requirements.md#113-branch-context)
- [EVCS Core Architecture](../02-architecture/backend/contexts/evcs-core/architecture.md)
- [ADR-005: Bitemporal Versioning](../02-architecture/decisions/ADR-005-bitemporal-versioning.md)
- [ADR-006: Protocol-Based Type System](../02-architecture/decisions/ADR-006-protocol-based-type-system.md)
