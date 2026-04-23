# Configuration Guide

**Last Updated:** 2026-04-23
**Status:** Active

This document describes all configuration options for the Backcast system. For environment-specific templates, see:
- **Backend:** `backend/.env.example`
- **Frontend:** `frontend/.env.example`
- **Docker Development:** `.env.dev.example`
- **Docker Production:** `deploy/.env.production.example`

---

## Quick Setup

### Local Development (Docker Compose)

```bash
# Copy the development template
cp .env.dev.example .env.dev

# Start services
docker-compose --env-file .env.dev up -d

# Run database migrations
docker-compose --env-file .env.dev exec backend uv run alembic upgrade head
```

### Production Deployment

```bash
# Copy and edit the production template
cp deploy/.env.production.example deploy/.env.production
nano deploy/.env.production  # Edit with production values

# Deploy
cd deploy && docker-compose --env-file .env.production up -d
```

---

## Environment Variables Reference

### Backend Configuration

#### Database Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_SERVER` | No | `localhost` | PostgreSQL server hostname |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL server port |
| `POSTGRES_USER` | Yes | - | Database username |
| `POSTGRES_PASSWORD` | Yes | - | Database password |
| `POSTGRES_DB` | No | `backcast_evs` | Database name |
| `DATABASE_URL` | Yes | - | Full SQLAlchemy connection string (constructed from above) |

**Format:** `postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_SERVER}:${POSTGRES_PORT}/${POSTGRES_DB}`

#### Security Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | - | JWT signing secret (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`) |
| `ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `30` | Refresh token lifetime |

#### Application Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PROJECT_NAME` | No | `"Backcast"` | Application name |
| `API_V1_STR` | No | `/api/v1` | API version prefix |
| `DEBUG` | No | `false` | Enable debug mode (development only) |
| `PORT` | No | `8020` | Backend server port |

#### CORS Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BACKEND_CORS_ORIGINS` | No | `[]` | Allowed origins (JSON array) |
| `BACKEND_CORS_METHODS` | No | `["*"]` | Allowed HTTP methods |
| `BACKEND_CORS_HEADERS` | No | `["*"]` | Allowed headers |

**Examples:**
- Development: `["http://localhost:5173", "http://localhost:3000"]`
- Production: `["https://app.yourdomain.com"]`

#### RBAC Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RBAC_POLICY_FILE` | No | `config/rbac.json` | Path to RBAC policy (json provider) |
| `RBAC_PROVIDER` | No | `json` | RBAC backend: `json`, `database`, or `entra` |
| `AUTH_PROVIDER` | No | `local` | Authentication provider: `local` or `oidc` |
| `USER_PROVIDER` | No | `local` | User provider: `local`, `entra`, or `hybrid` |

**RBAC Providers:**
- **json**: Static roles from `config/rbac.json` (simple, requires restart to update)
- **database**: Dynamic roles from database (recommended, admin UI can update)
- **entra**: Microsoft Entra ID integration (future)

#### Observability

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OTEL_ENABLED` | No | `false` | Enable OpenTelemetry tracing |
| `OTLP_ENDPOINT` | No | `http://localhost:6006/v1/traces` | OTLP trace export endpoint |

#### Logging

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | No | `logs/app.log` | Log file path |
| `LOG_MAX_BYTES` | No | `51200` | Max log file size before rotation (bytes) |
| `LOG_BACKUP_COUNT` | No | `10` | Number of backup log files to keep |

#### Telegram Notifications (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_ENABLED` | No | `false` | Enable Telegram notifications |
| `TELEGRAM_BOT_TOKEN` | No | - | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | No | - | Chat ID for notifications (get from @userinfobot) |

---

### Frontend Configuration

All frontend variables must be prefixed with `VITE_` to be accessible in the browser.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | Yes | - | Backend API URL |
| `VITE_WEBSOCKET_URL` | No | `VITE_API_URL` with `ws://` | WebSocket endpoint for AI chat |
| `VITE_GIT_SHA` | No | - | Git commit SHA (auto-injected at build) |
| `VITE_BUILD_DATE` | No | - | Build timestamp (auto-injected at build) |

**Examples:**
- Development: `VITE_API_URL=http://localhost:8020`
- Production: `VITE_API_URL=https://api.yourdomain.com`

---

## Docker Compose Configuration

### Development Setup

The `.env.dev.example` file provides a complete template for local development with Docker Compose.

**Key Services:**
- **postgres**: PostgreSQL 15 database
- **backend**: FastAPI application
- **frontend**: Vite dev server with hot reload

### Production Setup

The `deploy/.env.production.example` file provides a template for production deployment with Traefik reverse proxy and Let's Encrypt SSL.

**Key Services:**
- **traefik**: Reverse proxy with automatic SSL
- **postgres**: PostgreSQL database
- **backend**: Production FastAPI container
- **frontend**: Built React static files

---

## Security Best Practices

### Production Checklist

- [ ] Change `SECRET_KEY` to a cryptographically secure random value
- [ ] Set `DEBUG=false`
- [ ] Set `LOG_LEVEL=INFO` or `WARNING`
- [ ] Configure `BACKEND_CORS_ORIGINS` with explicit domains only
- [ ] Use strong database passwords
- [ ] Enable `RBAC_PROVIDER=database` for dynamic permission management
- [ ] Configure `OTEL_ENABLED=true` for production monitoring
- [ ] Set up `TELEGRAM_ENABLED` for critical error notifications

### Generating Secure Secrets

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate database password
openssl rand -base64 32
```

---

## Related Documentation

- [Development Docker Compose](./development/docker-compose.md) - Local development setup
- [Docker Deployment Guide](../../05-user-guide/docker-deployment-guide.md) - Production deployment
- [RBAC System](./decisions/ADR-007-rbac-service.md) - Role-based access control
- [Telegram Notifications](./cross-cutting/telegram-notifications.md) - Alert configuration
