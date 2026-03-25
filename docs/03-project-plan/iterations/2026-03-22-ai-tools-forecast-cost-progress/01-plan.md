# Plan: AI Tools for Forecast, Cost Registration, and Progress Entry

**Created:** 2026-03-22
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 - Single Comprehensive Template

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 - Single Comprehensive Template (`forecast_cost_progress_template.py`)
- **Architecture**: Create a single template file containing 13 AI tools organized by service layer (4 Forecast + 5 Cost Registration + 3 Progress Entry + 1 Summary)
- **Key Decisions**:
  - Separate tool for "compare forecast to budget" (clearer LLM intent matching)
  - All tools use temporal logging for consistency (even non-branchable entities)
  - Error handling returns error dictionaries (matches existing 45+ tools)
  - Single-record operations only (no bulk operations in this iteration)
  - Summary tool focuses on cost element details only (WBE aggregates deferred)

### Success Criteria

**Functional Criteria:**

- [ ] All 13 tools are discoverable via OpenAPI and executable by LangGraph agents VERIFIED BY: Integration test listing all tools
- [ ] Forecast tools (get, create, update, compare-to-budget) successfully wrap ForecastService methods VERIFIED BY: Unit tests for each tool
- [ ] Cost Registration tools (budget-status, create, list, trends, cumulative) successfully wrap CostRegistrationService methods VERIFIED BY: Unit tests for each tool
- [ ] Progress Entry tools (get-latest, create, history) successfully wrap ProgressEntryService methods VERIFIED BY: Unit tests for each tool
- [ ] Summary tool aggregates data from all three services for comprehensive cost element view VERIFIED BY: Integration test with real data
- [ ] Temporal context is logged for all tools (observability) VERIFIED BY: Log output analysis in tests
- [ ] Temporal metadata is included in all tool results VERIFIED BY: Result dictionary validation
- [ ] Error conditions return properly formatted error dictionaries VERIFIED BY: Unit tests for error paths

**Technical Criteria:**

- [ ] Code Quality: MyPy strict mode (zero errors) VERIFIED BY: `uv run mypy app/ai/tools/templates/forecast_cost_progress_template.py`
- [ ] Code Quality: Ruff linting (zero errors) VERIFIED BY: `uv run ruff check app/ai/tools/templates/forecast_cost_progress_template.py`
- [ ] All tools are properly registered in `__init__.py` VERIFIED BY: Count of tools in `create_project_tools()` output
- [ ] Tool decorators include correct permissions VERIFIED BY: Audit of decorator parameters
- [ ] Tool descriptions are AI-friendly (clear intent for LLMs) VERIFIED BY: Review of decorator descriptions

**Business Criteria:**

- [ ] Natural language queries about forecasts, costs, and progress are answered correctly VERIFIED BY: Manual testing with sample queries
- [ ] AI can provide comprehensive cost element summaries including all three data types VERIFIED BY: Integration test with realistic scenario
- [ ] Audit trail is maintained via temporal logging for all tool executions VERIFIED BY: Log inspection

### Scope Boundaries

**In Scope:**

- 13 AI tools wrapping existing service methods
- Tool registration in `__init__.py`
- Temporal logging for all tools
- Error handling with error dictionaries
- Unit tests for all tools
- Integration tests for tool discovery and execution

**Out of Scope:**

- Bulk operations (e.g., create multiple cost registrations at once)
- WBE-level aggregation in summary tool (cost element level only)
- Frontend changes (tools are discovered dynamically)
- Service layer modifications (tools wrap existing methods only)
- Additional forecasting methods beyond what's in ForecastService
- Historical accuracy tracking for forecasts

---

## Work Decomposition

### Task Breakdown

