# Test Strategy Guide

**Purpose:** Guide for choosing appropriate test types and writing effective tests

**Last Updated:** 2026-04-14
**Status:** Active

---

## Decision Tree: Unit vs Integration vs E2E Tests

```
Does the code touch the database?
├─ Yes → Integration test
│  ├─ Use test database with rollback
│  ├─ Use real fixtures with test data
│  └─ Test actual service methods
└─ No → Does it have complex business logic?
   ├─ Yes → Unit test
   │  ├─ Mock external dependencies
   │  ├─ Test edge cases and error paths
   │  └─ Fast, focused tests
   └─ No → Is it a thin wrapper around a service?
      ├─ Yes → Smoke test only
      │  ├─ Test it can be imported
      │  ├─ Test it has correct decorators
      │  └─ Don't mock the service
      └─ No → Unit test
```

---

## When to Use Each Test Type

### Unit Tests

**Use for:**
- Business logic with complex algorithms
- Validation logic with many edge cases
- Pure functions (no I/O, no database)
- Error handling and exception paths
- Utility functions and helpers

**Example:**
```python
def test_calculate_evm_metrics_validates_inputs():
    """Test EVM calculation with invalid inputs."""
    with pytest.raises(ValueError):
        calculate_evm_metrics(
            planned_value=-100,  # Negative
            earned_value=50,
            actual_cost=75
        )
```

**Don't use for:**
- Database queries
- API endpoint testing
- Service orchestration
- Tool template wrappers

---

### Integration Tests

**Use for:**
- Database queries and transactions
- API endpoint to database integration
- Service layer orchestration
- **Tool templates** (thin wrappers around services)
- Repository pattern testing

**Example:**
```python
@pytest.mark.asyncio
async def test_list_projects_returns_active_projects(test_db):
    """Test that list_projects returns only active projects."""
    # Arrange: Create test data
    project = await ProjectService.create(
        test_db,
        ProjectCreate(name="Test", code="T001")
    )

    # Act: Query through tool
    result = await crud_template.list_projects(
        context=ToolContext(session=test_db, user_id=user_id, user_role="admin")
    )

    # Assert: Verify actual database results
    assert len(result['projects']) >= 1
    assert any(p['id'] == project.id for p in result['projects'])
```

**Best Practices:**
- Use test database with transaction rollback
- Use fixtures for common test data
- Test actual behavior, not implementation
- Verify database state changes

---

### End-to-End Tests

**Use for:**
- Critical user workflows
- WebSocket connections
- Multi-component interactions
- Performance testing
- Authentication/authorization flows

**Use sparingly:**
- Slow and expensive to maintain
- Brittle (break with UI changes)
- Hard to debug
- Use only for critical paths

---

## Anti-Patterns to Avoid

### 1. Over-Mocking

**Bad:**
```python
def test_create_project():
    mock_service = AsyncMock()
    mock_service.create.return_value = MagicMock()
    with patch.object(ToolContext, 'project_service', mock_service):
        result = await create_project(...)
    # This tests the mock, not the actual function!
```

**Good:**
```python
@pytest.mark.asyncio
async def test_create_project_with_valid_input(test_db):
    """Test creating a project with valid input."""
    result = await crud_template.create_project(
        name="Test Project",
        code="T001",
        context=ToolContext(session=test_db, ...)
    )
    assert 'id' in result
    assert result['name'] == "Test Project"
```

### 2. Testing Implementation Details

**Bad:**
```python
def test_function_uses_specific_algorithm():
    assert function.__code__.co_name == 'specific_algorithm'
```

**Good:**
```python
def test_function_returns_correct_result():
    result = function(input_data)
    assert result == expected_output
```

### 3. Wrong Test Level

**Bad:** Unit testing database queries
```python
def test_project_repository_query():
    mock_session = AsyncMock()
    mock_session.execute.return_value = [...]
    # This doesn't test actual SQL behavior
```

**Good:** Integration testing database queries
```python
@pytest.mark.asyncio
async def test_project_repository_returns_projects(test_db):
    await Project.create(test_db, name="Test")
    projects = await ProjectRepository.get_all(test_db)
    assert len(projects) == 1
```

### 4. Coverage Without Quality

**Bad:** 100% coverage of meaningless tests
```python
def test_function_returns_something():
    assert function() is not None  # Useless assertion
```

