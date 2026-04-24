# ADR-007: RBAC Service Design

**Status:** Accepted  
**Date:** 2026-01-04  
**Decision Makers:** Antigravity AI (proposed), User (approved)

---

## Context

The application needed a flexible Role-Based Access Control (RBAC) system that:

1. Simplifies route-level authorization
2. Supports both role-based and permission-based checks
3. Is easily testable and maintainable
4. Allows for future database-backed implementations

Prior to this decision, the User model had a `role` field but no enforcement mechanism, and routes had no systematic authorization controls.

---

## Decision

We implemented a comprehensive RBAC system with three key components:

### 1. RBACService Abstract Interface

- **`RBACServiceABC`**: Abstract base class defining RBAC operations

  - `has_role(user_role, required_roles)` - Role membership check
  - `has_permission(user_role, required_permission)` - Permission check
  - `get_user_permissions(user_role)` - Get all permissions for a role

- **`JsonRBACService`**: JSON file-based implementation for configuration

  - Loads from `backend/config/rbac.json`
  - Caches configuration in memory
  - Simple initial setup for small deployments

- **Global singleton pattern** for app-scoped access via `get_rbac_service()`

### 2. RoleChecker Dependency

Class-based FastAPI dependency for declarative route authorization with three modes:

- **Role-only:** `RoleChecker(["admin", "manager"])`
- **Permission-only:** `RoleChecker(required_permission="delete")`
- **Combined (OR logic):** `RoleChecker(["admin"], "delete")`

### 3. JSON Configuration

Roles and permissions stored in `config/rbac.json`:

```json
{
  "roles": {
    "admin": {
      "permissions": ["create", "read", "update", "delete", "manage_users"]
    },
    "manager": {
      "permissions": ["create", "read", "update"]
    },
    "viewer": {
      "permissions": ["read"]
    }
  }
}
```

### 4. AI Assistant RBAC Roles

Three AI-specific roles for tool filtering in the AI chat system:

- `ai-viewer`: Read-only access (14 permissions) — project, WBE, cost element, forecast, schedule, EVM data reads
- `ai-manager`: Full project CRUD (37 permissions) — create/update workflows, change orders, forecasts, progress tracking
- `ai-admin`: System admin (13 permissions) — user/dept/cost-element-type management

These roles are assigned per-assistant via the `default_role` field on `AIAssistantConfig` and used by `filter_tools_by_role()` at agent creation time to restrict which tools each assistant can access.

### 5. ContextVar Session Injection

For thread-safe async session management in concurrent WebSocket connections:

- `_rbac_session` ContextVar provides request-scoped database sessions
- `get_rbac_session()` / `set_rbac_session()` helpers
- Fallback pattern: `session = self.session or get_rbac_session()` in `has_project_access()`, `get_user_projects()`, `get_project_role()`
- Replaces previous singleton `.session` mutation which was unsafe under concurrent requests

---

## Alternatives Considered

### 1. Decorator-based Authorization

**Approach:** Python decorators for routes

```python
@requires_role("admin")
async def admin_route():
    ...
```

**Pros:**

- Pythonic and familiar to many developers
- Less verbose syntax

**Cons:**

- Less flexible than dependency injection
- Harder to test (decorators wrap functions)
- Not type-safe
- Doesn't integrate well with FastAPI's dependency system

**Decision:** Rejected in favor of dependency injection approach

### 2. Hard-coded Role Checks

**Approach:** Manual role checks in each route

```python
async def some_route(current_user: User):
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(403)
    ...
```

**Pros:**

- Simple and straightforward
- No additional abstractions

**Cons:**

- Code duplication across routes
- Not maintainable as authorization grows
- Easy to forget checks
- No centralized permission logic

**Decision:** Rejected - not maintainable

### 3. Database-only RBAC

**Approach:** Store roles and permissions in database tables

**Pros:**

- Dynamic role/permission management
- UI-manageable
- Multi-tenant ready

**Cons:**

- Over-engineered for initial needs
- Adds database complexity
- Slower (requires DB queries)
- Not needed for small deployments

**Decision:** Deferred to future iteration (abstract interface allows for easy addition)

---

## Consequences

### Positive

✅ **Declarative security:** Route permissions visible at decorator level

```python
@app.post("/users/", dependencies=[Depends(RoleChecker(["admin"]))])
async def create_user(): ...
```

✅ **Testable:** Authorization logic isolated with 100% test coverage (95.56% achieved)

✅ **Flexible:** Supports role, permission, or combined checks with OR logic

✅**Extensible:** Easy to add database-backed implementation via abstract interface

✅ **Type-safe:** Full MyPy strict mode compliance

✅ **FastAPI-native:** Uses standard dependency injection patterns

