# Developer Onboarding Guide

Welcome to the **Backcast EVCS** project! This guide will help you get up to speed with our architecture, tools, and processes.

---

## 1. Project Overview

Backcast EVCS is an **Entity Version Control System** for relational database entities. It provides full branching, time-travel, and immutable history for complex data structures.

- **Stack**: FastAPI (Backend), React + Ant Design + TanStack Query (Frontend), PostgreSQL (Database).
- **Core Architecture**: Bitemporal versioning, Command pattern, Service-based orchestration.

## 2. Reading List

Start by reading these core documents in order:

1. **[Product Vision](../01-product-scope/vision.md)**: Why we are building this.
2. **[System Map](../02-architecture/00-system-map.md)**: High-level overview.
3. **[Coding Standards](../02-architecture/coding-standards.md)**: **MANDATORY READING**.
4. **[API Response Patterns](../02-architecture/cross-cutting/api-response-patterns.md)**: Modern filtering and response patterns.
5. **[Technical Debt Ledger](../03-project-plan/technical-debt/)**: Known issues and areas for improvement.

## 3. Local Setup

### Backend

1. `cd backend`
2. `pip install -r requirements.txt` (or use `uv` / `poetry`)
3. `./scripts/run-dev.sh` to start the FastAPI server.

### Frontend

1. `cd frontend`
2. `npm install`
3. `npm run dev` to start the Vite dev server.

## 4. Key Patterns to Master

### 4.1 Bitemporal Versioning

We use `valid_time` and `transaction_time`.

- See: [`ADR-005`](../02-architecture/decisions/ADR-005-bitemporal-versioning.md)

### 4.2 Server-Side Filtering

All tables support global search, multi-field filtering, and sorting managed by the backend.

- See: [`ADR-008`](../02-architecture/decisions/ADR-008-server-side-filtering.md)
- Helper: `app.core.filtering.FilterParser`

### 4.3 Command Pattern

State changes (Create/Update/Delete) for versioned entities MUST use the command pattern to ensure auditability and branch isolation.

- See: [`ADR-003`](../02-architecture/decisions/ADR-003-command-pattern.md)

## 5. Quality Gates

Before submitting a Pull Request:

1. **Linting**: No errors in `ruff` (backend) or `eslint` (frontend).
2. **Types**: 100% type safety (no `Any`/`any`). `mypy --strict` and `tsc --noEmit`.
3. **Tests**: All tests pass. Critical paths covered 100%.
4. **Checklist**: Complete the **[Code Review Checklist](../02-architecture/code-review-checklist.md)**.

## 6. PDCA Workflow

We follow the **Plan-Do-Check-Act** cycle for all major features:

1. **Plan**: Define objective and success criteria in `docs/03-project-plan/iterations/`.
2. **Do**: Implement and test.
3. **Check**: Verify against success criteria.
4. **Act**: Standardize patterns and document learnings.

---

**Questions?** Ask the AI Agent or consult the [`docs/04-pdca-prompts/`](../04-pdca-prompts/) for templates on how to collaborate effectively.
