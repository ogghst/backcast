# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Backcast EVS** (Entity Versioning System) is a Project Budget Management & Earned Value Management System for end-of-line automation projects. The system provides Git-style versioning with bitemporal entity tracking, branch isolation for change orders, and complete audit trails.

**Tech Stack:** Python 3.12+ / FastAPI (backend) + React 18 / TypeScript / Vite (frontend) + PostgreSQL 15+

**Architecture Docs:** See @docs/02-architecture for detailed architecture and @docs/02-architecture/backend/coding-standards.md and @docs/02-architecture/frontend/coding-standards.md for coding standards.

## Common Commands

### Backend (Python/FastAPI)

```bash
# Setup (from project root)
uv sync && docker-compose up -d postgres        # Install deps and start PostgreSQL

# Database migrations
cd backend && uv run alembic upgrade head       # Run migrations
uv run alembic revision --autogenerate -m "msg" # Create migration

# Development
uv run uvicorn app.main:app --reload            # Start dev server (port 8000)

# Testing
uv run pytest -k "test_name"                    # Run specific test
uv run pytest --cov=app                         # With coverage

# Code Quality (REQUIRED before commits)
uv run ruff check . && uv run mypy app/         # Must pass (zero errors)
```

### Frontend (React/TypeScript)

```bash
cd frontend

npm run dev                    # Start dev server (port 5173)
npm test                       # Run unit tests (Vitest)
npm run test:coverage          # With coverage
npm run build                  # Production build
npm run generate-client        # Generate types from OpenAPI spec

# Code Quality (REQUIRED before commits)
npm run lint                   # ESLint - must pass
```

### Full Quality Check

```bash
# Backend: cd backend && uv run ruff check . && uv run mypy app/ && uv run pytest
# Frontend: cd frontend && npm run lint && npm run test:coverage
```

## Architecture Overview

**Backend:** Layered architecture (API → Services → Repositories → Models). See @docs/02-architecture/00-system-map.md

**Frontend:** Feature-based organization with TanStack Query for server state, Zustand for client state. See @docs/02-architecture/frontend/contexts/01-core-architecture.md

**EVCS (Entity Versioning Control System):** Bitemporal versioning with PostgreSQL TSTZRANGE. All versioned entities support branch isolation for change orders. See @backend/app/core/versioning/

## Database Strategy

- **Connection:** AsyncPG with optimized pooling
- **Migrations:** Alembic (create with `--autogenerate`)
- **Indexes:** GIST indexes for range queries, partial indexes for current versions
- **Constraints:** Exclusion constraints for temporal ranges

## API Conventions

- **Base URL:** `/api/v1`
- **Authentication:** JWT Bearer tokens (`Authorization: Bearer <token>`)
- **Response Format:** JSON with standardized error handling
- **OpenAPI Docs:** Available at `/docs` (Swagger UI) and `/openapi.json`

## Quality Standards (REQUIRED for all commits)

- **Backend:** MyPy strict mode (zero errors), Ruff (zero errors), 80%+ test coverage
- **Frontend:** TypeScript strict mode, ESLint clean, 80%+ test coverage
- **Testing:** `pytest-asyncio` strict mode for async tests

**Ruff Configuration:** Line length 88, ignores `B008` (for FastAPI `Depends()`)

## Important Non-Obvious Patterns

**EVCS Entity Types:**
- **Versioned entities:** Use `TemporalBase`, `TemporalService[T]` (supports bitemporal tracking, branches, soft delete)
- **Non-versioned entities:** Use `SimpleBase`, `SimpleService` (standard CRUD, standard delete)
- **Key files:** `backend/app/core/versioning/temporal.py`, `backend/app/core/versioning/simple.py`

**Bounded Contexts:** Auth, User Mgmt, Dept Mgmt, Project/WBE, Cost Elements, Change Orders, EVM. See @docs/02-architecture/01-bounded-contexts.md

<<<<<<< HEAD
## Documentation

- [Documentation Guide](docs/00-meta/README.md)
- [System Architecture and Coding Standards](docs/02-architecture/README.md)
=======
**Documentation:**
- Architecture: @docs/02-architecture
- Product Scope: @docs/01-product-scope
>>>>>>> a11c273 (docs: Update CLAUDE.md and coding standards)
