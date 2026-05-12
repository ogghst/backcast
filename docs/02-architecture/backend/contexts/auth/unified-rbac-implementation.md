# Unified RBAC Implementation

**Last Updated:** 2026-05-11
**Status:** Complete (May 2026)
**Related ADR:** [ADR-014: Unified RBAC System](../../../decisions/ADR-014-unified-rbac.md)

---

## Overview

The Unified RBAC system is a comprehensive refactoring that replaced three separate authorization mechanisms (System RBAC, Project Roles, and Change Order Approvals) with a single, coherent system supporting scoped role assignments.

**Key Achievement:** One `UnifiedRBACService` now handles all authorization logic with support for global, project, and change_order scoped roles.

---

## Quick Reference

### Primary Components

| Component | File | Purpose |
|-----------|------|---------|
| **UnifiedRBACService** | `backend/app/core/rbac_unified.py` | Central RBAC service with cache-first permissions |
| **UserRoleAssignment** | `backend/app/models/domain/user_role_assignment.py` | Entity for scoped role assignments |
| **RoleChecker** | `backend/app/api/dependencies/auth.py` | FastAPI dependency for global authorization |
| **ProjectRoleChecker** | `backend/app/api/dependencies/auth.py` | FastAPI dependency for project-scoped authorization |

### Scope Types

- **GLOBAL**: System-wide roles (replaced `User.role` field)
- **PROJECT**: Project-scoped roles (replaced `ProjectMember` entity)
- **CHANGE_ORDER**: Change order scoped roles with authority levels (replaced `ApprovalMatrixService`)

### Cache Architecture

- **Permissions Cache**: 1-hour TTL for role → permissions mapping
- **Assignment Cache**: 5-minute TTL for user + scope → roles mapping
- **Performance Target**: <5ms for cached permission checks

---

## Implementation Documentation

For detailed implementation planning, analysis, and execution records, see the Unified RBAC Refactoring iteration:

### 1. Analysis Phase
**File:** [../../../../../03-project-plan/iterations/2026-05-10-unified-rbac-refactoring/00-analysis.md](../../../../../03-project-plan/iterations/2026-05-10-unified-rbac-refactoring/00-analysis.md)

**Contents:**
- PMI-aligned stakeholder analysis
- Architecture compliance review (EVCS patterns, bounded contexts)
- Enhanced risk register with quantitative analysis
- Solution options comparison (Full Unification vs Incremental vs Minimal)
- Cost estimation and schedule analysis
- Change control impact assessment

### 2. Planning Phase
**File:** [../../../../../03-project-plan/iterations/2026-05-10-unified-rbac-refactoring/01-plan.md](../../../../../03-project-plan/iterations/2026-05-10-unified-rbac-refactoring/01-plan.md)

**Contents:**
- Detailed task breakdown (28 tasks across 7 phases)
- Task dependency graph for parallel execution
- Test specification (unit, integration, migration, performance, security)
- Risk assessment and mitigation strategies
- Rollback plan and success criteria
- Implementation notes and phase execution order

### 3. Key Implementation Files

| File | Purpose |
|------|---------|
| `backend/app/core/rbac_unified.py` | `UnifiedRBACService` with two-tier caching |
| `backend/app/models/domain/user_role_assignment.py` | `UserRoleAssignment` entity (non-versioned) |
| `backend/app/schemas/user_role_assignment.py` | Pydantic CRUD schemas |
| `backend/app/api/routes/user_role_assignments.py` | Role assignment CRUD API |
| `alembic/versions/xxx_unified_rbac_part1.py` | Create user_role_assignments table |
| `alembic/versions/xxx_unified_rbac_part2.py` | Migrate User.role and ProjectMember data |

---

## Migration Summary

### From Old System

| Old Component | Replacement |
|---------------|-------------|
| `User.role` field | `UserRoleAssignment` with `scope_type='global'` |
| `ProjectMember` entity | `UserRoleAssignment` with `scope_type='project'` |
| `ApprovalMatrixService` | `UserRoleAssignment` with `scope_type='change_order'` + authority levels |
| `JsonRBACService` / `DatabaseRBACService` | `UnifiedRBACService` (single source of truth) |

### Migration Strategy

