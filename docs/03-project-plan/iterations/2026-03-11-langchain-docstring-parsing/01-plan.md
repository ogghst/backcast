# Plan: LangChain Docstring Parsing for AI Tool Parameter Descriptions

**Created:** 2026-03-11
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option A — RBACToolNode with Reusable RBAC Decorator

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option A — RBACToolNode with Reusable RBAC Decorator
- **Architecture**: Refactor `@ai_tool` decorator to compose with LangChain's `@tool(parse_docstring=True)`, centralize RBAC via `RBACToolNode` subclass, and extract reusable `@require_permission` decorator
- **Key Decisions**:
  - Use LangChain's native `parse_docstring=True` for automatic parameter descriptions
  - Use `InjectedToolArg` to hide `context: ToolContext` from LLM schema
  - Implement `RBACToolNode` as ToolNode subclass for permission checks
  - Create reusable `@require_permission` decorator for AI tools and API routes
  - Add `user_role` field to `ToolContext` for RBAC resolution

### Success Criteria

**Functional Criteria:**

- [ ] Tool schemas auto-generate parameter descriptions from Google-style docstrings VERIFIED BY: `test_docstring_parsing` unit test
- [ ] `context: ToolContext` parameter excluded from tool schemas (injected at runtime) VERIFIED BY: `test_injected_tool_arg_exclusion` unit test
- [ ] RBACToolNode denies tool execution when user lacks required permissions VERIFIED BY: `test_rbac_tool_node_permission_denied` integration test
- [ ] RBACToolNode allows tool execution when user has required permissions VERIFIED BY: `test_rbac_tool_node_permission_granted` integration test
- [ ] `@require_permission` decorator raises `PermissionError` for unauthorized roles VERIFIED BY: `test_require_permission_decorator` unit test
- [ ] All existing tools continue to work without modification VERIFIED BY: existing test suite passes

**Technical Criteria:**

- [ ] Code Quality: MyPy strict mode (zero errors) VERIFIED BY: `mypy app/ai/tools/ app/core/rbac.py --strict`
- [ ] Code Quality: Ruff linting (zero errors) VERIFIED BY: `ruff check app/ai/tools/ app/core/rbac.py`
- [ ] Test Coverage: ≥80% coverage for new code VERIFIED BY: `pytest --cov=app.ai.tools --cov=app.core.rbac`
- [ ] Type Safety: No `Any` types (`disallow_any_explicit = True`) VERIFIED BY: MyPy strict mode check
- [ ] Docstring Compliance: All tools follow Google-style docstring format VERIFIED BY: manual code review

**Business Criteria:**

- [ ] Reduced maintenance burden by eliminating dual tool system VERIFIED BY: deprecation of `__init__.py` Pydantic schema tools
- [ ] Reusable RBAC decorator shared between AI tools and API routes VERIFIED BY: `@require_permission` used in both contexts
- [ ] Alignment with LangGraph 1.0 best practices VERIFIED BY: compliance with LangChain tool patterns

### Scope Boundaries

**In Scope:**

- Refactor `@ai_tool` decorator to compose with `@tool(parse_docstring=True)`
- Add `@require_permission` decorator to `app/core/rbac.py`
- Create `RBACToolNode` subclass in `app/ai/tools/rbac_tool_node.py`
- Add `user_role` field to `ToolContext` in `app/ai/tools/types.py`
- Update `app/ai/tools/project_tools.py` to use `InjectedToolArg` and Google-style docstrings
- Deprecate Pydantic schema tools in `app/ai/tools/__init__.py`
- Update `app/ai/graph.py` to use `RBACToolNode`
- Update `app/ai/agent_service.py` to pass `user_role` to `ToolContext`
- Simplify `app/ai/tools/registry.py` to remove schema conversion logic
- Write comprehensive unit and integration tests for new functionality

**Out of Scope:**

