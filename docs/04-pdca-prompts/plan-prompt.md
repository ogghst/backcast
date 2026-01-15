# PLAN Phase: Work Decomposition & Success Criteria

## Purpose

Decompose the **approved approach from Analysis phase** into actionable tasks with measurable success criteria, documentation references, and test specifications.

**Prerequisite**: Analysis phase (00-analysis.md) must be completed with an **approved option**.

---

## TDD Workflow (Test-Driven Design)

This plan phase **requires** Test-Driven Design. Tests are written **first** to drive implementation.

### Red-Green-Refactor Cycle

1. **🔴 RED**: Write a failing test that defines desired behavior
   - Test must fail for the **expected reason** (missing code, not existing bugs)
   - Document what behavior this test validates

2. **🟢 GREEN**: Write minimal code to make test pass
   - Implement only what the test requires
   - Resist adding functionality beyond test scope

3. **🔵 REFACTOR**: Improve design while tests stay green
   - Extract methods, rename for clarity
   - Apply patterns (Service, Repository, Command)
   - Run tests after each small change

### Test-First Task Execution

For **each implementation task** in Phase 2:

1. Write test file first (e.g., `tests/unit/services/test_[feature].py`)
2. Run test: confirm it fails with expected error
3. Implement minimal code to pass
4. Refactor for clarity/patterns
5. Run all tests: verify no regressions

