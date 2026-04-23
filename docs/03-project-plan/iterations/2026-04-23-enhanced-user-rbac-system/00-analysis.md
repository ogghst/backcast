# Analysis: Enhanced User and RBAC System

**Created:** 2026-04-23
**Request:** Create a pluggable and configurable RBAC and user system that abstracts the source of information (JSON file, in-app admin, external identity providers like Microsoft Entra) while keeping actual business rules (project roles, permission-based API and functionalities). This will allow Backcast to scale from self-managed application to corporate scenarios.
**Issue URL:** https://github.com/ogghst/backcast/issues/54

---

## Clarified Requirements

### Problem Statement

Backcast currently has a single-provider architecture for all three pillars of identity and access management:

1. **Role/Permission source**: Hardcoded in `backend/config/rbac.json` (file-based, requires redeployment to change)
2. **User source**: In-app database only (users table, CRUD via admin section)
3. **Authentication source**: In-app JWT with username/password only

The system needs to support corporate scenarios where any combination of these pillars may be externally managed (e.g., Microsoft Entra ID providing user directory, group-based roles, and SSO authentication).

### Functional Requirements

**FR-1: Pluggable Permission Provider**
- The system MUST support loading role/permission mappings from multiple sources:
  - JSON file (current, default for self-managed)
  - Database (editable via admin UI)
  - External systems (e.g., Microsoft Entra groups mapped to Backcast roles)

**FR-2: Pluggable User Provider**
- The system MUST support user identity from multiple sources:
  - In-app database (current, default for self-managed)
  - External directory services (e.g., Microsoft Entra ID, LDAP)
  - Hybrid: local users coexisting with externally-managed users

**FR-3: Pluggable Authentication Provider**
- The system MUST support multiple authentication mechanisms:
  - Local username/password (current)
  - OAuth 2.0 / OpenID Connect (for Entra ID, Google, etc.)
  - SAML 2.0 (future consideration)

**FR-4: Business Rule Preservation**
- Regardless of provider, the following MUST remain consistent:
  - Permission format: `{resource}-{action}` (e.g., `project-read`, `cost-element-write`)
  - Project-level roles: `admin`, `editor`, `viewer` (from `ProjectRole` enum)
  - Project membership model (`ProjectMember` table)
  - `RoleChecker` and `ProjectRoleChecker` FastAPI dependency interfaces
  - AI assistant RBAC roles (`ai-viewer`, `ai-manager`, `ai-admin`)

**FR-5: Configuration-Driven Provider Selection**
- The system MUST allow selecting providers via configuration (environment variables or settings)
- Changing providers SHOULD NOT require code changes, only configuration

### Non-Functional Requirements

- **Performance**: External provider lookups MUST be cached; permission checks MUST remain < 1ms for cached entries
- **Graceful Degradation**: If an external provider is unavailable, the system MUST fail securely (deny access, not grant)
- **Backward Compatibility**: The existing JSON-based RBAC MUST remain the default with zero migration effort
- **No Breaking Changes**: All existing API endpoints, dependencies, and frontend auth flows MUST continue working

### Constraints

- This is a single-server deployment (in-memory caching is acceptable, no Redis needed)
- Microsoft Entra ID is the primary external provider target; the architecture should be generic enough for others
- The existing in-progress iteration (2026-04-23-standardize-ai-assistant-rbac) MUST be completed first or merged without conflict

---

## Context Discovery

### Product Scope

**Relevant Requirements from `docs/01-product-scope/functional-requirements.md`:**

- **Section 11.3 (Security)**: "JWT-based authentication with 15-minute token expiration. Refresh token rotation with 30-day validity. Multi-factor authentication support (optional). Role-based access control (RBAC) with 5 defined roles. Project-level permission isolation."
- **Section 16 (Security and Access Control)**: "Access controls must be configurable at the project level allowing different users to have appropriate access to specific projects based on their roles and responsibilities."
- **Section 21.2 (Organizational Constraints)**: "User Roles and Permissions: See Section 16 for detailed role definitions"

