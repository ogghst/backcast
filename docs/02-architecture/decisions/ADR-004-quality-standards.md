# ADR-004: Code Quality Standards

## Status

✅ Accepted (2025-12-27)

## Context

The Backcast EVS system requires enterprise-grade reliability for financial tracking and EVM calculations. To ensure code quality, maintainability, and reliability, we needed to establish clear standards that:

- Catch bugs at compile time where possible
- Ensure consistent code style
- Provide confidence in code correctness
- Support long-term maintainability

## Decision

Adopt strict code quality standards across the entire codebase.

### Static Type Checking

**Tool:** MyPy with strict mode

```toml
# pyproject.toml
[tool.mypy]
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
```

**Requirements:**

- 100% type hint coverage for all production code
- No `# type: ignore` without documented justification
- All function parameters and return types annotated
- Use `Mapped[]` for SQLAlchemy columns

### Linting

**Tool:** Ruff

```toml
# pyproject.toml
[tool.ruff]
target-version = "py312"
line-length = 88
select = ["E", "F", "W", "I", "UP", "B", "C4"]
```

**Requirements:**

- Zero linting errors in CI
- Automatic formatting via `ruff format`
- Import sorting via `ruff --fix`

### Test Coverage

**Tool:** pytest-cov

**Requirements:**

- Minimum 80% overall coverage
- 100% coverage for critical paths (versioning, calculations)
- Coverage reports in CI pipeline

```bash
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

### Test Structure

**Framework:** pytest with pytest-asyncio

**Requirements:**

- Unit tests for all business logic
- Integration tests for database operations
- API tests for all endpoints
- Test isolation (no shared state between tests)
- Clear test naming: `test_{feature}_{scenario}_{expected_outcome}`

### Documentation

**Requirements:**

- Docstrings for all public functions/classes
- Architecture decision records (ADRs) for significant choices
- API documentation via FastAPI automatic docs
- README files for each module

## Consequences

### Positive

- **Early Bug Detection:** Type errors caught before runtime
- **Consistent Style:** Ruff ensures uniform formatting
- **Confidence:** High test coverage enables safe refactoring
- **Maintainability:** Types and tests serve as documentation
- **Onboarding:** Clear standards for new contributors

### Negative

- **Development Speed:** Initial coding takes longer with strict types
- **CI Time:** Full test suite and type checking adds time
- **Learning Curve:** Team must learn strict typing patterns

## Metrics

| Metric             | Threshold | Current |
| ------------------ | --------- | ------- |
| MyPy Errors        | 0         | Target  |
| Ruff Errors        | 0         | Target  |
| Test Coverage      | ≥80%      | Target  |
| Type Hint Coverage | 100%      | Target  |

## Implementation

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
      - id: ruff-format
```

### CI Pipeline

```yaml
# .github/workflows/ci.yml
- name: Type Check
  run: mypy app --strict

- name: Lint
  run: ruff check app tests

- name: Test
  run: pytest --cov=app --cov-fail-under=80
```

## Related Documentation

- [Database Strategy](../cross-cutting/database-strategy.md) - Type safety in ORM
- [Security Practices](../cross-cutting/security-practices.md) - Security testing requirements
