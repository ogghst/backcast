# ADR-014: Unified RBAC System

**Status:** Accepted
**Date:** 2026-05-10
**Decision Makers:** Backend Team (proposed), System Architect (approved)
**Supersedes:** ADR-007 for scoped permissions and unified authorization

---

## Context

The application had three separate authorization systems that created conflicts and maintenance burden:

1. **System RBAC** (from ADR-007): Global role-based access via `User.role` field
2. **Project RBAC**: Project-scoped roles via `ProjectMember` entity
3. **Change Order Approvals**: Authority matrix via `ApprovalMatrixService`

**Problems:**

- **Checker Conflicts**: `RoleChecker` and `ProjectRoleChecker` couldn't be used together on the same route due to conflicting `user_role` resolution
- **Scoped Role Limitation**: Change order approvers needed per-project assignments (e.g., dept_head for Project A, viewer for Project B), but the system only supported global roles
- **System Maintenance**: Managing three separate authorization systems created technical debt and inconsistency

---

## Decision

We implemented a unified RBAC system with scoped role assignments that replaces all three previous systems.

### 1. UserRoleAssignment Entity

**New table** (`user_role_assignments`) replacing `User.role` and `ProjectMember`:

```python
class UserRoleAssignment(SimpleEntityBase):
    """Scoped role assignments for users."""
    id: UUID                      # Primary key
    user_id: UUID                 # FK to users.user_id (root ID)
    role_id: UUID                 # FK to rbac_roles.id
    scope_type: ScopeType         # global/project/change_order
    scope_id: UUID | None         # NULL for global
    metadata_: JSONB              # Stores authority_level, etc.
    granted_by: UUID              # User who granted the role
    granted_at: datetime          # When the role was granted
    expires_at: datetime | None   # Optional expiration

    __table_args__ = (
        UniqueConstraint("user_id", "scope_type", "scope_id"),
    )
```

**Scope Types:**
- **GLOBAL**: System-wide role (replaces `User.role`)
- **PROJECT**: Project-scoped role (replaces `ProjectMember`)
- **CHANGE_ORDER**: Change order scoped role (replaces `ApprovalMatrixService`)

### 2. UnifiedRBACService

**Single service** handling all authorization logic with cache-first approach:

**Key Methods:**
- `has_permission(user_id, permission, scope_type, scope_id)` - Check permission across scopes
- `get_user_roles(user_id, scope_type, scope_id)` - Get user's roles for a scope
- `assign_role(user_id, role_id, scope_type, scope_id, metadata, granted_by)` - Create assignment
- `revoke_role(user_id, scope_type, scope_id)` - Remove assignment
- `has_authority_level(user_id, required_authority, scope_id)` - Check approval authority
- `get_accessible_projects(user_id)` - List of project IDs user can access

**Permission Resolution Order:**
1. Check global roles (always)
2. Admin role bypasses all checks
3. Check scoped roles if not global scope

**Two-Tier Cache:**
- Permissions cache: `{role_name: (permissions_list, timestamp)}` (TTL: 1 hour)
- Assignment cache: `{(user_id, scope_type, scope_id): (role_names, timestamp)}` (TTL: 5 minutes)

### 3. UnifiedChecker FastAPI Dependency

**Single dependency** replacing `RoleChecker` and `ProjectRoleChecker`:

**Note:** The implementation retains the existing `RoleChecker` and `ProjectRoleChecker` classes for backward compatibility during migration, but they now delegate to `UnifiedRBACService` internally.

```python
class RoleChecker:
    """FastAPI dependency for authorization via UnifiedRBACService."""
    def __init__(
        self,
        allowed_roles: list[str] | None = None,
        required_permission: str | None = None,
    )
    async def __call__(current_user, session) -> User:
        # Checks roles/permissions via UnifiedRBACService
```

**Usage Examples:**