- **Approach:** Big bang migration (no parallel systems)
- **Data Integrity:** 100% loss-free migration verified with comprehensive tests
- **Audit Trail:** Preserved `granted_by`, `granted_at`, `expires_at` for all assignments
- **Rollback:** Database backup and restore procedures tested

---

## Testing Summary

### Test Coverage

- **Unit Tests:** 90%+ coverage for `UnifiedRBACService`
- **Integration Tests:** `RoleChecker` and `ProjectRoleChecker` dependencies
- **Migration Tests:** Data integrity and audit trail preservation
- **Performance Tests:** <5ms target for cached checks verified
- **Security Tests:** Privilege escalation, cache poisoning, audit trail integrity

### Quality Metrics

- **MyPy Strict Mode:** Zero errors
- **Ruff Linting:** Zero errors
- **Test Coverage:** 80%+ for all new modules
- **Performance:** p50 <5ms, p95 <10ms for cached permission checks

---

## Architecture Decisions

### Key Design Choices

1. **Non-Versioned Entity:** `UserRoleAssignment` uses `SimpleEntityBase` (not versioned) because role assignments are security metadata, not business-critical data. Audit trail provides sufficient history.

2. **Big Bang Migration:** Complete replacement of three systems in one deployment. Chosen for architectural purity despite higher risk (mitigated with comprehensive testing).

3. **Two-Tier Cache:** Separate caches for permissions (long-lived) and assignments (shorter-lived) optimizes for the read-heavy workload of permission checks.

4. **Authority Level Metadata:** Change order approvers store authority levels in `metadata_` JSONB field for flexibility and extensibility.

5. **ContextVar Session Injection:** Thread-safe pattern for request-scoped database sessions in concurrent WebSocket connections.

### Relationship to ADR-007

[ADR-007: RBAC Service Design](../../../decisions/ADR-007-rbac-service.md) established the foundation for RBAC in the system. ADR-008 extends this pattern with scoped permissions and unified authorization. The abstract interface pattern from ADR-007 is preserved, but the implementation evolved from JSON-based to database-backed with scoped role assignments.

---

## Related Documentation

- **Current ADR:** [ADR-014: Unified RBAC System](../../../decisions/ADR-014-unified-rbac.md)
- **Historical ADR:** [ADR-007: RBAC Service Design](../../../decisions/ADR-007-rbac-service.md)
- **Backend Auth Architecture:** [./architecture.md](./architecture.md)
- **Frontend Authentication:** [../../../frontend/contexts/06-authentication.md](../../../frontend/contexts/06-authentication.md)

---

## Maintenance Notes

### Cache Management

- **Permissions Cache:** Automatically refreshed on role/permission changes via `refresh_permissions_cache()`
- **Assignment Cache:** Automatically invalidated on write operations (assign/revoke/update)
- **Manual Refresh:** Available via admin API if needed

### Performance Monitoring

Key metrics to monitor:
- Permission check latency (target: <5ms cached)
- Cache hit/miss rates (target: >95% permissions, >90% assignments)
- Concurrent request handling (target: 100 rps without errors)

### Common Operations

**Check user's roles for a project:**
```python
roles = await unified_service.get_user_roles(
    user_id, ScopeType.PROJECT, project_id
)
```

**Assign a role with authority level:**
```python
await unified_service.assign_role(
    user_id=user_id,
    role_id=approver_role_id,
    scope_type=ScopeType.CHANGE_ORDER,
    scope_id=change_order_id,
    metadata={"authority_level": "HIGH"},
    granted_by=admin_user_id,
)
```

**Check approval authority:**
```python
has_auth = await unified_service.has_authority_level(
    user_id=user_id,
    required_authority="HIGH",
    scope_id=change_order_id,
)
```

---

## Future Enhancements

Potential areas for future expansion (not currently in scope):

1. **Department-Level Scoping:** Add `DEPARTMENT` scope type for organizational hierarchy
2. **WBE-Level Scoping:** Add `WBE` scope type for work breakdown element access
3. **Role Inheritance:** Implement hierarchical role structures (admin inherits all permissions)
4. **Permission Wildcards:** Support patterns like `project-*` for bulk permissions
5. **Audit Trail Enhancement:** Add `UserRoleAssignmentAudit` table for complete change history

---

**Implementation Status:** ✅ Complete (May 2026)
