# Backcast

# BackCast - Project Earned value Simulator, Time traveller and Analyzer

![Favicon](frontend/public/assets/images/backcast.png)

## Overview

BackCast is a comprehensive application designed for the Project Management Directorate to simulate, test, and validate financial management processes for end-of-line automation projects before implementing them in production environments.

The system enables organizations to:

- Model complex project scenarios with multiple machines (WBEs) and departmental cost elements
- Track project financial performance using Earned Value Management (EVM) principles
- Validate business rules and performance metrics under various conditions
- Support complete project lifecycle financial management including budgets, costs, forecasts, change orders, and quality events
- Generate accurate EVM calculations and reports for decision-making

This tool serves as a simulation and validation platform, allowing the Project Management Directorate to refine business rules, test performance metrics, and establish best practices for project financial management without impacting production systems.

The system provides:

- **Git-like Versioning:** Complete entity history with branching and time-travel capabilities
- **EVM Compliance:** Full Earned Value Management per ANSI/EIA-748
- **EVM Analyzer UI:** Interactive master-detail interface for EVM analysis at all aggregation levels
- **Change Order Isolation:** Test modifications in branches before merging
- **Audit Trail:** Immutable history for compliance and analysis

## Key Features

### EVM Analyzer Master-Detail UI

**Latest Feature (2026-01-22):** Generic EVM Analyzer supporting multiple entity types with comprehensive visualizations.

**Capabilities:**

- **Multi-Level Analysis:** View EVM metrics for Cost Elements, WBEs, and Projects
- **Summary View:** Quick overview with organized metric categories (Schedule, Cost, Performance, Forecast)
- **Advanced Analysis Modal:** Detailed EVM analysis with:
  - Performance gauges (CPI, SPI) with traditional semi-circle display
  - Time-series charts (PV/EV/AC progression, Forecast vs. Actual)
  - Granularity selector (Day/Week/Month)
  - Historical trend analysis
- **Time-Travel Support:** All queries respect control date, branch, and mode settings
- **Generic Components:** Reusable UI components work across all entity types
- **Batch Aggregation:** Server-side aggregation for WBEs and Projects (sum + weighted average)

**Documentation:**
- [EVM API Guide](docs/02-architecture/evm-api-guide.md) - API endpoint reference
- [EVM Components Guide](docs/02-architecture/evm-components-guide.md) - Component usage
- [EVM Time-Travel Semantics](docs/02-architecture/evm-time-travel-semantics.md) - Time-travel behavior
- [EVM Calculation Guide](docs/02-architecture/evm-calculation-guide.md) - Formulas and interpretation

**Performance:**
- Summary view renders in <500ms
- Modal with charts renders in <2s
- Time-series queries complete in <1s for 1-year ranges

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
cd backend
uv run uvicorn app.main:app --reload --port 8020 --host 0.0.0.0

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
- [EVM API Guide](docs/02-architecture/evm-api-guide.md) - EVM API reference
- [EVM Components Guide](docs/02-architecture/evm-components-guide.md) - EVM UI components
- [EVM Calculation Guide](docs/02-architecture/evm-calculation-guide.md) - EVM formulas
- [PDCA Prompts](docs/04-pdca-prompts/) - AI collaboration templates
- [Docker Deployment Guide](docs/05-user-guide/docker-deployment-guide.md) - Production deployment

## Project Status

- [Product Backlog](docs/03-project-plan/product-backlog.md) - Product backlog

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
