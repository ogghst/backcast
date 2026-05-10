# Analysis: Unified RBAC Refactoring

**Created:** 2026-05-10  
**Request:** Unify three separate authorization systems (System RBAC, Project Roles, Change Order Approval Matrix) into a single, coherent RBAC system with scoped role assignments

---

## Clarified Requirements

### Functional Requirements

**Core Problems to Solve:**
1. **Checker conflicts**: RoleChecker and ProjectRoleChecker cannot be used together on the same route due to conflicting `user_role` resolution (system role vs project role)
2. **Scoped change order roles**: Need per-project approver assignments (e.g., dept_head for Project A, viewer for Project B)
3. **System maintenance burden**: Managing three separate authorization systems creates technical debt and inconsistency

**Requirements:**
1. **Unified permission checker**: Single dependency (`UnifiedChecker`) that handles system, project, and change_order scope checks
2. **Scoped role assignments**: Support role assignments with scope_type (global/project/change_order) and scope_id
3. **Approval authority integration**: Merge ApprovalMatrixService into unified RBAC system
4. **Single source of truth**: All role/permission definitions in RBACRole/RBACRolePermission tables
5. **Authority level storage**: Store approval authority levels in UserRoleAssignment.metadata as JSON
6. **Big bang migration**: No backwards compatibility - complete replacement of existing systems

### Non-Functional Requirements

**Performance:**
- Permission checks must remain fast (target: <5ms for cached checks)
- Support high concurrency with thread-safe session management
- Cache TTL strategy similar to current DatabaseRBACService (5 minutes for project membership)

**Maintainability:**
- Single RBAC service implementation (no more multiple systems)
- Clear separation between role assignment and permission checking
- Extensible scope types for future needs (department, WBE, etc.)

**Security:**
- Fail-secure defaults (deny access if cache miss or system error)
- Audit trail for role assignments (granted_by, granted_at, expires_at)
- Support for temporary role assignments with expiration

### Constraints

**Technical Constraints:**
- Must use existing RBACRole/RBACRolePermission tables (already created)
- Must maintain compatibility with current User.role field during migration
- Must preserve existing permission semantics (no breaking changes to permissions)
- Must work with current ContextVar session injection pattern

**Time Constraints:**
- Big bang migration means complete feature must be delivered in one iteration
- Cannot have gradual rollout or parallel systems

**Architecture Constraints:**
- Must align with ADR-007 (RBAC Service Design) principles
- Must support existing AI assistant RBAC roles (ai-viewer, ai-manager, ai-admin)
- Must maintain EVCS entity patterns where applicable

---

## Context Discovery

### Product Scope

**Relevant User Stories:**
- Change order approval workflow requires per-project approver assignments
- Project management requires role-based access control at project level
- System administration requires global role management
- AI assistants require role-based tool filtering

**Business Requirements:**
- Single coherent authorization model across all system contexts
- Flexible role assignment to support organizational hierarchy
- Audit trail for all authorization decisions
- Support for temporary elevated permissions (e.g., contractors)

### Architecture Context

**Bounded Contexts Involved:**
1. **Auth Context**: User authentication, JWT tokens, session management
2. **User Management Context**: User domain, role assignments
3. **Project Management Context**: Project-level permissions, project members
4. **Change Management Context**: Change orders, approval workflow
5. **AI Context**: AI assistant role-based tool filtering

**Existing Patterns to Follow:**
- **SimpleEntityBase**: UserRoleAssignment should be non-versioned (like RBACRole, ProjectMember)
- **DatabaseRBACService**: Cache-first approach with TTL refresh
- **ContextVar session injection**: Thread-safe async session management
- **Service layer pattern**: Business logic in services, not in dependencies
- **FastAPI dependencies**: Declarative authorization via Depends()

**Architectural Constraints:**
- **ADR-007**: RBAC Service Design - must extend abstract interface pattern
- **ADR-005**: Bitemporal versioning - role assignments are non-versioned (audit only)
- **Layered architecture**: API → Services → Models (no repository pattern)

### Codebase Analysis

**Backend:**

**Existing Related APIs:**
- `/api/auth/login` - JWT token issuance (backend/app/api/routes/auth.py)
- `/api/v1/users/` - User management with system roles
- `/api/v1/projects/{id}/members` - Project member management
- `/api/v1/rbac/` - RBAC admin API for role/permission management

