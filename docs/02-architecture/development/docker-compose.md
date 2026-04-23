# Docker Compose Development Setup

This document describes the standardized Docker Compose setup for local development of the Backcast project.

## Overview

The development setup provides:

- **Hot-reload backend** - FastAPI auto-restarts on code changes
- **Hot-reload frontend** - Vite dev server with HMR
- **PostgreSQL 15** - Persistent database with Adminer GUI
- **Isolated dependencies** - No local Python/Node installation required

## Quick Start

### 1. Create environment file

```bash
cp .env.dev.example .env.dev
```

### 2. Start all services

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev up
```

### 3. Run database migrations

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev --profile migrations up alembic
```

### 4. Access the application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8020
- **API Docs**: http://localhost:8020/docs
- **Adminer (DB GUI)**: http://localhost:7090

## Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| postgres | `backcast_dev_postgres` | 5432 | PostgreSQL 15 database |
| backend | `backcast_dev_backend` | 8020 | FastAPI with hot-reload |
| frontend | `backcast_dev_frontend` | 5173 | Vite dev server with HMR |
| adminer | `backcast_dev_adminer` | 7090 | Database GUI |
| alembic | `backcast_dev_alembic` | - | Migration runner (profile) |

## Common Commands

### Start only database (for local development)

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev up postgres adminer
```

### Rebuild containers (after dependency changes)

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev build
docker compose -f docker-compose.dev.yml --env-file .env.dev up
```

### Run backend tests

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev run backend uv run pytest
```

### Run frontend tests

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev run frontend npm test
```

### View logs

```bash
# All services
docker compose -f docker-compose.dev.yml logs -f

# Specific service
docker compose -f docker-compose.dev.yml logs -f backend
```

### Stop and clean

```bash
# Stop containers
docker compose -f docker-compose.dev.yml --env-file .env.dev down

# Remove volumes (deletes database data!)
docker compose -f docker-compose.dev.yml --env-file .env.dev down -v
```

## Development Workflow

### Backend Development

Edit files in `backend/` - changes trigger automatic reload via uvicorn `--reload`.

To run alembic migrations:

```bash
# Create migration
docker compose -f docker-compose.dev.yml --env-file .env.dev run alembic alembic revision --autogenerate -m "description"

# Apply migrations
docker compose -f docker-compose.dev.yml --env-file .env.dev --profile migrations up alembic
```

### Frontend Development

Edit files in `frontend/` - Vite HMR applies changes instantly in the browser.

The `node_modules` directory is persisted in a Docker volume to avoid reinstalling dependencies on every restart.

### Database Access

1. **Adminer GUI**: http://localhost:7090
   - Server: `postgres`
   - Username: `postgres` (or `$POSTGRES_USER`)
   - Password: `postgres` (or `$POSTGRES_PASSWORD`)
   - Database: `backcast_evs`

2. **psql from host** (requires local postgresql-client):
   ```bash
   psql -h localhost -U postgres -d backcast_evs
   ```

3. **psql from container**:
   ```bash
   docker compose -f docker-compose.dev.yml --env-file .env.dev exec postgres psql -U postgres -d backcast_evs
   ```

## Volumes

| Volume | Purpose |
|--------|---------|
| `postgres_dev_data` | Database persistence |
| `backend_venv` | Python virtual environment cache |
| `frontend_node_modules` | npm dependencies cache |

## Troubleshooting

### Port conflicts

If ports are already in use, modify them in `.env.dev`:
- `POSTGRES_PORT=5432` → `POSTGRES_PORT=5433`
- Frontend/backend ports need to be changed in `docker-compose.dev.yml`

### Backend can't connect to database

Wait for postgres health check:
```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev logs postgres
```

### Frontend API connection errors

Ensure `VITE_API_URL` in `.env.dev` matches the backend port (default: `http://localhost:8020`).

### Clean rebuild

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev down -v
docker compose -f docker-compose.dev.yml --env-file .env.dev build --no-cache
docker compose -f docker-compose.dev.yml --env-file .env.dev up
```

## Production vs Development

- **Development**: `docker-compose.dev.yml` (hot-reload, verbose logs, exposed ports)
- **Production**: `deploy/docker-compose.yml` (Traefik, optimized builds, security-hardened)

Never use the development setup in production environments.
