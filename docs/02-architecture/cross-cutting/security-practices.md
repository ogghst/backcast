# Security Practices

**Last Updated:** 2026-07-01

## Authentication

### Password Security

**Hashing Algorithm:** Argon2 (via pwdlib)
- Industry-standard key derivation function
- Memory-hard algorithm resistant to GPU attacks
- Automatic parameter tuning for security/performance balance

**Implementation:**
```python
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()
hashed = password_hash.hash("user_password")
is_valid = password_hash.verify("user_password", hashed)
```

**Password Requirements:**
- Minimum 8 characters
- No maximum length (hashed regardless)
- No complexity requirements enforced (rely on strong hashing)
- Future: Consider implementing password strength meter

---

### JWT Token Security

**Token Structure:**
- Algorithm: configurable via `settings.ALGORITHM` (env-driven; `jwt_utils.py` validates with `algorithms=[settings.ALGORITHM]`). Not hardcoded to HS256.
- Payload: `{"sub": "user_id", "exp": timestamp}`
- Secret: `SECRET_KEY` from environment

**Token Lifetime:**
- Access tokens: `settings.ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 minutes)
- Refresh tokens: implemented — login (`POST /api/auth/login`) returns both an access and a refresh token; `POST /api/auth/refresh` issues a new access token from a valid refresh token; `POST /api/auth/logout` revokes it. Lifetime is `settings.REFRESH_TOKEN_EXPIRE_DAYS` (default 30 days).

**Security Measures:**
- Tokens signed with `SECRET_KEY` from environment, using `settings.ALGORITHM`
- Expiration enforced on every request (expired tokens rejected in `validate_jwt_token`)
- No sensitive data in token payload
- Refresh tokens are revocable server-side (not purely stateless)

**Implementation:**
```python
import jwt
from datetime import datetime, timedelta, timezone

def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

> **Active-user cache:** `get_current_user` performs a cache-first `is_active` check against the in-memory `_user_active_cache` (TTL 300s). A deactivated user may retain access until the TTL elapses, so any deactivation path **must** call `invalidate_user_active_cache(user_id)` to take effect immediately.

---

## Authorization

### Unified RBAC

The legacy single-column `User.role` model (and the `admin`/`viewer`/`editor` triple) was removed during the 2026-05-16 Unified RBAC cleanup — the `users.role` column was dropped (migration `fa57821982c7_drop_users_role_column.py`) and code no longer reads `current_user.versions[0].role`. Authorization is now driven by **scoped role assignments** managed by `UnifiedRBACService` (`app/core/rbac_unified.py`). See [ADR-014: Unified RBAC System](../decisions/ADR-014-unified-rbac.md).

**Data model:** `UserRoleAssignment(user_id, role_id, scope_type, scope_id, metadata_, granted_by, granted_at, expires_at)` where `scope_type ∈ {GLOBAL, PROJECT, CHANGE_ORDER}` (`scope_id` is NULL for global). Roles and their permission strings live in `rbac_roles` / `rbac_role_permissions` (seeded from `app/db/seed_users_rbac.py`).

**Roles (seeded):** `admin`, `manager`, `cost-controller`, `pmo-director`, `viewer`, `ai-viewer`, `ai-manager`, `ai-admin`. The `admin` global role short-circuits every check and `get_user_permissions()` returns the wildcard `["*"]` for it.

**Permissions:** granular strings (e.g. `project-read`, `project-update`, `cost-registration-create`, `evm-read`, `ai-chat`, `mcp-tool-execute`). Notable gates:
- `portfolio-read` is manager+ only — intentionally **not** granted to `viewer` / `ai-viewer`.
- `role-assignment-{read,create,update,delete}` is `admin`-only.

**Resolution order (`has_permission`):** (1) global roles are always checked; (2) `admin` global role bypasses everything; (3) otherwise the scoped role for the requested `scope_type`/`scope_id` is also checked. Checks are cache-first (permissions cache TTL 1h, assignment cache TTL 5min) and fail-secure.

**Enforcement points:**
- Route level via dependencies — `RoleChecker` (global roles/permissions, incl. any-of `required_permissions`) and `ProjectRoleChecker` (project-scoped permission). Both delegate to `UnifiedRBACService`.
- Service layer for fine-grained/authority checks (`has_authority_level` for change-order approvals: LOW < MEDIUM < HIGH < CRITICAL).

