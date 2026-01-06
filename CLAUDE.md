# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Backcast EVS** (Entity Versioning System) is a Project Budget Management & Earned Value Management System for end-of-line automation projects. The system provides Git-style versioning with bitemporal entity tracking, branch isolation for change orders, and complete audit trails.

**Tech Stack:** Python 3.12+ / FastAPI (backend) + React 18 / TypeScript / Vite (frontend) + PostgreSQL 15+

## Common Commands

### Backend (Python/FastAPI)

```bash
# Setup (from project root)
uv sync                              # Install dependencies
docker-compose up -d postgres        # Start PostgreSQL

# Database
cd backend
uv run alembic upgrade head          # Run migrations
uv run alembic revision --autogenerate -m "description"  # Create migration

# Development
uv run uvicorn app.main:app --reload # Start dev server (port 8000)

# Testing
uv run pytest                        # Run all tests
uv run pytest tests/unit/            # Unit tests only
uv run pytest tests/api/             # API integration tests only
uv run pytest --cov=app              # With coverage report
uv run pytest -k "test_name"         # Run specific test

# Code Quality
uv run ruff check .                  # Linting (zero errors required)
uv run mypy app/                     # Type checking (strict mode, zero errors)
```

### Frontend (React/TypeScript)

```bash
cd frontend

# Setup
npm install                          # Install dependencies

# Development
npm run dev                          # Start dev server (port 5173)

# Testing
npm test                             # Run unit tests (Vitest)
npm run test:coverage                # With coverage
npm run e2e                          # E2E tests (Playwright)

# Code Quality
npm run lint                         # ESLint
npm run format                       # Prettier

# Build
npm run build                        # Production build

# API Client Generation
npm run generate-client              # Generate types from OpenAPI spec
```

### Full Quality Check

```bash
# Backend (all checks)
cd backend && uv run ruff check . && uv run mypy app/ && uv run pytest

# Frontend (all checks)
cd frontend && npm run lint && npm run test:coverage
```

## Architecture Overview

### Backend Layered Architecture

```
API Routes (app/api/) → Services (app/services/) → Repositories (app/repositories/) → Models (app/models/) → Database
```

- **API Layer**: FastAPI routes, input validation via Pydantic, dependency injection
- **Service Layer**: Business logic, orchestration, transaction management
- **Repository Layer**: Data access, SQLAlchemy queries
- **Model Layer**: Database schema definitions

### Frontend Architecture

- **Feature-Based**: Organized by domain in `src/features/` (e.g., `features/users/`)
- **State Management**:
  - Server State: TanStack Query (React Query) - API caching
  - Client State: Zustand - auth, modals, UI state
  - Local State: useState/useReducer - component-local logic
- **API Client**: Centralized Axios instance (`src/api/client.ts`)
- **Routing**: React Router v6 with centralized route definitions

## EVCS (Entity Versioning Control System)

The core feature is a **bitemporal versioning system** implemented with PostgreSQL `TSTZRANGE`:

- **Bitemporal Tracking**: Valid time (business time) + Transaction time (system time)
- **Branch Isolation**: All versioned entities support branch isolation for change orders
- **Soft Delete**: Reversible deletion with `deleted_at` timestamp
- **Version Chain**: DAG structure via `parent_id` for history traversal
- **Generic Framework**: `TemporalBase`, `TemporalService[T]`, generic commands (Create/Update/Delete)

**Key Files:**

- `backend/app/core/versioning/` - Core versioning logic
- `backend/app/core/versioning/temporal.py` - `TemporalBase`, `TemporalService[T]`
- `backend/app/core/versioning/commands.py` - Generic commands for versioned entities
- `backend/app/core/versioning/simple.py` - `SimpleBase`, `SimpleService` for non-versioned entities

**Non-Versioned Entities**: Use `SimpleBase` for config/preferences (standard CRUD with standard delete).

## Database Strategy

- **Connection**: AsyncPG with optimized pooling
- **Migrations**: Alembic (create with `--autogenerate`)
- **Indexes**: GIST indexes for range queries, partial indexes for current versions
- **Constraints**: Exclusion constraints for temporal ranges

## API Conventions

- **Base URL**: `/api/v1`
- **Authentication**: JWT Bearer tokens (set via `Authorization: Bearer <token>`)
- **Response Format**: JSON with standardized error handling
- **OpenAPI Docs**: Auto-generated at `/docs` (Swagger UI) and `/openapi.json`

## Quality Standards

**Required for all commits:**

- **Backend**: MyPy strict mode (zero errors), Ruff (zero errors), 80%+ test coverage
- **Frontend**: TypeScript strict mode, ESLint clean, 80%+ test coverage
- **Testing**: `pytest-asyncio` strict mode for async tests

**Ruff Configuration**: Line length 88, ignores `B008` (for FastAPI `Depends()`)

## Key Project Files

- `backend/app/core/config.py` - Settings management (Pydantic Settings)
- `backend/app/db/session.py` - Database session management
- `backend/tests/conftest.py` - Shared test fixtures (db_session, client)
- `frontend/src/api/client.ts` - Axios configuration with interceptors
- `frontend/src/config/` - Frontend configuration

## Bounded Contexts

The system is partitioned into:

1. Authentication & Authorization
2. User Management
3. Department Management
4. Project & WBE Management
5. Cost Element & Financial Tracking
6. Change Order & Branching
7. EVM Calculations & Reporting

See `docs/02-architecture/01-bounded-contexts.md` for details.

## Documentation

- [Documentation Guide](docs/00-meta/README.md)
- [System Architecture](docs/02-architecture/00-system-map.md)
- [Coding Standards](docs/00-meta/coding_standards.md)
- [ADR Index](docs/02-architecture/decisions/adr-index.md) - Architecture Decision Records
- [Current Iteration](docs/03-project-plan/current-iteration.md)
