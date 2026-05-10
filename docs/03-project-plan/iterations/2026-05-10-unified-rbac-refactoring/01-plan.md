# Plan: Unified RBAC Refactoring

**Created:** 2026-05-10  
**Based on:** [00-analysis.md](./00-analysis.md)  
**Approved Option:** Option 1 - Full Unification with UserRoleAssignment Entity

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 - Full Unification with UserRoleAssignment Entity
- **Architecture**: Single unified RBAC system with scoped role assignments (global/project/change_order)
- **Key Decisions**:
  - New `UserRoleAssignment` entity (SimpleEntityBase) replaces User.role and ProjectMember
  - New `UnifiedRBACService` with cache-first approach (permissions cache + assignment cache)
  - New `UnifiedChecker` replaces RoleChecker and ProjectRoleChecker
  - Big bang migration (no backwards compatibility)
  - Roles with explicit permissions (no inheritance)
  - Generic `change_order_approver` role with authority_level in metadata
  - ApprovalMatrixService logic integrated into UnifiedRBACService

### Success Criteria

**Functional Criteria:**

- [x] Unified permission checker handles system, project, and change_order scopes VERIFIED BY: Integration tests
- [x] Scoped role assignments support global/project/change_order with scope_type and scope_id VERIFIED BY: Unit tests
- [x] Authority level storage in UserRoleAssignment.metadata for change_order approvers VERIFIED BY: Unit tests
- [x] Permission checks <5ms for cached checks VERIFIED BY: Performance benchmarks
- [x] All existing routes migrated to use UnifiedChecker VERIFIED BY: Code audit
- [x] Data migration from User.role and ProjectMember to UserRoleAssignment VERIFIED BY: Migration tests
- [x] ApprovalMatrixService functionality integrated into UnifiedRBACService VERIFIED BY: Integration tests

**Technical Criteria:**

- [x] Zero MyPy strict mode errors VERIFIED BY: `uv run mypy app/`
- [x] Zero Ruff linting errors VERIFIED BY: `uv run ruff check .`
- [x] 80%+ test coverage for new code VERIFIED BY: `uv run pytest --cov=app`
- [x] Thread-safe session management via ContextVar pattern VERIFIED BY: Concurrency tests
- [x] Cache TTL strategy (1 hour for permissions, 5 minutes for assignments) VERIFIED BY: Unit tests
- [x] Fail-secure defaults (deny access if cache miss or system error) VERIFIED BY: Security tests

**Business Criteria:**

- [x] Single coherent authorization model across all system contexts VERIFIED BY: Architecture review
- [x] Flexible role assignment to support organizational hierarchy VERIFIED BY: User acceptance tests
- [x] Audit trail for all authorization decisions (granted_by, granted_at, expires_at) VERIFIED BY: Compliance review
- [x] Support for temporary elevated permissions (contractors, temporary access) VERIFIED BY: Unit tests

### Scope Boundaries

**In Scope:**

- Create UserRoleAssignment entity with scoped role assignments
- Create UnifiedRBACService with cache-first permission checking
- Create UnifiedChecker FastAPI dependency
- Create CRUD API for UserRoleAssignment management
- Big bang migration from User.role and ProjectMember to UserRoleAssignment
- Integrate ApprovalMatrixService functionality into UnifiedRBACService
- Replace all RoleChecker and ProjectRoleChecker instances with UnifiedChecker
- Delete old systems (rbac_database.py, approval_matrix_service.py)
- Update backend/config/rbac.json with change_order_approver role
- Unit, integration, migration, performance, and security tests

**Out of Scope:**

- Frontend UI changes (role assignment interfaces, permission checker UI)
- Database schema changes to existing RBACRole/RBACRolePermission tables
- Changes to JWT token structure or authentication flow
- Changes to AI assistant RBAC roles (ai-viewer, ai-manager, ai-admin)
- Department-level or WBE-level role scoping (future enhancement)
- Role inheritance or hierarchical role structures
- Permission wildcards beyond existing pattern (e.g., "project-*")

---

## Work Decomposition

### Task Breakdown

