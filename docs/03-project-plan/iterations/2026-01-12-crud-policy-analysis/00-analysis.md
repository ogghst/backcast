## Request Analysis: Analyze CRUD Policies & Externalize Configuration

### Clarified Requirements

The user wants to evaluate the current backend CRUD policies (Authentication, Authorization, Validation) for production readiness. Specifically:

1.  **Analyze current RBAC policies**: Are the roles and permissions defined in `backend/config/rbac.json` sufficient for a production environment?
2.  **Move configuration to .env**: Identify hardcoded configuration values (specifically the RBAC configuration path and potentially others) and move them to environment variables.
3.  **Output**: An analysis document following `docs/04-pdca-prompts/analysis-prompt.md`.

### Context Discovery Findings

**Product Scope:**

- The system manages complexity entities: **Projects, WBEs, Cost Elements**.
- **Users** have roles: `admin`, `manager`, `viewer`.
- **Current State**: `rbac.json` defines broad permissions for `admin` but very limited permissions for `manager` (only user/department) and `viewer` (only department).

**Architecture Context:**

- **RBAC**: Implemented in `backend/app/core/rbac.py` as `JsonRBACService`.
- **Configuration**: managed via `backend/app/api/dependencies/auth.py` and `backend/app/core/config.py`.
- **Patterns**: Decorator-based permission checking (`@Depends(RoleChecker(required_permission="..."))`) is used consistently in routes.

**Codebase Analysis:**

- **Backend**:
  - `backend/app/core/rbac.py`: Hardcodes the path to `config/rbac.json` in `JsonRBACService` default init.
  - `backend/config/rbac.json`:
    - `admin`: Full access (Good).
    - `manager`: Missing access to Projects, WBEs, Cost Elements. **Insufficient for production**.
    - `viewer`: Missing access to Projects, WBEs, Cost Elements. **Insufficient for production**.
  - `backend/app/core/config.py`: Uses `pydantic-settings`. Most settings are overridable, but `RBAC_CONFIG_FILE` is missing from `Settings`.

---

## Solution Options

### Option 1: Enhanced File-Based RBAC (Recommended)

**Architecture & Design:**

- Keep the JSON-based RBAC service but make the file path configurable via `Settings`.
- Update `rbac.json` to reflect realistic production roles.

**UX Design:**

- No direct UI change, but enables "Manager" and "Viewer" users to actually use the application's core features (Projects/WBEs).

**Implementation:**

1.  **Modify `backend/app/core/config.py`**: Add `RBAC_POLICY_FILE: str = "config/rbac.json"` to `Settings`.
2.  **Modify `backend/app/core/rbac.py`**: Inject `settings.RBAC_POLICY_FILE` into `JsonRBACService` initialization instead of hardcoded path logic.
3.  **Update `backend/config/rbac.json`**:
    - **Manager**: Add `read/create/update` for Projects, WBEs, Cost Elements.
    - **Viewer**: Add `read` for Projects, WBEs, Cost Elements.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | Simple, version-controllable permissions, fix immediate gaps. |
| Cons | Requires redeploy to change permissions (unlike DB-based). |
| Complexity | Low |
| Maintainability | Good (Config as Code) |
| Performance | Excellent (In-memory lookup) |

---

### Option 2: Database-Based RBAC

**Architecture & Design:**

- Migrate roles and permissions to database tables (`roles`, `permissions`, `role_permissions`).
- Implement `DbRBACService`.

**Implementation:**

- Create models, migrations, and admin API to manage roles.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | Dynamic updates at runtime, fine-grained control via UI. |
| Cons | High complexity to implement now (new tables, UI pages). Overkill for current stage. |
| Complexity | High |
| Maintainability | Fair (More moving parts) |

---

## Comparison Summary

| Criteria           | Option 1 (File-Based)  | Option 2 (DB-Based) |
| ------------------ | ---------------------- | ------------------- |
| Development Effort | Low (< 1 hour)         | High (2-3 days)     |
| Flexibility        | Medium (Deploy needed) | High (Runtime)      |
| Production Ready   | Yes                    | Yes                 |

## Recommendation

**I recommend Option 1** because:

1.  It addresses the immediate "insufficient policies" issue with minimal complexity.
2.  It satisfies the requirement to "move configuration in .env".
3.  File-based RBAC is sufficient for internal enterprise apps where roles don't change daily.

**Action Plan:**

1.  Update `backend/app/core/config.py` to include `RBAC_POLICY_FILE`.
2.  Refactor `backend/app/core/rbac.py` to use `settings`.
3.  Expand `backend/config/rbac.json` with full permissions for Manager/Viewer.
