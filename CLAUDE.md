# Backcast

Project Budget & Earned Value Management for end-of-line automation projects: Git-style versioning with bitemporal entity tracking, branch isolation for change orders, and full audit trails.

**Stack:** Python 3.12 / FastAPI + SQLAlchemy 2 / AsyncPG / Alembic (backend); React 18 / TypeScript / Vite / TanStack Query / Zustand (frontend); PostgreSQL 15.

## Commands

Backend (from `backend/`, using `uv` — `uv run` manages the venv, no manual activation):

```bash
uv sync                                          # install deps
docker-compose up -d postgres                    # start Postgres (compose service "postgres")
uv run alembic upgrade head                      # apply migrations
uv run alembic revision --autogenerate -m "msg"  # create migration
uv run uvicorn app.main:app --reload --port 8020 # dev server (port 8020 is non-default)
uv run pytest -k "name"                          # run a specific test
```

Frontend (from `frontend/`):

```bash
npm run dev             # dev server (Vite default port 5173)
npm run generate-client # regen API types: cd's into backend, runs generate-openapi, then openapi codegen
```

Quality gates are enforced in config, not run separately: `backend/pyproject.toml` sets mypy strict + pytest `--cov-fail-under=80`; ruff (line 88, ignores `E501`/`B008`/`UP042`). Frontend: `npm run lint` (ESLint) + `npm run typecheck`. Run gates only on the scope you changed.

## Architecture

- **Backend:** layered API → Services → Models; **no repository pattern** — services use `AsyncSession` directly.
- **Frontend:** feature-based directories.

## EVCS — Entity Versioning Control System

Bitemporal versioning on PostgreSQL `TSTZRANGE`: GIST indexes for range queries, partial indexes for current versions, exclusion constraints for temporal ranges. Branch isolation supports change orders.

**Entity tiers** (guide: `docs/02-architecture/backend/contexts/evcs-core/entity-classification.md`):

- **Simple:** `SimpleEntityBase` → `SimpleService` — `app/core/base/base.py`, `app/core/simple/service.py`
- **Versionable:** `EntityBase` + `VersionableMixin` → `TemporalService` — `app/core/versioning/service.py`
- **Branchable:** `EntityBase` + `VersionableMixin` + `BranchableMixin` → `BranchableService` — `app/core/branching/service.py`

**Relationships use root IDs, not version IDs.** Versioned entities (Project, WBSElement, CostElement) expose:

- **Root ID** (`project_id`, `wbs_element_id`, `cost_element_id`) — stable across all versions; used in FKs, URLs, API endpoints.
- **Version ID** (`id`) — PK of a single version row; never used in relationships.

Relationships between versioned entities reference **root IDs**. There are **no DB-level FK constraints** on them (root_id is not unique across versions); integrity is enforced in application code. Example: `WBSElement.project_id` references the root `project_id`, not a specific version's `id`.

## API

Base URL `/api/v1`; JWT Bearer auth (`Authorization: Bearer <token>`); docs at `/docs` (Swagger) and `/openapi.json`.

## Docs

Entry point: [`docs/00-meta/README.md`](docs/00-meta/README.md)