**Vision Document**: Target users include Project Managers, Department Managers, Project Controllers, and Executives -- all are internal corporate users who may authenticate via corporate identity providers.

### Architecture Context

**Bounded Contexts Involved:**
- **User Management** (`backend/contexts/user-management/`): User CRUD, profiles, roles
- **Auth** (`backend/contexts/auth/`): Authentication, JWT, RBAC enforcement
- **AI Integration**: Uses RBAC for tool permission checks (being standardized in active iteration)

**Existing Patterns:**
- `RBACServiceABC` abstract base class with `JsonRBACService` implementation -- already designed for pluggable backends (ADR-007)
- `contextvars` for request-scoped session injection (being added in active iteration)
- `RoleChecker` / `ProjectRoleChecker` as FastAPI dependencies
- `require_permission` decorator for AI tools
- Frontend `useAuthStore` (Zustand) with `permissions` array from `/auth/me`
- Frontend `<Can>` component for declarative authorization

**Archural Constraints:**
- ADR-007 explicitly deferred "Database-only RBAC" as a future iteration, noting "abstract interface allows for easy addition"
- ADR-007 Future Considerations include: "Database-backed RBAC", "API for role management", "Audit logging for authorization decisions"
- The `RBACServiceABC` interface already has the right abstraction level for what we need

### Codebase Analysis

**Backend -- Current Architecture:**

| Component | File | Current State |
|-----------|------|---------------|
| RBAC Service (ABC) | `backend/app/core/rbac.py` | Abstract interface with `has_role`, `has_permission`, `get_user_permissions`, `has_project_access`, `get_user_projects`, `get_project_role` |
| RBAC Implementation | `backend/app/core/rbac.py` | `JsonRBACService` loads from `rbac.json`, singleton via `get_rbac_service()` |
| Auth Dependencies | `backend/app/api/dependencies/auth.py` | `get_current_user` (JWT decode + DB lookup), `RoleChecker`, `ProjectRoleChecker` |
| Auth Routes | `backend/app/api/routes/auth.py` | `/register`, `/login`, `/me`, `/refresh`, `/logout` |
| Security Core | `backend/app/core/security.py` | Argon2 password hashing, JWT creation/validation |
| User Model | `backend/app/models/domain/user.py` | EVCS Versionable entity with `email`, `hashed_password`, `role`, `is_active` |
| User Service | `backend/app/services/user.py` | Extends `TemporalService[User]`, CRUD via versioning commands |
| Project Member | `backend/app/models/domain/project_member.py` | `ProjectMember` with `user_id`, `project_id`, `role` (project-level roles) |
| RBAC Config | `backend/config/rbac.json` | 6 roles: admin, manager, viewer, ai-viewer, ai-manager, ai-admin |
| Settings | `backend/app/core/config.py` | `RBAC_POLICY_FILE` setting, `SECRET_KEY`, `ALGORITHM` |

**Frontend -- Current Architecture:**

| Component | File | Current State |
|-----------|------|---------------|
| Auth Store | `frontend/src/features/auth/` | Zustand store with `token`, `user`, `permissions` |
| Permission Hook | `usePermission` | `hasPermission()` and `hasRole()` |
| `<Can>` Component | `<Can>` | Declarative conditional rendering by permission |
| Route Protection | `ProtectedRoute` | Token + user check, optional role guard |
| Auth API | Login, me endpoints | Email/password form, JWT storage in localStorage |

**Key Insight -- What Already Exists:**

The `RBACServiceABC` is already an abstract interface designed for exactly this kind of extensibility. The `get_rbac_service()` singleton pattern already supports swapping implementations. The gap is NOT in the RBAC abstraction -- it is in:

1. No database-backed implementation of `RBACServiceABC`
2. No external identity provider integration (OAuth2/OIDC)
3. No user directory abstraction (all users must be in the local DB)
4. No admin UI for managing roles/permissions
5. No provider configuration/selection mechanism