**Data Models:**
- `backend/app/models/domain/rbac.py` - RBACRole, RBACRolePermission (SimpleEntityBase)
- `backend/app/models/domain/project_member.py` - ProjectMember (SimpleEntityBase)
- `backend/app/models/domain/user.py` - User with `role` field (system role)
- `backend/app/models/domain/change_order.py` - ChangeOrder with approval workflow

**Similar Patterns:**
- **ProjectMember**: Non-versioned entity with user_id, project_id, role - pattern to follow for UserRoleAssignment
- **DatabaseRBACService**: Cache-first with TTL, ContextVar session injection - pattern to replicate
- **ApprovalMatrixService**: Authority level mapping - logic to integrate into unified service

**Key Files:**
- `backend/app/core/rbac.py` - RBACServiceABC, JsonRBACService, RoleChecker
- `backend/app/core/rbac_database.py` - DatabaseRBACService (current implementation)
- `backend/app/core/enums.py` - ProjectRole enum with permissions
- `backend/app/api/dependencies/auth.py` - RoleChecker, ProjectRoleChecker (conflicting)
- `backend/app/services/approval_matrix_service.py` - Approval authority validation
- `backend/app/services/change_order_config_service.py` - Workflow configuration

**Frontend:**

**Comparable Components:**
- Role management UIs (system roles, project roles)
- Project member management interfaces
- Change order approval interfaces

**State Management:**
- TanStack Query for server state (role assignments, permissions)
- Zustand for client state (UI state, form state)

**Routing Structure:**
- `/admin/rbac` - RBAC administration
- `/projects/{id}/settings/members` - Project member management
- `/change-orders/{id}` - Approval workflow UI

---

## Solution Options

### Option 1: Full Unification with UserRoleAssignment Entity (Recommended)

**Architecture & Design:**

**New Entity: UserRoleAssignment**
```python
# Non-versioned entity (SimpleEntityBase)
- id: UUID (PK)
- user_id: UUID (FK to users.user_id)
- role_id: UUID (FK to rbac_roles.id)  # Changed from role name to FK
- scope_type: Enum('global', 'project', 'change_order')
- scope_id: UUID | NULL  # NULL for global scope
- metadata: JSONB  # Stores authority_level, etc.
- granted_by: UUID (FK to users.user_id)
- granted_at: TIMESTAMP
- expires_at: TIMESTAMP | NULL
- __table_args__: (UniqueConstraint(user_id, scope_type, scope_id))
```

**New Service: UnifiedRBACService**
- `assign_role(user_id, role_id, scope_type, scope_id, metadata, granted_by)` - Create role assignment
- `revoke_role(user_id, role_id, scope_type, scope_id)` - Remove role assignment
- `has_permission(user_id, permission, scope_type, scope_id)` - Check permission across scopes
- `get_user_roles(user_id, scope_type, scope_id)` - Get user's roles for a scope
- `get_assignments_by_scope(scope_type, scope_id)` - Get all role assignments for a scope
- `refresh_cache()` - Reload role/permission mappings

**New Checker: UnifiedChecker**
```python
class UnifiedChecker:
    def __init__(self, required_permission: str, scope_type: str, scope_id_param: str = None)
    async def __call__(self, request) -> User:
        # 1. Get current user from JWT
        # 2. Check global roles first (cache)
        # 3. Check scoped roles if scope_type provided (cache)
        # 4. Return user if authorized, raise HTTPException if not
```

**Migration Strategy:**
1. Create UserRoleAssignment table
2. Migrate User.role → UserRoleAssignment (scope_type='global')
3. Migrate ProjectMember → UserRoleAssignment (scope_type='project')
4. Update all routes to use UnifiedChecker
5. Remove old systems (RoleChecker, ProjectRoleChecker, ApprovalMatrixService)

**UX Design:**

**Role Assignment UI:**
- Single unified interface for assigning roles at any scope
- Scope selector (Global / Project / Change Order)
- Role selector (filtered by applicability to scope)
- Authority level editor (for change_order approvers)
- Expiration date picker (optional)
- Audit trail showing who granted/revoked and when

**Permission Checker UI:**
- "Check Permissions" tool for admins
- User selector + scope selector
- Shows all granted permissions for that context
- Highlights which roles grant which permissions

