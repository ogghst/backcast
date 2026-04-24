# Analysis: Architectural Unification of AI Tool and API RBAC

**Created:** 2026-04-23
**Request:** Clarified requirement - Architectural unification, not permission overrides
**Issue URL:** https://github.com/ogghst/backcast/issues/58

**Status:** ANALYSIS COMPLETE (UPDATED WITH DECISIONS)

---

## Decisions (Post-Analysis)

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Add new AI-specific roles to `rbac.json` matching existing AI assistant profiles | AI assistants are system users with their own role-based capabilities, just like human users. Three roles needed: `ai-viewer`, `ai-manager`, `ai-admin` matching the three assistant configs. |
| 2 | Standard roles shall be sufficient; additional granularity deferred | The three new AI roles map 1:1 to existing assistant profiles. If finer control is needed later, new roles can be added incrementally. |
| 3 | Full permission check result required | Every tool invocation must be checked against both the assistant's RBAC role AND the user's RBAC role. The most restrictive wins. |
| 4 | Add new roles to `rbac.json` per Decision 1 | Concrete implementation: add `ai-viewer`, `ai-manager`, `ai-admin` roles with permissions derived from each assistant's `allowed_tools` mapped to tool `permissions` metadata. |
| 5 | Simple dropdown for assistant selection (existing component is sufficient) | The current `AssistantSelector` component already works well. No UI redesign needed for RBAC integration. |
| 6 | Show only tools available to the selected assistant | Filter the tool list presented to the LLM based on the assistant's role permissions. Tools the assistant lacks permissions for should not appear in the LLM's tool list. |

### New RBAC Roles (to add to `rbac.json`)

Based on the three assistant profiles in `backend/seed/ai_assistant_configs.json`:

**`ai-viewer`** (Friendly Project Analyzer):
- Read-only project insights for all team members
- Permissions: project-read, wbe-read, cost-element-read, cost-element-type-read, cost-registration-read, change-order-read, forecast-read, schedule-baseline-read, evm-read, user-read, department-read, quality-event-read, ai-chat, progress-entry-read (read subset matching viewer + evm-read + ai-chat)

**`ai-manager`** (Senior Project Manager):
- Full project operations including create/update workflows
- Permissions: Same as `manager` role (project CRUD, WBE CRUD, cost element CRUD, change order workflow, forecast CRUD, progress entries, cost registrations, schedule baseline, EVM, ai-chat)

**`ai-admin`** (System Manager):
- System configuration and user/department management
- Permissions: Same as `admin` role subset for user/department/cost-element-type management + project-read

---

## Clarified Requirements

### Problem Statement

The codebase has TWO SEPARATE RBAC enforcement mechanisms:

1. **API Endpoint RBAC** (`app/api/dependencies/auth.py`): FastAPI dependencies (`RoleChecker`, `ProjectRoleChecker`) that protect HTTP routes
2. **AI Tool RBAC** (`app/ai/tools/decorator.py`, `app/ai/middleware/backcast_security.py`): Decorator and middleware that protect LangChain tools

**This creates:**
- **Redundant checks**: AI tools check permissions twice (middleware + decorator)
- **Fragile session injection**: Both paths mutate `rbac_service.session` on a singleton, risking corruption under concurrent WebSocket connections
- **Dead code**: `require_permission` decorator in `rbac.py` was designed for unification but never adopted
- **Inconsistent session handling**: API deps set-and-forget, middleware uses try/finally restore

### What This Is NOT About

- Permission overrides per AI assistant
- Custom tool lists per assistant
- Fine-grained permission editing
- Special configuration for individual AI tools

### What This IS About

- **Remove redundancy**: AI tools shouldn't check permissions twice
- **Fix session injection**: Use contextvars instead of mutating singleton state
- **Adopt existing unification helpers**: Use `require_permission` and `inject_rbac_session` that already exist but are unused

### Non-Functional Requirements

- **Performance**: Permission checks must not add significant latency (< 1ms per check)
- **Thread-safety**: Session injection must be safe under concurrent WebSocket connections
- **Backward Compatibility**: Existing API and AI tool functionality must continue working

---

## Current Architecture Analysis

### How API RBAC Works