✅ AI assistants receive role-based tool filtering (e.g., ai-manager gets 61/76 tools, ai-viewer gets 45/76)

✅ ContextVar-based session injection ensures thread-safe concurrent WebSocket sessions

✅ Single permission check point (middleware-only) — redundant decorator check removed

### Negative

⚠️ JSON file not suitable for high-concurrency write scenarios (read-only in production)

⚠️ No built-in role hierarchy (e.g., admin inherits manager permissions)

⚠️ OR logic for combined checks might be less intuitive than AND logic

### Mitigations

- Document that JSON implementation is for development/small deployments
- Database-backed implementation can be added when needed without changing route code
- Permission system enables fine-grained control without requiring hierarchy
- Combined check behavior clearly documented in docstrings and examples

---

## Usage Examples

### Role-based Authorization

```python
from app.api.dependencies.auth import RoleChecker

allow_admin = RoleChecker(["admin"])

@app.post("/users/", dependencies=[Depends(allow_admin)])
async def create_user(): ...
```

### Permission-based Authorization

```python
allow_delete = RoleChecker(required_permission="delete")

@app.delete("/items/{id}", dependencies=[Depends(allow_delete)])
async def delete_item(): ...
```

### Combined Authorization (OR Logic)

```python
# Grants access if user has admin role OR delete permission
admin_or_delete = RoleChecker(["admin"], "delete")

@app.delete("/important/{id}", dependencies=[Depends(admin_or_delete)])
async def delete_important(): ...
```

---

## Implementation Details

### Files Created/Modified

- `backend/app/core/rbac.py` - Core RBAC service — added `_rbac_session` ContextVar, `get/set_rbac_session()`, contextvar fallback in project access methods
- `backend/app/api/dependencies/auth.py` - Added RoleChecker (+68 lines)
- `backend/config/rbac.json` - Configuration — added `ai-viewer`, `ai-manager`, `ai-admin` roles
- `backend/tests/core/test_rbac.py` - Unit tests (11 tests)
- `backend/tests/api/test_role_checker.py` - Integration tests (7 tests)
- `backend/app/ai/tools/__init__.py` - Added `filter_tools_by_role()` for role-based tool filtering
- `backend/app/ai/tools/decorator.py` - Removed redundant permission check (middleware-only enforcement)
- `backend/app/ai/middleware/backcast_security.py` - Uses `set_rbac_session()` contextvar instead of singleton mutation
- `backend/app/ai/deep_agent_orchestrator.py` - Applies `filter_tools_by_role()` after execution mode filtering
- `backend/app/models/domain/ai.py` - Added `default_role` field to `AIAssistantConfig`

### Test Coverage

- 18 total tests (100% passing)
- 95.56% coverage on `app/core/rbac.py`
- All authorization modes tested
- Error cases covered (missing file, invalid JSON, unknown roles)

### Type Safety

- MyPy strict mode: ✅ Passing
- Explicit type annotations for JSON returns
- Full type hints on all public methods

---

## Related Decisions

- [ADR-001: FastAPI + SQLAlchemy 2.0](file:///home/nicola/dev/backcast_evs/docs/02-architecture/decisions/ADR-001-backend-stack.md) (assumed)
- [ADR-006: Protocol-based Type System](file:///home/nicola/dev/backcast_evs/docs/02-architecture/decisions/ADR-006-protocol-based-type-system.md)

---

## Future Considerations

1. **Database-backed RBAC**: When multi-tenancy or dynamic role management is needed (open consideration, no ADR yet)
2. **Role hierarchy**: Implement inheritance (e.g., admin inherits all manager permissions)
3. **API for role management**: CRUD endpoints for roles/permissions
4. **Audit logging**: Track authorization decisions for security analysis
5. **AND logic option**: Add `require_all=True` parameter for stricter combined checks
6. **AI role management UI**: Admin interface for managing AI assistant RBAC roles

---

## References

- Implementation Plan: [docs/03-project-plan/iterations/2026-01-04-rbac-implementation/01-plan.md](file:///home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-04-rbac-implementation/01-plan.md)
- DO Phase: [docs/03-project-plan/iterations/2026-01-04-rbac-implementation/02-do.md](file:///home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-04-rbac-implementation/02-do.md)
- FastAPI Security: https://fastapi. tiangolo.com/tutorial/security/
- OAuth2 Scopes: https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/

---

## Changelog

| Date | Change | Author |
|---|---|---|
| 2026-01-04 | Initial ADR — RBAC service design with JSON config, RoleChecker dependency | Antigravity AI |
| 2026-04-23 | Added AI assistant RBAC roles, contextvar session injection, role-based tool filtering | Backend Team |
