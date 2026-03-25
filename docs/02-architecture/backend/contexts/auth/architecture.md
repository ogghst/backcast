# Authentication & Authorization Architecture

**Last Updated:** 2026-01-04  
**Owner:** Backend Team  
**ADRs:**

- [ADR-007: RBAC Service Design](../../decisions/ADR-007-rbac-service.md)

---

## Responsibility

The Authentication & Authorization (Auth) context provides secure user identity verification and fine-grained access control for the Backcast  system. It enables:

- **User Authentication:** JWT-based token generation and validation
- **Role-Based Access Control (RBAC):** Permission management with resource-specific granularity
- **Declarative Authorization:** FastAPI dependency injection for route protection
- **Extensible Design:** Abstract interface allowing multiple RBAC backends (JSON, database, external services)

---

## Architecture

### Component Overview

```mermaid
graph TB
    subgraph "API Layer"
        A[Auth Routes /auth/*]
        B[Protected Routes]
    end

    subgraph "Dependencies Layer"
        C[get_current_user]
        D[get_current_active_user]
        E[RoleChecker]
    end

    subgraph "Service Layer"
        F[AuthService]
        G[UserService]
        H[RBACService]
    end

    subgraph "Core Security"
        I[JWT Token Utils]
        J[Password Hashing]
    end

    subgraph "Model Layer"
        K[User Model]
        L[RBAC Config]
    end

    A --> C
    B --> E
    E --> C
    E --> H
    C --> I
    C --> G
    F --> I
    F --> J
    F --> G
    H --> L
    G --> K
```

### Layer Responsibilities

| Layer            | Responsibility                            | Key Components                                            |
| ---------------- | ----------------------------------------- | --------------------------------------------------------- |
| **API**          | HTTP endpoints for auth operations        | `/auth/register`, `/auth/login`, `/auth/me`               |
| **Dependencies** | Reusable auth/authz checks                | `get_current_user`, `RoleChecker`                         |
| **Service**      | Business logic for auth & user management | `AuthService`, `UserService`, `RBACServiceABC`            |
| **Core**         | Cryptographic operations                  | `create_access_token`, `verify_password`, `hash_password` |
| **Model**        | Data structures                           | `User`, `Token`, `rbac.json`                              |

---

## Authentication Flow

### 1. User Registration

```mermaid
sequenceDiagram
    participant C as Client
    participant API as /auth/register
    participant SVC as UserService
    participant DB as Database

    C->>API: POST /auth/register
    API->>API: Validate UserRegister schema
    API->>SVC: create_user(user_in, actor_id)
    SVC->>SVC: hash_password()
    SVC->>DB: INSERT user
    DB-->>SVC: User created
    SVC-->>API: UserPublic
    API-->>C: 201 Created + UserPublic
```

**Key Points:**

- Password hashing performed in `UserService` layer
- Default role: `viewer`
- Actor ID for registration: system UUID (`00000000-0000-0000-0000-000000000000`)

### 2. User Login

```mermaid
sequenceDiagram
    participant C as Client
    participant API as /auth/login
    participant Auth as AuthService
    participant User as UserService
    participant JWT as Security Core
    participant DB as Database

    C->>API: POST /auth/login (credentials)
    API->>Auth: authenticate(email, password)
    Auth->>User: get_by_email(email)
    User->>DB: SELECT user
    DB-->>User: User record
    User-->>Auth: User | None
    Auth->>Auth: verify_password()
    alt Valid credentials
        Auth->>JWT: create_access_token(sub=email)
        JWT-->>Auth: JWT token
        Auth-->>API: Token
        API-->>C: 200 OK + {access_token, token_type}
    else Invalid credentials
        Auth-->>API: None
        API-->>C: 401 Unauthorized
    end
```

**JWT Payload:**

```json
{
  "sub": "user@example.com",
  "exp": "<expiration_timestamp>"
}
```

### 3. Protected Route Access

```mermaid
sequenceDiagram
    participant C as Client
    participant Route as Protected Route
    participant Dep as get_current_user
    participant JWT as Security Core
    participant User as UserService
    participant DB as Database

    C->>Route: GET /users (Bearer token)
    Route->>Dep: Depends(get_current_user)
    Dep->>JWT: jwt.decode(token)
    JWT-->>Dep: {sub: email}
    Dep->>User: get_by_email(email)
    User->>DB: SELECT user
    DB-->>User: User record
    User-->>Dep: User
    alt Active user
        Dep-->>Route: User object
        Route-->>C: 200 OK + data
    else Inactive or not found
        Dep-->>Route: HTTPException(401)
        Route-->>C: 401 Unauthorized
    end
```

---

## Authorization (RBAC) Flow

### Architecture

The RBAC system follows an **abstract interface + concrete implementation** pattern:

```mermaid
classDiagram
    class RBACServiceABC {
        <<abstract>>
        +has_role(user_role, required_roles) bool
        +has_permission(user_role, permission) bool
        +get_user_permissions(user_role) list[str]
    }

    class JsonRBACService {
        -config_path: Path
        -_config: dict
        +_load_config() dict
        +has_role() bool
        +has_permission() bool
        +get_user_permissions() list[str]
    }

    class RoleChecker {
        -allowed_roles: list[str] | None
        -required_permission: str | None
        +__call__(current_user, rbac_service) User
    }

    RBACServiceABC <|-- JsonRBACService : implements
    RoleChecker --> RBACServiceABC : depends on
```