```
Request → OAuth2 Bearer → get_current_user() → RoleChecker / ProjectRoleChecker
                                                            ↓
                                                    rbac_service.has_permission()
                                                    rbac_service.has_project_access()
                                                            ↓
                                                    HTTPException(403) if denied
```

**`RoleChecker`** (`auth.py:68-133`): FastAPI dependency. Checks `rbac_service.has_role()` or `rbac_service.has_permission()`. Raises `HTTPException(403)`.

**`ProjectRoleChecker`** (`auth.py:136-195`): FastAPI dependency. Injects session via `rbac_service.session = session` (set-and-forget, no restoration). Calls `rbac_service.has_project_access()`. Raises `HTTPException(403)`.

### How AI Tool RBAC Works

```
WebSocket → BackcastSecurityMiddleware.awrap_tool_call()
                        ↓
            _check_tool_permission()          ← First check
            (rbac_service.has_permission()
             rbac_service.has_project_access()
             with try/finally session swap)
                        ↓ (if passed)
            @ai_tool wrapper checks again     ← Second check (REDUNDANT)
            (rbac_service.has_permission())
                        ↓ (if passed)
            Execute tool function
```

**`BackcastSecurityMiddleware._check_tool_permission()`** (`backcast_security.py:198-304`): Checks all permissions from tool metadata. For project-scoped tools, temporarily swaps `rbac_service.session` with try/finally. Returns error string or `None`.

**`@ai_tool` wrapper** (`decorator.py:150-161`): Checks permissions AGAIN after the middleware already checked them. Calls `rbac_service.has_permission()` for each permission. Returns `{"error": ...}` if denied.

### Key Architectural Problems

#### 1. **Redundant Permission Checks for AI Tools**

AI tools go through TWO permission checks per invocation:

| Check | Location | What it checks |
|-------|----------|---------------|
| Middleware `_check_tool_permission()` | `backcast_security.py:198-304` | All permissions + project access |
| `@ai_tool` wrapper | `decorator.py:150-161` | Permissions only (no project access) |

The middleware is more comprehensive (handles project-level checks, UUID parsing, concurrent session safety). The decorator's check is a strict subset — it only checks global permissions, missing project-level access entirely.

#### 2. **Fragile Singleton Session Mutation**

`JsonRBACService` is a global singleton (`get_rbac_service()`). Both API and AI paths mutate its `.session` attribute:

- **`ProjectRoleChecker`** (`auth.py:179`): `rbac_service.session = session` — set-and-forget, no restoration
- **`BackcastSecurityMiddleware`** (`backcast_security.py:250-293`): Uses try/finally to restore original session

The try/finally pattern in the middleware suggests this is known to be fragile — but under concurrent WebSocket connections, two requests can still swap sessions between each other's try/finally blocks.

#### 3. **Existing Unification Helpers Are Unused**

- **`require_permission()` decorator** (`rbac.py:175-297`): Generic decorator that checks permissions from either a `context` kwarg or `user_role` kwarg. Handles both sync and async. Raises `PermissionError`. **Not used by any API dep or AI tool.**
- **`inject_rbac_session()` helper** (`rbac.py:653-682`): Safely injects session if `rbac_service.session is None`. **Used by some AI tools but not by middleware or API deps.**

---

## Solution Design

### Option 1: Remove Redundancy + Fix Session Injection (Recommended)

**Concept**: The real problem is not "we need a new service class" — it's that permissions are checked twice for AI tools, and session injection mutates a singleton. Fix both with targeted changes using existing patterns.

**Changes:**

#### Change 1: Remove duplicate permission check from `@ai_tool` decorator

The middleware already enforces permissions before the tool function runs. The decorator's check at `decorator.py:150-161` is a strict subset of what the middleware does.

```python
# decorator.py — REMOVE the permission check block (lines 150-161):
#
#   from app.core.rbac import get_rbac_service
#   rbac_service = get_rbac_service()
#   for permission in tool_permissions:
#       if not rbac_service.has_permission(context_obj.user_role, permission):
#           ...
#           return {"error": f"Permission denied: {permission} required"}
#
# The middleware's _check_tool_permission() handles this comprehensively.
```

**Impact**: Every AI tool invocation removes one redundant `has_permission()` call per permission.

#### Change 2: Replace singleton session mutation with contextvars

