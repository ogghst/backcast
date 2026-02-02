# Environment Configuration

**Last Updated:** 2026-02-02
**Status:** Live

## Overview

The Backcast EVS application uses environment-specific configuration to separate development, test, and production environments. Each environment has its own database and configuration settings.

## Environment Files

We use three separate environment files:

- **`.env.development`** - Local development environment
- **`.env.test`** - Testing environment (pytest, integration tests)
- **`.env.production`** - Production deployment

> **⚠️ IMPORTANT**: Never commit `.env.production` to version control! It contains sensitive production credentials.

## Database Separation

Each environment uses a **different database name** to prevent data conflicts:

| Environment | Database Name | Database User | Purpose |
|-------------|---------------|---------------|---------|
| Development | `backcast_evs_dev` | `backcast_dev` | Local development and testing |
| Test | `backcast_evs_test` | `backcast_test` | Automated test suite |
| Production | `backcast_evs_prod` | `backcast_prod` | Production data |

## Configuration Loading

The application automatically searches for environment files in multiple locations:

1. **Project root** (preferred): `/home/nicola/dev/backcast_evs/.env.{environment}`
2. **Backend directory**: `/home/nicola/dev/backcast_evs/backend/.env.{environment}`
3. **Fallback**: `.env` for backwards compatibility

The search is performed in `backend/app/core/config.py`:

```python
# Search for env file in multiple locations (in order)
env_paths = [
    Path(__file__).parent.parent.parent.parent / env_file,  # Project root
    Path(env_file),                                            # Current directory
    Path(".env")                                               # Fallback
]

loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        loaded = True
        break
```

This allows environment files to be placed in the project root for Docker Compose convenience while still supporting standalone backend usage.

## Usage

### Development (Default)

```bash
# Uses .env.development by default
docker-compose up -d postgres
cd backend && uv run uvicorn app.main:app --reload
```

### Testing

```bash
# Set test environment
export ENVIRONMENT=test
cd backend && uv run pytest
```

### Production

```bash
# Set production environment
export ENVIRONMENT=production
docker-compose --env-file .env.production up -d
```

## Environment Variables

### Required Variables

All environments must have these variables set:

```bash
# Application
ENVIRONMENT=development|test|production
DEBUG=true|false
SECRET_KEY=your-secret-key
PORT=8020

# Database - IMPORTANT: Different database names for each environment!
POSTGRES_HOST=localhost      # Use 'postgres' when running in Docker
POSTGRES_PORT=5432
POSTGRES_USER=backcast_user  # Consider different users per environment
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=backcast_evs_dev # Change to _test or _prod

# Database URL (constructed from above)
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# CORS
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Logging
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
```

### Docker Compose Integration

Docker Compose loads environment variables from shell environment before running:

```bash
# Development
set -a && source .env.development && set +a
docker compose up -d

# Test
set -a && source .env.test && set +a
docker compose up -d

# Production
set -a && source .env.production && set +a
docker compose up -d
```

Each environment gets:
- Unique container names (e.g., `backcast_evs_postgres_development`)
- Separate Docker volumes (e.g., `postgres_data_development`)
- Isolated data

**Note**: `set -a` enables automatic export of variables, and `set +a` disables it after sourcing.

## Initial Setup

### 1. Create Environment Files

```bash
# Copy the template
cp .env.example .env.development
cp .env.example .env.test
cp .env.example .env.production

# Edit each file with appropriate values
# IMPORTANT: Use different database names!
```

### 2. Start Development Environment

```bash
# Source environment variables
set -a && source .env.development && set +a

# Start PostgreSQL for development
docker compose up -d postgres

# Run migrations
cd backend && uv run alembic upgrade head

# Start development server
uv run uvicorn app.main:app --reload
```

### 3. Create Test Database

```bash
# Connect to PostgreSQL (using an existing superuser, e.g., backcast_prod or postgres)
docker exec <container_name> psql -U <superuser> -d backcast_evs -c "CREATE DATABASE backcast_evs_test;"
docker exec <container_name> psql -U <superuser> -d backcast_evs -c "CREATE USER backcast_test WITH PASSWORD 'test_password_change_me';"
docker exec <container_name> psql -U <superuser> -d backcast_evs -c "GRANT ALL PRIVILEGES ON DATABASE backcast_evs_test TO backcast_test;"

# Grant schema privileges
docker exec <container_name> psql -U <superuser> -d backcast_evs_test -c "GRANT ALL ON SCHEMA public TO backcast_test; GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO backcast_test; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO backcast_test; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO backcast_test; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO backcast_test;"
```

**Note**: Replace `<container_name>` with your actual PostgreSQL container name and `<superuser>` with a user that has CREATE DATABASE privileges (e.g., `postgres` or `backcast_prod`).

### 4. Verify Configuration

```bash
# Test configuration loading
cd backend
ENVIRONMENT=development uv run python -c "from app.core.config import settings; print(f'Environment: {settings.ENVIRONMENT}'); print(f'Database: {settings.DATABASE_URL}')"

# Expected output:
# Environment: development
# Database: postgresql+asyncpg://backcast_dev:dev_password_change_me@localhost:5432/backcast_evs_dev
```

## Switching Environments

### Quick Switch

```bash
# Switch to test environment
export ENVIRONMENT=test
cd backend && uv run pytest

# Switch back to development
export ENVIRONMENT=development
uv run uvicorn app.main:app --reload
```

### Docker Compose Switch

```bash
# Stop development containers
docker compose down

# Start production containers
set -a && source .env.production && set +a
docker compose up -d
```

## Security Best Practices

1. **Never commit `.env.production`** - It's in `.gitignore`
2. **Use strong passwords** - Different passwords for each environment
3. **Rotate secrets** - Change `SECRET_KEY` periodically
4. **Restrict CORS** - Production should only allow actual frontend domains
5. **Disable DEBUG** - Always set `DEBUG=false` in production

## Troubleshooting

### "Connection refused" Error

**Problem**: Tests fail with database connection error.

**Solution**:
```bash
# Check which environment is active
echo $ENVIRONMENT

# Ensure .env.{environment} file exists
ls -la .env.development .env.test .env.production

# Verify database is running
docker ps | grep postgres

# For Docker Compose: ensure you sourced the env file first
set -a && source .env.development && set +a
docker compose ps
```

### "Database already exists" Error

**Problem**: Trying to create a database that already exists.

**Solution**:
```bash
# Check existing databases
docker exec backcast_evs_postgres_development psql -U backcast_dev -l

# Drop and recreate if needed
docker exec backcast_evs_postgres_development psql -U backcast_dev -c "DROP DATABASE backcast_evs_test;"
```

### Wrong Database Loaded

**Problem**: Application loads production data in development.

**Solution**:
```bash
# Check current environment
python -c "from app.core.config import settings; print(settings.ENVIRONMENT, settings.DATABASE_URL)"

# Ensure ENVIRONMENT variable is set correctly
export ENVIRONMENT=development
```

## See Also

- [Database Strategy](database-strategy.md)
- [Security Practices](security-practices.md)
- [Coding Standards](../backend/coding-standards.md)