---

## Impact on Existing Work

### Active Iteration: 2026-04-23-standardize-ai-assistant-rbac

There is an active iteration on branch `develop` that:
- Adds `ai-viewer`, `ai-manager`, `ai-admin` roles to `rbac.json`
- Adds `default_role` field to `AIAssistantConfig` model
- Removes redundant permission checks from `@ai_tool` decorator
- Adds `contextvars`-based session injection to `rbac.py`
- Updates `ProjectRoleChecker` and middleware to use contextvars
- Filters tools by assistant role in agent creation

**Impact Assessment: LOW CONFLICT RISK**

The active iteration works INSIDE the existing `RBACServiceABC` / `JsonRBACService` framework. The enhanced RBAC system proposed here works AROUND it -- adding alternative implementations of the same abstract interface. The two efforts are complementary:

- The active iteration fixes internal plumbing (session injection, redundant checks)
- This issue adds external pluggability (new providers, admin UI)

**Recommendation:** Complete the active iteration first. Its contextvar changes and AI role additions are prerequisites that this new work builds upon.

---

## Solution Options

### Option 1: Provider Abstraction Layer (Evolutionary)

**Architecture & Design:**

Extend the existing `RBACServiceABC` pattern with three independent provider abstractions, each following the same ABC + concrete implementation + factory pattern already established.

**New Abstractions:**

1. **PermissionProvider** (replaces/enhances `RBACServiceABC`):
   - `JsonPermissionProvider` (current `JsonRBACService`, renamed)
   - `DatabasePermissionProvider` (new, stores roles/permissions in DB tables)
   - `EntraPermissionProvider` (new, maps Entra groups to Backcast permissions)

2. **UserProvider**:
   - `LocalUserProvider` (current `UserService`, wraps existing functionality)
   - `EntraUserProvider` (new, reads users from Microsoft Graph API)
   - `HybridUserProvider` (new, merges local + external users)

3. **AuthProvider**:
   - `LocalAuthProvider` (current JWT + password flow)
   - `OIDCAuthProvider` (new, OpenID Connect for Entra/Google/etc.)

**Factory Pattern:**

```python
# backend/app/core/providers/__init__.py
def create_rbac_service() -> RBACServiceABC:
    provider_type = settings.RBAC_PROVIDER  # "json" | "database" | "entra"
    if provider_type == "json":
        return JsonRBACService(...)
    elif provider_type == "database":
        return DatabaseRBACService(...)
    elif provider_type == "entra":
        return EntraRBACService(...)

def create_auth_provider() -> AuthProvider:
    provider_type = settings.AUTH_PROVIDER  # "local" | "oidc"
    ...
```

**Settings additions:**

```
RBAC_PROVIDER=json          # json | database | entra
AUTH_PROVIDER=local         # local | oidc
USER_PROVIDER=local         # local | entra | hybrid
OIDC_CLIENT_ID=             # Entra/other OIDC client ID
OIDC_CLIENT_SECRET=         # Entra/other OIDC client secret
OIDC_TENANT_ID=             # Entra tenant ID
OIDC_DISCOVERY_URL=         # Auto-constructed from tenant ID for Entra
```

**Database schema additions:**

New tables: `rbac_roles`, `rbac_role_permissions`, `external_user_mappings`

**UX Design:**

- Admin section gains "RBAC Configuration" page with tabs for roles/permissions management
- Login page gains "Sign in with Microsoft" button when OIDC is configured
- User list page shows source indicator (local vs external) per user
- No changes to project-level permission UI (ProjectMember model unchanged)

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Follows existing ABC pattern (ADR-007); each provider is independently testable; gradual rollout possible; no breaking changes; existing JsonRBACService works unchanged |
| Cons            | Three new abstractions to maintain; external provider integrations have complexity (token refresh, API rate limits, caching); admin UI is new frontend work |
| Complexity      | Medium-High |
| Maintainability | Good -- each provider is isolated behind an ABC |
| Performance     | Good -- caching layer between providers and checks |