- Migration of all 22 planned tools from templates (only `project_tools.py` updated as example)
- Frontend changes (no UI modifications required)
- RBAC permission model changes (no new permissions defined)
- Database schema changes (no migrations required)
- API route changes (only decorator made available for future use)
- Performance optimization (baseline performance maintained, not optimized)

---

## Work Decomposition

### Task Breakdown

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | --- | --- | --- | --- | --- |
| 1 | Add `@require_permission` decorator to RBAC module | `app/core/rbac.py` | None | Decorator attaches `_required_permissions` metadata, resolves `user_role` from `context` or `current_user`, calls `RBACServiceABC.has_permission()`, raises `PermissionError` if denied | Medium |
| 2 | Add `user_role` field to `ToolContext` | `app/ai/tools/types.py` | None | `ToolContext` dataclass includes `user_role: str` field with Google-style docstring | Low |
| 3 | Create `RBACToolNode` subclass | `app/ai/tools/rbac_tool_node.py` | Task 1, Task 2 | Class extends `ToolNode`, stores `context`, implements `_check_tool_permission()` that reads `_tool_metadata.permissions`, calls `RBACServiceABC.has_permission()`, returns `None` if granted, error message if denied | Medium |
| 4 | Refactor `@ai_tool` decorator to compose with LangChain | `app/ai/tools/decorator.py` | Task 1 | Decorator applies `langchain_tool(parse_docstring=True)(func)`, attaches `ToolMetadata` with permissions, sets `_is_ai_tool` flag, returns `BaseTool` instance | Medium |
| 5 | Update `project_tools.py` with `InjectedToolArg` and docstrings | `app/ai/tools/project_tools.py` | Task 4 | Tools use `Annotated[ToolContext, InjectedToolArg]`, follow Google-style docstring format (Context, Args, Returns, Raises), maintain backward compatibility | Low |
| 6 | Update `agent_service.py` to pass `user_role` | `app/ai/agent_service.py` | Task 2 | `ToolContext` initialization includes `user_role=user.role` parameter | Low |
| 7 | Update `graph.py` to use `RBACToolNode` | `app/ai/graph.py` | Task 3 | `create_graph()` function uses `RBACToolNode(tools, context)` instead of `ToolNode(tools)` | Low |
| 8 | Deprecate Pydantic schema tools in `__init__.py` | `app/ai/tools/__init__.py` | Task 4 | `create_project_tools()` function updated to use `@ai_tool` decorated functions, old Pydantic schema code marked as deprecated | Low |
| 9 | Simplify `registry.py` | `app/ai/tools/registry.py` | Task 4 | `as_langchain_tools()` simplified since tools are already `BaseTool` instances | Low |
| 10 | Write unit tests for `@require_permission` decorator | `tests/unit/core/test_rbac.py` (NEW) | Task 1 | Tests verify metadata attachment, permission check logic, error raising for unauthorized roles, `user_role` resolution from `context` and `current_user` | Medium |
| 11 | Write unit tests for `RBACToolNode` | `tests/unit/ai/tools/test_rbac_tool_node.py` (NEW) | Task 3 | Tests verify permission check flow, success path with valid permissions, error path with invalid permissions, tool metadata reading | Medium |
| 12 | Write unit tests for refactored `@ai_tool` decorator | `tests/unit/ai/tools/test_decorator.py` (NEW) | Task 4 | Tests verify `parse_docstring=True` composition, `InjectedToolArg` support, `ToolMetadata` attachment, `_is_ai_tool` flag, schema generation from docstrings | Medium |
| 13 | Write integration test for docstring parsing | `tests/integration/ai/tools/test_docstring_parsing.py` (NEW) | Task 4, Task 5 | Test verifies tool schema includes parameter descriptions from Google-style docstrings | Medium |
| 14 | Write integration test for `InjectedToolArg` exclusion | `tests/integration/ai/tools/test_injected_tool_arg.py` (NEW) | Task 4, Task 5 | Test verifies `context` parameter excluded from tool schema but injected at runtime | Medium |
| 15 | Write integration test for `RBACToolNode` permission denied | `tests/security/ai/test_rbac_tool_node.py` (NEW) | Task 3, Task 4, Task 5 | Test verifies `RBACToolNode` returns error `ToolMessage` when user lacks required permissions | Medium |
| 16 | Write integration test for `RBACToolNode` permission granted | `tests/security/ai/test_rbac_tool_node.py` (NEW) | Task 3, Task 4, Task 5 | Test verifies `RBACToolNode` allows execution when user has required permissions | Medium |
| 17 | Run existing test suite and verify backward compatibility | All tests | Task 1-9 | All existing tests pass without modification: `pytest tests/integration/ai/tools/ tests/security/ai/test_tool_rbac.py -v` | Low |
| 18 | Run MyPy strict mode and fix type errors | All changed files | Task 1-9 | `mypy app/ai/tools/ app/core/rbac.py --strict` returns zero errors | Low |
| 19 | Run Ruff and fix linting errors | All changed files | Task 1-9 | `ruff check app/ai/tools/ app/core/rbac.py` returns zero errors | Low |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| --- | --- | --- | --- |
| Tool schemas auto-generate parameter descriptions from docstrings | T-001 | `tests/integration/ai/tools/test_docstring_parsing.py` | Tool schema `args_schema` fields contain descriptions extracted from Google-style docstring Args sections |
| `context` parameter excluded from tool schemas | T-002 | `tests/integration/ai/tools/test_injected_tool_arg.py` | Tool schema `args_schema` does NOT include `context` field; `context` successfully injected at runtime via `InjectedToolArg` |
| RBACToolNode denies execution when permission denied | T-003 | `tests/security/ai/test_rbac_tool_node.py` | `RBACToolNode._check_tool_permission()` returns error message string when user lacks required permission |
| RBACToolNode allows execution when permission granted | T-004 | `tests/security/ai/test_rbac_tool_node.py` | `RBACToolNode._check_tool_permission()` returns `None` when user has required permission; tool executes successfully |
| `@require_permission` raises `PermissionError` for unauthorized roles | T-005 | `tests/unit/core/test_rbac.py` | Decorated function raises `PermissionError` with message "Permission denied: {permission} required" when user lacks permission |
| All existing tools continue to work | T-006 | Existing test suite | All tests in `tests/integration/ai/tools/` and `tests/security/ai/test_tool_rbac.py` pass without modification |
| MyPy strict mode compliance | T-007 | MyPy type check | `mypy app/ai/tools/ app/core/rbac.py --strict` returns zero errors, no `Any` types used |
| Ruff linting compliance | T-008 | Ruff lint check | `ruff check app/ai/tools/ app/core/rbac.py` returns zero errors |