```python
# Global permission check
@router.get("/admin", dependencies=[Depends(RoleChecker(required_permission="user-delete"))])
async def admin_route(): ...

# Project-scoped permission check
@router.get("/projects/{project_id}",
    dependencies=[Depends(ProjectRoleChecker(required_permission="project-update"))])
async def project_route(project_id: UUID): ...
```

### 4. Authority Level Support

**Change order approvers** can have authority levels stored in `UserRoleAssignment.metadata`:

```python
metadata_ = {"authority_level": "HIGH"}  # LOW, MEDIUM, HIGH, CRITICAL
```

**Hierarchy:** CRITICAL > HIGH > MEDIUM > LOW

**Usage:** `UnifiedRBACService.has_authority_level(user_id, "HIGH", scope_id)` checks if user has sufficient authority.

### 5. Database Schema

**Migration:**
- Created `user_role_assignments` table
- Migrated `User.role` → `UserRoleAssignment` (scope_type='global')
- Migrated `ProjectMember` → `UserRoleAssignment` (scope_type='project')
- Dropped `project_members` table and `users.role` column (2026-05-16 cleanup iteration)

**Role Definitions:** Stored in `rbac_roles` and `rbac_role_permissions` tables (seeded from `config/rbac.json`)

### 6. Thread Safety

**ContextVar pattern** for request-scoped session injection:

```python
_unified_rbac_session: ContextVar[AsyncSession | None] = ContextVar("_unified_rbac_session")

def get_unified_rbac_session() -> AsyncSession | None:
    return _unified_rbac_session.get()

def set_unified_rbac_session(session: AsyncSession | None) -> None:
    _unified_rbac_session.set(session)
```

**Usage:** `set_unified_rbac_session(session)` before permission checks, `set_unified_rbac_session(None)` after.

### 7. Service Pattern Compliance

**Justified Deviation from SimpleService[T] Pattern:**

The `UnifiedRBACService` does not extend `SimpleService[T]` due to:

1. **Two-tier caching**: Permissions cache (1h TTL) + assignment cache (5min TTL)
2. **Singleton pattern**: Global service instance shared across requests
3. **ContextVar injection**: Per-request database session via ContextVar
4. **Complex authorization**: Permission resolution, scope hierarchy, authority levels

**CRUD Delegation:**

Basic CRUD operations delegate to `SimpleService[UserRoleAssignment]`:
- `assign_role()` → `SimpleService.create()`
- `update_assignment()` → `SimpleService.update()`
- `revoke_role()` → `SimpleService.delete()`

This maintains the benefits of the standard service pattern (command objects, consistent error handling) while preserving the specialized caching and authorization logic.

**Reference**: `app/core/rbac_unified.py` (lines 80-90, 553-634, 661-707)

---

## Alternatives Considered

### 1. Incremental Unification with Parallel Systems

**Approach:** Phase 1: Add `UserRoleAssignment` alongside existing systems. Phase 2: Migrate routes incrementally. Phase 3: Deprecate old systems.

**Pros:** Lower risk (gradual rollout), can test thoroughly in production, easier rollback

**Cons:** Longer timeline (months vs weeks), parallel systems increase maintenance burden temporarily, data sync complexity

**Decision:** Rejected in favor of big bang approach (chosen approach)

### 2. Minimal Unification - Fix Only Checker Conflicts

**Approach:** Modify `RoleChecker` to accept `scope_type` parameter and check both `User.role` and `ProjectMember` based on scope. Keep `ApprovalMatrixService` separate.

**Pros:** Minimal changes (lower risk), faster implementation (weeks vs months), no data migration needed

**Cons:** Doesn't fully solve problems (scoped roles, system maintenance), still maintaining three separate systems, no scoped role assignments (future enhancement needed)

**Decision:** Rejected - doesn't align with "full unification" requirement

---

## Consequences

### Positive

✅ **Single Coherent System**: One `UnifiedRBACService` handles all authorization logic