| #   | Task                                                                 | Files                                                                          | Dependencies | Success Criteria                                                                                                                                                         | Complexity |
| --- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- |
| 1   | Create forecast_cost_progress_template.py with Forecast tools        | `backend/app/ai/tools/templates/forecast_cost_progress_template.py`            | None         | 4 Forecast tools implemented with temporal logging, proper decorators, and error handling                                                                                | Medium     |
| 2   | Add Cost Registration tools to template                              | `backend/app/ai/tools/templates/forecast_cost_progress_template.py`            | Task 1       | 5 Cost Registration tools implemented with temporal logging, proper decorators, and error handling                                                                       | Medium     |
| 3   | Add Progress Entry tools to template                                  | `backend/app/ai/tools/templates/forecast_cost_progress_template.py`            | Task 2       | 3 Progress Entry tools implemented with temporal logging, proper decorators, and error handling                                                                          | Medium     |
| 4   | Implement Summary tool                                               | `backend/app/ai/tools/templates/forecast_cost_progress_template.py`            | Task 3       | 1 Summary tool that aggregates data from all three services for comprehensive cost element view                                                                         | High       |
| 5   | Register tools in __init__.py                                        | `backend/app/ai/tools/__init__.py`                                             | Task 4       | All 13 tools imported and added to `create_project_tools()` list                                                                                                        | Low        |
| 6   | Write unit tests for Forecast tools                                  | `backend/tests/unit/ai/tools/test_forecast_cost_progress_template.py`         | Task 1       | Tests for get_forecast, create_forecast, update_forecast, compare_forecast_to_budget covering happy path, edge cases, and error conditions                               | Medium     |
| 7   | Write unit tests for Cost Registration tools                         | `backend/tests/unit/ai/tools/test_forecast_cost_progress_template.py`         | Task 2       | Tests for get_budget_status, create_cost_registration, list_cost_registrations, get_cost_trends, get_cumulative_costs covering happy path, edge cases, and error conditions | Medium     |
| 8   | Write unit tests for Progress Entry tools                            | `backend/tests/unit/ai/tools/test_forecast_cost_progress_template.py`         | Task 3       | Tests for get_latest_progress, create_progress_entry, get_progress_history covering happy path, edge cases, and error conditions                                          | Medium     |
| 9   | Write unit tests for Summary tool                                    | `backend/tests/unit/ai/tools/test_forecast_cost_progress_template.py`         | Task 4       | Tests for get_cost_element_summary covering happy path, edge cases (missing data), and error conditions                                                                   | Medium     |
| 10  | Write integration test for tool discovery and execution              | `backend/tests/integration/ai/test_forecast_cost_progress_tools.py`           | Task 9       | Test verifies all 13 tools are discoverable, properly decorated, and executable through LangGraph                                                                        | High       |
| 11  | Run quality checks (MyPy, Ruff)                                      | N/A                                                                            | Task 10      | Zero MyPy errors, zero Ruff errors, 80%+ test coverage                                                                                                                  | Low        |

**Task Execution Flow:**
1. Tasks 1-4: Implement tools sequentially (Forecast → Cost Registration → Progress Entry → Summary)
2. Task 5: Register all tools after implementation complete
3. Tasks 6-9: Write unit tests (can run in parallel after corresponding implementation task)
4. Task 10: Integration test after all unit tests pass
5. Task 11: Quality gate before completion

### Test-to-Requirement Traceability