---

### Option 2: Strategy Pattern with Unified Identity Provider

**Architecture & Design:**

Instead of three separate provider abstractions, create a single `IdentityProvider` abstraction that handles authentication, user lookup, and permission resolution as a unified concern.

**Single Abstraction:**

1. **IdentityProvider** (ABC):
   - `LocalIdentityProvider` (wraps current auth + user + RBAC)
   - `EntraIdentityProvider` (wraps OIDC + Graph API + group-to-role mapping)
   - `DatabaseIdentityProvider` (local auth + DB-stored roles)

**How it works:**

Each `IdentityProvider` implementation is responsible for the complete chain:
1. Authenticate the user (validate credentials/token)
2. Resolve the user's identity (email, name, roles)
3. Resolve the user's permissions (from roles or direct mapping)
4. Provide project-level access checks

The existing `get_current_user` FastAPI dependency becomes provider-aware, delegating to the configured `IdentityProvider` instead of directly decoding JWTs.

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Simpler mental model (one abstraction instead of three); easier to add new providers (one class to implement); avoids complex provider composition logic |
| Cons            | Violates single responsibility (one class handles auth + users + permissions); harder to mix-and-match providers (e.g., local auth with Entra permissions); each provider reimplements common logic (caching, session management) |
| Complexity      | Medium |
| Maintainability | Fair -- providers tend to grow large and monolithic |
| Performance     | Good |

---

### Option 3: Incremental Entra-First (Minimum Viable)

**Architecture & Design:**

Skip the full abstraction layer. Add OIDC authentication and Entra group-to-role mapping as the minimum viable external integration. Keep the existing `RBACServiceABC` as-is, add only what is needed for Entra.

**Changes:**

1. Add `authlib` or `python-social-auth` dependency for OIDC
2. Add new auth routes: `/auth/oidc/login`, `/auth/oidc/callback`
3. Add Entra group-to-Backcast-role mapping in `rbac.json` or a new config section
4. On OIDC login: create/update local user record from Entra profile, map groups to roles
5. Local users continue to use existing password flow

No new abstractions, no database-backed RBAC, no admin UI for role editing. The JSON file remains the single source of truth for permissions, but role assignment can come from Entra groups.

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | ---------- |
| Pros            | Smallest scope; fastest to deliver; minimal risk; addresses the most likely corporate scenario (Entra SSO) first |
| Cons            | Not truly pluggable; adding a second external provider requires refactoring; no admin UI for role management; role-to-permission mapping still requires JSON file changes and redeployment |
| Complexity      | Low-Medium |
| Maintainability | Poor long-term -- will need refactoring when adding database RBAC or second external provider |
| Performance     | Good |

---

## Comparison Summary

| Criteria           | Option 1: Provider Abstraction | Option 2: Unified Identity | Option 3: Entra-First |
| ------------------ | ------------------------------ | -------------------------- | --------------------- |
| Development Effort | High (3-4 iterations)          | Medium (2-3 iterations)    | Low (1 iteration)     |
| Flexibility        | Excellent                      | Good                       | Limited               |
| Admin UI           | Included                       | Included                   | Not included          |
| Extensibility      | Excellent (add providers independently) | Good (add provider class) | Poor (refactor needed) |
| Risk               | Medium (scope)                 | Medium (monolith risk)     | Low                   |
| Backward Compat    | Full (JsonRBACService preserved) | Full                    | Full                  |
| Best For           | Long-term platform; multi-corp | Moderate extensibility     | Quick Entra SSO win   |

---

## Recommendation

**I recommend Option 1 (Provider Abstraction Layer) delivered incrementally across multiple iterations, starting with the highest-value pieces first.**

**Rationale:**

1. **The architecture is already half-built.** `RBACServiceABC` was explicitly designed for this (ADR-007: "Easy to add database-backed implementation via abstract interface"). The factory pattern (`get_rbac_service()`) already supports swapping implementations. We are extending an established pattern, not creating a new one.