✅ **Flexible Scoped Assignments**: Users can have different roles at global, project, and change_order levels

✅ **Extensible Design**: Easy to add new scope types (department, WBE, etc.) in the future

✅ **Performance**: Cache-first design with <5ms target for cached permission checks

✅ **Audit Trail**: All role assignments have `granted_by`, `granted_at`, `expires_at` fields

✅ **Authority Levels**: Change order approvers can have hierarchical authority levels

✅ **Thread Safety**: ContextVar pattern ensures safe concurrent access in WebSocket sessions

✅ **Migration**: Big bang migration with complete data integrity (all users and project members migrated)

### Negative

⚠️ **Big Bang Risk**: Complete system replacement in one deployment (mitigated with comprehensive testing)

⚠️ **Data Migration Complexity**: Migrating from `User.role` and `ProjectMember` to `UserRoleAssignment` (mitigated with verification tests)

⚠️ **Cache Invalidation**: Need to invalidate assignment cache when roles are granted/revoked (handled automatically)

### Mitigations

- Comprehensive test suite (unit, integration, migration, performance, security)
- Database backup before migration
- Staged deployment (dev → staging → production)
- Rollback plan documented
- Performance monitoring during migration

---

## Usage Examples

### Checking Permissions

```python
from app.core.rbac_unified import get_unified_rbac_service
from app.models.domain.user_role_assignment import ScopeType

service = get_unified_rbac_service()

# Check global permission
has_perm = await service.has_permission(
    user_id=user.user_id,
    required_permission="user-delete",
    scope_type=ScopeType.GLOBAL,
    scope_id=None,
)

# Check project-scoped permission
has_perm = await service.has_permission(
    user_id=user.user_id,
    required_permission="project-update",
    scope_type=ScopeType.PROJECT,
    scope_id=project_id,
)

# Check change order approver authority
has_auth = await service.has_authority_level(
    user_id=user.user_id,
    required_authority="HIGH",
    scope_id=change_order_id,
)
```

### Assigning Roles

```python
from app.core.rbac_unified import get_unified_rbac_service
from app.models.domain.user_role_assignment import ScopeType

service = get_unified_rbac_service()

# Assign global admin role
assignment = await service.assign_role(
    user_id=user.user_id,
    role_id=admin_role_id,
    scope_type=ScopeType.GLOBAL,
    scope_id=None,
    granted_by=admin_user.user_id,
)

# Assign project manager role with metadata
assignment = await service.assign_role(
    user_id=user.user_id,
    role_id=manager_role_id,
    scope_type=ScopeType.PROJECT,
    scope_id=project_id,
    metadata={"authority_level": "HIGH"},
    granted_by=admin_user.user_id,
)
```

### Route Authorization

```python
from app.api.dependencies.auth import RoleChecker, ProjectRoleChecker

# Global permission check
@router.delete("/users/{user_id}",
    dependencies=[Depends(RoleChecker(required_permission="user-delete"))]
)
async def delete_user(user_id: UUID): ...

# Project-scoped permission check
@router.put("/projects/{project_id}",
    dependencies=[Depends(ProjectRoleChecker(required_permission="project-update"))]
)
async def update_project(project_id: UUID): ...
```

---

## Implementation Details

### Files Created/Modified

**New Files:**
- `backend/app/core/rbac_unified.py` - UnifiedRBACService implementation
- `backend/app/models/domain/user_role_assignment.py` - UserRoleAssignment entity
- `backend/app/schemas/user_role_assignment.py` - CRUD schemas
- `backend/app/api/routes/user_role_assignments.py` - CRUD API endpoints

