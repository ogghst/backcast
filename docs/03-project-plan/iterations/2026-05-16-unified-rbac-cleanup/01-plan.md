# Plan: ADR-014 Unified RBAC Cleanup -- Remove Legacy Artifacts

**Created:** 2026-05-16
**Based on:** [00-analysis.md](00-analysis.md)
**Approved Option:** Option 1 (Sequential Cleanup)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 from analysis -- Sequential cleanup in strict dependency order
- **Architecture**: Three-step removal: (A) delete `app/core/rbac.py`, (B) delete `app/models/domain/project_member.py` + drop table, (C) remove `User.role` column
- **Key Decisions**:
  - Frontend contract unchanged -- role names identical between old and new systems
  - Seeder inverted: `UserRoleAssignment` records seeded first, display role derived from those assignments
  - Migration includes verification step asserting every `project_members` row has matching `UserRoleAssignment` before drop

### Success Criteria

**Functional Criteria:**

- [ ] SC-F1: All existing route permissions enforced identically after cleanup VERIFIED BY: existing test suite passes (no permission regressions)
- [ ] SC-F2: `UserPublic.role` field returns identical values (e.g., "admin", "viewer", "manager") after cleanup VERIFIED BY: `/auth/me` endpoint test
- [ ] SC-F3: Admin checks in `users.py` work via `UnifiedRBACService` VERIFIED BY: non-admin users still get 403 on admin-only operations
- [ ] SC-F4: Login notification payload includes role derived from `UnifiedRBACService` VERIFIED BY: auth route test
- [ ] SC-F5: AI agent service resolves roles via `UnifiedRBACService` VERIFIED BY: AI agent role resolution test
- [ ] SC-F6: Seeder creates users and role assignments without reading `user.role` column VERIFIED BY: seed from empty database succeeds
- [ ] SC-F7: `project_members` table no longer exists in database VERIFIED BY: migration applies cleanly, table absent
- [ ] SC-F8: `users.role` column no longer exists in database VERIFIED BY: migration applies cleanly, column absent

**Technical Criteria:**

- [ ] SC-T1: Zero references to `app.core.rbac` in production code VERIFIED BY: `grep -r "from app.core.rbac" app/` returns nothing
- [ ] SC-T2: Zero references to `RBACServiceABC` in test code VERIFIED BY: `grep -r "RBACServiceABC" tests/` returns nothing
- [ ] SC-T3: Zero references to `ProjectMember` in test code VERIFIED BY: `grep -r "ProjectMember" tests/` returns nothing
- [ ] SC-T4: Zero references to `user.role` / `.role` on User objects in production code VERIFIED BY: `grep -rn "\.role" app/ --include="*.py"` returns nothing unrelated to `rbac_role` or `user_id`
- [ ] SC-T5: MyPy strict mode passes (zero errors) VERIFIED BY: `uv run mypy app/`
- [ ] SC-T6: Ruff passes (zero errors) VERIFIED BY: `uv run ruff check .`
- [ ] SC-T7: All tests pass VERIFIED BY: `uv run pytest`

### Scope Boundaries

**In Scope:**

- Delete `app/core/rbac.py` and all its consumers
- Delete `app/models/domain/project_member.py` and drop `project_members` table
- Remove `User.role` column from model, schema, and database
- Update all ~50 test files to use `MockUnifiedRBACService`
- Update seeder to invert bootstrap order
- Create two Alembic migrations (drop project_members, drop users.role)
- Update `conftest.py` fixtures

**Out of Scope:**

- Frontend changes (role names unchanged)
- Changes to `UnifiedRBACService` or `UserRoleAssignment` model
- Changes to `RoleChecker` / `ProjectRoleChecker` dependencies (already use unified system)
- Changes to RBAC roles table structure
- Performance optimization of role lookups

---

## Work Decomposition

### Step A: Remove `app/core/rbac.py`

#### Task A-1: Delete `app/core/rbac.py` and update production references

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| A-1 | Delete `app/core/rbac.py` and update production code | `app/core/rbac.py` (DELETE), `app/ai/tools/rbac_tool_node.py` (lines 73-74) | None | SC-T1: zero production imports from `app.core.rbac` | Low |

**Detailed changes:**

1. **DELETE** `app/core/rbac.py` (entire file, 721 lines)

2. **EDIT** `app/ai/tools/rbac_tool_node.py` (line 73-74):
   - Remove docstring reference to `RBACServiceABC`
   - Replace "Uses RBACServiceABC.has_project_access" with "Uses UnifiedRBACService.has_permission"
   - Replace "Falls back to RBACServiceABC.has_permission" with "Uses UnifiedRBACService.has_permission"

**Note:** `app/core/rbac.py` contains a `ProjectRole` enum. Only one test file imports it: `tests/api/test_dependencies/test_project_role_checker.py` line 14. The duplicate `ProjectRole` in `app/core/enums.py` (line 72) already exists and is the authoritative version. The import in the test file will be updated in Task A-3.