---

## Test Specification

### Test Hierarchy

```
tests/
├── unit/
│   ├── core/
│   │   └── test_rbac.py (NEW) — @require_permission decorator tests
│   └── ai/
│       └── tools/
│           ├── test_decorator.py (NEW) — refactored @ai_tool tests
│           └── test_rbac_tool_node.py (NEW) — RBACToolNode unit tests
├── integration/
│   └── ai/
│       └── tools/
│           ├── test_docstring_parsing.py (NEW) — schema generation from docstrings
│           └── test_injected_tool_arg.py (NEW) — context exclusion from schema
├── security/
│   └── ai/
│       └── test_rbac_tool_node.py (NEW) — RBACToolNode permission tests
└── (existing tests remain unchanged)
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Verification |
| --- | --- | --- | --- | --- |
| T-001 | `test_docstring_parsing_generates_parameter_descriptions` | AC: Tool schemas auto-generate parameter descriptions | Integration | Tool schema `args_schema.fields["search"].description` matches docstring Args section |
| T-002 | `test_injected_tool_arg_excluded_from_schema` | AC: context parameter excluded from schemas | Integration | `context` not in `tool.args_schema.fields`; tool executes with context injected |
| T-003 | `test_rbac_tool_node_permission_denied_returns_error` | AC: RBACToolNode denies unauthorized access | Integration | `RBACToolNode._check_tool_permission()` returns error message string; tool execution blocked |
| T-004 | `test_rbac_tool_node_permission_granted_allows_execution` | AC: RBACToolNode allows authorized access | Integration | `RBACToolNode._check_tool_permission()` returns `None`; tool executes successfully |
| T-005 | `test_require_permission_decorator_raises_for_unauthorized` | AC: @require_permission raises PermissionError | Unit | Decorated function raises `PermissionError` when `user_role` lacks permission |
| T-006 | `test_require_permission_decorator_resolves_user_role_from_context` | AC: @require_permission resolves user_role | Unit | Decorator successfully reads `user_role` from `context` parameter when provided |
| T-007 | `test_require_permission_decorator_resolves_user_role_from_current_user` | AC: @require_permission resolves user_role | Unit | Decorator successfully reads `user_role` from `current_user` parameter when provided |
| T-008 | `test_ai_tool_decorator_attaches_tool_metadata` | AC: @ai_tool attaches metadata | Unit | Decorated tool has `_tool_metadata` attribute with correct permissions and category |
| T-009 | `test_ai_tool_decorator_sets_is_ai_tool_flag` | AC: @ai_tool sets flag | Unit | Decorated tool has `_is_ai_tool` attribute set to `True` |
| T-010 | `test_ai_tool_decorator_composes_with_langchain_tool` | AC: @ai_tool composes with LangChain | Unit | Decorated tool is instance of `BaseTool` from `langchain_core.tools` |
| T-011 | `test_tool_context_includes_user_role_field` | AC: ToolContext includes user_role | Unit | `ToolContext` dataclass has `user_role: str` field with correct type annotation |
| T-012 | `test_backward_compat_existing_tools_work` | AC: All existing tools continue to work | Integration | Existing test suite passes without modification |

### Test Infrastructure Needs

**Fixtures needed:**

- `mock_rbac_service()` — Mock `RBACServiceABC` with configurable role/permission mappings (in `conftest.py`)
- `tool_context()` — Factory for creating `ToolContext` instances with test session and user (in `conftest.py`)
- `sample_langchain_tool()` — Factory for creating sample LangChain tool with `InjectedToolArg` (in test files)

**Mocks/stubs:**

- `RBACServiceABC.has_permission()` — Mock to return `True`/`False` based on test scenario
- `AsyncSession` — Use `pytest-asyncio` with in-memory database or mock session
- LangChain `ToolNode` — Mock parent class methods to isolate `RBACToolNode` behavior

**Database state:**

- Minimal seed data required (use fixtures for project/service creation)
- Most tests use mocked services to avoid database dependencies

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| Technical | LangGraph version incompatibility with `parse_docstring=True` | Low | High | Verify LangChain version before starting; test in isolation first |
| Technical | MyPy strict mode errors with LangChain types (extensive use of `Any`) | Medium | Medium | Use `type: ignore` sparingly with explanatory comments; prioritize strict typing in our code |
| Integration | Existing tools break due to signature changes | Medium | High | Maintain backward compatibility in decorator; run existing tests early and often |
| Integration | `InjectedToolArg` not compatible with LangGraph StateGraph | Low | High | Test `RBACToolNode` integration with `StateGraph` early in Task 7 |
| Process | TDD cycle overhead increases implementation time | High | Low | Focus on critical test coverage first; refactor tests in CHECK phase if needed |
| Process | Task dependencies block parallel execution | Medium | Low | Frontend-independent tasks allow backend focus; no critical path issues |

**Risk Mitigation Strategy:**

1. **Start with Task 1-3 (RBAC foundation)**: Prove `@require_permission` and `RBACToolNode` work in isolation before integrating
2. **Test-First for Critical Path**: Write tests for Tasks 10-16 alongside implementation to catch issues early
3. **Incremental Integration**: Update one tool function at a time (Task 5) to validate pattern before applying to all tools
4. **Continuous Quality Gates**: Run MyPy and Ruff after each task to prevent type/lint debt accumulation

---

## Documentation References

### Required Reading

- **Coding Standards**: `docs/02-architecture/backend/coding-standards.md` — Google-style docstrings, MyPy strict mode, Ruff configuration
- **LangGraph 1.0 Documentation**: [LangChain Tools Guide](https://docs.langchain.com/oss/python/langchain/tools) — `@tool`, `parse_docstring`, `InjectedToolArg`, `ToolNode`
- **Analysis Phase**: `docs/03-project-plan/iterations/2026-03-11-langchain-docstring-parsing/00-analysis.md` — Detailed requirements and design decisions

### Code References

- **Current decorator pattern**: `backend/app/ai/tools/decorator.py` — Existing `@ai_tool` implementation
- **Current RBAC service**: `backend/app/core/rbac.py` — `RBACServiceABC`, `JsonRBACService`, `get_rbac_service()`
- **Current tool context**: `backend/app/ai/tools/types.py` — `ToolContext`, `ToolMetadata`
- **Current tools example**: `backend/app/ai/tools/project_tools.py` — Sample tool implementations
- **Existing RBAC tests**: `backend/tests/security/ai/test_tool_rbac.py` — Test patterns for permission checks
- **Existing tool tests**: `backend/tests/integration/ai/tools/test_project_tools.py` — Integration test patterns

---

## Prerequisites

### Technical

- [x] Python 3.12+ environment
- [x] LangChain and LangGraph dependencies installed
- [x] PostgreSQL database available for integration tests
- [x] `pytest-asyncio` configured for async test support
- [ ] Verify LangChain version supports `parse_docstring=True` and `InjectedToolArg`:
  ```bash
  cd backend && python -c "from langchain_core.tools import tool, InjectedToolArg; print('OK')"
  ```

### Documentation

- [x] Analysis phase approved (Option A selected)
- [ ] Review LangGraph 1.0 tool patterns (see References above)
- [ ] Review backend coding standards (Google-style docstrings)

---

## Task Dependency Graph

```yaml
# Task Dependency Graph for PDCA DO Phase
tasks:
  - id: BE-001
    name: "Add @require_permission decorator to RBAC module"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Add user_role field to ToolContext"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-003
    name: "Create RBACToolNode subclass"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002]

  - id: BE-004
    name: "Refactor @ai_tool decorator to compose with LangChain"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-005
    name: "Update project_tools.py with InjectedToolArg and docstrings"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: BE-006
    name: "Update agent_service.py to pass user_role"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-007
    name: "Update graph.py to use RBACToolNode"
    agent: pdca-backend-do-executor
    dependencies: [BE-003]

  - id: BE-008
    name: "Deprecate Pydantic schema tools in __init__.py"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: BE-009
    name: "Simplify registry.py"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: TEST-001
    name: "Write unit tests for @require_permission decorator"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]
    kind: test

  - id: TEST-002
    name: "Write unit tests for RBACToolNode"
    agent: pdca-backend-do-executor
    dependencies: [BE-003]
    kind: test

  - id: TEST-003
    name: "Write unit tests for refactored @ai_tool decorator"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]
    kind: test

  - id: TEST-004
    name: "Write integration test for docstring parsing"
    agent: pdca-backend-do-executor
    dependencies: [BE-004, BE-005]
    kind: test

  - id: TEST-005
    name: "Write integration test for InjectedToolArg exclusion"
    agent: pdca-backend-do-executor
    dependencies: [BE-004, BE-005]
    kind: test

  - id: TEST-006
    name: "Write integration test for RBACToolNode permission denied"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-004, BE-005]
    kind: test

  - id: TEST-007
    name: "Write integration test for RBACToolNode permission granted"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-004, BE-005]
    kind: test

  - id: TEST-008
    name: "Run existing test suite and verify backward compatibility"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002, BE-003, BE-004, BE-005, BE-006, BE-007, BE-008, BE-009]
    kind: test

  - id: QA-001
    name: "Run MyPy strict mode and fix type errors"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002, BE-003, BE-004, BE-005, BE-006, BE-007, BE-008, BE-009]

  - id: QA-002
    name: "Run Ruff and fix linting errors"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002, BE-003, BE-004, BE-005, BE-006, BE-007, BE-008, BE-009]