**Modified Files:**
- `backend/app/api/dependencies/auth.py` - RoleChecker and ProjectRoleChecker delegate to UnifiedRBACService
- `backend/app/services/change_order_workflow_service.py` - Uses UnifiedRBACService for authority checks
- `backend/config/rbac.json` - Added `change_order_approver` role
- `backend/app/api/routes/users.py` - Admin checks via `_is_admin()` helper using UnifiedRBACService
- `backend/app/api/routes/auth.py` - Login notification resolves role via UnifiedRBACService
- `backend/app/ai/agent_service.py` - Role resolution via UnifiedRBACService
- `backend/app/ai/tools/templates/user_management_template.py` - `_resolve_user_role()` helper
- `backend/app/db/seeder.py` - Reads role from seed JSON, not `user.role` column
- `backend/app/models/schemas/user.py` - `from_user_async()` resolves role/permissions from UnifiedRBACService

**Migration Files:**
- `alembic/versions/20260510_add_user_role_assignments_table.py` - Create user_role_assignments table
- `alembic/versions/20260510b_migrate_existing_roles_to_unified_rbac.py` - Migrate User.role and ProjectMember data
- `alembic/versions/20260511_add_project_scoped_rbac_roles.py` - Add project-scoped RBAC roles
- `alembic/versions/20260511b_migrate_project_members_to_unified.py` - Migrate project members to unified
- `alembic/versions/1eba1b50cdf5_drop_project_members_table.py` - Drop project_members table (2026-05-16)
- `alembic/versions/fa57821982c7_drop_users_role_column.py` - Drop users.role column (2026-05-16)

**Deleted Files (2026-05-16 cleanup):**
- `backend/app/core/rbac.py` - RBACServiceABC, JsonRBACService (replaced by UnifiedRBACService)
- `backend/app/core/rbac_database.py` - DatabaseRBACService (replaced by UnifiedRBACService)
- `backend/app/models/domain/project_member.py` - ProjectMember entity (replaced by UserRoleAssignment)
- `backend/app/models/schemas/project_member.py` - ProjectMember schemas
- `backend/app/api/routes/project_members.py` - Project member API routes
- `backend/app/services/project_member.py` - ProjectMember service
- `backend/app/services/approval_matrix_service.py` - ApprovalMatrixService (integrated into UnifiedRBACService)
- `backend/tests/unit/core/test_rbac.py` - Tests for deleted legacy RBAC module
- `backend/tests/unit/core/test_rbac_project_access.py` - Tests for deleted legacy RBAC module
- `backend/tests/unit/core/test_rbac_database.py` - Tests for deleted legacy RBAC module

### Test Coverage

- Unit tests for UnifiedRBACService (cache, permissions, CRUD, authority levels)
- Integration tests for RoleChecker and ProjectRoleChecker
- Migration verification tests (data integrity, audit trail preservation)
- Performance benchmarks (<5ms for cached checks)
- Security tests (privilege escalation, expired roles, cache poisoning)

### Type Safety

- MyPy strict mode: ✅ Passing
- Explicit type annotations for all public methods
- Generic UUID types for user_id, role_id, scope_id

---

## Related Decisions

- [ADR-007: RBAC Service Design](./ADR-007-rbac-service.md) - Original RBAC system (superseded for scoped permissions)
- [ADR-005: Bitemporal Versioning](./ADR-005-bitemporal-versioning.md) - UserRoleAssignment is non-versioned (audit only)

---

## References

- Implementation Plan: [docs/03-project-plan/iterations/2026-05-10-unified-rbac-refactoring/01-plan.md](../../03-project-plan/iterations/2026-05-10-unified-rbac-refactoring/01-plan.md)
- Analysis: [docs/03-project-plan/iterations/2026-05-10-unified-rbac-refactoring/00-analysis.md](../../03-project-plan/iterations/2026-05-10-unified-rbac-refactoring/00-analysis.md)

---

## Changelog

| Date | Change | Author |
|---|---|---|
| 2026-05-10 | Initial ADR — Unified RBAC system with scoped role assignments | Backend Team |
| 2026-05-16 | Cleanup complete — all legacy RBAC artifacts removed, project_members and users.role dropped | Backend Team |