#### Task A-2: Update `tests/conftest.py` -- remove legacy mock classes and fixtures

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| A-2 | Remove MockRBACService, NoAIRBACService, and legacy fixtures from conftest | `tests/conftest.py` | A-1 | Legacy mock classes deleted, override_auth fixture updated | Medium |

**Detailed changes to `tests/conftest.py`:**

1. **Remove import** (line 28): `from app.core.rbac import RBACServiceABC, get_rbac_service`

2. **DELETE** class `MockRBACService(RBACServiceABC)` (lines 293-345) -- the entire class

3. **Keep** class `MockUnifiedRBACService` (lines 348-420) unchanged

4. **DELETE** fixture `mock_rbac_service` (lines 498-505) that returns `MockRBACService()`

5. **DELETE** fixture `mock_rbac_service_no_ai` (lines 508-571) that returns `NoAIRBACService(RBACServiceABC)`. The `NoAIRBACService` class defined inside this fixture is also deleted.

6. **UPDATE** fixture `override_auth` (lines 579-616):
   - Remove `mock_rbac_service: MockRBACService` parameter
   - Remove line 607: `app.dependency_overrides[get_rbac_service] = lambda: mock_rbac_service`
   - Keep unified mock setup (lines 609-611) as-is
   - Remove `set_unified_rbac_service(original_unified)` from cleanup (line 615) -- replace with `set_unified_rbac_service(None)` to reset

#### Task A-3: Update all ~50 test files that import from `app.core.rbac`

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| A-3 | Replace legacy RBAC imports and mocks in all test files | ~50 test files (see file list below) | A-1, A-2 | SC-T2: zero references to `RBACServiceABC` in tests | High |

**Mechanical replacement pattern -- apply to each test file:**

**Pattern 1: Files that import `RBACServiceABC` and `get_rbac_service` for dependency override (~30 files)**

These files define a local `MockRBACService(RBACServiceABC)` or use the conftest `MockRBACService`, then override with `app.dependency_overrides[get_rbac_service]`.

For each file:
1. Remove `from app.core.rbac import RBACServiceABC, get_rbac_service`
2. Add `from app.core.rbac_unified import get_unified_rbac_service, set_unified_rbac_service`
3. Add `from tests.conftest import MockUnifiedRBACService` (if not already imported)
4. Delete the local `MockRBACService(RBACServiceABC)` class definition (if present)
5. Replace `app.dependency_overrides[get_rbac_service] = mock_get_rbac_service` with `set_unified_rbac_service(MockUnifiedRBACService())`
6. In cleanup/teardown: replace `app.dependency_overrides.pop(get_rbac_service, None)` with `set_unified_rbac_service(None)`

**Pattern 2: Files that import `RBACServiceABC` and `set_rbac_service` for direct mock injection (~4 files)**

Files: `tests/security/ai/test_tool_rbac.py`, `tests/api/routes/test_cost_element_type_ai_tools.py`, `tests/api/routes/test_ai_config_tools.py`, `tests/api/routes/test_ai_tools_discovery_fix.py`

For each file:
1. Remove `from app.core.rbac import RBACServiceABC, set_rbac_service`
2. Add `from app.core.rbac_unified import set_unified_rbac_service`
3. Delete local `MockRBACService(RBACServiceABC)` subclass
4. Replace `set_rbac_service(mock_service)` with `set_unified_rbac_service(MockUnifiedRBACService())`
5. Replace `set_rbac_service(None)` with `set_unified_rbac_service(None)`

**Pattern 3: Files that import `JsonRBACService` for unit testing (~2 files)**

Files: `tests/unit/core/test_rbac.py`, `tests/unit/core/test_rbac_project_access.py`

These files **test the legacy module itself**. After `app/core/rbac.py` is deleted:
- `tests/unit/core/test_rbac.py` (995 lines): **DELETE ENTIRELY** -- it tests `RBACServiceABC`, `JsonRBACService`, `require_permission`, `get_rbac_session`, `set_rbac_session`. All of these are removed.
- `tests/unit/core/test_rbac_project_access.py`: **DELETE ENTIRELY** -- it tests `JsonRBACService` project access methods that query `ProjectMember`.

**Pattern 4: Special case -- `tests/api/test_dependencies/test_project_role_checker.py`**

This file imports `ProjectRole` from `app.core.rbac`:
1. Change `from app.core.rbac import ProjectRole` to `from app.core.enums import ProjectRole`
2. Also replace `ProjectMember` usage (addressed in Step B)

**Pattern 5: Files that define inline `_MockRBAC` classes**

Files: `tests/api/routes/test_dashboard_layouts.py` (line 131), `tests/integration/test_rbac_admin_api.py` (line 94)