2. **The three pillars are genuinely independent concerns.** Authentication (how you log in), user directory (who you are), and permissions (what you can do) have different change rates, different external dependencies, and different caching strategies. Separating them is correct architecture, not over-engineering.

3. **Incremental delivery is natural.** Each provider can be built and shipped independently:
   - Phase 1: OIDC authentication (highest corporate value)
   - Phase 2: Database-backed RBAC with admin UI (self-managed flexibility)
   - Phase 3: External user directory integration (Entra user sync)

4. **Option 3 (Entra-First) builds technical debt.** It adds OIDC without the abstraction layer that makes it pluggable. When database RBAC is needed later, the OIDC integration would need refactoring.

5. **Option 2 (Unified Provider) creates monoliths.** Each identity provider class would grow to 500+ lines covering auth + users + permissions, violating SRP and making testing harder.

**Alternative consideration:** If the immediate business need is ONLY "let users sign in with Microsoft Entra" and there is no near-term plan for database-backed RBAC or admin UI, Option 3 delivers fastest. However, given that ADR-007 already identified database RBAC as a future need and the codebase is already structured for it, the incremental cost of Option 1 over Option 3 is modest.

---

## Suggested Iteration Breakdown

### Prerequisite: Complete active iteration 2026-04-23-standardize-ai-assistant-rbac

The contextvar session injection and AI role standardization must be merged before this work begins.

### Iteration 1: OIDC Authentication + Provider Framework (8-13 points)

**Scope:**
- Create `backend/app/core/providers/` package with `AuthProvider` ABC
- Implement `LocalAuthProvider` (wraps current JWT + password logic)
- Implement `OIDCAuthProvider` (OIDC discovery, authorization code flow, token validation)
- Add `authlib` dependency
- Add OIDC configuration to `Settings` (`AUTH_PROVIDER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_TENANT_ID`)
- Add auth routes: `/auth/oidc/login`, `/auth/oidc/callback`
- Update `get_current_user` to delegate to configured auth provider
- On OIDC login: create/update local `User` record from OIDC claims
- Frontend: Add "Sign in with Microsoft" button on login page (conditionally shown)
- Tests for auth provider ABC, OIDC flow, local auth preservation

**Dependencies:** Active AI RBAC iteration complete

### Iteration 2: Database-Backed RBAC + Admin API (8-13 points)

**Scope:**
- Create `DatabaseRBACService` implementing `RBACServiceABC`
- Database schema: `rbac_roles` table, `rbac_role_permissions` table
- Alembic migration for new tables
- Seed from `rbac.json` on first run (migration)
- Admin API endpoints: CRUD for roles and permissions
- `RBAC_PROVIDER` setting: `json` (default) or `database`
- Cache layer with TTL for database lookups
- Tests for database RBAC service, admin API

**Dependencies:** None (independent of Iteration 1)

### Iteration 3: Admin UI + User Source Indicator (5-8 points)

**Scope:**
- Frontend: RBAC Configuration page in Admin section
- Role/permission management UI (CRUD)
- User list: show auth source indicator (local/OIDC)
- User detail: show linked external identity info
- Frontend tests for admin RBAC UI

**Dependencies:** Iteration 2

### Iteration 4: External User Provider (5-8 points) -- Optional

**Scope:**
- Create `UserProvider` ABC
- `EntraUserProvider`: read users/groups from Microsoft Graph API
- `HybridUserProvider`: merge local + external users
- User sync job: periodic sync from Entra to local DB
- `USER_PROVIDER` setting
- Frontend: user source management in admin

**Dependencies:** Iteration 1

---

