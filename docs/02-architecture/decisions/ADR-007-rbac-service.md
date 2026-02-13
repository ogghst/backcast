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

- `backend/app/core/rbac.py` - Core RBAC service (201 lines)
- `backend/app/api/dependencies/auth.py` - Added RoleChecker (+68 lines)
- `backend/config/rbac.json` - Configuration
- `backend/tests/core/test_rbac.py` - Unit tests (11 tests)
- `backend/tests/api/test_role_checker.py` - Integration tests (7 tests)

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

1. **Database-backed RBAC (ADR-008)**: When multi-tenancy or dynamic role management is needed
2. **Role hierarchy**: Implement inheritance (e.g., admin inherits all manager permissions)
3. **API for role management**: CRUD endpoints for roles/permissions
4. **Audit logging**: Track authorization decisions for security analysis
5. **AND logic option**: Add `require_all=True` parameter for stricter combined checks
6. **Caching strategy**: Add cache invalidation for database-backed implementation

---

## References

- Implementation Plan: [docs/03-project-plan/iterations/2026-01-04-rbac-implementation/01-plan.md](file:///home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-04-rbac-implementation/01-plan.md)
- DO Phase: [docs/03-project-plan/iterations/2026-01-04-rbac-implementation/02-do.md](file:///home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-04-rbac-implementation/02-do.md)
- FastAPI Security: https://fastapi. tiangolo.com/tutorial/security/
- OAuth2 Scopes: https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/