For each file:
1. Delete the inline `_MockRBAC` / `AllowAllRBAC` class
2. Replace with `MockUnifiedRBACService()`

**Complete file list for Pattern 1 and 2 (sorted by path):**

```
tests/test_forecast_time_travel.py
tests/api/test_search_route.py
tests/api/test_dependencies/test_project_role_checker.py
tests/api/routes/ai_chat/test_chat.py
tests/api/routes/ai_chat/test_websocket.py
tests/api/routes/change_orders/test_branch_creation.py
tests/api/routes/change_orders/test_change_order_archive_endpoint.py
tests/api/routes/change_orders/test_change_order_filtering.py
tests/api/routes/change_orders/test_change_order_merge_endpoint.py
tests/api/routes/change_orders/test_change_order_stats.py
tests/api/routes/change_orders/test_change_order_temporal_consistency.py
tests/api/routes/change_orders/test_change_order_visibility.py
tests/api/routes/change_orders/test_impact_analysis.py
tests/api/routes/cost_elements/test_cost_element_branch_creation.py
tests/api/routes/cost_elements/test_cost_element_default_as_of.py
tests/api/routes/cost_elements/test_cost_element_types.py
tests/api/routes/cost_elements/test_cost_elements.py
tests/api/routes/cost_elements/test_cost_elements_evm_history.py
tests/api/routes/cost_elements/test_cost_elements_forecast.py
tests/api/routes/cost_elements/test_cost_elements_schedule_baseline.py
tests/api/routes/cost_elements/test_cost_registrations.py
tests/api/routes/cost_elements/test_cost_aggregation.py
tests/api/routes/evm/test_evm_comparison_logic.py
tests/api/routes/evm/test_evm_generic.py
tests/api/routes/evm/test_evm_metrics.py
tests/api/routes/evm/test_evm_timeseries_cpi_spi_fields.py
tests/api/routes/evm/test_wbe_update_change_order_branch.py
tests/api/routes/integration/test_list_endpoint_consistency.py
tests/api/routes/integration/test_time_machine.py
tests/api/routes/progress_entries/test_progress_entries.py
tests/api/routes/projects/test_project_branches.py
tests/api/routes/schedule_baselines/test_schedule_baselines.py
tests/api/routes/test_dashboard_layouts.py
tests/api/routes/wbes/test_wbes.py
tests/api/routes/test_ai_tools_discovery_fix.py
tests/api/routes/test_cost_element_type_ai_tools.py
tests/api/routes/test_ai_config_tools.py
tests/security/ai/test_tool_rbac.py
tests/integration/ai/test_project_access_integration.py
tests/integration/test_control_date_api.py
tests/integration/test_dashboard_api.py
tests/integration/test_evm_integration.py
tests/integration/test_progress_time_travel.py
tests/integration/test_rbac_admin_api.py
tests/integration/test_wbe_revenue_api.py
```

#### Task A-4: Quality gate -- verify Step A is complete

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| A-4 | Run quality checks to verify Step A completion | All | A-1, A-2, A-3 | SC-T1, SC-T2, SC-T5, SC-T6, SC-T7 | Low |

**Verification commands:**
1. `grep -r "from app.core.rbac import\|import app.core.rbac" app/ tests/ --include="*.py"` -- must return zero results (excluding `app/core/rbac_unified.py` which is different)
2. `grep -r "RBACServiceABC" app/ tests/ --include="*.py"` -- must return zero results
3. `uv run mypy app/` -- zero errors
4. `uv run ruff check .` -- zero errors
5. `uv run pytest --tb=short -q 2>&1 | tail -5` -- all tests pass

---

### Step B: Remove `app/models/domain/project_member.py`

#### Task B-1: Delete model file and create migration

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| B-1 | Delete ProjectMember model and create verification+drop migration | `app/models/domain/project_member.py` (DELETE), new Alembic migration | A-4 | SC-F7, SC-T3 | Medium |

**Detailed changes:**

1. **DELETE** `app/models/domain/project_member.py` (entire file, 112 lines)

2. **CREATE** new Alembic migration (e.g., `20260516_drop_project_members_table.py`):
   - **Verification step** (as a data migration, runs before table drop):
     ```python
     # Verify every project_members row has matching UserRoleAssignment
     verify_sql = """
     SELECT COUNT(*) FROM project_members pm
     WHERE NOT EXISTS (
       SELECT 1 FROM user_role_assignments ura
       JOIN rbac_roles rr ON ura.role_id = rr.id
       WHERE ura.user_id = pm.user_id
         AND ura.scope_type = 'project'
         AND ura.scope_id = pm.project_id
     )
     """
     # Assert count == 0, raise if > 0
     ```
   - **Drop step**:
     ```python
     op.drop_constraint('uq_project_members_user_project', 'project_members', type_='unique')
     op.drop_table('project_members')
     ```
   - **Downgrade**: `op.create_table(...)` with full schema recreation (for rollback safety)