**See**: [do-prompt.md](do-prompt.md#red-green-refactor-cycle-protocol) for detailed TDD guidance.

---

## Phase 1: Scope & Success Criteria

### 1.1 Approved Approach Summary

Reference the approved option from analysis:

- **Selected Option**: [Option X from analysis]
- **Architecture**: [Brief description]
- **Key Decisions**: [List critical decisions made]

### 1.2 Success Criteria (Measurable)

Define **testable acceptance criteria**:

**Functional Criteria:**

- [Specific feature behavior] VERIFIED BY: [test type]
- [Edge case handling] VERIFIED BY: [test type]
- [Error condition] VERIFIED BY: [test type]

**Technical Criteria:**

- Performance: [metric] VERIFIED BY: [measurement method]
- Security: [requirement] VERIFIED BY: [test type]
- Code Quality: [standard] VERIFIED BY: [quality gate]

**Business Criteria:**

- [User outcome] VERIFIED BY: [measurement method]
- [Business metric] VERIFIED BY: [measurement method]

**TDD Criteria:**

- [ ] All tests written **before** implementation code VERIFIED BY: Git commit history
- [ ] Tests validate **all acceptance criteria** VERIFIED BY: Test-to-requirement traceability matrix
- [ ] Each test **failed first** (RED phase) VERIFIED BY: Do-prompt daily log
- [ ] Test coverage ≥80% VERIFIED BY: `pytest --cov` report
- [ ] Tests follow Arrange-Act-Assert pattern VERIFIED BY: Code review
- [ ] Fixtures used for shared test setup VERIFIED BY: Reference to [conftest.py](../../../backend/tests/conftest.py)

### 1.3 Scope Boundaries

**In Scope:**

- [Specific features/changes]
- [Components affected]
- [Testing requirements]
- [Documentation updates]

**Out of Scope:**

- [Explicitly list what's NOT done]
- [Items deferred to future iterations]
- [Assumptions requiring validation]

---

## Phase 2: Work Decomposition

### 2.1 Task Breakdown (Test-First)

Break down work into **sequential, atomic tasks** with **test-first subtasks**:

```text
├── Task 1: [Feature Name]
│   ├── Test-First Subtask 1.1: Write test for [behavior]
│   │   ├── File: tests/unit/[test_file].py
│   │   ├── Success: Test fails with expected error
│   │   └── Prerequisite: Fixtures from conftest.py
│   ├── Implementation Subtask 1.2: Implement [behavior]
│   │   ├── Files: [implementation files]
│   │   ├── Dependencies: Test 1.1 written and failing
│   │   ├── Success: Test 1.1 passes, all tests pass
│   │   └── Refactor: Apply [pattern] after tests pass
│   └── Estimated: [complexity: Low/Med/High]
├── Task 2: [Next feature - depends on Task 1]
│   └── [same structure: test first, then implement]
└── Task N: [Feature]
    └── [same structure]
```

**Test-First Task Ordering Principles:**

1. **Tests Before Implementation**: Each task MUST start with test subtask
2. **Database/Models First**: Schema tests before API/service tests
3. **Backend Before Frontend**: API tests written before UI consumes it
4. **Incremental Complexity**: Start with happy path, add edge cases
5. **Interface Design**: Tests drive API/service signatures

### 2.1.1 Test-to-Requirement Traceability

Map each acceptance criterion to specific test cases:

| Acceptance Criterion | Test ID | Test File                    | Expected Behavior |
| -------------------- | ------- | ---------------------------- | ----------------- |
| [AC1 from Phase 1]   | T-001   | tests/unit/[feature]         | [description]     |
| [AC2 from Phase 1]   | T-002   | tests/integration/[feature]  | [description]     |

**Requirements:**

- Each acceptance criterion must have ≥1 test
- Test names clearly indicate which criterion they validate
- Complex criteria require multiple tests (happy path, edge cases, errors)

### 2.2 File Change List

List all files to be created or modified:

| File Path           | Action | Purpose                |
| ------------------- | ------ | ---------------------- |
| `path/to/file.ext`  | Create | [Brief description]    |
| `path/to/other.ext` | Modify | [What changes and why] |

---

## Phase 3: Test Specification (Test-First)

### 3.1 Test Hierarchy (Write in This Order)

```text
├── Unit Tests (write first - drive interface design)
│   ├── Test file structure: tests/unit/[service|model]/test_[name].py
│   ├── Happy path tests (start here)
│   ├── Edge cases and boundaries
│   └── Error handling
├── Integration Tests (write after unit tests pass)
│   ├── Test file structure: tests/integration/[domain]/test_[name].py
│   ├── Database/repository integration
│   └── Service layer integration
└── End-to-End Tests (if applicable - write last)
    └── Critical user flows (tests/e2e/)
```

### 3.2 Test Case Template (First 3-5 Tests)

Document tests **simplest to most complex**, following AAA pattern:

| Test ID | Test Name                                    | Acceptance Criterion | Type | Verification               |
| ------- | -------------------------------------------- | -------------------- | ---- | -------------------------- |
| T-001   | test_[feature]_happy_path_returns_[result]   | [AC from Phase 1]    | Unit | Returns expected [result]   |
| T-002   | test_[feature]_with_[edge_case]_returns_[result] | [AC from Phase 1]    | Unit | Handles [edge case] correct |
| T-003   | test_[feature]_when_[error_condition]_raises_[error] | [AC from Phase 1]    | Unit | Raises [Error] with message |

**Test Naming Convention**: `test_{feature}_{scenario}_{expected_outcome}`

**Example Test Structure (AAA Pattern)**:

```python
@pytest.mark.asyncio
async def test_project_create_with_valid_data_returns_project(db_session: AsyncSession):
    """Test creating a project with valid data.

    Acceptance Criteria:
    - Project created with provided code, name, budget
    - Status defaults to "Active"
    - Created project has valid UUID
    """
    # Arrange
    service = ProjectService(db_session)
    project_in = ProjectCreate(
        code="TEST-001",
        name="Test Project",
        budget=Decimal("10000.00")
    )
    actor_id = uuid4()

    # Act
    result = await service.create_project(project_in, actor_id)

    # Assert
    assert result.code == "TEST-001"
    assert result.name == "Test Project"
    assert result.status == "Active"
    assert result.project_id is not None
```

### 3.3 Test Infrastructure

**Framework**: pytest with pytest-asyncio (strict mode)

**Required Fixtures** (from `backend/tests/conftest.py`):

- `db_session` - Async database session with transaction rollback
- `db_engine` - Async engine for test DB
- `client` - Async HTTP client for API tests

**Custom Fixtures Needed** (list domain-specific fixtures):

```python
# Example: Add to conftest.py
@pytest.fixture
async def sample_project(db_session: AsyncSession) -> Project:
    """Create a sample project for tests."""
    # Implementation
```

**Mock/Stub Requirements**:

- External APIs: [list if needed]
- Time-dependent logic: Use `control_date` parameter (project pattern)
- Database state: Use fresh `db_session` per test

### 3.4 TDD Validation Checklist

Before implementation:

- [ ] Test file created following naming convention
- [ ] Test written with AAA structure (Arrange-Act-Assert)
- [ ] Test runs and fails with **expected error** (not pre-existing bug)
- [ ] Test failure reason documented in do-prompt log
- [ ] Test name clearly describes expected behavior

After implementation:

- [ ] New test passes
- [ ] All existing tests still pass (no regressions)
- [ ] Coverage report shows ≥80% (or 100% for critical paths)
- [ ] Code passes mypy strict and ruff checks

---

## Phase 4: Risk Assessment

### 4.1 Risks and Mitigations

| Risk Type   | Description     | Probability  | Impact       | Mitigation Strategy   |
| ----------- | --------------- | ------------ | ------------ | --------------------- |
| Technical   | [specific risk] | Low/Med/High | Low/Med/High | [concrete mitigation] |
| Integration | [specific risk] | Low/Med/High | Low/Med/High | [concrete mitigation] |
| Schedule    | [specific risk] | Low/Med/High | Low/Med/High | [concrete mitigation] |

---

## Phase 5: Documentation References

### 5.1 Required Documentation

Link to relevant docs for implementation:

**Architecture & Standards:**

- Coding Standards: `docs/02-architecture/coding-standards.md`
- [Relevant ADRs]: `docs/02-architecture/decisions/...`
- [Bounded Context]: `docs/02-architecture/01-bounded-contexts.md`

**Domain & Requirements:**

- [User Stories]: `docs/01-product-scope/...`
- [Functional Specs]: `docs/01-product-scope/...`

**Project Context:**

- Current Iteration: `docs/03-project-plan/current-iteration.md`
- Related Iterations: [links]

### 5.2 Code References

**Existing Patterns to Follow:**

- Backend: [link to similar implementation]
- Frontend: [link to similar component]
- Tests: [link to test pattern reference]

**Database Schema:**

- Relevant tables: [table names]
- Relationships: [describe]
- Indexes: [list if needed]

---

## Phase 6: Prerequisites & Dependencies

### 6.1 Technical Prerequisites

- [ ] Database migrations applied
- [ ] Dependencies installed
- [ ] Environment configured
- [ ] External services available

### 6.2 Documentation Prerequisites

- [ ] Analysis phase approved
- [ ] Architecture docs reviewed
- [ ] Related ADRs understood

---

## Output Template

```markdown
# Plan: [Request Title]

**Created:** [Date]
**Based on:** [Link to 00-analysis.md]
**Approved Option:** [Option X]

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: [Option X from analysis]
- **Architecture**: [Brief description]
- **Key Decisions**: [List critical decisions made]

### Success Criteria

**Functional Criteria:**

- [Specific feature behavior] VERIFIED BY: [test type]
- [Edge case handling] VERIFIED BY: [test type]
- [Error condition] VERIFIED BY: [test type]

**Technical Criteria:**

- Performance: [metric] VERIFIED BY: [measurement method]
- Security: [requirement] VERIFIED BY: [test type]
- Code Quality: [standard] VERIFIED BY: [quality gate]

**Business Criteria:**

- [User outcome] VERIFIED BY: [measurement method]

### Scope Boundaries

**In Scope:**

- [List]

**Out of Scope:**

- [List]

---

## Work Decomposition

### Task Breakdown

| Task | Description | Files  | Dependencies  | Success  | Est. Complexity |
| ---- | ----------- | ------ | ------------- | -------- | --------------- |
| 1    | [desc]      | [list] | [none/task X] | [verify] | Low/Med/High    |
| 2    | [desc]      | [list] | [task 1]      | [verify] | Low/Med/High    |
| 3    | [desc]      | [list] | [task 2]      | [verify] | Low/Med/High    |

---

## Test Specification

### Test Hierarchy
```

├── Unit Tests
│ ├── [test areas]
├── Integration Tests
│ ├── [test areas]
└── E2E Tests (if applicable)
└── [critical flows]

```

### Test Cases

| Test ID | Description | Type | Verification |
| ------- | ----------- | ---- | ------------ |
| T-001   | [desc]      | Unit | [expected]   |
| T-002   | [desc]      | Int  | [expected]   |
| T-003   | [desc]      | Unit | [expected]   |

### Test Infrastructure

- **Test Framework**: [framework]
- **Fixtures Needed**: [list]
- **Mock Requirements**: [list]

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --------- | ----------- | ----------- | ------ | ---------- |
| Technical | [desc]      | Low/Med/High| Low/Med/High| [strategy] |
| Integration| [desc]     | Low/Med/High| Low/Med/High| [strategy] |

---

## Documentation References

### Required Documentation

**Architecture & Standards:**
- Coding Standards: `docs/02-architecture/coding-standards.md`
- [Relevant ADR]: `docs/02-architecture/decisions/...`

**Domain & Requirements:**
- [User Story]: `docs/01-product-scope/...`

**Project Context:**
- Current Iteration: `docs/03-project-plan/current-iteration.md`

### Code References

**Existing Patterns:**
- Backend: [link to similar implementation]
- Frontend: [link to similar component]

**Database Schema:**
- Tables: [list]
- Relationships: [describe]

---

## Prerequisites & Dependencies

### Technical Prerequisites

- [ ] [Prerequisite 1]
- [ ] [Prerequisite 2]

### Documentation Prerequisites

- [x] Analysis phase approved

```

---

## TDD Quick Reference

### Test-First Command Sequence

```bash
# 1. Create test file
touch backend/tests/unit/services/test_[feature].py

# 2. Write test (AAA pattern)
# Edit: test_[feature]_[scenario]_[expected]()

# 3. Run test - confirm FAILS
uv run pytest tests/unit/services/test_[feature].py::test_[name] -v

# 4. Implement minimal code

# 5. Run test - confirm PASSES
uv run pytest tests/unit/services/test_[feature].py::test_[name] -v

# 6. Refactor

# 7. Run all tests
uv run pytest tests/unit/ -v

# 8. Run coverage
uv run pytest tests/unit/ --cov=app
```

### Common Test Patterns

**Service Pattern**:

```python
@pytest.mark.asyncio
async def test_[service]_[method]_with_[input]_returns_[expected](db_session: AsyncSession):
    # Arrange
    service = [Service](db_session)
    input_data = [Input](...)

    # Act
    result = await service.[method](input_data)

    # Assert
    assert result.[field] == [expected_value]
```

**API Test Pattern**:

```python
@pytest.mark.asyncio
async def test_[endpoint]_with_[auth]_returns_[status](client: AsyncClient):
    # Arrange
    headers = {"Authorization": f"Bearer {token}"}

    # Act
    response = await client.post("/api/v1/[resource]", json={...}, headers=headers)

    # Assert
    assert response.status_code == [expected_status]
    assert response.json()["[field]"] == [expected_value]
```

---

## Output File

Create file: `docs/03-project-plan/iterations/YYYY-MM-DD-{title}/01-plan.md`

**Location**: Same folder as `00-analysis.md`

---

## Key Principles

1. **Test-Driven**: Tests written **before** implementation (RED-GREEN-REFACTOR)
2. **Measurable**: Success criteria objectively verifiable via test execution
3. **Sequential**: Tasks ordered with clear dependencies; tests before code
4. **Actionable**: Each task clear and executable with TDD subtasks
5. **Reference-Rich**: Link to existing patterns, fixtures, and documentation
6. **Interface Design**: Tests drive API/service signatures (not pre-designed)
