# Backcast EVS

**Project Budget Management & Earned Value Management System with Git-Style Versioning**

## Overview

Backcast EVS (Entity Versioning System) is a comprehensive project financial management platform for end-of-line automation projects. The system provides:

- **Git-like Versioning:** Complete entity history with branching and time-travel capabilities
- **EVM Compliance:** Full Earned Value Management per ANSI/EIA-748
- **Change Order Isolation:** Test modifications in branches before merging
- **Audit Trail:** Immutable history for compliance and analysis

## Quick Start

### Development Setup

```bash
# Install dependencies
uv sync

# Setup database
docker-compose up -d postgres

# Run migrations
cd backend
uv run alembic upgrade head

# Start development server
uv run uvicorn app.main:app --reload

# Start frontend development server
cd frontend
npm run dev
```

### Running Tests

```bash
# Backend
cd backend
uv run pytest
uv run pytest --cov=app --cov-report=html

# Frontend
cd frontend
npm test
```

### Code Quality

```bash
# Backend Linting
uv run ruff check .

# Frontend Linting
cd frontend
npm run lint

# Type checking
uv run mypy app/
```

## Documentation

**Start Here:** [Documentation Guide](docs/00-meta/README.md)

**Quick Links:**

- [Product Vision](docs/01-product-scope/vision.md) - Business goals
- [System Map](docs/02-architecture/00-system-map.md) - Architecture overview
- [Current Work](docs/03-project-plan/current-iteration.md) - Sprint status
- [PDCA Prompts](docs/04-pdca-prompts/) - AI collaboration templates

## Project Status

See [Current Iteration](docs/03-project-plan/current-iteration.md) for details.

## Technology Stack

- **Runtime:** Python 3.12+
- **Framework:** FastAPI (async ASGI)
- **ORM:** SQLAlchemy 2.0 (async)
- **Database:** PostgreSQL 15+
- **Validation:** Pydantic V2
- **Testing:** pytest, httpx
- **Quality:** MyPy (strict), Ruff

### Frontend

- **Runtime:** Node.js
- **Framework:** React 18, Vite 7
- **UI Library:** Ant Design 5
- **State Management:** Zustand, React Query
- **Testing:** Vitest, Playwright

## Contributing

This project follows strict quality standards:

- **Type Safety:** MyPy strict mode (100% coverage)
- **Testing:** 80% minimum coverage
- **Linting:** Zero Ruff errors
- **Process:** PDCA cycle for all major changes

See [Coding Standards](docs/00-meta/coding_standards.md) for detailed guidelines.

## License

[License TBD]

## Contact

- **Project Owner:** [TBD]
- **Tech Lead:** [TBD]