#### Task B-2: Update test files that use ProjectMember

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| B-2 | Replace ProjectMember with UserRoleAssignment in 3 test files | `tests/api/test_dependencies/test_project_role_checker.py`, `tests/api/routes/test_project_access.py`, `tests/integration/ai/test_project_access_integration.py` | B-1 | SC-T3: zero ProjectMember references in tests | Medium |

**Detailed changes per file:**

1. **`tests/api/test_dependencies/test_project_role_checker.py`**:
   - Remove `from app.models.domain.project_member import ProjectMember`
   - Replace `ProjectMember(user_id=..., project_id=..., role=...)` instances (lines 87, 142) with `UserRoleAssignment(user_id=..., scope_id=project_id, scope_type=ScopeType.PROJECT, role_id=...)`
   - This requires looking up `RBACRole.id` for the role name, or adjusting the test pattern

2. **`tests/api/routes/test_project_access.py`** (heaviest usage -- 10+ instances):
   - Remove `from app.models.domain.project_member import ProjectMember`
   - Replace all `ProjectMember(...)` instantiations with `UserRoleAssignment(...)` using `ScopeType.PROJECT`
   - The inline `MockRBACService` subclass in this file queries `ProjectMember` table -- replace with `UserRoleAssignment` queries against the unified system, or simplify by using `MockUnifiedRBACService`

3. **`tests/integration/ai/test_project_access_integration.py`** (6 instances):
   - Remove `from app.models.domain.project_member import ProjectMember`
   - Replace all `ProjectMember(...)` instantiations with `UserRoleAssignment(...)`

#### Task B-3: Quality gate -- verify Step B is complete

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| B-3 | Run quality checks to verify Step B completion | All | B-1, B-2 | SC-F7, SC-T3, SC-T5, SC-T6, SC-T7 | Low |

**Verification commands:**
1. `grep -r "ProjectMember" tests/ app/ --include="*.py"` -- must return zero results
2. `grep -r "project_member" app/ --include="*.py"` -- must return zero results (model file deleted)
3. `uv run alembic upgrade head` -- migration applies cleanly
4. `uv run mypy app/` -- zero errors
5. `uv run ruff check .` -- zero errors
6. `uv run pytest --tb=short -q 2>&1 | tail -5` -- all tests pass

---

### Step C: Remove `User.role` field

#### Task C-1: Create async helper for admin checks in `users.py`

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| C-1 | Replace `current_user.role != "admin"` with UnifiedRBACService lookups | `app/api/routes/users.py` | B-3 | SC-F3: admin checks work via unified system | Medium |

**Detailed changes to `app/api/routes/users.py`:**

The three `current_user.role != "admin"` checks (lines 136, 169, 228) need to be replaced. Each route handler already receives `current_user: User` but does NOT currently have a `session: AsyncSession` parameter.

1. Add imports:
   ```python
   from sqlalchemy.ext.asyncio import AsyncSession
   from app.db.session import get_db
   from app.core.rbac_unified import get_unified_rbac_service, set_unified_rbac_session
   ```

2. Add a helper function `_is_admin(user_id: UUID, session: AsyncSession) -> bool`:
   ```python
   async def _is_admin(user_id: UUID, session: AsyncSession) -> bool:
       set_unified_rbac_session(session)
       try:
           svc = get_unified_rbac_service()
           roles = await svc.get_user_roles(user_id, "global", None)
           return "admin" in roles
       finally:
           set_unified_rbac_session(None)
   ```

3. Update `read_user` (line 136): Add `session: AsyncSession = Depends(get_db)` parameter, replace `current_user.role != "admin"` with `not await _is_admin(current_user.user_id, session)`

4. Update `update_user` (line 169): Same pattern -- add session param, replace role check

5. Update `get_user_history` (line 228): Same pattern

#### Task C-2: Update `auth.py` login notification

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| C-2 | Replace `user.role` in login notification with UnifiedRBACService lookup | `app/api/routes/auth.py` | B-3 | SC-F4: login notification includes role | Low |

**Detailed changes to `app/api/routes/auth.py` (line 102):**

The `login` handler already has `session: AsyncSession = Depends(get_db)` available via the `AuthService`. Replace:
```python
details={"name": user.full_name, "role": user.role}
```
With a lookup:
```python
from app.core.rbac_unified import get_unified_rbac_service, set_unified_rbac_session
set_unified_rbac_session(session)  # session from auth_service
try:
    unified_svc = get_unified_rbac_service()
    roles = await unified_svc.get_user_roles(user.user_id, "global", None)
    display_role = roles[0] if roles else "unknown"
finally:
    set_unified_rbac_session(None)
details={"name": user.full_name, "role": display_role}
```