**Implementation:**

**Key Technical Details:**
- **Cache strategy**: Two-tier cache (permissions cache + assignment cache)
  - Permissions cache: {role_id: [permissions]} (TTL: 1 hour)
  - Assignment cache: {(user_id, scope_type, scope_id): [role_ids]} (TTL: 5 minutes)
- **Database queries**: Single query per permission check (JOIN UserRoleAssignment → RBACRole → RBACRolePermission)
- **Session management**: Use existing ContextVar pattern for thread safety
- **Migration scripts**: Alembic migrations with data copying logic

**Integration Points:**
- Replace `RoleChecker` with `UnifiedChecker` in all routes
- Replace `ProjectRoleChecker` with `UnifiedChecker(scope_type='project')`
- Integrate `ApprovalMatrixService.can_approve()` into `has_permission()` with metadata check
- Update AI assistant role filtering to use role_id instead of role name

**Potential Technical Challenges:**
- **Complex permission checks**: Change order approval requires comparing authority levels in metadata
  - Solution: Add special method `has_authority_level(user_id, required_level, scope_id)` to service
- **Cache invalidation**: Need to invalidate assignment cache when roles are granted/revoked
  - Solution: Call `refresh_cache()` after write operations (same as current DatabaseRBACService)
- **Role name to ID migration**: Existing code uses role names (strings)
  - Solution: Keep role name as unique identifier, add role_id for foreign key (dual reference)

**Testing Approach:**
- Unit tests for UnifiedRBACService (permission checks, caching, role assignment)
- Integration tests for UnifiedChecker (FastAPI dependency)
- Migration tests (data integrity, backwards compatibility check)
- Performance tests (cache hit/miss rates, concurrent requests)
- Security tests (privilege escalation, expired roles, cache poisoning)

**Trade-offs:**

| Aspect          | Assessment                                 |
| --------------- | ------------------------------------------ |
| Pros            | - Single coherent authorization system<br>- Flexible scoped role assignments<br>- Extensible to future scope types<br>- Clear audit trail<br>- Resolves checker conflicts |
| Cons            | - Big bang migration is high-risk<br>- Complex permission checks (metadata-based)<br>- Requires extensive testing<br>- Temporary performance degradation during migration |
| Complexity      | High (new entity, service, checker, migration) |
| Maintainability | Excellent (single system, clear patterns) |
| Performance     | Good (cached checks, single DB query)     |

---

### Option 2: Incremental Unification with Parallel Systems

**Architecture & Design:**

**Phase 1: Add UserRoleAssignment alongside existing systems**
- Create UserRoleAssignment entity and service
- Implement UnifiedChecker in parallel with RoleChecker/ProjectRoleChecker
- Keep existing systems functional

**Phase 2: Migrate routes incrementally**
- Start with non-critical routes (e.g., dashboard, reports)
- Gradually migrate project and change order routes
- Keep old systems as fallback

**Phase 3: Deprecate old systems**
- Remove RoleChecker, ProjectRoleChecker, ApprovalMatrixService
- Clean up unused code and database columns

**UX Design:**
- Same as Option 1, but rolled out gradually
- Users see consistent UI throughout migration

**Implementation:**

**Key Technical Details:**
- Feature flags to enable/disable unified RBAC per route
- Database triggers to sync UserRoleAssignment with ProjectMember/User.role
- Gradual data migration (batch jobs)
- Monitoring and rollback plans

**Integration Points:**
- Add UnifiedChecker as optional dependency
- Routes can use old or new checker during migration
- API versioning to support both systems temporarily

**Potential Technical Challenges:**
- **Data consistency**: Keeping UserRoleAssignment in sync with ProjectMember/User.role during migration
  - Solution: Database triggers + application-level sync logic
- **Feature flag management**: Complex configuration during migration
  - Solution: Centralized feature flag service
- **Testing complexity**: Need to test both systems in parallel
  - Solution: Separate test suites for old and new systems

**Testing Approach:**
- A/B testing between old and new systems
- Canary deployments for gradual rollout
- Automated rollback tests

**Trade-offs:**