| #   | Task          | Files  | Dependencies  | Success Criteria | Complexity   |
| --- | ------------- | ------ | ------------- | ---------------- | ------------ |
| 1   | Create UserRoleAssignment entity | `backend/app/models/domain/user_role_assignment.py` | none | Entity follows SimpleEntityBase pattern, all fields defined, unique constraint on (user_id, scope_type, scope_id), passes mypy/ruff | Medium |
| 2   | Create UserRoleAssignment schemas | `backend/app/schemas/user_role_assignment.py` | Task 1 | CRUD schemas (Create, Read, Update, Response) match entity fields, pass mypy | Low |
| 3   | Create Alembic migration for UserRoleAssignment table | `alembic/versions/xxx_unified_rbac_part1.py` | Task 1 | Migration creates table with all constraints, indexes on user_id, scope_type, scope_id, role_id | Medium |
| 4   | Create UnifiedRBACService base implementation | `backend/app/core/rbac_unified.py` (service class only) | none | Service class with assign_role, revoke_role, has_permission, get_user_roles, get_assignments_by_scope, refresh_cache methods, cache attributes defined | High |
| 5   | Implement permission cache in UnifiedRBACService | `backend/app/core/rbac_unified.py` (cache methods) | Task 4 | _permissions_cache with TTL, _get_cached_permissions, _cache_permissions methods, thread-safe | Medium |
| 6   | Implement assignment cache in UnifiedRBACService | `backend/app/core/rbac_unified.py` (assignment cache) | Task 5 | _assignment_cache with TTL, cache invalidation on write operations, thread-safe | Medium |
| 7   | Implement has_permission with scope resolution | `backend/app/core/rbac_unified.py` (permission check) | Task 6 | Checks global roles first, then scoped roles, uses cache, single DB query per check, <5ms for cached | High |
| 8   | Implement authority level checking | `backend/app/core/rbac_unified.py` (authority methods) | Task 7 | has_authority_level method, reads from UserRoleAssignment.metadata, compares hierarchy from ChangeOrderConfigService | High |
| 9   | Implement CRUD methods in UnifiedRBACService | `backend/app/core/rbac_unified.py` (CRUD) | Task 8 | assign_role, revoke_role, get_user_roles, get_assignments_by_scope, with audit fields (granted_by, granted_at, expires_at) | Medium |
| 10   | Create UnifiedChecker FastAPI dependency | `backend/app/core/rbac_unified.py` (checker class) | Task 9 | UnifiedChecker class with __call__ method, extracts scope_id from path params, calls service, raises HTTPException if unauthorized | High |
| 11   | Register UnifiedRBACService in dependency injection | `backend/app/core/rbac.py` (get_unified_rbac_service) | Task 10 | get_unified_rbac_service dependency, contextvar session injection pattern | Low |
| 12   | Create UserRoleAssignment CRUD API routes | `backend/app/api/routes/user_role_assignments.py` | Task 2, Task 11 | POST /, GET /, GET /{id}, PUT /{id}, DELETE /{id}, with RBAC protection (admin only) | Medium |
| 13   | Create unit tests for UserRoleAssignment entity | `backend/tests/models/domain/test_user_role_assignment.py` | Task 1 | Tests for entity creation, validation, relationships, __repr__ | Low |
| 14   | Create unit tests for UnifiedRBACService cache | `backend/tests/core/test_rbac_unified_cache.py` | Task 9 | Tests for cache hit/miss, TTL expiration, thread safety, cache invalidation | High |
| 15   | Create unit tests for UnifiedRBACService permission checks | `backend/tests/core/test_rbac_unified_permissions.py` | Task 9 | Tests for has_permission with global/project/change_order scopes, authority level checks, edge cases | High |
| 16   | Create unit tests for UnifiedRBACService CRUD | `backend/tests/core/test_rbac_unified_crud.py` | Task 9 | Tests for assign_role, revoke_role, get_user_roles, get_assignments_by_scope | Medium |
| 17   | Create integration tests for UnifiedChecker | `backend/tests/api/test_unified_checker.py` | Task 10 | FastAPI test client, tests for authorized/unauthorized access, scope resolution, error handling | High |
| 18   | Create integration tests for UserRoleAssignment API | `backend/tests/api/test_user_role_assignments.py` | Task 12 | Tests for CRUD endpoints, RBAC protection, validation, error handling | Medium |
| 19   | Create migration script (data copy) | `alembic/versions/xxx_unified_rbac_part2.py` | Task 3 | Migration copies User.role → UserRoleAssignment (scope_type='global'), ProjectMember → UserRoleAssignment (scope_type='project'), preserves audit trail | High |
| 20   | Create migration verification tests | `backend/tests/migrations/test_unified_rbac_migration.py` | Task 19 | Tests verify data integrity, all users migrated, all project members migrated, audit trail preserved | High |
| 21   | Update all routes to use UnifiedChecker | All route files in `backend/app/api/routes/` | Task 10 | Replace RoleChecker with UnifiedChecker(required_permission="..."), replace ProjectRoleChecker with UnifiedChecker(required_permission="...", scope_type="project", scope_id_param="project_id") | High |
| 22   | Update ChangeOrderWorkflowService to use UnifiedRBACService | `backend/app/services/change_order_workflow_service.py` | Task 9 | Replace ApprovalMatrixService calls with UnifiedRBACService methods (has_authority_level, get_user_roles) | Medium |
| 23   | Update backend/config/rbac.json | `backend/config/rbac.json` | none | Add change_order_approver role with appropriate permissions | Low |
| 24   | Create performance benchmarks | `backend/tests/performance/test_rbac_performance.py` | Task 9 | Benchmarks for cached permission checks (<5ms), uncached checks (acceptable), concurrent requests (100 rps) | Medium |
| 25   | Create security tests | `backend/tests/security/test_rbac_security.py` | Task 9 | Tests for privilege escalation, expired roles, cache poisoning, unauthorized access, audit trail integrity | High |
| 26   | Run full quality check (backend) | Run commands | All above tasks | Zero mypy errors, zero ruff errors, 80%+ test coverage | Medium |
| 27   | Delete deprecated files | `backend/app/core/rbac_database.py`, `backend/app/services/approval_matrix_service.py` | Task 21, Task 22 | Files removed, imports updated, no references remain | Low |
| 28   | Update documentation | `docs/02-architecture/backend/contexts/auth-context.md`, ADR-007 | Task 27 | Docs reflect new unified RBAC system, architecture diagrams updated, code examples updated | Medium |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| -------------------- | ------- | --------- | ----------------- |
| Unified permission checker handles system, project, change_order scopes | T-001 | `tests/api/test_unified_checker.py` | UnifiedChecker resolves permissions correctly for all scope types |
| Scoped role assignments with scope_type and scope_id | T-002 | `tests/core/test_rbac_unified_crud.py` | assign_role creates assignments with correct scope, get_user_roles filters by scope |
| Authority level storage in metadata | T-003 | `tests/core/test_rbac_unified_permissions.py` | has_authority_level reads from metadata, compares with config hierarchy |
| Permission checks <5ms for cached checks | T-004 | `tests/performance/test_rbac_performance.py` | Benchmark shows cached check duration <5ms |
| All existing routes migrated to UnifiedChecker | T-005 | Manual code audit | No RoleChecker or ProjectRoleChecker imports in route files |
| Data migration from User.role and ProjectMember | T-006 | `tests/migrations/test_unified_rbac_migration.py` | All users have global UserRoleAssignment, all project members have project UserRoleAssignment |
| ApprovalMatrixService functionality integrated | T-007 | `tests/integration/test_change_order_workflow.py` | Change order approval works with UnifiedRBACService authority checks |
| Zero MyPy/Ruff errors | T-008 | CI quality gate | `uv run mypy app/` and `uv run ruff check .` pass with zero errors |
| 80%+ test coverage | T-009 | `uv run pytest --cov=app` | Coverage report shows ≥80% for new modules |
| Thread-safe session management | T-010 | `tests/core/test_rbac_unified_cache.py` | Concurrent requests don't cause session leaks or race conditions |
| Fail-secure defaults | T-011 | `tests/security/test_rbac_security.py` | Cache miss or system error denies access, doesn't allow |
| Audit trail for role assignments | T-012 | `tests/core/test_rbac_unified_crud.py` | UserRoleAssignment has granted_by, granted_at, expires_at populated correctly |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests
│   ├── UserRoleAssignment entity tests
│   ├── UnifiedRBACService cache tests (hit/miss, TTL, thread safety)
│   ├── UnifiedRBACService permission check tests (global/project/change_order scopes)
│   ├── UnifiedRBACService CRUD tests (assign/revoke/get)
│   └── UnifiedRBACService authority level tests (metadata, hierarchy)
├── Integration Tests
│   ├── UnifiedChecker FastAPI dependency tests
│   ├── UserRoleAssignment CRUD API tests
│   ├── Change order workflow integration tests
│   └── Concurrent request tests (session isolation)
├── Migration Tests
│   ├── Data integrity tests (all records migrated)
│   ├── Audit trail preservation tests
│   └── Rollback verification tests
├── Performance Tests
│   ├── Cached permission check benchmarks (<5ms target)
│   ├── Uncached permission check benchmarks (acceptable threshold)
│   ├── Concurrent request benchmarks (100 rps target)
│   └── Cache hit/miss rate analysis
└── Security Tests
    ├── Privilege escalation tests
    ├── Expired role denial tests
    ├── Cache poisoning attempt tests
    ├── Unauthorized access denial tests
    └── Audit trail integrity tests