Note: The `login` handler does not currently take a direct `session` parameter -- it creates an `AuthService(session)`. The session is available from `auth_service.session` or via `Depends(get_db)`. Verify which pattern is used and adapt accordingly.

#### Task C-3: Update `UserPublic` schema and `from_user`/`from_user_async`

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| C-3 | Update UserBase, UserPublic to derive role from UnifiedRBACService | `app/models/schemas/user.py` | B-3 | SC-F2: UserPublic.role returns correct values | High |

**Detailed changes to `app/models/schemas/user.py`:**

1. **`UserBase.role`** (line 34): Keep the field but make it optional with default `"viewer"`. This field is used by `UserRegister` for initial registration. Change semantics: during registration, `role` is the requested role. After creation, it is derived.

2. **`UserPublic.from_user()`** (lines 100-126): Currently reads `user.role`. Change to:
   - Remove the `role=user.role` from the constructor
   - Add role resolution via `UnifiedRBACService.get_user_roles(user.user_id, "global", None)` -- but this is async and `from_user` is sync. Two options:
     - **Option A (recommended)**: Make `from_user` call `get_user_roles` synchronously via cache. The cache is populated during `_get_cached_permissions`. If cache is empty, return "viewer" as default.
     - **Option B**: Mark `from_user` as deprecated and ensure all callers use `from_user_async` instead. Check all callers first.
   - The sync version can use `_get_cached_permissions` pattern with a role-name fallback:
     ```python
     unified_service = get_unified_rbac_service()
     perms = unified_service._get_cached_permissions(user.role)  # still reads user.role
     ```
   - After `user.role` column is removed, this must change to a cache-only lookup. The simplest path: deprecate `from_user()` and ensure all production callers use `from_user_async()`.

3. **`UserPublic.from_user_async()`** (lines 128-188): Replace all `user.role` reads with:
   ```python
   roles = await unified_service.get_user_roles(user.user_id, "global", None)
   display_role = roles[0] if roles else "viewer"
   ```
   Use `display_role` for both the permission cache lookup AND the `UserPublic.role` field.

4. **`UserUpdate.role`** (line 60): Keep the field. When a user update includes a new role, the route handler should update the `UserRoleAssignment` instead of the column. This is a behavioral change that must be handled in the users route handler (Task C-1 may need to extend to handle role updates).

#### Task C-4: Update AI agent service role resolution

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| C-4 | Replace `user.role` fallback in AI agent role resolution | `app/ai/agent_service.py` | B-3 | SC-F5: AI agent resolves roles correctly | Low |

**Detailed changes to `app/ai/agent_service.py` (line 274):**

Replace:
```python
role = user.role if user else "guest"
```
With:
```python
if user:
    from app.core.rbac_unified import get_unified_rbac_service
    unified_svc = get_unified_rbac_service()
    roles = await unified_svc.get_user_roles(user.user_id, "global", None)
    role = roles[0] if roles else "guest"
else:
    role = "guest"
```

The `_user_role_cache` at lines 260-268 should be updated to cache by `user_id` -> role from `UnifiedRBACService` instead of reading `user.role`.

#### Task C-5: Update AI tool templates

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| C-5 | Replace `user.role` serialization in AI tool templates | `app/ai/tools/templates/user_management_template.py` | B-3 | SC-F5 | Low |

**Detailed changes to `app/ai/tools/templates/user_management_template.py`:**

This file reads `user.role` at 4 locations (lines 102, 167, 250, 348) when serializing user data for AI tool responses.

For each location, the function already has `session` available via `context.session` or `AsyncSession` parameter. Replace `user.role` with:
```python
from app.core.rbac_unified import get_unified_rbac_service, set_unified_rbac_session
set_unified_rbac_session(session)
try:
    unified_svc = get_unified_rbac_service()
    roles = await unified_svc.get_user_roles(user.user_id, "global", None)
    display_role = roles[0] if roles else "unknown"
finally:
    set_unified_rbac_session(None)
```

Alternatively, extract this into a helper function `_get_display_role(user_id: UUID, session: AsyncSession) -> str` to avoid repetition across the 4 locations.

#### Task C-6: Update change order service and route

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| C-6 | Replace `approver.role` in change order error messages and response data | `app/services/change_order_service.py`, `app/api/routes/change_orders.py` | B-3 | Error messages include role | Low |

**Detailed changes:**

1. **`app/services/change_order_service.py`** -- 3 locations (lines 1388, 1550, 2426):
   - Each location already has `self.session` (AsyncSession) available
   - Replace `approver.role` with role resolution via `UnifiedRBACService`
   - The error messages at lines 1388 and 1550 include `approver.role` in the f-string. Resolve the role before raising:
     ```python
     set_unified_rbac_session(self.session)
     try:
         approver_roles = await unified_rbac.get_user_roles(approver.user_id, "global", None)
         approver_role = approver_roles[0] if approver_roles else "unknown"
     finally:
         set_unified_rbac_session(None)
     ```
   - Line 2426: `assigned_approver` dict -- replace `approver.role` with resolved role