| Aspect          | Assessment                                 |
| --------------- | ------------------------------------------ |
| Pros            | - Lower risk (gradual rollout)<br>- Can test thoroughly in production<br>- Easier rollback if issues found<br>- Less performance impact |
| Cons            | - Longer timeline (months vs weeks)<br>- Parallel systems increase maintenance burden temporarily<br>- Data sync complexity<br>- Feature flag overhead |
| Complexity      | Medium (incremental changes, but complex coordination) |
| Maintainability | Fair (temporary complexity, better long-term) |
| Performance     | Excellent (no sudden load changes)         |

---

### Option 3: Minimal Unification - Fix Only Checker Conflicts

**Architecture & Design:**

**Keep existing systems, fix only the conflict:**
- Modify RoleChecker to accept `scope_type` parameter
- Modify ProjectRoleChecker to use RoleChecker internally
- Add scope-aware permission resolution to RBACServiceABC
- Keep ApprovalMatrixService separate (not unified)

**New Checker Implementation:**
```python
class UnifiedChecker(RoleChecker):  # Extend RoleChecker
    def __init__(self, required_permission: str, scope_type: str = 'global', scope_id_param: str = None)
    async def __call__(self, request) -> User:
        # Reuse RoleChecker logic with scope awareness
        # If scope_type='project', check project roles instead of system roles
```

**No new entities or services:**
- Keep User.role for system roles
- Keep ProjectMember for project roles
- Keep ApprovalMatrixService for change order approval
- Just fix the dependency conflict

**UX Design:**
- No changes to UI (same role assignment interfaces)
- Same user experience, just works correctly

**Implementation:**

**Key Technical Details:**
- Modify RoleChecker to check both User.role and ProjectMember based on scope_type
- Add `get_scoped_role(user_id, scope_type, scope_id)` to RBACServiceABC
- Implement in both JsonRBACService and DatabaseRBACService
- Update route dependencies to pass scope_type

**Integration Points:**
- Modify existing RoleChecker (minimal changes)
- Update ProjectRoleChecker to use modified RoleChecker
- No changes to services or data models

**Potential Technical Challenges:**
- **Three systems still exist**: Still managing separate authorization systems
  - Solution: Accept this as technical debt for now
- **Limited flexibility**: Can't easily add new scope types
  - Solution: Future enhancement if needed
- **Approval authority still separate**: Change order approval still uses ApprovalMatrixService
  - Solution: Keep as-is (not critical for all use cases)

**Testing Approach:**
- Unit tests for modified RoleChecker
- Integration tests for scope-based permission checks
- Regression tests for existing functionality

**Trade-offs:**

| Aspect          | Assessment                                 |
| --------------- | ------------------------------------------ |
| Pros            | - Minimal changes (lower risk)<br>- Faster implementation (weeks vs months)<br>- No data migration needed<br>- Solves immediate problem (checker conflicts) |
| Cons            | - Doesn't fully unify systems (technical debt remains)<br>- Still maintaining three separate systems<br>- No scoped role assignments (future enhancement needed)<br>- Approval authority still separate |
| Complexity      | Low (modifications to existing code only) |
| Maintainability | Fair (improves current state, but not ideal) |
| Performance     | Excellent (no new queries or cache layers) |

---

## Comparison Summary

| Criteria           | Option 1 (Full Unification) | Option 2 (Incremental) | Option 3 (Minimal Fix) |
| ------------------ | --------------------------- | ---------------------- | ---------------------- |
| Development Effort | 3-4 weeks                   | 6-8 weeks              | 1-2 weeks              |
| Risk Level         | High (big bang migration)   | Medium (incremental)   | Low (minimal changes)  |
| Solves All Problems| Yes                         | Yes (eventually)       | No (checker only)      |
| Maintainability    | Excellent                   | Good (after migration) | Fair (technical debt)  |
| Flexibility        | High (extensible)           | High (extensible)      | Low (rigid)            |
| Performance        | Good (cached)               | Excellent              | Excellent              |
| Migration Complexity| High (data migration)       | Medium (gradual)       | None                   |
| Best For           | Long-term architectural health | Production stability | Quick win, low risk    |

---

## Recommendation

**I recommend Option 1 (Full Unification with UserRoleAssignment Entity) because:**

1. **Solves the Complete Problem**: Addresses all three issues (checker conflicts, scoped roles, system maintenance burden) in one cohesive solution

