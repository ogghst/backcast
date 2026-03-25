# System Map: Backcast 

**Last Updated:** 2026-01-01
**Technology:** Python 3.12, FastAPI, React 18, PostgreSQL, AsyncIO

## High-Level Architecture

Backcast  is a full-stack application for project financial management.

- **Frontend**: React SPA (Single Page Application) for user interaction.
- **Backend**: FastAPI implementation of Entity Versioning Control System (EVCS).

**Frontend (SPA)** → **API Layer** → **Service Layer** → **Repository Layer** → **Database**

## Core Technology Choices

### Backend

- **Web Framework:** FastAPI (async ASGI)
- **ORM:** SQLAlchemy 2.0 (async)
- **Database:** PostgreSQL 15+
- **Migration:** Alembic
- **Testing:** pytest (asyncio)

### Frontend

- **Framework:** React 18 + Vite
- **Language:** TypeScript
- **UI Library:** Ant Design 6
- **Data Fetching:** TanStack Query (React Query)
- **State:** Zustand

## Key Bounded Contexts

The system is partitioned into the following bounded contexts. See [01-bounded-contexts.md](01-bounded-contexts.md).

1.  Authentication & Authorization
2.  User Management
3.  Department Management
4.  Project & WBE Management
5.  Cost Element & Financial Tracking
6.  Change Order & Branching
7.  EVM Calculations & Reporting

## Versioning Architecture (EVCS Core)

**Pattern:** Bitemporal Single-Table with PostgreSQL `TSTZRANGE`  
**Immutability:** Append-only, updates create new versions  
**ADR:** [ADR-005: Bitemporal Versioning](decisions/ADR-005-bitemporal-versioning.md)

**Key Features:**

- **Bitemporal:** Track valid time (business) and transaction time (system)
- **Branching:** All entities support branch isolation for change orders
- **Soft Delete:** Reversible deletion with `deleted_at` timestamp
- **Version Chain:** DAG structure via `parent_id` for history traversal
- **Generic Framework:** `TemporalBase`, `TemporalService[T]`, generic commands
- **Non-Versioned:** `SimpleBase` for config/preferences (standard CRUD)

**Documentation:** [EVCS Core Architecture](backend/contexts/evcs-core/architecture.md)

## Directory Structure

```
.
├── backend/
│   ├── app/           # FastAPI application
│   ├── tests/         # Pytest suite
│   └── alembic/       # Database migrations
│
└── frontend/
    ├── src/
    │   ├── api/       # API clients
    │   ├── features/  # Domain features
    │   └── layouts/   # UI Layouts
    └── vite.config.ts
```

## Cross-Cutting Concerns

- **Database Strategy:** AsyncPG connection pooling.
- **API Conventions:** REST, `/api/v1` prefix.
- **Security:** JWT access tokens, Argon2 hashing.
- **Performance:** <200ms API response target.
- **Seed Data:** Deterministic UUIDv5-based seeding with ID-based relationships.

## Key Design Decisions

- **[ADR-001](decisions/ADR-001-technology-stack.md)** - Technology Stack (FastAPI, SQLAlchemy 2.0, React)
- **[ADR-003](decisions/ADR-003-command-pattern.md)** - Command Pattern for state changes
- **[ADR-004](decisions/ADR-004-quality-standards.md)** - Quality Standards (MyPy strict, 80% coverage)
- **[ADR-005](decisions/ADR-005-bitemporal-versioning.md)** - Bitemporal Versioning (supersedes ADR-002)
- **[ADR-006](decisions/ADR-006-protocol-based-type-system.md)** - Protocol-based Type System
- **[ADR-007](decisions/ADR-007-rbac-service.md)** - RBAC Service Design

**Detailed Architecture:**

- [Backend Contexts](backend/contexts/)
- [Frontend Contexts](frontend/contexts/)
- [ADR Index](decisions/adr-index.md)
