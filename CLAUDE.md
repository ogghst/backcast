## Project Overview

**Backcast** is a Project Budget Management & Earned Value Management System for end-of-line automation projects. The system provides Git-style versioning with bitemporal entity tracking, branch isolation for change orders, and complete audit trails.

**Tech Stack:** Python 3.12+ / FastAPI (backend) + React 18 / TypeScript / Vite (frontend) + PostgreSQL 15+

## Common Commands

### Backend (Python/FastAPI)

```bash

# Virtual environment setup (prior to **every** backend command)
cd backend && source .venv/bin/activate

# Setup (from project root)
uv sync && docker-compose up -d postgres        # Install deps and start PostgreSQL

# Database migrations
cd backend && uv run alembic upgrade head       # Run migrations
uv run alembic revision --autogenerate -m "msg" # Create migration

# Development
uv run uvicorn app.main:app --reload --port 8020 # Start dev server (port 8020)

# Logs (troubleshooting)
tail -f backend/logs/app.log                         # Live app logs

# Testing
uv run pytest -k "test_name"                    # Run specific test
uv run pytest --cov=app                         # With coverage

# Code Quality (REQUIRED before commits)
uv run ruff format . && uv run ruff check . && uv run mypy app/  # Format, lint, and type check (must pass)
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

**Backend:** Layered architecture (API → Services → Models). No repository pattern — services access the database directly via `AsyncSession`.

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

The codebase and test suite are large. To improve efficiency, perform quality checks (linting, type checking) and execute tests **ONLY on the modified codebase** and its relevant scope. Do not run full project-wide checks or the entire test suite unless explicitly requested or necessary for integration verification.

- **Backend:** MyPy strict mode (zero errors), Ruff (zero errors), 80%+ test coverage
- **Frontend:** TypeScript strict mode, ESLint clean, 80%+ test coverage
- **Testing:** `pytest-asyncio` strict mode for async tests

**Ruff Configuration:** Line length 88, ignores `B008` (for FastAPI `Depends()`)

## Important Non-Obvious Patterns

**EVCS Entity Tiers:**

- **Simple:** `SimpleEntityBase` → `SimpleService` (`app/core/base/base.py`, `app/core/simple/service.py`)
- **Versionable:** `EntityBase + VersionableMixin` → `TemporalService` (`app/core/versioning/service.py`)
- **Branchable:** `EntityBase + VersionableMixin + BranchableMixin` → `BranchableService` (`app/core/branching/service.py`)
- **Entity guide:** `docs/02-architecture/backend/contexts/evcs-core/entity-classification.md`

## Documentation

[`docs/00-meta/README.md`](docs/00-meta/README.md)

## External Resources

- **Context7 MCP**: Up-to-date library documentation and code examples
  - Call `mcp__plugin_context7_context7__resolve-library-id` with library name to get ID
  - Call `mcp__plugin_context7_context7__query-docs` with library ID and query
- **webReader**: Fetch current documentation from websites
  - Call `mcp__web_reader__webReader` with URL to fetch web content as markdown

# Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed

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

## 5. Understand the Real Requirement

**Interview me until you have 95% confidence about what I actually want, not what I think I should want.**

When receiving a request:

- Don't assume the stated solution is the right one
- Ask clarifying questions to understand the underlying problem
- Surface tradeoffs between different approaches
- If something seems off, say so - don't blindly implement
- The goal is to solve the actual problem, not just follow instructions

## 6. Agent Delegation for Codebase Changes

**ALWAYS use specialized agents for code modifications.**

When making changes to the codebase:

- **Frontend changes** (React, TypeScript, UI components): Use the `frontend-developer` agent
- **Backend changes** (Python, FastAPI, services, models): Use the `backend-developer` agent

You may directly edit files for:

- Configuration files (CLAUDE.md, package.json, tsconfig.json, etc.)
- Documentation files
- Simple typo fixes
- Emergency hotfixes when agents are unavailable