2. **Aligns with Strategic Goals**: The clarified requirements explicitly state "Fully unify - merge ApprovalMatrixService into the unified RBAC system" and "Big bang migration (no backwards compatibility)"

3. **Architectural Integrity**: Creates a single, coherent authorization model that follows existing patterns (SimpleEntityBase, DatabaseRBACService cache strategy)

4. **Future-Proof Design**: Extensible scope types allow for future requirements (department-level roles, WBE-level roles) without major refactoring

5. **Audit Trail**: Built-in audit logging (granted_by, granted_at, expires_at) supports security and compliance requirements

6. **Clean Migration**: While risky, big bang migration avoids the complexity of parallel systems and feature flags

**Risk Mitigation Strategies:**
- Comprehensive test suite (unit, integration, migration, performance, security)
- Staged deployment (dev → staging → production with rollback plan)
- Performance monitoring during migration
- Backup/restore procedures for data migration

**Alternative consideration:** Choose Option 2 (Incremental Unification) if:
- Production stability is more important than architectural purity
- Timeline allows for 6-8 week gradual rollout
- Team prefers lower-risk incremental changes over big bang

**Do NOT choose Option 3** because:
- It doesn't fully solve the stated problems (scoped roles, system maintenance)
- Creates more technical debt
- Doesn't align with the "full unification" requirement

---

## Decision Questions & Answers

1. **Risk Tolerance**: ✅ **Big bang migration (Option 1)** - Team is comfortable with full replacement approach.

2. **Timeline Priority**: ✅ **No time constraints** - Build the right long-term solution rather than quick fix.

3. **Production Constraints**: ✅ **No production constraints** - No deployment window limitations or uptime blocking big bang approach.

4. **Future Requirements**: ✅ **Keep current scope types** - Start with global/project/change_order; extensible design allows future additions.

5. **Team Capacity**: ✅ **Sufficient capacity** - Team can dedicate 3-4 weeks to this feature.

---

## FINAL DECISION: Option 1 - Full Unification

**Decision Date**: 2026-05-10

**Chosen Approach**: Full unification with UserRoleAssignment entity, UnifiedRBACService, and UnifiedChecker using big bang migration.

**Rationale**:
- Solves all three stated problems completely
- Aligns with requirements (fully unify, big bang, scoped roles)
- No timeline or production constraints blocking this approach
- Creates extensible architecture for future needs
- Team has capacity for 3-4 week implementation

---

## Next Steps

Once a decision is made:

1. **Document decision**: Update this analysis with the chosen option and rationale
2. **Create PLAN phase**: Develop detailed implementation plan with phases, tasks, and success criteria
3. **Execute PLAN**: Follow PDCA cycle (Plan → Do → Check → Act)
4. **Verify**: Ensure all acceptance criteria are met before marking complete

---

## References

### Architecture Documentation
- [ADR-007: RBAC Service Design](/home/nicola/dev/backcast/docs/02-architecture/decisions/ADR-007-rbac-service.md)
- [Security Practices](/home/nicola/dev/backcast/docs/02-architecture/cross-cutting/security-practices.md)
- [Backend Coding Standards](/home/nicola/dev/backcast/docs/02-architecture/backend/coding-standards.md)
- [API Conventions](/home/nicola/dev/backcast/docs/02-architecture/cross-cutting/api-conventions.md)

### Product Scope
- [Functional Requirements](/home/nicola/dev/backcast/docs/01-product-scope/functional-requirements.md)
- [Change Management User Stories](/home/nicola/dev/backcast/docs/01-product-scope/change-management-user-stories.md)

### Code References
- `backend/app/core/rbac.py` - RBACServiceABC, JsonRBACService, RoleChecker
- `backend/app/core/rbac_database.py` - DatabaseRBACService
- `backend/app/core/enums.py` - ProjectRole enum
- `backend/app/api/dependencies/auth.py` - RoleChecker, ProjectRoleChecker
- `backend/app/services/approval_matrix_service.py` - Approval authority validation
- `backend/app/models/domain/rbac.py` - RBACRole, RBACRolePermission
- `backend/app/models/domain/project_member.py` - ProjectMember

### Related Iterations
- [2026-01-04: RBAC Implementation](/home/nicola/dev/backcast/docs/03-project-plan/iterations/2026-01-04-rbac-implementation/) - Original RBAC system implementation
