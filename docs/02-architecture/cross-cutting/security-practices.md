# Security Practices

**Last Updated:** 2025-12-29

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
- Algorithm: HS256 (HMAC with SHA-256)
- Payload: `{"sub": "user_id", "exp": timestamp}`
- Secret: 256-bit random key (from environment variable)

**Token Lifetime:**
- Access tokens: 30 minutes
- Refresh tokens: Not yet implemented (planned)

**Security Measures:**
- Tokens signed with `SECRET_KEY` from environment
- Expiration enforced on every request
- No sensitive data in token payload
- Tokens stateless (server doesn't store them)

**Implementation:**
```python
import jwt
from datetime import datetime, timedelta, timezone

def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
```

---

## Authorization

### Role-Based Access Control (RBAC)

**Roles:**
- `admin`: Full system access
- `viewer`: Read-only access
- `editor`: Read + write to own resources

**Enforcement Points:**
- Route level via dependencies (`get_current_active_user`)
- Service layer for fine-grained checks
- Database constraints where possible

**Pattern:**
```python
@router.post("/users")
async def create_user(
    current_user: User = Depends(get_current_active_user),
):
    if current_user.versions[0].role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    # ...
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
    role: str = Field(pattern="^(admin|viewer|editor)$")
```

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
