# Backcast 

Backend implementation for the Backcast Entity Versioning System (EVS) - a Project Budget Management and Earned Value Management (EVM) application with Git-style versioning capabilities.

[![CI](https://github.com/ogghst/backcast_evs/workflows/CI/badge.svg)](https://github.com/ogghst/backcast_evs/actions)
[![codecov](https://codecov.io/gh/ogghst/backcast_evs/branch/main/graph/badge.svg)](https://codecov.io/gh/ogghst/backcast_evs)

## Features

- **Entity Versioning System**: Git-like versioning for database entities with branching and time-travel capabilities
- **EVM Analytics**: Complete Earned Value Management calculations and reporting
- **Type-Safe**: Strict MyPy type checking for robust code
- **Async-First**: Built with FastAPI and async SQLAlchemy for high performance
- **Test Coverage**: Comprehensive test suite with 80%+ coverage target

## Technology Stack

- **Python 3.12+**
- **FastAPI 0.115+** - Modern async web framework
- **SQLAlchemy 2.0+** - Async ORM with type hints
- **PostgreSQL 15+** - Database with advanced features
- **Pydantic 2.0+** - Data validation and settings
- **pytest** - Testing framework with async support

## Getting Started

### Prerequisites

- Python 3.12 or higher
- PostgreSQL 15 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/ogghst/backcast_evs.git
   cd backcast_evs/backend
   ```

2. **Install dependencies**

   ```bash
   uv sync
   ```

3. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

4. **Run database migrations**

   ```bash
   uv run alembic upgrade head
   ```

5. **Start the development server**
   ```bash
   uv run uvicorn app.main:app --reload --port 8020
   ```

The API will be available at `http://localhost:8020`

### Database Seeding

By default, the database is NOT seeded automatically on startup. To seed the database with initial demonstration data, use the provided script:

```bash
uv run python scripts/reseed_db.py
```

**WARNING:** This script will clear ALL data currently in the database before reseeding.

## Development

### Code Quality Tools

This project uses automated code quality tools:

- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checker (strict mode)
- **pytest**: Testing framework with coverage reporting

### Running Quality Checks

```bash
# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Type check
uv run mypy app --strict

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app --cov-report=term-missing
```

### Pre-commit Hooks

Install pre-commit hooks to automatically run quality checks before commits:

```bash
uv run pre-commit install
```

Now ruff and mypy will run automatically on every commit.

### Project Structure

```
app/
├── api/              # API routes and dependencies
│   ├── routes/       # Endpoint definitions
│   └── dependencies/ # Dependency injection
├── core/             # Core configuration and utilities
├── db/               # Database session management
├── models/           # Data models
│   ├── domain/       # SQLAlchemy ORM models
│   └── schemas/      # Pydantic schemas
├── repositories/     # Data access layer
├── services/         # Business logic layer
└── main.py           # FastAPI application entry point

tests/
├── unit/             # Unit tests
├── integration/      # Integration tests
└── api/              # API endpoint tests
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/unit/test_config.py

# Run with coverage report
uv run pytest --cov=app --cov-report=html
```

### Test Coverage

We maintain a minimum of 80% test coverage. View the HTML coverage report:

```bash
uv run pytest --cov=app --cov-report=html
open htmlcov/index.html
```

**Coverage Policy:**

- Minimum coverage: 80% (enforced in CI)
- New code should maintain or improve coverage
- Coverage reports generated on every test run
- Codecov integration tracks coverage trends

## CI/CD Pipeline

### Continuous Integration

Every push and pull request triggers automated quality checks:

1. **Code Linting** - Ruff checks code style and common errors
2. **Code Formatting** - Ruff ensures consistent formatting
3. **Type Checking** - MyPy validates type hints in strict mode
4. **Test Suite** - Pytest runs all tests with coverage reporting
5. **Coverage Check** - Build fails if coverage drops below 80%

### CI Troubleshooting

**Build failing on coverage?**

```bash
# Run locally to see coverage report
uv run pytest --cov=app --cov-report=term-missing

# Check which files need more tests
uv run pytest --cov=app --cov-report=html
open htmlcov/index.html
```

**Build failing on type checks?**

```bash
# Run MyPy locally
uv run mypy app --strict

# Fix common issues:
# - Add type hints to function signatures
# - Import types from typing module
# - Use Optional[T] for nullable values
```

**Build failing on linting?**

```bash
# Check what needs fixing
uv run ruff check .

# Auto-fix most issues
uv run ruff check . --fix

# Format code
uv run ruff format .
```

### Branch Protection (Recommended)

For production repositories, configure these settings on `main` and `develop` branches:

- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging
- ✅ Require pull request reviews (1+ approvers)
- ✅ Required checks: `test` job from CI workflow
- ✅ Dismiss stale pull request approvals when new commits are pushed

## API Documentation

Interactive API documentation is available when the server is running:

- **Swagger UI**: http://localhost:8020/docs
- **ReDoc**: http://localhost:8020/redoc
- **OpenAPI JSON**: http://localhost:8020/api/v1/openapi.json

## Documentation

Detailed documentation is available in the `docs/` directory:

- [Product Requirements Document](docs/prd.md)
- [Backend Architecture](docs/backend_architecture.md)
- [Agile Implementation Plan](docs/agile_implementation_plan.md)
- [Sprint 1 Plan](docs/sprint_1_plan.md)

## Contributing

1. Create a feature branch from `develop`
2. Make your changes
3. Ensure all tests pass and coverage is maintained
4. Run quality checks (`ruff`, `mypy`)
5. Submit a pull request

## License

[Add your license here]

## Contact

[Add contact information]