2. **`app/api/routes/change_orders.py`** (line 1083):
   - Same pattern -- resolve role from `UnifiedRBACService`
   - The `UnifiedRBACService` is already being used in the same function (lines 1087-1094), so the session is already set

#### Task C-7: Update seeder -- invert bootstrap order

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| C-7 | Invert seeder: create UserRoleAssignment first, derive display role from assignments | `app/db/seeder.py`, `seed/users.json` | B-3 | SC-F6: seed from empty DB succeeds | Medium |

**Detailed changes to `app/db/seeder.py`:**

1. **`seed_users()`** (line 71): Currently creates users with `role` from `users.json`. Change to:
   - Still read `role` from `users.json` for initial `UserRegister` creation
   - The `User` model will still have `role` column at this point in the seeder flow, but the column will be dropped by migration AFTER seeder runs. The seed data in `users.json` includes `role` field -- keep it for now, but the `UserRegister` schema's `role` field should still work (it sets the initial role column value).
   - After removing the `role` column from the `User` model (Task C-9), the `users.json` `role` field will be ignored by `UserRegister`. The `role` field in `UserRegister` should then be removed or repurposed.
   - **Decision**: The seeder should create `UserRoleAssignment` records directly from `users.json` data, without reading `user.role`. This means `seed_user_role_assignments()` should read from the seed data file directly, not from `User.role`.

2. **`seed_user_role_assignments()`** (line 1171): Currently reads `user.role` to determine which `RBACRole` to assign. Change to:
   - Load user seed data from `users.json`
   - For each user in seed data, look up the `role` field from the JSON (not from the DB model)
   - Create `UserRoleAssignment` based on the JSON role name
   - This breaks the dependency on `user.role` column

3. **Alternative simpler approach**: Read from both `users.json` and the existing `user.role` (if column still exists). For the migration period, `seed_user_role_assignments()` can check `users.json` first. After the column is dropped, only the JSON data source is used.

**Seed data `seed/users.json`**: No changes needed -- the file already contains `role` for each user. This becomes the single source of truth for initial role assignment.

#### Task C-8: Remove `role` from `User` model

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| C-8 | Remove role column from User model | `app/models/domain/user.py` | C-1 through C-7 | SC-F8: role column gone from model | Low |

**Detailed changes to `app/models/domain/user.py`:**

1. Remove line 53: `role: Mapped[str] = mapped_column(String(50), nullable=False, default="viewer")`
2. Update class docstring (line 33): Remove "role" from "Versioned fields" list
3. Update `__repr__` (line 68): No change needed (it does not include role)

#### Task C-9: Create Alembic migration to drop `users.role` column

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| C-9 | Create migration to drop role column from users table | New Alembic migration | C-8 | SC-F8: column dropped, migration applies cleanly | Medium |

**Migration structure:**

```python
def upgrade() -> None:
    # Step 1: Verify all users have at least one global UserRoleAssignment
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM users u
                WHERE NOT EXISTS (
                    SELECT 1 FROM user_role_assignments ura
                    WHERE ura.user_id = u.user_id
                    AND ura.scope_type = 'global'
                    AND ura.scope_id IS NULL
                )
            ) THEN
                RAISE EXCEPTION 'Data integrity error: some users lack global role assignments';
            END IF;
        END;
        $$;
    """)

    # Step 2: Drop the column
    op.drop_column('users', 'role')

def downgrade() -> None:
    op.add_column('users', sa.Column('role', sa.String(50), nullable=True, server_default='viewer'))
```

Note: `users` is a versioned table (EVCS). Dropping a column is a non-breaking DDL operation. The `role` column being `NOT NULL` with a default means the downgrade must add it as nullable or with a server default.

#### Task C-10: Update conftest `_create_mock_user` and schemas

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| C-10 | Remove `role` from _create_mock_user, update UserBase/UserRegister | `tests/conftest.py`, `app/models/schemas/user.py` | C-8, C-9 | _create_mock_user works without role | Low |

**Detailed changes:**

1. **`tests/conftest.py`** (`_create_mock_user`, lines 423-449):
   - Remove `role: str = "viewer"` parameter
   - Remove `role=role` from the `User(...)` constructor
   - The `User()` constructor will no longer accept `role` after C-8

