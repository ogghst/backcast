# Entity Version Control System (EVCS) Architecture

## 1. Project Scope

This project implements a robust, Git-style version control system for relational database entities. Unlike simple audit logs, this system provides full branching capabilities, time-travel functionality, and immutable state history for complex data structures.

**Key Capabilities:**

- **Branching:** Support for parallel development of entity states (e.g., `main`, `draft`, `feature/legal-review`).
- **Time Travel:** Ability to reconstruct the state of an entity (and its related children) at any specific timestamp in the past.
- **Immutability:** Updates create new version nodes; historical data is never overwritten (APPEND-ONLY).
- **Strong Typing:** Fully typed codebase verified at compile-time.

## 2. Project Structure

The project is organized into several key directories:

- **`backend/`**: Contains the FastAPI application, database models, and versioning logic.
  - `app/api/`: Endpoint definitions and dependencies.
  - `app/core/`: Configuration, security, and versioning core logic.
  - `app/models/`: SQLAlchemy ORM models and Pydantic schemas.
  - `app/repositories/`: Data access layer implementing the versioning logic.
  - `app/services/`: Business logic orchestrating multiple repositories.
- **`frontend/`**: Contains the React application.
  - `src/`: Source code for the frontend application.
  - `vite.config.ts`: Vite configuration.
- **`docs/`**: Bounded-context documentation (product scope, architecture, project plan, PDCA prompts).
  - `docs/00-meta/`: Entry point and documentation guides.
  - `docs/01-product-scope/`: Business requirements and vision.
  - `docs/02-architecture/`: System design, contexts, cross-cutting concerns, ADRs.
  - `docs/03-project-plan/`: Current work, backlog, iteration history.
  - `docs/04-pdca-prompts/`: AI collaboration templates.
- **`scripts/`**: Utility scripts for database management and development tasks.

## 3. Documentation

The project uses a **bounded-context documentation structure** to minimize context rot and improve maintainability.

**Quick Navigation:**

- **[Documentation Guide](file:///home/nicola/dev/backcast_evs/docs/00-meta/README.md)**: How to find and maintain documentation
- **[Product Vision](file:///home/nicola/dev/backcast_evs/docs/01-product-scope/vision.md)**: Business goals and user needs
- **[System Map](file:///home/nicola/dev/backcast_evs/docs/02-architecture/00-system-map.md)**: High-level architecture overview
- **[Sprint Backlog](file:///home/nicola/dev/backcast_evs/docs/03-project-plan/sprint-backlog.md)**: Active sprint status and goals
- **[PDCA Prompts](file:///home/nicola/dev/backcast_evs/docs/04-pdca-prompts/)**: AI collaboration templates

**Detailed Documentation:**

- **Architecture:** `docs/02-architecture/` - Bounded contexts, cross-cutting concerns, ADRs

## 4. Work Process (Strict Rules)

> [!IMPORTANT]
> To ensure project health and visibility, the following rules are **MANDATORY**:
>
> 1.  **PDCA Alignment**: Every major change must follow the Plan-Do-Check-Act cycle using the **[PDCA Prompts](file:///home/nicola/dev/backcast_evs/docs/04-pdca-prompts/)**.
> 2.  **Documentation Updates**:
>     - Update **[Sprint Backlog](file:///home/nicola/dev/backcast_evs/docs/03-project-plan/sprint-backlog.md)** during active work
>     - Create iteration record in `docs/03-project-plan/iterations/` after completion
>     - Update **[Sprint Backlog](file:///home/nicola/dev/backcast_evs/docs/03-project-plan/sprint-backlog.md)** as priorities change
>     - Update architecture docs when patterns change

---

> [!NOTE]
> This project follows strict type safety (MyPy strict mode) and automated quality checks (Ruff).