Replace mutable `.session` attribute on the singleton with a `contextvars.ContextVar`. This is Python's built-in mechanism for request-scoped state in async code — each async task gets its own session automatically.

```python
# app/core/rbac.py — add:
import contextvars

_rbac_session: contextvars.ContextVar[AsyncSession | None] = contextvars.ContextVar(
    "_rbac_session", default=None
)

def get_rbac_session() -> AsyncSession | None:
    return _rbac_session.get()

def set_rbac_session(session: AsyncSession | None) -> None:
    _rbac_session.set(session)
```

Update `JsonRBACService.has_project_access()` to use the contextvar as fallback:

```python
# In has_project_access(), replace:
#   if self.session is None:
# with:
session = self.session or get_rbac_session()
if session is None:
    ...
```

Same for `get_user_projects()` and `get_project_role()`.

#### Change 3: Update callers to use contextvar instead of mutation

**`ProjectRoleChecker`** (`auth.py:176-179`):
```python
# Before:
if hasattr(rbac_service, "session"):
    rbac_service.session = session

# After:
from app.core.rbac import set_rbac_session
set_rbac_session(session)
```

**`BackcastSecurityMiddleware._check_tool_permission()`** (`backcast_security.py:248-293`):
```python
# Before: try/finally session swap on singleton
# After:
from app.core.rbac import set_rbac_session

if project_id is not None:
    set_rbac_session(ctx.session)
    # ... check permissions (no try/finally needed) ...
```

**AI tools that use `inject_rbac_session()`** — already using the helper, will work with contextvar fallback. No change needed.

#### Change 4: Update `require_permission` decorator to use contextvar

The existing `require_permission` decorator (`rbac.py:175-297`) can be updated to support project-level checks using the contextvar session, making it a viable shared helper for future use.

**Benefits:**
- Eliminates redundant permission check (AI tools: 2 checks → 1)
- Fixes thread-safety issue with singleton session mutation
- Removes fragile try/finally session swap
- Uses Python's contextvars (built for exactly this pattern)
- Minimal code changes (3 files, ~40 lines changed, ~15 lines removed)
- No new service classes, no new abstractions
- `RBACServiceABC` remains the single source of truth

**Trade-offs:**
- Permission checking still has two call sites (middleware + API deps) — but they serve genuinely different contexts (WebSocket tools vs HTTP routes)
- Error handling stays context-appropriate: `HTTPException` for API, error string for AI tools — these are fundamentally different response patterns
- `require_permission` decorator remains unused in production code but is now viable for future adoption

---

### Option 2: Decorator-Based Unification

**Concept**: Create a unified decorator that works for both FastAPI routes and AI tools.

**Architecture:**
```python
def require_permission(*permissions: str):
    """Unified permission decorator for both API and AI tools."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            user_role = _extract_user_role(kwargs)
            context = _extract_context(kwargs)

            for permission in permissions:
                if not rbac_service.has_permission(user_role, permission):
                    if _is_fastapi_context():
                        raise HTTPException(status_code=403, detail="Permission denied")
                    else:
                        return {"error": "Permission denied"}

            return await func(*args, **kwargs)
        return async_wrapper
    return decorator
```

**Benefits:**
- Single decorator for both systems
- Less code to write

**Trade-offs:**
- Still has dual error handling (HTTPException vs dict)
- FastAPI dependency system is more idiomatic than decorators for route protection
- Doesn't address the session injection problem
- Mix of two patterns (decorator + dependency) creates confusion
- Doesn't eliminate the middleware's check — just adds a third check point

---

### Option 3: Minimal Change - Extract Common Functions

**Concept**: Extract common permission checking logic into utility functions, keep existing structure.

**Architecture:**
```python
# app/core/permission_utils.py
async def check_permission_with_error(
    rbac_service: RBACServiceABC,
    user_role: str,
    required_permission: str,
    error_type: Literal["http", "dict"] = "http",
) -> bool | None:
    if not rbac_service.has_permission(user_role, required_permission):
        if error_type == "http":
            raise HTTPException(status_code=403, detail="Permission denied")
        else:
            return {"error": "Permission denied"}
    return True
```

**Benefits:**
- Minimal code changes
- Extracts common logic

**Trade-offs:**
- Still has dual error handling paths
- Doesn't fix session injection fragility
- Doesn't eliminate redundant AI tool checks
- Doesn't improve testability significantly