**Good:** Meaningful tests of critical paths
```python
def test_function_handles_error_case():
    with pytest.raises(SpecificException):
        function(invalid_input)
```

---

## Test Code Quality Standards

### Must Pass:
- ✅ MyPy strict mode (zero errors)
- ✅ Ruff linting (zero errors)
- ✅ Tests execute successfully
- ✅ Tests actually test production code paths

### Should Have:
- 📝 Clear test names that communicate intent
- 📝 AAA pattern (Arrange-Act-Assert)
- 📝 Comments explaining complex setup
- 📝 Descriptive assertion messages

### Must Not:
- ❌ Test mock behavior instead of actual code
- ❌ Test implementation details
- ❌ Use extensive mocking for integration problems
- ❌ Pass static analysis but fail at runtime

---

## Incremental Testing Workflow

1. **Write Test**
   ```bash
   # Create test file
   touch tests/unit/services/test_my_feature.py
   ```

2. **Run Test**
   ```bash
   # Run just this test file
   uv run pytest tests/unit/services/test_my_feature.py -v
   ```

3. **Check Coverage**
   ```bash
   # Check coverage for specific component
   uv run pytest tests/unit/services/test_my_feature.py \
       --cov=app.services.my_feature \
       --cov-report=term-missing
   ```

4. **Verify Coverage**
   - Look at missing lines in coverage report
   - Add tests for uncovered critical paths
   - Skip low-value edge cases if not critical

5. **Only Then Commit**
   ```bash
   # Run full quality check
   uv run ruff check .
   uv run mypy app/
   uv run pytest --cov=app
   ```

---

## Examples by Component Type

### Service Layer

**Unit test for business logic:**
```python
def test_evm_calculates_cpi_correctly():
    """Test CPI calculation formula."""
    result = calculate_cpi(earned_value=100, actual_cost=90)
    assert result == 1.11  # EV/AC = 100/90
```

**Integration test for database operations:**
```python
@pytest.mark.asyncio
async def test_project_service_creates_project(test_db):
    """Test project creation with actual database."""
    project = await ProjectService.create(
        test_db,
        ProjectCreate(name="Test", code="T001")
    )
    assert project.id is not None
    assert project.name == "Test"
```

### API Layer

**Integration test for endpoint:**
```python
@pytest.mark.asyncio
async def test_create_project_endpoint(client, test_db):
    """Test POST /projects creates project in database."""
    response = await client.post("/api/v1/projects", json={
        "name": "Test",
        "code": "T001"
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Test"
```

### AI Tools

**Smoke test for tool templates:**
```python
def test_crud_template_can_be_imported():
    """Test that CRUD template module exists."""
    from app.ai.tools.templates import crud_template
    assert crud_template is not None

def test_crud_template_has_required_functions():
    """Test that all CRUD functions exist."""
    from app.ai.tools.templates import crud_template
    assert hasattr(crud_template, 'list_projects')
    assert hasattr(crud_template, 'create_project')
```

**Integration test for tool functionality:**
```python
@pytest.mark.asyncio
async def test_list_projects_tool_returns_projects(test_db):
    """Test list_projects tool with actual database."""
    # Create test project
    await ProjectService.create(test_db, ProjectCreate(...))

    # Call tool
    result = await crud_template.list_projects(
        context=ToolContext(session=test_db, ...)
    )

    # Verify actual results
    assert len(result['projects']) >= 1
```

---

## Coverage Targets

**By Component Type:**
- **Business Logic (services):** 80%+
- **API Endpoints:** 70%+ (integration tests cover most)
- **Tool Templates:** 20-40% (smoke tests sufficient)
- **Utility Functions:** 90%+ (pure functions, easy to test)
- **Overall:** 60-70% (realistic target)

**Critical Paths:** 80%+ regardless of component type

**Low Value:**
- Simple getters/setters: 0-50% acceptable
- Configuration code: 0-30% acceptable
- Type definitions: 0% acceptable

---

## References

- **Test Execution Runbook:** `docs/02-architecture/testing/test-execution-runbook.md`
- **ADR-004:** Test Coverage Strategy
- **Project CLAUDE.md:** Quality standards and testing commands

---

**Document Owner:** PDCA ACT Phase 2026-03-15
**Review Schedule:** Quarterly
**Next Review:** 2026-06-15
