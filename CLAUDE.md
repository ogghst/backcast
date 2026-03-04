## Project Overview

**Backcast EVS** (Entity Versioning System) is a Project Budget Management & Earned Value Management System for end-of-line automation projects. The system provides Git-style versioning with bitemporal entity tracking, branch isolation for change orders, and complete audit trails.

**Tech Stack:** Python 3.12+ / FastAPI (backend) + React 18 / TypeScript / Vite (frontend) + PostgreSQL 15+

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

**Backend:** Layered architecture (API → Services → Repositories → Models).

**Frontend:** Feature-based organization with TanStack Query for server state, Zustand for client state.

**EVCS (Entity Versioning Control System):** Bitemporal versioning with PostgreSQL TSTZRANGE. All versioned entities support branch isolation for change orders.

## Database Strategy

- **Connection:** AsyncPG with optimized pooling
- **Migrations:** Alembic (create with `--autogenerate`)
- **Indexes:** GIST indexes for range queries, partial indexes for current versions
- **Constraints:** Exclusion constraints for temporal ranges
- **Querying:** use postgres mcp tool to investigate database schema and data

## API Conventions

- **Base URL:** `/api/v1`
- **Authentication:** JWT Bearer tokens (`Authorization: Bearer <token>`)
- **Response Format:** JSON with standardized error handling
- **OpenAPI Docs:** Available at `/docs` (Swagger UI) and `/openapi.json`

## Quality Standards (REQUIRED for all commits)

codebase and test suite is large. To improve efficiency, when validating the performed work execute only tests relevant to the scope

- **Backend:** MyPy strict mode (zero errors), Ruff (zero errors), 80%+ test coverage
- **Frontend:** TypeScript strict mode, ESLint clean, 80%+ test coverage
- **Testing:** `pytest-asyncio` strict mode for async tests

**Ruff Configuration:** Line length 88, ignores `B008` (for FastAPI `Depends()`)

## Important Non-Obvious Patterns

**EVCS Entity Types:**
- **Versioned entities:** Use `TemporalBase`, `TemporalService[T]` (supports bitemporal tracking, branches, soft delete)
- **Non-versioned entities:** Use `SimpleBase`, `SimpleService` (standard CRUD, standard delete)
- **Key files:** `backend/app/core/versioning/temporal.py`, `backend/app/core/versioning/simple.py`

## Documentation

| Need | Start Here |
|------|------------|
| Project overview & onboarding | [`docs/00-meta/README.md`](docs/00-meta/README.md) |
| Architecture & coding standards | [`docs/02-architecture/README.md`](docs/02-architecture/README.md) |
| Domain terminology | [`docs/01-product-scope/glossary.md`](docs/01-product-scope/glossary.md) |
| Current sprint status | [`docs/03-project-plan/sprint-backlog.md`](docs/03-project-plan/sprint-backlog.md) |

# Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
