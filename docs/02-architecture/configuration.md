# Configuration Guide

**Last Updated:** 2026-03-02
**Status:** Active

This document describes the configuration options for Backcast .

---

## Environment Variables

### Backend Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Yes | - | Secret key for JWT token signing |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Token expiration time |
| `CORS_ORIGINS` | No | `*` | Allowed CORS origins (comma-separated) |
| `ENVIRONMENT` | No | `development` | `development`, `staging`, `production` |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_HOST` | No | `localhost` | Database host |
| `DB_PORT` | No | `5432` | Database port |
| `DB_NAME` | No | `backcast_evs` | Database name |
| `DB_USER` | No | `postgres` | Database user |
| `DB_PASSWORD` | No | - | Database password |
| `DB_POOL_SIZE` | No | `5` | Connection pool size |
| `DB_MAX_OVERFLOW` | No | `10` | Max connections beyond pool |

### Frontend Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_BASE_URL` | Yes | - | Backend API URL |
| `VITE_APP_TITLE` | No | `Backcast ` | Application title |

---

## Docker Compose Configuration

### Development Setup

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: backcast_evs
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/backcast_evs
      JWT_SECRET_KEY: dev-secret-key-change-in-production
      CORS_ORIGINS: http://localhost:5173
    ports:
      - "8000:8000"
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    environment:
      VITE_API_BASE_URL: http://localhost:8000/api/v1
    ports:
      - "5173:5173"
    depends_on:
      - backend

volumes:
  postgres_data:
```

---

## Application Settings

### Backend Settings (app/core/config.py)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    cors_origins: list[str] = ["*"]

    # Environment
    environment: str = "development"
    debug: bool = False

    class Config:
        env_file = ".env"
```

### Feature Flags

Currently no feature flags are implemented. Future flags may include:

| Flag | Description | Status |
|------|-------------|--------|
| `ENABLE_FORECASTS` | Enable forecast feature | Planned |
| `ENABLE_QUALITY_EVENTS` | Enable quality event tracking | Planned |
| `ENABLE_TIME_MACHINE_UI` | Enable time travel UI | Planned |

---

## Database Configuration

### Connection Pooling

The system uses SQLAlchemy's async connection pooling:

```python
engine = create_async_engine(
    database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

### Session Management

Sessions are managed via async context managers:

```python
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
```

---

## Logging Configuration

### Backend Logging

```python
# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default"
        }
    },
    "loggers": {
        "app": {
            "level": "INFO",
            "handlers": ["console"]
        },
        "sqlalchemy.engine": {
            "level": "WARNING"
        }
    }
}
```

### Frontend Logging

```typescript
// Configure based on environment
const logLevel = import.meta.env.PROD ? 'error' : 'debug';
```

---

## Security Configuration

### JWT Settings

```python
# Token configuration
JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]  # REQUIRED
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

### CORS Settings

```python
# Development
CORS_ORIGINS = ["http://localhost:5173"]

# Production
CORS_ORIGINS = ["https://backcast.example.com"]
```

### Password Hashing

Uses bcrypt for password hashing:

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

---

## Alembic Configuration

### alembic.ini

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]
```

### env.py

```python
# Async migration support
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata
```

---

## Related Documentation

- [Database Strategy](./cross-cutting/database-strategy.md) - Database architecture
- [API Conventions](./cross-cutting/api-conventions.md) - API patterns
- [Migration Troubleshooting](./migration-troubleshooting.md) - Migration issues