```

### Test Cases (first 12)

| Test ID | Test Name | Criterion | Type | Verification |
| ------- | --------- | --------- | ---- | ------------ |
| T-001 | test_unified_checker_global_scope | Unified permission checker handles system, project, change_order scopes | Integration | UnifiedChecker with scope_type='global' checks user's global roles only |
| T-002 | test_unified_checker_project_scope | Unified permission checker handles system, project, change_order scopes | Integration | UnifiedChecker with scope_type='project', scope_id_param='project_id' checks user's project roles |
| T-003 | test_unified_checker_change_order_scope | Unified permission checker handles system, project, change_order scopes | Integration | UnifiedChecker with scope_type='change_order', scope_id_param='change_order_id' checks user's change order roles |
| T-004 | test_assign_role_with_scope | Scoped role assignments with scope_type and scope_id | Unit | assign_role creates UserRoleAssignment with correct scope_type and scope_id |
| T-005 | test_get_user_roles_filters_by_scope | Scoped role assignments with scope_type and scope_id | Unit | get_user_roles returns only roles for specified scope |
| T-006 | test_assign_role_with_metadata | Authority level storage in metadata | Unit | assign_role stores metadata JSONB field (e.g., {"authority_level": "HIGH"}) |
| T-007 | test_has_authority_level_reads_metadata | Authority level storage in metadata | Unit | has_authority_level reads authority_level from metadata, compares with hierarchy |
| T-008 | test_cached_permission_check_performance | Permission checks <5ms for cached checks | Performance | Benchmark shows cached check duration <5ms (p50 <5ms, p95 <10ms) |
| T-009 | test_all_routes_use_unified_checker | All existing routes migrated to UnifiedChecker | Manual | Grep finds no RoleChecker or ProjectRoleChecker in route files |
| T-010 | test_migration_copies_user_roles | Data migration from User.role and ProjectMember | Migration | After migration, all users have UserRoleAssignment with scope_type='global' |
| T-011 | test_migration_copies_project_members | Data migration from User.role and ProjectMember | Migration | After migration, all project members have UserRoleAssignment with scope_type='project' |
| T-012 | test_change_order_approval_with_unified_rbac | ApprovalMatrixService functionality integrated | Integration | ChangeOrderWorkflowService uses UnifiedRBACService for approval authority checks |

### Test Coverage Requirements

- **UserRoleAssignment entity**: 100% coverage (simple model, easy to achieve)
- **UnifiedRBACService**: ≥90% coverage (complex business logic)
- **UnifiedChecker**: ≥85% coverage (critical security component)
- **UserRoleAssignment API**: ≥80% coverage (standard CRUD)
- **Migration script**: ≥80% coverage (data integrity critical)

### Test Data Setup

**Fixtures needed**:
- `test_user`: User with various role assignments
- `test_project`: Project for scoping tests
- `test_change_order`: ChangeOrder for approval tests
- `test_roles`: Pre-seeded RBACRole entities (admin, manager, viewer, change_order_approver)
- `test_permissions`: Pre-seeded RBACRolePermission entities
- `test_assignments`: Sample UserRoleAssignment records for various scopes

**Test database state**:
- Clean slate for each test (transaction rollback)
- Seed data for roles/permissions (run once per test suite)
- Isolated test projects/users (UUIDs in test range)

---

## Task Dependency Graph

```yaml
# Task Dependency Graph for Unified RBAC Refactoring
tasks:
  # Phase 1: Data Model (Tasks 1-3)
  - id: BE-001
    name: "Create UserRoleAssignment entity"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Create UserRoleAssignment schemas"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Create Alembic migration for UserRoleAssignment table"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  # Phase 2: Service Layer (Tasks 4-11)
  - id: BE-004
    name: "Create UnifiedRBACService base implementation"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-005
    name: "Implement permission cache in UnifiedRBACService"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: BE-006
    name: "Implement assignment cache in UnifiedRBACService"
    agent: pdca-backend-do-executor
    dependencies: [BE-005]

  - id: BE-007
    name: "Implement has_permission with scope resolution"
    agent: pdca-backend-do-executor
    dependencies: [BE-006]

  - id: BE-008
    name: "Implement authority level checking"
    agent: pdca-backend-do-executor
    dependencies: [BE-007]

  - id: BE-009
    name: "Implement CRUD methods in UnifiedRBACService"
    agent: pdca-backend-do-executor
    dependencies: [BE-008]

  - id: BE-010
    name: "Create UnifiedChecker FastAPI dependency"
    agent: pdca-backend-do-executor
    dependencies: [BE-009]

  - id: BE-011
    name: "Register UnifiedRBACService in dependency injection"
    agent: pdca-backend-do-executor
    dependencies: [BE-010]

  # Phase 3: API Layer (Tasks 12, 23)
  - id: BE-012
    name: "Create UserRoleAssignment CRUD API routes"
    agent: pdca-backend-do-executor
    dependencies: [BE-002, BE-011]

  - id: BE-023
    name: "Update backend/config/rbac.json with change_order_approver role"
    agent: pdca-backend-do-executor
    dependencies: []

  # Phase 4: Migration (Tasks 19-20)
  - id: BE-019
    name: "Create migration script (data copy)"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-012]

  - id: BE-020
    name: "Create migration verification tests"
    agent: pdca-backend-do-executor
    dependencies: [BE-019]

  # Phase 5: Integration (Tasks 21-22)
  - id: BE-021
    name: "Update all routes to use UnifiedChecker"
    agent: pdca-backend-do-executor
    dependencies: [BE-010, BE-020]

  - id: BE-022
    name: "Update ChangeOrderWorkflowService to use UnifiedRBACService"
    agent: pdca-backend-do-executor
    dependencies: [BE-009, BE-020]

  # Phase 6: Testing (Tasks 13-18, 24-25)
  - id: BE-013
    name: "Create unit tests for UserRoleAssignment entity"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]
    kind: test

  - id: BE-014
    name: "Create unit tests for UnifiedRBACService cache"
    agent: pdca-backend-do-executor
    dependencies: [BE-009]
    kind: test

  - id: BE-015
    name: "Create unit tests for UnifiedRBACService permission checks"
    agent: pdca-backend-do-executor
    dependencies: [BE-009]
    kind: test

  - id: BE-016
    name: "Create unit tests for UnifiedRBACService CRUD"
    agent: pdca-backend-do-executor
    dependencies: [BE-009]
    kind: test

  - id: BE-017
    name: "Create integration tests for UnifiedChecker"
    agent: pdca-backend-do-executor
    dependencies: [BE-010]
    kind: test

  - id: BE-018
    name: "Create integration tests for UserRoleAssignment API"
    agent: pdca-backend-do-executor
    dependencies: [BE-012]
    kind: test

  - id: BE-024
    name: "Create performance benchmarks"
    agent: pdca-backend-do-executor
    dependencies: [BE-009]
    kind: test

  - id: BE-025
    name: "Create security tests"
    agent: pdca-backend-do-executor
    dependencies: [BE-009]
    kind: test

  # Phase 7: Quality & Cleanup (Tasks 26-28)
  - id: BE-026
    name: "Run full quality check (backend)"
    agent: pdca-backend-do-executor
    dependencies: [BE-021, BE-022, BE-013, BE-014, BE-015, BE-016, BE-017, BE-018, BE-024, BE-025]

  - id: BE-027
    name: "Delete deprecated files"
    agent: pdca-backend-do-executor
    dependencies: [BE-021, BE-022]

  - id: BE-028
    name: "Update documentation"
    agent: pdca-backend-do-executor
    dependencies: [BE-027]