| Acceptance Criterion                                                  | Test ID                                                              | Test File                                                                           | Expected Behavior                                                                                           |
| --------------------------------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| All 13 tools discoverable via OpenAPI                                  | T-DISCOVER-001                                                       | `tests/integration/ai/test_forecast_cost_progress_tools.py`                        | `len(tools) == 13` and all tools have BaseTool type                                                         |
| Forecast tools wrap ForecastService                                   | T-FORECAST-001, T-FORECAST-002, T-FORECAST-003, T-FORECAST-004       | `tests/unit/ai/tools/test_forecast_cost_progress_template.py`                      | Each tool calls correct service method and returns AI-friendly dict                                          |
| Cost Registration tools wrap CostRegistrationService                  | T-COSTREG-001 through T-COSTREG-005                                   | `tests/unit/ai/tools/test_forecast_cost_progress_template.py`                      | Each tool calls correct service method and returns AI-friendly dict                                          |
| Progress Entry tools wrap ProgressEntryService                        | T-PROGRESS-001, T-PROGRESS-002, T-PROGRESS-003                        | `tests/unit/ai/tools/test_forecast_cost_progress_template.py`                      | Each tool calls correct service method and returns AI-friendly dict                                          |
| Summary tool aggregates data from all services                        | T-SUMMARY-001                                                        | `tests/unit/ai/tools/test_forecast_cost_progress_template.py`                      | Result contains forecast, cost, and progress data for cost element                                           |
| Temporal context logged for all tools                                 | T-TEMPORAL-001                                                       | `tests/unit/ai/tools/test_forecast_cost_progress_template.py`                      | Log contains `[TEMPORAL_CONTEXT]` message with tool name, as_of, branch, mode                                 |
| Temporal metadata in results                                         | T-TEMPORAL-002                                                       | `tests/unit/ai/tools/test_forecast_cost_progress_template.py`                      | Result dict contains `_temporal_context` key with as_of, branch_name, branch_mode                            |
| Error conditions return error dictionaries                            | T-ERROR-001 through T-ERROR-013                                      | `tests/unit/ai/tools/test_forecast_cost_progress_template.py`                      | Error paths return `{"error": str, "details": dict}` format                                                   |
| Tools have correct permissions                                        | T-PERMS-001                                                          | `tests/integration/ai/test_forecast_cost_progress_tools.py`                        | Each tool decorator has required permission scope                                                             |
| Code quality (MyPy, Ruff)                                             | T-QUALITY-001                                                        | CI pipeline                                                                        | Zero MyPy errors, zero Ruff errors                                                                          |

---

## Service Method Mappings

### Forecast Tools (4 tools)

| Tool Name                     | Service Method                            | Service Class            | Permissions           |
| ----------------------------- | ----------------------------------------- | ------------------------ | --------------------- |
| get_forecast                  | `get_for_cost_element(cost_element_id, branch)` | ForecastService         | forecast-read         |
| create_forecast               | `create_forecast(forecast_in, actor_id, branch, control_date)` | ForecastService         | forecast-create       |
| update_forecast               | `update_forecast(forecast_id, forecast_in, actor_id, control_date)` | ForecastService         | forecast-update       |
| compare_forecast_to_budget    | `get_budget_status(cost_element_id, as_of, branch)` + `get_for_cost_element()` | CostRegistrationService + ForecastService | forecast-read, cost-registration-read |

### Cost Registration Tools (5 tools)

| Tool Name                  | Service Method                                                    | Service Class            | Permissions               |
| -------------------------- | ----------------------------------------------------------------- | ------------------------ | ------------------------ |
| get_budget_status          | `get_budget_status(cost_element_id, as_of, branch)`               | CostRegistrationService  | cost-registration-read    |
| create_cost_registration   | `create_cost_registration(registration_in, actor_id, branch, control_date)` | CostRegistrationService  | cost-registration-create  |
| list_cost_registrations    | `get_cost_registrations(filters, skip, limit, as_of)`             | CostRegistrationService  | cost-registration-read    |
| get_cost_trends            | `get_costs_by_period(cost_element_id, period, start_date, end_date, as_of)` | CostRegistrationService  | cost-registration-read    |
| get_cumulative_costs       | `get_cumulative_costs(cost_element_id, start_date, end_date, as_of)` | CostRegistrationService  | cost-registration-read    |

### Progress Entry Tools (3 tools)