2. **`app/models/schemas/user.py`**:
   - `UserBase.role` (line 34): Remove the `role` field from `UserBase` (it is inherited by `UserRegister` and `UserRead`)
   - `UserUpdate.role` (line 60): Remove the `role` field. Role updates should go through the dedicated RBAC assignment endpoint, not user update.
   - `UserPublic.role` (line 90): **Keep** this field -- it is the frontend contract. But it is now populated only via `from_user_async()`, not from the ORM model attribute.
   - `UserPublic.from_user()` (sync): Deprecate. Since `user.role` no longer exists, this cannot work. Either remove it or make it return a default.
   - `UserPublic.from_user_async()` (async): Already updated in C-3. Verify it no longer references `user.role`.

3. **Fixtures that create users with specific roles**: `mock_admin_user`, `mock_viewer_user`, etc. These set `role="admin"` / `role="viewer"` in `_create_mock_user()`. After removing `role` from `_create_mock_user`, these fixtures no longer set role on the `User` instance itself. The role is determined by the `MockUnifiedRBACService` which returns `["admin"]` by default. If specific tests need different roles, they should configure the `MockUnifiedRBACService` accordingly.

#### Task C-11: Final quality gate -- verify Step C is complete

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | ---- | ----- | ------------ | ---------------- | ---------- |
| C-11 | Run full quality checks to verify all steps complete | All | C-1 through C-10 | All SCs pass | Low |

**Verification commands:**
1. `grep -rn "\.role" app/ --include="*.py" | grep -v "rbac_role\|user_id\|role_id\|project_role\|_role\b"` -- must return zero results
2. `grep -rn "User.*role\|user\.role" app/ --include="*.py"` -- must return zero results
3. `uv run alembic upgrade head` -- all migrations apply cleanly
4. `uv run mypy app/` -- zero errors
5. `uv run ruff check .` -- zero errors
6. `uv run pytest --tb=short -q 2>&1 | tail -5` -- all tests pass

---

## Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| --- | --- | --- | --- |
| SC-F1: Route permissions unchanged | T-001 | Existing test suite | All existing tests pass |
| SC-F2: UserPublic.role returns correct value | T-002 | `tests/api/routes/test_auth.py` (existing) | `/auth/me` returns expected role string |
| SC-F3: Admin checks via UnifiedRBACService | T-003 | `tests/api/routes/test_users.py` (existing) | Non-admin gets 403 on admin endpoints |
| SC-F4: Login notification has role | T-004 | `tests/api/routes/auth/test_auth.py` (existing) | Login succeeds, notification payload has role |
| SC-F5: AI agent role resolution | T-005 | `tests/unit/ai/test_agent_service.py` (existing) | Agent resolves roles from UnifiedRBACService |
| SC-F6: Seeder works without user.role | T-006 | `tests/test_seeder.py` (existing or new) | Seed from empty DB creates all data correctly |
| SC-F7: project_members table dropped | T-007 | Alembic migration verification | Table absent after migration |
| SC-F8: users.role column dropped | T-008 | Alembic migration verification | Column absent after migration |
| SC-T1: No legacy RBAC imports in production | T-009 | Grep verification | Zero results |
| SC-T2: No RBACServiceABC in tests | T-010 | Grep verification | Zero results |
| SC-T3: No ProjectMember in tests | T-011 | Grep verification | Zero results |

---

## Test Specification

### Test Hierarchy

```
test_rbac.py (DELETE) -- tests legacy module, no longer applicable
test_rbac_project_access.py (DELETE) -- tests JsonRBACService, no longer applicable

Existing test suite -- all must pass:
tests/api/routes/auth/ -- auth/me role derivation
tests/api/routes/users/ -- admin checks via unified RBAC
tests/api/routes/change_orders/ -- approver role in responses
tests/ai/ -- agent service role resolution
tests/integration/ -- end-to-end permission enforcement
tests/api/test_dependencies/test_project_role_checker.py -- ProjectRole from enums
```

### Test Infrastructure Needs

