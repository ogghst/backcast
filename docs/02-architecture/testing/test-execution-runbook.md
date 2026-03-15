# Test Execution Runbook

**Purpose:** Guide for running tests incrementally and troubleshooting common issues

**Last Updated:** 2026-03-15
**Status:** Active

---

## Incremental Testing Workflow

### Step 1: Run Tests for Modified Files Only

```bash
# Activate virtual environment
cd backend && source .venv/bin/activate

# Run specific test file
uv run pytest tests/unit/ai/test_agent_service.py -v

# Run specific test
uv run pytest tests/unit/ai/test_agent_service.py::test_chat_stream_sends_tokens -v

# Run tests matching pattern
uv run pytest tests/unit/ai/ -k "stream" -v
```

### Step 2: Check Coverage for Specific Component

```bash
# Check coverage for specific file
uv run pytest tests/unit/ai/test_agent_service.py \
    --cov=app.ai.agent_service \
    --cov-report=term-missing

# Check coverage for multiple files
uv run pytest tests/unit/ai/ \
    --cov=app.ai \
    --cov-report=html

# Open HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Step 3: Interpret Coverage Results

```
Name                                      Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------
app/ai/agent_service.py                     150     80    47%   23-45, 67-89, 120-145
```

**What this means:**
- **Stmts:** Total statements (lines of executable code)
- **Miss:** Statements not executed by tests
- **Cover:** Percentage of code tested
- **Missing:** Specific line numbers not covered

**Action:** Look at missing lines - are they critical paths?

### Step 4: Add More Tests If Needed

```bash
# If coverage inadequate for critical paths:
# 1. Identify which lines are missing
# 2. Write tests to execute those lines
# 3. Run coverage again to verify

# Example: Lines 23-45 not covered
# → These might be error handling paths
# → Write test that triggers that error
# → Re-run coverage
```

### Step 5: Only Run Full Test Suite Before Commit

```bash
# Full quality check (REQUIRED before commit)
uv run ruff check .
uv run mypy app/
uv run pytest --cov=app

# Or use project alias if defined
npm run test:full  # (if configured)
```

---

## Quality Gate Commands

### Backend (Python/FastAPI)

```bash
cd backend && source .venv/bin/activate

# Must pass before commit
uv run ruff check .                    # Linting
uv run mypy app/                       # Type checking
uv run pytest --cov=app                # All tests + coverage

# Optional: Check specific component
uv run pytest tests/unit/ai/ --cov=app.ai
```

### Frontend (React/TypeScript)

```bash
cd frontend

# Must pass before commit
npm run lint                           # ESLint
npm run test:coverage                  # Vitest + coverage

# Optional: Run specific test file
npm test -- src/features/ai/tests
```

---

## Troubleshooting Common Issues

### Issue 1: LangGraph Import Hangs

**Symptom:**
```bash
uv run pytest tests/unit/ai/test_agent_service.py
# Hangs indefinitely, no output
```

**Cause:** Incompatibility between pytest-asyncio and LangGraph

**Workaround:**
1. Avoid importing LangGraph in test files
2. Mock LangGraph components in unit tests
3. Use separate test file for integration tests

```python
# Bad: Imports LangGraph directly
from langgraph.graph import StateGraph

# Good: Mock the LangGraph dependency
from unittest.mock import MagicMock
StateGraph = MagicMock()
```

**Long-term solution:** Create separate test suite with different pytest config

---

### Issue 2: Async Test Fixtures Not Working

**Symptom:**
```python
@pytest.fixture
async def my_fixture():
    return await get_data()

# Error: fixture function not async
```

**Cause:** Missing `@pytest.mark.asyncio` on test or fixture

**Solution:**
```python
import pytest

@pytest.fixture
async def my_fixture():
    """Async fixture must be marked."""
    return await get_data()

@pytest.mark.asyncio  # Required!
async def test_something(my_fixture):
    assert my_fixture is not None
```

---

### Issue 3: Database Isolation Problems

**Symptom:**
```bash
# Test 1 passes
# Test 2 fails because Test 1's data is still there
```

**Cause:** Tests not properly isolated, database not rolled back

**Solution:**
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def test_db():
    """Create test database with automatic rollback."""
    # Create test session
    async with AsyncSession(engine) as session:
        yield session
        # Automatically rolls back after test
        await session.rollback()
```

---

### Issue 4: Mock Not Called

**Symptom:**
```python
mock_service.get_by_id.assert_called_once()
# AssertionError: Expected 'mock' to have been called once.
# But it was not called.
```

**Cause:**
1. Mock not patched before function import
2. Mock path incorrect
3. Function using different instance

**Solution:**
```python
# Bad: Patch after import
from app.services import project_service
with patch('app.services.project_service'):

# Good: Patch before use
with patch('app.services.project_service.ProjectService.get_by_id'):
    from app.services import project_service
    # Now it's patched
```

---

### Issue 5: Test Passes But Coverage Doesn't Increase

**Symptom:**
```bash
# Added new test
uv run pytest tests/unit/ai/test_agent_service.py --cov=app.ai.agent_service
# Coverage: 11.56% (same as before)
```

**Cause:** Test doesn't execute the code you think it does

**Debug:**
```python
# Add debug print
def test_my_function():
    result = my_function()
    print(f"Result: {result}")  # Check if it even runs

# Or use pytest's verbose output
uv run pytest tests/unit/ai/test_agent_service.py -vv -s
```