| Tool Name                  | Service Method                                               | Service Class         | Permissions            |
| -------------------------- | ------------------------------------------------------------ | --------------------- | ---------------------- |
| get_latest_progress        | `get_latest_progress(cost_element_id, as_of)`                | ProgressEntryService  | progress-entry-read    |
| create_progress_entry      | `create(actor_id, root_id, control_date, progress_in, **fields)` | ProgressEntryService  | progress-entry-create  |
| get_progress_history       | `get_progress_history(cost_element_id, skip, limit, as_of)`  | ProgressEntryService  | progress-entry-read    |

### Summary Tool (1 tool)

| Tool Name                  | Service Methods                                     | Service Classes                                    | Permissions                              |
| -------------------------- | --------------------------------------------------- | -------------------------------------------------- | ---------------------------------------- |
| get_cost_element_summary  | `get_for_cost_element()` + `get_budget_status()` + `get_latest_progress()` | ForecastService + CostRegistrationService + ProgressEntryService | forecast-read, cost-registration-read, progress-entry-read |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests (tests/unit/ai/tools/test_forecast_cost_progress_template.py)
│   ├── Forecast Tools Tests
│   │   ├── test_get_forecast_happy_path
│   │   ├── test_get_forecast_not_found
│   │   ├── test_create_forecast_success
│   │   ├── test_create_forecast_invalid_input
│   │   ├── test_update_forecast_success
│   │   ├── test_update_forecast_not_found
│   │   ├── test_compare_forecast_to_budget_variance
│   │   └── test_compare_forecast_to_budget_no_forecast
│   ├── Cost Registration Tools Tests
│   │   ├── test_get_budget_status_success
│   │   ├── test_get_budget_status_no_registrations
│   │   ├── test_create_cost_registration_success
│   │   ├── test_create_cost_registration_over_budget
│   │   ├── test_list_cost_registrations_with_filters
│   │   ├── test_get_cost_trends_daily
│   │   ├── test_get_cost_trends_weekly
│   │   ├── test_get_cumulative_costs_success
│   │   └── test_get_cumulative_costs_no_data
│   ├── Progress Entry Tools Tests
│   │   ├── test_get_latest_progress_success
│   │   ├── test_get_latest_progress_not_found
│   │   ├── test_create_progress_entry_success
│   │   ├── test_create_progress_entry_invalid_percentage
│   │   ├── test_get_progress_history_success
│   │   └── test_get_progress_history_pagination
│   ├── Summary Tool Tests
│   │   ├── test_get_cost_element_summary_complete
│   │   ├── test_get_cost_element_summary_partial_data
│   │   └── test_get_cost_element_summary_not_found
│   ├── Temporal Logging Tests
│   │   ├── test_temporal_context_logged_all_tools
│   │   └── test_temporal_metadata_added_to_results
│   └── Error Handling Tests
│       ├── test_error_format_invalid_uuid
│       └── test_error_format_service_exception
├── Integration Tests (tests/integration/ai/test_forecast_cost_progress_tools.py)
│   ├── test_all_tools_discoverable
│   ├── test_tools_have_correct_permissions
│   ├── test_tool_execution_via_langgraph
│   └── test_end_to_end_summary_workflow
```

### Test Cases (First 3-5)

| Test ID                                       | Test Name                                          | Criterion        | Type         | Expected Result                                                                                   |
| --------------------------------------------- | -------------------------------------------------- | ---------------- | ------------ | ------------------------------------------------------------------------------------------------- |
| T-FORECAST-001                                | test_get_forecast_happy_path                       | AC-Forecast-1    | Unit         | Returns forecast dict with id, eac_amount, basis_of_estimate, branch, and _temporal_context     |
| T-FORECAST-002                                | test_get_forecast_not_found                        | AC-Forecast-2    | Unit         | Returns error dict with "not found" message                                                       |
| T-COSTREG-001                                 | test_get_budget_status_success                     | AC-CostReg-1    | Unit         | Returns budget status with budget, used, remaining, percentage, and _temporal_context           |
| T-COSTREG-002                                 | test_create_cost_registration_success              | AC-CostReg-2    | Unit         | Creates registration, returns created dict with id, cost_element_id, amount, registration_date   |
| T-PROGRESS-001                                | test_create_progress_entry_success                 | AC-Progress-1   | Unit         | Creates progress entry, returns dict with progress_entry_id, cost_element_id, progress_percentage |

### Test Infrastructure Needs

- **Fixtures needed**:
  - `db_session` - from `tests/conftest.py`
  - `test_user` - from `tests/conftest.py`
  - `test_cost_element` - new fixture for creating test cost element
  - `tool_context` - new fixture for creating ToolContext with session and user_id

- **Mocks/stubs**:
  - None needed - tests use real database with test data

- **Database state**:
  - Need test data: projects, WBEs, cost elements
  - Each test should clean up after itself or use transactions

---

## Risk Assessment

| Risk Type   | Description                                                                                  | Probability | Impact      | Mitigation                                                                                                         |
| ----------- | -------------------------------------------------------------------------------------------- | ----------- | ----------- | ------------------------------------------------------------------------------------------------------------------ |
| Technical   | Service method signatures may have changed from expected patterns                             | Low         | Medium      | Verify actual signatures during implementation, adapt tool code as needed                                           |
| Integration | Temporal logging may not work correctly for non-branchable entities (cost/progress)          | Low         | Low         | Test temporal logging on all entity types, add metadata even if branch context is limited                         |
| Integration | Summary tool may have performance issues with multiple service calls                         | Medium      | Medium      | Implement efficient queries, add caching if needed, monitor performance in integration tests                      |
| Testing     | Unit tests may not cover all edge cases (missing data, invalid IDs, permission errors)       | Medium      | Low         | Comprehensive test planning, review test coverage, add tests for discovered edge cases during implementation      |
| Documentation | Tool descriptions may not be clear enough for LLMs to use effectively                       | Medium      | Medium      | Review descriptions against actual use cases, test with real queries, iterate on language                        |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph for AI Tools - Forecast, Cost Registration, Progress Entry
tasks:
  - id: BE-001
    name: "Create forecast_cost_progress_template.py with Forecast tools"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Add Cost Registration tools to template"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Add Progress Entry tools to template"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-004
    name: "Implement Summary tool"
    agent: pdca-backend-do-executor
    dependencies: [BE-003]

  - id: BE-005
    name: "Register tools in __init__.py"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: BE-006
    name: "Write unit tests for Forecast tools"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-007
    name: "Write unit tests for Cost Registration tools"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-008
    name: "Write unit tests for Progress Entry tools"
    agent: pdca-backend-do-executor
    dependencies: [BE-003]

  - id: BE-009
    name: "Write unit tests for Summary tool"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: BE-010
    name: "Write integration test for tool discovery and execution"
    agent: pdca-backend-do-executor
    dependencies: [BE-005, BE-006, BE-007, BE-008, BE-009]

  - id: BE-011
    name: "Run quality checks (MyPy, Ruff) and verify coverage"
    agent: pdca-backend-do-executor
    dependencies: [BE-010]
    kind: test
```