## Risks and Dependencies

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| OIDC token validation edge cases (nonce, PKCE, token replay) | Medium | Medium | Use well-tested library (`authlib`), follow OIDC spec strictly |
| Entra group-to-role mapping complexity (nested groups, dynamic groups) | Medium | Low | Start with flat group mapping; nested groups deferred |
| Database RBAC performance under load | Low | Medium | Cache with TTL; benchmark before release |
| Frontend auth flow changes break existing sessions | Low | High | OIDC is additive; local auth unchanged; feature-flagged |
| Migration from JSON to DB RBAC loses customizations | Low | High | Seed script reads existing `rbac.json` and imports into DB |
| Active iteration conflicts | Low | Medium | Complete active iteration first; this builds on its contextvar changes |

**External Dependencies:**
- `authlib` Python package (OIDC client library)
- Microsoft Entra ID tenant and app registration (for testing)
- No infrastructure changes needed (single-server deployment)

---

## Decisions

1. **Start with Database-Backed RBAC + Admin UI.** OIDC authentication is deferred to a future iteration, but the provider abstraction architecture MUST already plan for it (ABC interfaces, factory pattern, settings placeholders). This gives immediate value for self-managed deployments while laying the groundwork for OIDC later.

2. **Copy-on-login for external users.** When OIDC is implemented, external users will be created/updated in the local DB on first login from OIDC claims. This preserves the EVCS User model, avoids real-time external directory queries, and keeps the system resilient to external provider downtime.

3. **Entra group-to-Backcast-role mapping.** A configurable mapping table in the database (or config file initially) that maps Entra group IDs/names to Backcast roles. This is more flexible than Entra app roles and doesn't require Entra admin privileges to reconfigure.

4. **Admin UI for both providers.** The admin RBAC configuration UI will be available regardless of the active provider. When using the JSON provider, it shows the current configuration in read-only mode with a clear prompt to switch to the database provider for editing. When using the database provider, full CRUD is available.

### Revised Iteration Order

1. **Iteration 1 (NOW):** Provider Framework + Database-Backed RBAC + Admin API + Admin UI
2. **Iteration 2 (NEXT):** OIDC Authentication + Entra Group Mapping
3. **Iteration 3 (LATER):** External User Provider + Hybrid User Directory

---

## References

**Architecture Docs:**
- [ADR-007: RBAC Service Design](/home/nicola/dev/backcast/docs/02-architecture/decisions/ADR-007-rbac-service.md)
- [Auth Context Architecture](/home/nicola/dev/backcast/docs/02-architecture/backend/contexts/auth/architecture.md)
- [User Management Context](/home/nicola/dev/backcast/docs/02-architecture/backend/contexts/user-management/architecture.md)
- [Frontend Auth Context](/home/nicola/dev/backcast/docs/02-architecture/frontend/contexts/06-authentication.md)
- [Security Practices](/home/nicola/dev/backcast/docs/02-architecture/cross-cutting/security-practices.md)

**Source Files:**
- `backend/app/core/rbac.py` -- `RBACServiceABC`, `JsonRBACService`, `require_permission`, `inject_rbac_session`
- `backend/app/api/dependencies/auth.py` -- `get_current_user`, `RoleChecker`, `ProjectRoleChecker`
- `backend/app/api/routes/auth.py` -- Auth endpoints (`/register`, `/login`, `/me`, `/refresh`, `/logout`)
- `backend/app/core/security.py` -- JWT creation, Argon2 password hashing
- `backend/app/core/config.py` -- Settings with `RBAC_POLICY_FILE`
- `backend/app/models/domain/user.py` -- User model (EVCS Versionable)
- `backend/app/models/domain/project_member.py` -- ProjectMember model
- `backend/app/services/user.py` -- UserService extending TemporalService
- `backend/config/rbac.json` -- Current RBAC configuration (6 roles)

**Active Iteration:**
- [Standardize AI Assistant RBAC (00-analysis)](/home/nicola/dev/backcast/docs/03-project-plan/iterations/2026-04-23-standardize-ai-assistant-rbac/00-analysis.md)

**GitHub Issue:**
- https://github.com/ogghst/backcast/issues/54

**Product Scope:**
- [Functional Requirements](/home/nicola/dev/backcast/docs/01-product-scope/functional-requirements.md) (Sections 11.3, 16, 21.2)