- **No new test files required** -- the cleanup is verified by existing tests continuing to pass
- **Deleted test files**: `tests/unit/core/test_rbac.py`, `tests/unit/core/test_rbac_project_access.py`
- **Modified fixtures**: `override_auth`, `mock_rbac_service`, `mock_rbac_service_no_ai` (deleted), `_create_mock_user` (role removed)
- **Mock changes**: All test files using `MockRBACService(RBACServiceABC)` switch to `MockUnifiedRBACService`

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| Technical | Test file bulk update introduces subtle breakage (wrong mock pattern) | Medium | Medium | Each test file follows identical mechanical pattern; run full suite after Step A |
| Technical | `UserPublic.from_user()` (sync) cannot resolve role without column | High | High | Deprecate sync version; ensure all callers use `from_user_async()` first |
| Data | Some users lack global `UserRoleAssignment` (migration verification fails) | Low | High | Verification step in migration catches this; manual fix required before migration proceeds |
| Integration | `users.json` seed data role names do not match `RBACRole` names in DB | Low | Medium | Seeder already logs warnings for unrecognized roles; verify role names match before cleanup |
| Technical | `UserRegister.role` removal breaks user creation endpoint | Medium | High | Keep `UserRegister.role` for initial role specification; route handler creates `UserRoleAssignment` during registration |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  # === Step A: Remove app/core/rbac.py ===
  - id: A-1
    name: "Delete app/core/rbac.py and update production references"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: A-2
    name: "Update conftest.py -- remove legacy mock classes and fixtures"
    agent: pdca-backend-do-executor
    dependencies: [A-1]

  - id: A-3
    name: "Update ~50 test files to replace legacy RBAC imports and mocks"
    agent: pdca-backend-do-executor
    dependencies: [A-2]

  - id: A-4
    name: "Quality gate: verify Step A (run mypy, ruff, pytest)"
    agent: pdca-backend-do-executor
    dependencies: [A-3]
    kind: test

  # === Step B: Remove project_member.py ===
  - id: B-1
    name: "Delete ProjectMember model and create verification+drop migration"
    agent: pdca-backend-do-executor
    dependencies: [A-4]

  - id: B-2
    name: "Update 3 test files to replace ProjectMember with UserRoleAssignment"
    agent: pdca-backend-do-executor
    dependencies: [B-1]

  - id: B-3
    name: "Quality gate: verify Step B (run mypy, ruff, pytest)"
    agent: pdca-backend-do-executor
    dependencies: [B-2]
    kind: test

  # === Step C: Remove User.role field ===
  - id: C-1
    name: "Replace admin checks in users.py with UnifiedRBACService lookups"
    agent: pdca-backend-do-executor
    dependencies: [B-3]

  - id: C-2
    name: "Update auth.py login notification role lookup"
    agent: pdca-backend-do-executor
    dependencies: [B-3]

  - id: C-3
    name: "Update UserPublic schema and from_user/from_user_async"
    agent: pdca-backend-do-executor
    dependencies: [B-3]

  - id: C-4
    name: "Update AI agent service role resolution"
    agent: pdca-backend-do-executor
    dependencies: [B-3]

  - id: C-5
    name: "Update AI tool templates (4 locations)"
    agent: pdca-backend-do-executor
    dependencies: [B-3]

  - id: C-6
    name: "Update change order service and route approver.role references"
    agent: pdca-backend-do-executor
    dependencies: [B-3]

  - id: C-7
    name: "Update seeder to invert bootstrap order"
    agent: pdca-backend-do-executor
    dependencies: [B-3]

  - id: C-8
    name: "Remove role column from User model"
    agent: pdca-backend-do-executor
    dependencies: [C-1, C-2, C-3, C-4, C-5, C-6, C-7]

  - id: C-9
    name: "Create Alembic migration to drop users.role column"
    agent: pdca-backend-do-executor
    dependencies: [C-8]

  - id: C-10
    name: "Update conftest _create_mock_user and UserBase/UserRegister schemas"
    agent: pdca-backend-do-executor
    dependencies: [C-8]

  - id: C-11
    name: "Final quality gate: verify all steps (mypy, ruff, pytest, grep checks)"
    agent: pdca-backend-do-executor
    dependencies: [C-9, C-10]
    kind: test
```

---

## Prerequisites

### Technical

- [x] Database is on latest migration (Alembic head)
- [x] `UserRoleAssignment` table exists with data migrated from `User.role` and `project_members`
- [x] `UnifiedRBACService` is fully operational and used by all route-level dependencies
- [x] `MockUnifiedRBACService` exists in `tests/conftest.py`

### Documentation

- [x] Analysis phase approved (00-analysis.md)
- [x] ADR-014 reviewed: `docs/02-architecture/decisions/ADR-014-unified-rbac.md`

---

## Documentation References

### Required Reading

- ADR-014: `docs/02-architecture/decisions/ADR-014-unified-rbac.md`
- UnifiedRBACService: `backend/app/core/rbac_unified.py`
- MockUnifiedRBACService: `backend/tests/conftest.py` (lines 348-420)
- UserRoleAssignment model: `backend/app/models/domain/user_role_assignment.py`

### Code References

- Legacy module (to delete): `backend/app/core/rbac.py`
- Deprecated model (to delete): `backend/app/models/domain/project_member.py`
- User model: `backend/app/models/domain/user.py`
- User schemas: `backend/app/models/schemas/user.py`
- Auth routes: `backend/app/api/routes/auth.py`
- User routes: `backend/app/api/routes/users.py`
- Seeder: `backend/app/db/seeder.py`
- Agent service: `backend/app/ai/agent_service.py`
- AI tool templates: `backend/app/ai/tools/templates/user_management_template.py`
- Change order service: `backend/app/services/change_order_service.py`
- Change order routes: `backend/app/api/routes/change_orders.py`
- Existing RBAC migration: `backend/alembic/versions/20260510b_migrate_existing_roles_to_unified_rbac.py`