**Execution Levels:**
- **Level 0** (can run in parallel): BE-001
- **Level 1**: BE-002 (depends on BE-001), BE-006 (depends on BE-001)
- **Level 2**: BE-003 (depends on BE-002), BE-007 (depends on BE-002)
- **Level 3**: BE-004 (depends on BE-003), BE-008 (depends on BE-003)
- **Level 4**: BE-005 (depends on BE-004), BE-009 (depends on BE-004)
- **Level 5**: BE-010 (depends on BE-005, BE-006, BE-007, BE-008, BE-009)
- **Level 6**: BE-011 (depends on BE-010) - marked as `kind: test` to ensure serialized execution

**Parallelization Opportunities:**
- BE-006, BE-007, BE-008 can run in parallel with corresponding implementation tasks (test-driven approach)
- All test tasks can run in parallel except BE-010 (integration test requires all implementation complete)
- BE-011 must run last as quality gate

---

## Documentation References

### Required Reading

- Coding Standards: `docs/02-architecture/coding-standards.md`
- AI Tool Development Guide: `docs/02-architecture/ai/tool-development-guide.md`
- Temporal Context Patterns: `docs/02-architecture/ai/temporal-context-patterns.md`
- Bounded Contexts: `docs/02-architecture/01-bounded-contexts.md`