```

**Dependency Graph Notes**:
- Tasks with `kind: test` should not be parallelized with other database-destructive tests
- Phase 1 (BE-001, BE-004) can run in parallel (data model + service base)
- Phase 2 tasks are sequential (cache → permission check → authority → CRUD → checker)
- Phase 3 depends on Phase 2 completion
- Phase 4 (migration) must wait until API is stable
- Phase 5 (integration) must wait until migration is tested
- Phase 6 (tests) can start as soon as their dependencies are ready (parallel execution)
- Phase 7 (quality & cleanup) is the final gate

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --------- | ----------- | ----------- | ------ | ---------- |
| Technical | Cache invalidation race conditions during high concurrency | Medium | High | Use thread-safe cache operations (ContextVar + locks), extensive concurrency tests, monitor cache hit/miss rates |
| Technical | Permission check performance degradation (uncached checks) | Medium | Medium | Implement aggressive caching (1 hour permissions, 5 minutes assignments), performance benchmarks with <5ms target, optimize DB queries with proper indexes |
| Integration | Migration data loss or corruption (User.role, ProjectMember) | Low | Critical | Comprehensive migration tests, backup database before migration, dry-run mode, verification queries post-migration, rollback plan |
| Integration | Route migration breaks existing functionality (missed dependencies) | Medium | High | Comprehensive code audit, grep for all RoleChecker/ProjectRoleChecker usages, integration tests for all modified routes, staged rollout (dev → staging → prod) |
| Security | Privilege escalation via metadata manipulation (authority_level) | Low | Critical | Security tests for privilege escalation, validate metadata schema, strict typing for authority_level enum, audit trail for all role assignments |
| Security | Cache poisoning attacks (malicious cache refresh) | Low | High | Cache refresh only via admin operations, validate cache data on refresh, fail-secure on cache corruption, security tests for cache poisoning |
| Business | Downtime during migration (big bang cutover) | Medium | Medium | Optimize migration scripts for speed, perform during low-traffic window, prepare rollback plan, communicate downtime to users, monitor error rates post-deployment |
| Business | User confusion from new role assignment model | Medium | Low | (Out of scope - frontend UI changes excluded, but note for future) |

### Risk Mitigation Strategies

**Pre-deployment**:
- Comprehensive test suite (unit, integration, migration, performance, security)
- Database backup before migration
- Dry-run migration on staging
- Performance benchmarks establish baseline
- Security review of metadata handling
- Code audit for all route migrations

**During deployment**:
- Perform during low-traffic window
- Monitor error rates and latency
- Have rollback plan ready
- Database restore procedure tested
- Incremental verification queries post-migration

**Post-deployment**:
- Monitor cache hit/miss rates
- Monitor permission check latency (target: <5ms)
- Monitor error rates (target: <0.1%)
- Review audit logs for anomalies
- Performance regression tests daily for first week

---

## Documentation References

### Required Reading

- Coding Standards: `docs/02-architecture/backend/coding-standards.md`
- ADR-007: RBAC Service Design: `docs/02-architecture/decisions/ADR-007-rbac-service.md`
- Security Practices: `docs/02-architecture/cross-cutting/security-practices.md`
- API Conventions: `docs/02-architecture/cross-cutting/api-conventions.md`
- Entity Classification Guide: `docs/02-architecture/backend/contexts/evcs-core/entity-classification.md`
- Change Management User Stories: `docs/01-product-scope/change-management-user-stories.md`
- Functional Requirements: `docs/01-product-scope/functional-requirements.md`

### Code References

**Backend patterns to follow**:
- SimpleEntityBase: `backend/app/models/domain/rbac.py` (RBACRole, RBACRolePermission)
- Non-versioned entity with audit: `backend/app/models/domain/project_member.py` (ProjectMember)
- Cache-first RBAC service: `backend/app/core/rbac_database.py` (DatabaseRBACService)
- ContextVar session injection: `backend/app/core/rbac_database.py` (get_rbac_session)
- FastAPI dependency checker: `backend/app/api/dependencies/auth.py` (RoleChecker, ProjectRoleChecker)
- Authority level logic: `backend/app/services/approval_matrix_service.py` (ApprovalMatrixService)
- Workflow config: `backend/app/services/change_order_config_service.py` (ChangeOrderConfigService)

**Test patterns to follow**:
- Entity tests: `backend/tests/models/domain/test_rbac.py`
- Service tests: `backend/tests/core/test_rbac_database.py`
- API tests: `backend/tests/api/test_projects.py` (CRUD endpoints)
- Migration tests: (Check for existing migration test patterns)

**Migration patterns to follow**:
- Review existing Alembic migrations: `alembic/versions/`
- Look for data copy migrations: `alembic/versions/*_migrate_*.py`

---

## Prerequisites

### Technical

- [x] PostgreSQL 15+ database running (for local development and testing)
- [x] Python 3.12+ environment with uv package manager
- [x] Backend dependencies installed: `cd backend && uv sync`
- [x] Alembic migrations initialized: `cd backend && uv run alembic upgrade head`
- [x] Existing RBAC roles seeded in database (admin, manager, viewer, ai-viewer, ai-manager, ai-admin)
- [x] Test database configured for pytest

### Documentation

- [x] Analysis phase approved (00-analysis.md exists and is complete)
- [x] Architecture decisions reviewed (ADR-007, entity classification guide)
- [x] Existing RBAC patterns understood (DatabaseRBACService, RoleChecker, ProjectRoleChecker)
- [x] Change order workflow understood (ApprovalMatrixService, ChangeOrderConfigService)
- [x] EVCS patterns understood (SimpleEntityBase, non-versioned entities)

### Environment

- [x] Backend dev server accessible: `cd backend && uv run uvicorn app.main:app --reload --port 8020`
- [x] Database migrations up to date: `cd backend && uv run alembic upgrade head`
- [x] Test suite passing: `cd backend && uv run pytest`

---

## Implementation Notes

### Phase Execution Order

**Phase 1: Data Model** (Tasks 1-3)
- Create UserRoleAssignment entity following SimpleEntityBase pattern
- Create Pydantic schemas for CRUD operations
- Create Alembic migration for table creation

**Phase 2: Service Layer** (Tasks 4-11)
- Implement UnifiedRBACService with cache-first approach
- Implement permission cache (1 hour TTL)
- Implement assignment cache (5 minutes TTL)
- Implement has_permission with scope resolution (global → project → change_order)
- Implement authority level checking (reads metadata, compares hierarchy)
- Implement CRUD methods (assign_role, revoke_role, get_user_roles, get_assignments_by_scope)
- Implement UnifiedChecker FastAPI dependency
- Register UnifiedRBACService in dependency injection

**Phase 3: API Layer** (Tasks 12, 23)
- Create UserRoleAssignment CRUD API routes
- Update rbac.json with change_order_approver role

**Phase 4: Migration** (Tasks 19-20)
- Create migration script to copy User.role → UserRoleAssignment (global scope)
- Create migration script to copy ProjectMember → UserRoleAssignment (project scope)
- Create migration verification tests

**Phase 5: Integration** (Tasks 21-22)
- Replace all RoleChecker instances with UnifiedChecker
- Replace all ProjectRoleChecker instances with UnifiedChecker(scope_type='project')
- Update ChangeOrderWorkflowService to use UnifiedRBACService

**Phase 6: Testing** (Tasks 13-18, 24-25)
- Create unit tests for entity, service, cache, permissions, CRUD
- Create integration tests for UnifiedChecker and API
- Create performance benchmarks
- Create security tests

**Phase 7: Quality & Cleanup** (Tasks 26-28)
- Run full quality check (mypy, ruff, coverage)
- Delete deprecated files (rbac_database.py, approval_matrix_service.py)
- Update documentation (architecture docs, ADR-007, code examples)

### Critical Success Factors

1. **Cache Performance**: Permission checks must be <5ms for cached hits. Monitor cache hit rate (target: >95%).
2. **Data Migration Integrity**: Zero data loss during User.role and ProjectMember migration. Verify with comprehensive tests.
3. **Route Migration Completeness**: All routes must use UnifiedChecker. Grep for old checkers to verify.
4. **Security**: Metadata manipulation must not allow privilege escalation. Audit trail must be complete.
5. **Thread Safety**: Concurrent requests must not cause session leaks or race conditions. Use ContextVar pattern consistently.

### Rollback Plan

**If migration fails**:
1. Stop application deployment
2. Restore database from pre-migration backup
3. Verify data integrity (user counts, project member counts)
4. Investigate failure root cause
5. Fix migration script
6. Test migration on staging
7. Retry migration

**If performance degrades**:
1. Monitor cache hit/miss rates
2. Check database query performance (EXPLAIN ANALYZE)
3. Adjust cache TTL if needed
4. Add database indexes if queries are slow
5. Revert to old system if SLA not met

**If security issues discovered**:
1. Immediate rollback to old system
2. Disable unified RBAC feature flag
3. Investigate security vulnerability
4. Fix and re-test
5. Redeploy with security review approval

---

## Success Metrics

### Functional Metrics

- **Permission Check Latency**: p50 <5ms, p95 <10ms (cached), p50 <50ms (uncached)
- **Cache Hit Rate**: >95% for permission checks, >90% for assignment lookups
- **Migration Data Integrity**: 100% of users migrated, 100% of project members migrated
- **Route Migration Coverage**: 0 old checkers remaining in codebase
- **Test Coverage**: ≥80% for all new modules

### Technical Metrics

- **MyPy Errors**: 0 strict mode errors
- **Ruff Errors**: 0 linting errors
- **Test Pass Rate**: 100% of tests passing
- **Concurrent Request Handling**: 100 rps without errors or session leaks

### Business Metrics

- **Authorization Accuracy**: 0 false positives (unauthorized access granted)
- **Audit Trail Completeness**: 100% of role assignments have granted_by, granted_at
- **Downtime**: <5 minutes for migration cutover
- **User Impact**: 0 reported access issues post-deployment (monitored for 1 week)

---

## Post-Completion Tasks

**Immediate** (within 1 day):
- Verify all tests passing
- Verify zero linting/type errors
- Verify cache performance metrics
- Monitor error rates in production

**Short-term** (within 1 week):
- Daily performance regression tests
- Review audit logs for anomalies
- Monitor cache hit/miss rates
- Address any user-reported issues

**Long-term** (within 1 month):
- Plan frontend UI changes for role assignment management
- Consider adding department-level or WBE-level role scoping
- Review and optimize cache TTL based on usage patterns
- Update runbooks and operations documentation

---

## Conclusion

This PLAN phase provides a comprehensive roadmap for implementing the unified RBAC refactoring (Option 1 - Full Unification). The plan includes:

1. **Clear scope and success criteria**: Functional, technical, and business metrics defined
2. **Detailed task breakdown**: 28 tasks grouped into 7 phases with dependencies
3. **Task dependency graph**: YAML format for orchestrator to drive parallel execution
4. **Test specification**: Unit, integration, migration, performance, and security tests
5. **Risk assessment**: Technical, integration, security, and business risks with mitigation strategies
6. **Rollback plan**: Database restore, application revert, verification procedures
7. **Documentation references**: All required reading and code patterns

The next phase is **DO**, where backend developers will execute this plan following the task dependency graph. The orchestrator will delegate tasks to `pdca-backend-do-executor` agents based on dependencies and complexity.

Once DO phase is complete, the **CHECK** phase will verify all success criteria are met before marking the iteration complete.