```

### Dependency Graph Explanation

**Level 0 (Can run in parallel):**
- BE-001: `@require_permission` decorator (foundational RBAC)
- BE-002: `ToolContext.user_role` field (data model change)

**Level 1:**
- BE-003: `RBACToolNode` (depends on BE-001 for decorator, BE-002 for context)
- BE-004: Refactored `@ai_tool` decorator (depends on BE-001 for RBAC integration)

**Level 2:**
- BE-005: Update `project_tools.py` (depends on BE-004 for new decorator pattern)
- BE-008: Deprecate Pydantic schemas (depends on BE-004 for new pattern)
- BE-009: Simplify registry (depends on BE-004 for new pattern)

**Level 3:**
- BE-006: Update `agent_service.py` (depends on BE-002 for `user_role`)
- BE-007: Update `graph.py` (depends on BE-003 for `RBACToolNode`)

**Test Tasks (depend on implementation tasks):**
- TEST-001 to TEST-007: Each test depends on its corresponding implementation task(s)
- TEST-008: Full suite runs after all implementation complete

**Quality Tasks (final gates):**
- QA-001, QA-002: Run after all implementation complete

**Note**: Tests marked with `kind: test` should be executed sequentially within each agent to avoid database conflicts.

---

## Success Metrics Summary

### Functional Metrics

| Metric | Target | Measurement Method |
| --- | --- | --- |
| Docstring parsing accuracy | 100% of parameters have descriptions | Test T-001 verifies schema field descriptions |
| Context exclusion from schema | 100% of tools hide context | Test T-002 verifies context not in schema |
| RBAC denial accuracy | 100% of unauthorized requests denied | Test T-003 verifies error returned |
| RBAC grant accuracy | 100% of authorized requests allowed | Test T-004 verifies execution succeeds |
| Decorator error raising | 100% of unauthorized calls raise PermissionError | Test T-005 verifies exception raised |
| Backward compatibility | 100% of existing tests pass | Test T-006 runs existing suite |

### Technical Metrics

| Metric | Target | Measurement Method |
| --- | --- | --- |
| MyPy strict compliance | 0 errors | `mypy app/ai/tools/ app/core/rbac.py --strict` |
| Ruff linting compliance | 0 errors | `ruff check app/ai/tools/ app/core/rbac.py` |
| Test coverage (new code) | ≥80% | `pytest --cov=app.ai.tools --cov=app.core.rbac` |
| Type safety | 0 `Any` types | Manual code review + MyPy check |

### Business Metrics

| Metric | Target | Measurement Method |
| --- | --- | --- |
| Dual tool system elimination | 1 tool pattern remains | Code review: only `@ai_tool` used |
| Reusable RBAC decorator | Used in 2+ contexts | Code review: AI tools + API routes |
| LangGraph 1.0 alignment | 100% compliance | Code review against LangChain docs |

---

## Key Principles

1. **Define WHAT, not HOW**: This plan specifies test specifications and success criteria, not implementation code. DO phase will handle actual code.
2. **Measurable**: Every success criterion is objectively verifiable through automated tests or quality checks.
3. **Sequential**: Tasks are ordered with clear dependencies to enable incremental validation.
4. **Traceable**: Each requirement maps to specific test specifications with unique test IDs.
5. **Actionable**: Each task is clear enough for DO phase execution with defined acceptance criteria.

> **Note**: This plan drives the DO phase. Tests are **specified** here but **implemented** in DO following RED-GREEN-REFACTOR. The task dependency graph enables parallel execution of independent tasks by multiple backend agents.