### Code References

- Backend pattern - Cost Element Template: `backend/app/ai/tools/templates/cost_element_template.py`
- Backend pattern - Analysis Template: `backend/app/ai/tools/templates/analysis_template.py`
- Tool Registration: `backend/app/ai/tools/__init__.py`
- Temporal Logging: `backend/app/ai/tools/temporal_logging.py`
- Tool Decorator: `backend/app/ai/tools/decorator.py`
- Service Layer - ForecastService: `backend/app/services/forecast_service.py`
- Service Layer - CostRegistrationService: `backend/app/services/cost_registration_service.py`
- Service Layer - ProgressEntryService: `backend/app/services/progress_entry_service.py`

### Test Pattern References

- Unit test conftest: `backend/tests/conftest.py`
- AI tool test examples: `backend/tests/unit/ai/tools/test_cost_element_template.py`
- AI integration test examples: `backend/tests/integration/ai/test_temporal_context_integration.py`

---

## Prerequisites

### Technical

- [x] Database migrations applied (forecast, cost_registration, progress_entry tables exist)
- [x] Dependencies installed (langchain, langchain-core, pydantic, sqlalchemy)
- [x] Environment configured (PostgreSQL running, test database available)
- [x] Service layer complete (ForecastService, CostRegistrationService, ProgressEntryService)

### Documentation

- [x] Analysis phase approved (00-analysis.md exists with user decisions)
- [ ] Architecture docs reviewed (tool development guide, temporal context patterns)
- [ ] Related ADRs understood (RBAC, EVCS architecture)

---

## Critical Files

### Files to Create

1. **`backend/app/ai/tools/templates/forecast_cost_progress_template.py`** (~700 lines)
   - Module docstring explaining the three service layers
   - 13 tool functions with @ai_tool decorators
   - Temporal logging for all tools
   - Error handling with error dictionaries
   - AI-friendly return formats (dicts, not domain models)

2. **`backend/tests/unit/ai/tools/test_forecast_cost_progress_template.py`** (~800 lines)
   - Unit tests for all 13 tools
   - Tests for happy paths, edge cases, error conditions
   - Temporal logging verification tests
   - Mock setup for service dependencies

3. **`backend/tests/integration/ai/test_forecast_cost_progress_tools.py`** (~200 lines)
   - Tool discovery test (all 13 tools registered)
   - Tool execution via LangGraph
   - End-to-end workflow test
   - Permission verification test

### Files to Modify

1. **`backend/app/ai/tools/__init__.py`** (+20 lines)
   - Import `forecast_cost_progress_template`
   - Add 13 tools to `create_project_tools()` function
   - Maintain alphabetical organization

---

## Implementation Notes

### Tool Design Principles

1. **Service Wrapping, Not Logic Duplication**
   - All business logic remains in service layer
   - Tools only convert between AI-friendly formats and service formats
   - No business logic in tool functions

2. **Temporal Consistency**
   - All tools use `log_temporal_context()` for observability
   - All tools use `add_temporal_metadata()` for result transparency
   - Branchable entities (Forecast) use full temporal context
   - Non-branchable entities (Cost, Progress) still log temporal context for consistency

3. **Error Handling Pattern**
   ```python
   try:
       # Service call
       return {"success": True, "data": ...}
   except ValueError:
       return {"error": "Invalid input: ..."}
   except KeyError:
       return {"error": "Entity not found: ..."}
   except Exception as e:
       logger.error(f"Error in tool_name: {e}")
       return {"error": str(e)}
   ```