---

## Comparison and Recommendation

| Aspect | Option 1: Remove Redundancy | Option 2: Decorator | Option 3: Minimal |
|--------|---------------------------|---------------------|-------------------|
| **Removes duplicate checks** | Yes (2→1 for AI tools) | No (adds third check) | No |
| **Fixes session injection** | Yes (contextvars) | No | No |
| **Code changes** | ~55 lines (3 files) | ~80 lines (4 files) | ~30 lines (2 files) |
| **New abstractions** | None | 1 new decorator | 1 new util module |
| **Thread-safety** | Fixed | Not addressed | Not addressed |
| **Uses existing code** | `require_permission`, `inject_rbac_session` exist | Replaces existing patterns | Adds alongside existing |
| **Risk** | Low (removes code, fixes bug) | Medium (new pattern) | Low (adds helpers) |

### APPROVED: **Option 1 - Remove Redundancy + Fix Session Injection + AI-Specific Roles**

**Rationale:**

1. **The problem is simpler than it first appears.** The existing `RBACServiceABC` is already the unified permission service. We don't need a `PermissionChecker` wrapper — we need to fix HOW it's called.

2. **Removing code is better than adding code.** The `@ai_tool` decorator's permission check is redundant with the middleware. Deleting it is the cleanest fix.

3. **The session injection is a real bug.** Mutating a singleton's attribute from concurrent async handlers is unsafe. Contextvars is the Python-standard fix.

4. **Existing helpers (`require_permission`, `inject_rbac_session`) were built for this.** They just need to be updated for contextvar support and actually adopted.

5. **AI assistants need their own RBAC roles.** Each assistant profile maps to a role with permissions derived from its `allowed_tools`. This ensures the RBAC system treats AI assistants as first-class users with proper permission enforcement.

**Implementation Priority:**

**Phase 1 — Core Fixes** (2-3 hours):
- Add `ai-viewer`, `ai-manager`, `ai-admin` roles to `rbac.json`
- Remove `@ai_tool` permission check (decorator.py:150-161)
- Add `_rbac_session` contextvar to `rbac.py`
- Update `JsonRBACService.has_project_access()`, `get_user_projects()`, `get_project_role()` to use contextvar fallback
- Update `ProjectRoleChecker` and middleware to use `set_rbac_session()`
- Add `default_role` field to `AIAssistantConfig` model and seed data
- Filter tools by assistant role permissions when creating the agent

**Phase 2 — Validation** (1-2 hours):
- Run existing RBAC tests (should pass unchanged)
- Add test for concurrent session isolation
- Verify AI tool permission checks still work end-to-end
- Test that each AI assistant only sees tools it has permissions for

**Phase 3 — Cleanup** (Optional):
- Update `require_permission` decorator to support project-level checks via contextvar
- Remove dead code paths made unnecessary by the changes

---

## Success Criteria

1. **No duplicate checks**: AI tool permission is checked once (middleware only)
2. **Thread-safe session handling**: Contextvar-based, no singleton mutation
3. **All existing tests pass**: No behavioral changes
4. **Fewer lines of code**: Net reduction from removing redundant check
5. **AI-specific RBAC roles**: Three new roles (`ai-viewer`, `ai-manager`, `ai-admin`) in `rbac.json` with permissions matching assistant profiles
6. **Role-based tool filtering**: Each AI assistant only sees tools its RBAC role permits
7. **Assistant-role binding**: `AIAssistantConfig` has a `default_role` field linking it to an RBAC role

---

## References

**Source Files:**
- `backend/app/core/rbac.py` — `RBACServiceABC`, `JsonRBACService`, `require_permission`, `inject_rbac_session`
- `backend/app/api/dependencies/auth.py` — `RoleChecker`, `ProjectRoleChecker`
- `backend/app/ai/tools/decorator.py` — `@ai_tool` decorator
- `backend/app/ai/middleware/backcast_security.py` — `BackcastSecurityMiddleware`

**Configuration:**
- `backend/config/rbac.json`

**Tests:**
- `backend/tests/security/ai/test_tool_rbac.py`
- `backend/tests/unit/core/test_rbac.py`

**GitHub Issue:**
- https://github.com/ogghst/backcast/issues/58