**Common reasons:**
1. Test mocked the function it's trying to test
2. Exception caught and silently ignored
3. Code path not actually reached
4. Wrong function/class being tested

---

## Test Performance Optimization

### Run Only Failed Tests

```bash
# First run: 100 tests, 5 fail
uv run pytest

# Rerun only failed tests
uv run pytest --lf  # "last failed"

# Rerun failed tests first, then all
uv run pytest --ff  # "failed first"
```

### Run Tests in Parallel

```bash
# Install pytest-xdist
uv add --dev pytest-xdist

# Run on all CPU cores
uv run pytest -n auto

# Run on specific number of workers
uv run pytest -n 4
```

**Warning:** Parallel tests can mask shared state issues. Use with caution.

### Stop After N Failures

```bash
# Stop after first failure
uv run pytest -x

# Stop after 5 failures
uv run pytest --maxfail=5

# Saves time when many tests are failing
```

### Skip Slow Tests

```bash
# Mark slow tests with decorator
@pytest.mark.slow
async def test_very_slow_operation():
    await long_running_task()

# Skip slow tests during development
uv run pytest -m "not slow"

# Run only slow tests before release
uv run pytest -m "slow"
```

---

## Test Organization

### Directory Structure

```
backend/tests/
├── unit/                    # Fast, isolated tests
│   ├── ai/                  # AI component tests
│   │   ├── test_agent_service.py
│   │   └── tools/
│   │       ├── test_ai_tool_decorator.py
│   │       └── test_crud_template.py
│   ├── services/            # Service layer tests
│   └── api/                 # API endpoint tests
├── integration/             # Slower, database tests
│   ├── ai/
│   │   └── tools/
│   │       └── test_crud_tools_integration.py
│   └── services/
└── conftest.py              # Shared fixtures
```

### Test Naming Conventions

```python
# Good: Clear, descriptive names
def test_create_project_with_valid_input_succeeds():
    """Test creating a project with valid input."""
    pass

def test_create_project_with_duplicate_code_fails():
    """Test creating a project with duplicate code fails."""
    pass

# Bad: Vague names
def test_project():
    """Test project."""
    pass

def test_it_works():
    """Test that it works."""
    pass
```

### Test Class Organization

```python
class TestProjectServiceCreate:
    """All tests for ProjectService.create()."""

    def test_create_with_valid_input_succeeds(self):
        pass

    def test_create_with_duplicate_code_fails(self):
        pass

    def test_create_with_invalid_budget_raises_error(self):
        pass

class TestProjectServiceUpdate:
    """All tests for ProjectService.update()."""
    pass
```

---

## Continuous Integration

### Pre-commit Hooks (Optional)

```bash
# Install pre-commit
uv add --dev pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: local
    hooks:
      - id: ruff
        name: ruff linting
        entry: uv run ruff check .
        language: system
      - id: mypy
        name: mypy type checking
        entry: uv run mypy app/
        language: system
      - id: pytest
        name: run tests
        entry: uv run pytest --cov=app
        language: system
EOF

# Install hooks
pre-commit install
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: |
          cd backend
          uv sync
      - name: Run linting
        run: |
          cd backend
          uv run ruff check .
      - name: Run type checking
        run: |
          cd backend
          uv run mypy app/
      - name: Run tests
        run: |
          cd backend
          uv run pytest --cov=app
```

---

## Coverage Reporting

### Generate HTML Report

```bash
# Generate detailed HTML coverage report
uv run pytest --cov=app --cov-report=html

# Open in browser
open htmlcov/index.html

# Navigate to specific file
# Click on file to see which lines are covered (green)
# and which are not (red)
```

### Coverage Trends

```bash
# Generate coverage data over time
uv run pytest --cov=app --cov-report=json

# Parse JSON for tracking
python -c "import json; data=json.load(open('coverage.json')); print(f\"Coverage: {data['totals']['percent_covered']:.2f}%\")"
```

### Minimum Coverage Enforcement

```bash
# Fail if coverage below threshold
uv run pytest --cov=app --cov-fail-under=60

# Use different thresholds for different components
uv run pytest tests/unit/ai/ --cov=app.ai --cov-fail-under=40
uv run pytest tests/unit/services/ --cov=app.services --cov-fail-under=70
```

---

## Quick Reference

### Common Commands

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific file
uv run pytest tests/unit/ai/test_agent_service.py

# Run specific test
uv run pytest tests/unit/ai/test_agent_service.py::test_chat_stream_sends_tokens

# Run tests matching pattern
uv run pytest -k "stream"

# Run with coverage
uv run pytest --cov=app

# Run coverage for specific component
uv run pytest --cov=app.ai.agent_service --cov-report=term-missing

# Stop after first failure
uv run pytest -x

# Run failed tests only
uv run pytest --lf

# Run in parallel
uv run pytest -n auto

# Skip slow tests
uv run pytest -m "not slow"
```

### Quality Checks

```bash
# Full quality check (REQUIRED before commit)
cd backend && source .venv/bin/activate
uv run ruff check . && uv run mypy app/ && uv run pytest --cov=app

# Frontend
cd frontend
npm run lint && npm run test:coverage
```

---

## References

- **Test Strategy Guide:** `docs/02-architecture/testing/test-strategy-guide.md`
- **ADR-004:** Test Coverage Strategy
- **Project CLAUDE.md:** Quality standards

---

**Document Owner:** PDCA ACT Phase 2026-03-15
**Review Schedule:** Quarterly
**Next Review:** 2026-06-15