4. **AI-Friendly Return Formats**
   - Always return dicts, never domain models
   - Convert UUIDs to strings
   - Convert Decimals to floats
   - Include human-readable field names
   - Add `_temporal_context` metadata

5. **Permission Scopes**
   - Forecast: `forecast-read`, `forecast-create`, `forecast-update`
   - Cost Registration: `cost-registration-read`, `cost-registration-create`
   - Progress Entry: `progress-entry-read`, `progress-entry-create`
   - Summary: All read permissions combined

### Service Method Parameter Mapping

**Key Pattern Differences:**

1. **ForecastService.get_for_cost_element()**
   - Parameters: `cost_element_id: UUID`, `branch: str`
   - Tool receives: `cost_element_id: str`
   - Tool converts: `UUID(cost_element_id)`

2. **CostRegistrationService.get_budget_status()**
   - Parameters: `cost_element_id: UUID`, `as_of: datetime | None`, `branch: str`
   - Tool receives: `cost_element_id: str`, `as_of_date: str | None` (ISO format)
   - Tool converts: `UUID(cost_element_id)`, `datetime.fromisoformat(as_of_date) if as_of_date else None`

3. **ProgressEntryService.create()**
   - Parameters: `actor_id: UUID`, `root_id: UUID | None`, `control_date: datetime | None`, `progress_in: Any`, `**fields`
   - Tool receives: `cost_element_id: str`, `progress_percentage: float`, `notes: str | None`
   - Tool builds: `progress_in` dict with required fields

### Summary Tool Implementation Strategy

The summary tool needs to call three services sequentially:

```python
@ai_tool(
    name="get_cost_element_summary",
    description="Get comprehensive summary of cost element including forecast, costs, and progress",
    permissions=["forecast-read", "cost-registration-read", "progress-entry-read"],
    category="summary",
)
async def get_cost_element_summary(
    cost_element_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,
) -> dict[str, Any]:
    """Get comprehensive summary for cost element."""
    log_temporal_context("get_cost_element_summary", context)

    try:
        # 1. Get forecast data
        forecast = await ForecastService(context.session).get_for_cost_element(
            UUID(cost_element_id),
            branch=context.branch_name or "main"
        )

        # 2. Get budget status
        budget_status = await CostRegistrationService(context.session).get_budget_status(
            UUID(cost_element_id),
            as_of=context.as_of,
            branch=context.branch_name or "main"
        )

        # 3. Get latest progress
        progress = await ProgressEntryService(context.session).get_latest_progress(
            UUID(cost_element_id),
            as_of=context.as_of
        )

        # 4. Aggregate results
        return add_temporal_metadata({
            "cost_element_id": cost_element_id,
            "forecast": {...},
            "budget_status": {...},
            "progress": {...},
        }, context)

    except Exception as e:
        return add_temporal_metadata({"error": str(e)}, context)
```

---

## Definition of Done

- [ ] All 13 tools implemented in `forecast_cost_progress_template.py`
- [ ] All tools registered in `__init__.py`
- [ ] Unit tests written for all tools (80%+ coverage)
- [ ] Integration test passes (tool discovery and execution)
- [ ] Zero MyPy errors (`uv run mypy app/ai/tools/templates/forecast_cost_progress_template.py`)
- [ ] Zero Ruff errors (`uv run ruff check app/ai/tools/templates/forecast_cost_progress_template.py`)
- [ ] All temporal logging verified (log output analysis)
- [ ] All error paths tested
- [ ] Documentation complete (docstrings, type hints)
- [ ] Manual testing with sample queries successful

---

## Success Metrics

- **Tool Count**: 13 tools discoverable via OpenAPI
- **Test Coverage**: ≥80% for `forecast_cost_progress_template.py`
- **Code Quality**: Zero MyPy/Ruff errors
- **Test Pass Rate**: 100% (all unit and integration tests pass)
- **Performance**: Summary tool executes in <2 seconds with typical data
- **Observability**: All tool executions logged with temporal context