**Pattern:**
```python
from app.api.dependencies.auth import RoleChecker, ProjectRoleChecker

# Global permission check
@router.delete("/users/{user_id}",
    dependencies=[Depends(RoleChecker(required_permission="user-delete"))])
async def delete_user(user_id: UUID): ...

# Any-of permissions (route reachable by holders of different read perms)
@router.get("/dashboard",
    dependencies=[Depends(RoleChecker(required_permissions=["project-read", "portfolio-read"]))])
async def dashboard(): ...

# Project-scoped permission check
@router.put("/projects/{project_id}",
    dependencies=[Depends(ProjectRoleChecker(required_permission="project-update"))])
async def update_project(project_id: UUID): ...
```

---

## Input Validation

### Pydantic Schemas

All API inputs validated through Pydantic:
- Type checking
- Format validation (email, UUID, etc.)
- Custom validators for business rules
- Automatic error responses (422)

**Example:**
```python
class UserRegister(BaseModel):
    email: EmailStr  # Validates email format
    password: str = Field(min_length=8)
```

> Note: effective authorization is governed by Unified RBAC role assignments (see above), not by a role string on the registration payload.

### SQL Injection Prevention

**SQLAlchemy ORM:**
- Parameterized queries (never string concatenation)
- Type-safe query construction
- No raw SQL without careful review

**❌ Never do this:**
```python
query = f"SELECT * FROM users WHERE email = '{email}'"
```

**✅ Always do this:**
```python
stmt = select(User).where(User.email == email)
```

---

## Data Protection

### Sensitive Data Handling

**Never Log:**
- Passwords (hashed or plain)
- JWT tokens
- API keys
- Personal identifiable information (PII) without masking

**Storage:**
- Passwords: Only hashed values in database
- Secrets: Environment variables, never in code
- PII: Encrypted at rest (future enhancement)

### Data Minimization
- Only collect necessary data
- Delete inactive users after retention period (future)
- Audit log retention: 2 years

---

## CORS Security

### Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,  # Explicit list
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Production:**
- Whitelist specific origins only
- Never use `allow_origins=["*"]` with `allow_credentials=True`

---

## Error Handling Security

### Avoid Information Leakage

**❌ Don't expose:**
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))  # Leaks internals
```

**✅ Generic errors for users:**
```python
except Exception as e:
    logger.error(f"Error processing request: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### Logging
- Log full errors for debugging
- Return generic messages to users
- Never log credentials or tokens

---

## Dependency Security

### Vulnerability Scanning

**Tools:**
- `pip-audit`: Scan for known vulnerabilities
- Dependabot: Automated updates (GitHub)

**Process:**
- Run `pip-audit` before each deployment
- Review and update dependencies monthly
- Test updates in staging first

---

## Security Headers

### Recommended Headers (Future)
```python
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

---

## Audit Trail

### What to Log
- Authentication events (login, logout, failures)
- Authorization failures
- Data modifications (via versioning system)
- Admin actions

### How to Log
```python
logger.info(
    "User authentication",
    extra={
        "user_id": user.id,
        "action": "login",
        "ip_address": request.client.host,
        "timestamp": datetime.now(timezone.utc),
    }
)
```

---

## Incident Response

### Security Incident Protocol

1. **Detect**: Monitor logs for suspicious activity
2. **Contain**: Disable affected accounts immediately
3. **Investigate**: Review audit logs, identify scope
4. **Remediate**: Fix vulnerability, patch system
5. **Notify**: Inform affected users if PII compromised
6. **Document**: Post-mortem, update security practices

### Contact
- Security incidents: [security@example.com]
- Escalation: [CTO contact]

---

## Compliance

### GDPR Considerations (Future)
- User data export API
- Right to deletion implementation
- Consent management
- Data retention policies

### Future Security Enhancements
- [ ] Two-factor authentication (2FA)
- [ ] API key management for service accounts
- [ ] IP whitelisting for admin endpoints
- [ ] Security scanning in CI/CD pipeline
- [ ] Penetration testing schedule