### Permission Model

**Resource-Specific Permissions** - Format: `{resource}-{action}`

```json
{
  "roles": {
    "admin": {
      "permissions": [
        "user-read",
        "user-create",
        "user-update",
        "user-delete",
        "department-read",
        "department-create",
        "department-update",
        "department-delete"
      ]
    },
    "manager": {
      "permissions": [
        "user-read",
        "user-update",
        "department-read",
        "department-create",
        "department-update"
      ]
    },
    "viewer": {
      "permissions": ["user-read", "department-read"]
    }
  }
}
```

**Benefits:**

- **Granular Control:** Separate read/write access per resource
- **Resource Isolation:** Can grant user access without department access
- **Scalability:** Easy to add new resources with independent permissions
- **Audit Clarity:** Clear understanding of what each permission grants

### RoleChecker Dependency

The `RoleChecker` provides **three authorization modes**:

#### 1. Role-Only Authorization

```python
@router.get("/admin", dependencies=[Depends(RoleChecker(["admin"]))])
async def admin_only_route():
    return {"message": "Admin access"}
```

**Logic:** User's role must be in `allowed_roles` list

#### 2. Permission-Only Authorization

```python
@router.get("/users", dependencies=[Depends(RoleChecker(required_permission="user-read"))])
async def list_users():
    return {"users": [...]}
```

**Logic:** User's role must have the `required_permission`

#### 3. Combined Authorization (OR Logic)

```python
@router.delete(
    "/users/{id}",
    dependencies=[Depends(RoleChecker(["admin"], "user-delete"))]
)
async def delete_user(id: UUID):
    return {"deleted": id}
```

**Logic:** User passes if **either** they have admin role **OR** user-delete permission

### Authorization Decision Flow

```mermaid
flowchart TD
    A[Request arrives] --> B{RoleChecker configured?}
    B -->|No| C[Allow - no auth required]
    B -->|Yes| D[Get current_user]
    D --> E{allowed_roles specified?}
    E -->|Yes| F{user.role in allowed_roles?}
    F -->|Yes| C
    F -->|No| G{required_permission specified?}
    E -->|No| G
    G -->|Yes| H{has_permission\user.role, permission\?}
    G -->|No| I[Deny - no criteria]
    H -->|Yes| C
    H -->|No| I
    I --> J[HTTP 403 Forbidden]
```

---

## Security Components

### JWT Configuration

**Algorithm:** HS256 (HMAC with SHA-256)

**Token Expiration:** 30 minutes (configurable via `settings.ACCESS_TOKEN_EXPIRE_MINUTES`)

**Payload:**

```python
{
    "sub": str,  # Subject (user email)
    "exp": int   # Expiration timestamp
}
```

**Secret Key:** Environment variable `SECRET_KEY` (must be 32+ characters)

### Password Hashing

**Library:** `passlib` with `bcrypt` scheme

**Configuration:**

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

**Functions:**

- `hash_password(password: str) -> str`: Create bcrypt hash
- `verify_password(plain: str, hashed: str) -> bool`: Verify password

---

## Code Locations

### Core Files

```
backend/app/
├── api/
│   ├── dependencies/
│   │   └── auth.py                    # Auth dependencies (get_current_user, RoleChecker)
│   └── routes/
│       ├── auth.py                    # Auth endpoints (/register, /login, /me)
│       ├── users.py                   # User management with RBAC
│       └── departments.py             # Department management with RBAC
├── core/
│   ├── rbac.py                        # RBAC service (RBACServiceABC, JsonRBACService)
│   ├── security.py                    # JWT & password utilities
│   └── config.py                      # Settings (SECRET_KEY, JWT expiry)
├── models/
│   ├── domain/
│   │   └── user.py                    # User ORM model
│   └── schemas/
│       └── user.py                    # Pydantic schemas
└── services/
    ├── auth.py                        # AuthService (login logic)
    └── user.py                        # UserService (CRUD operations)

config/
└── rbac.json                          # RBAC permission configuration
```

### Tests

```
backend/tests/
├── core/
│   └── test_rbac.py                   # Unit tests for RBAC service (18 tests)
└── api/
    └── test_role_checker.py           # Integration tests for RoleChecker (7 tests)
```

---

## Testing Strategy

**Coverage:** 95.56% of `app/core/rbac.py`

**Total Tests:** 18 RBAC tests passing

---

## Related Documentation

- [ADR-007: RBAC Service Design](../../decisions/ADR-007-rbac-service.md)
- [User Management Context](../user-management/architecture.md)
- [Cross-Cutting: Security](../../cross-cutting/security.md)
- [System Map](../../00-system-map.md)

---

## Changelog

| Date       | Change                                              | Author       |
| ---------- | --------------------------------------------------- | ------------ |
| 2026-01-04 | Added RBAC implementation, fine-grained permissions | Backend Team |
| 2025-12-29 | Initial authentication documentation                | Backend Team |
