# Implementation Plan: LangGraph Agent Enhancement

**Created:** 2026-03-09
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option B - Full StateGraph Rewrite
**Iteration:** E09-LANGGRAPH
**Points:** 13

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option:** Option B - Full StateGraph Rewrite
- **Architecture:** Complete rewrite using LangGraph 1.0+ best practices with StateGraph, TypedDict state, ToolNode, and MemorySaver checkpointer
- **Key Decisions:**
  - Big bang migration acceptable (high risk tolerance, no timeline pressure)
  - `@ai_tool` decorator MUST wrap existing service methods, not duplicate logic
  - LangGraph domain expert available for guidance
  - Full testing team available for comprehensive coverage
  - Foundation for 15+ future tools (CRUD, Change Orders, Analysis)

### Success Criteria

**Functional Criteria:**

- [ ] Agent uses `StateGraph` from `langgraph.graph` with `TypedDict` state VERIFIED BY: Integration test `tests/integration/ai/test_graph_execution.py::test_stategraph_compilation_and_execution`
- [ ] Agent node calls LLM with `bind_tools()` for tool binding VERIFIED BY: Unit test `tests/unit/ai/test_graph.py::test_agent_node_binds_tools_correctly`
- [ ] `ToolNode` from `langgraph.prebuilt` executes tool calls VERIFIED BY: Integration test `tests/integration/ai/test_graph_execution.py::test_tool_node_execution`
- [ ] Conditional edges route based on `tool_calls` presence VERIFIED BY: Unit test `tests/unit/ai/test_graph.py::test_conditional_edges_routing`
- [ ] `@ai_tool` decorator wraps existing service methods VERIFIED BY: Unit test `tests/unit/ai/tools/test_decorator.py::test_decorator_wraps_service_method`
- [ ] Tool registry auto-discovers decorated tools VERIFIED BY: Unit test `tests/unit/ai/tools/test_registry.py::test_auto_discovery_of_decorated_tools`
- [ ] Context injection (db session, user_id, RBAC) works VERIFIED BY: Integration test `tests/integration/ai/tools/test_tool_execution.py::test_context_injection`
- [ ] Existing tools (`list_projects`, `get_project`) migrated to new pattern VERIFIED BY: Regression test `tests/integration/ai/tools/test_existing_tools.py::test_migrated_tools_produce_same_results`
- [ ] WebSocket streaming works with `app.astream_events()` VERIFIED BY: Integration test `tests/integration/ai/test_streaming.py::test_websocket_streaming_with_astream_events`
- [ ] Checkpointer saves and restores state VERIFIED BY: Unit test `tests/unit/ai/test_checkpointer.py::test_state_persistence_and_restoration`

**Technical Criteria:**

- [ ] Performance: Agent invocation <500ms for simple queries VERIFIED BY: Performance benchmark `tests/performance/ai/test_agent_performance.py::test_simple_query_latency`
- [ ] Performance: Streaming latency <100ms for first token VERIFIED BY: Performance benchmark `tests/performance/ai/test_streaming_performance.py::test_first_token_latency`
- [ ] Performance: Tool execution <100ms for simple tools VERIFIED BY: Performance benchmark `tests/performance/ai/test_tool_performance.py::test_simple_tool_execution`
- [ ] Security: RBAC enforced at tool level VERIFIED BY: Security test `tests/security/ai/test_tool_rbac.py::test_permission_denied_without_required_permission`
- [ ] Code Quality: MyPy strict mode (zero errors) VERIFIED BY: CI pipeline `mypy app/ai/`
- [ ] Code Quality: Ruff clean (zero errors) VERIFIED BY: CI pipeline `ruff check app/ai/`
- [ ] Code Quality: 80%+ test coverage for agent VERIFIED BY: CI pipeline `pytest --cov=app/ai --cov-report=term-missing`
- [ ] Code Quality: 80%+ test coverage for tools VERIFIED BY: CI pipeline `pytest --cov=app/ai/tools --cov-report=term-missing`

**Business Criteria:**

- [ ] New tool can be added in <50 lines of code VERIFIED BY: Developer documentation example showing minimal boilerplate
- [ ] Zero regression in existing AI chat functionality VERIFIED BY: Regression test suite `tests/regression/ai/test_existing_functionality.py`
- [ ] Scalable to 15+ tools without architectural changes VERIFIED BY: Architecture review confirming tool registry pattern

### Scope Boundaries

**In Scope:**

- Complete rewrite of agent orchestration using LangGraph 1.0+ StateGraph
- Implementation of `@ai_tool` decorator that wraps existing service methods
- Tool registry with auto-discovery and metadata management
- Migration of 2 existing tools (`list_projects`, `get_project`) to new pattern
- Graph visualization export for debugging
- Time travel debugging support via checkpointer
- Tool execution monitoring and performance instrumentation
- Comprehensive testing (unit, integration, performance, security)
- Developer documentation (tool development guide, API docs, troubleshooting guide)

**Out of Scope:**

- Implementation of 15+ additional tools (deferred to E09-U08, E09-U09, E09-U07)
- Frontend changes (no UI modifications required)
- New database migrations (reuses existing schema)
- Multi-modal input/output (future iteration)
- Tool result caching (future optimization)
- Advanced error recovery strategies (future enhancement)

---

## Work Decomposition

### Task Breakdown

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | --- | --- | --- | --- | --- |
| **Phase 1: Core LangGraph Refactoring (5 points)** |
| 1.1 | Define AgentState as TypedDict | `backend/app/ai/state.py` | None | Unit test passes: TypedDict with Annotated messages append behavior | Low |
| 1.2 | Create StateGraph structure | `backend/app/ai/graph.py` | 1.1 | Unit test: graph compiles, nodes added, conditional edges work | Medium |
| 1.3 | Implement agent node with bind_tools() | `backend/app/ai/graph.py` | 1.2 | Unit test: agent node calls LLM with tools bound | Medium |
| 1.4 | Integrate ToolNode from langgraph.prebuilt | `backend/app/ai/graph.py` | 1.3 | Integration test: ToolNode executes tool calls | Medium |
| 1.5 | Add MemorySaver checkpointer | `backend/app/ai/graph.py` | 1.4 | Unit test: state persists and restores across calls | Medium |
| 1.6 | Implement streaming with astream_events() | `backend/app/ai/agent_service.py` | 1.5 | Integration test: WebSocket streams tokens, tool calls, results | High |
| 1.7 | Test core graph execution | `tests/unit/ai/test_graph.py`, `tests/integration/ai/test_graph_execution.py` | 1.6 | 80%+ coverage for graph, all tests passing | Medium |
| **Phase 2: Tool Standardization (3 points)** |
| 2.1 | Implement @ai_tool decorator | `backend/app/ai/tools/decorator.py` | None | Unit test: decorator wraps function, generates schema, injects context | Medium |
| 2.2 | Implement tool registry | `backend/app/ai/tools/registry.py` | 2.1 | Unit test: registry auto-discovers tools, filters by permissions | Medium |
| 2.3 | Define ToolContext and ToolMetadata types | `backend/app/ai/tools/types.py` | 2.1 | Unit test: types serialize correctly, context injection works | Low |
| 2.4 | Migrate list_projects tool | `backend/app/ai/tools/project_tools.py` | 2.2, 2.3 | Integration test: wraps ProjectService.get_projects(), produces same results | Medium |
| 2.5 | Migrate get_project tool | `backend/app/ai/tools/project_tools.py` | 2.4 | Integration test: wraps ProjectService.get_project(), produces same results | Medium |
| 2.6 | Test tool layer | `tests/unit/ai/tools/`, `tests/integration/ai/tools/` | 2.5 | 80%+ coverage for tools, all tests passing | Medium |
| **Phase 3: Migration & Expansion (3 points)** |
| 3.1 | Implement graph visualization | `backend/app/ai/graph.py` | 1.7 | Integration test: export_graphviz() produces valid DOT format | Low |
| 3.2 | Add tool execution monitoring | `backend/app/ai/monitoring.py` | 2.6 | Unit test: execution time logged, tool calls tracked | Low |
| 3.3 | Create CRUD tool template | `backend/app/ai/tools/templates/crud_template.py` | 2.6 | Example shows wrapping ProjectService, WBEService methods | Medium |
| 3.4 | Create Change Order tool template | `backend/app/ai/tools/templates/change_order_template.py` | 2.6 | Example shows wrapping ChangeOrderService methods | Medium |
| 3.5 | Create Analysis tool template | `backend/app/ai/tools/templates/analysis_template.py` | 2.6 | Example shows wrapping EVMService, ForecastService methods | Medium |
| 3.6 | Integration and regression testing | `tests/integration/ai/`, `tests/regression/ai/` | 3.5 | All tests passing, no regression in existing functionality | High |
| **Phase 4: Testing & Documentation (2 points)** |
| 4.1 | Performance benchmarking | `tests/performance/ai/` | 3.6 | All benchmarks meet latency targets (<500ms agent, <100ms streaming, <100ms tools) | Medium |
| 4.2 | Security testing for RBAC | `tests/security/ai/` | 3.6 | Permission tests pass, unauthorized access blocked | Medium |
| 4.3 | Architecture decision record | `docs/02-architecture/decisions/xxx-langgraph-rewrite.md` | 4.1 | ADR approved and merged | Low |
| 4.4 | Tool development guide | `docs/02-architecture/ai/tool-development-guide.md` | 4.1 | Guide reviewed by domain expert, examples tested | Medium |
| 4.5 | API documentation update | `docs/02-architecture/ai/api-reference.md` | 4.4 | All public interfaces documented | Low |
| 4.6 | Troubleshooting guide | `docs/02-architecture/ai/troubleshooting.md` | 4.5 | Common issues and solutions documented | Low |
| 4.7 | Final quality gates | CI pipeline | 4.6 | Zero MyPy/Ruff errors, 80%+ coverage, all tests passing | Medium |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| --- | --- | --- | --- |
| Agent uses StateGraph with TypedDict state | T-001 | `tests/unit/ai/test_graph.py::test_stategraph_compilation` | StateGraph(AgentState) compiles successfully |
| Agent node calls LLM with bind_tools() | T-002 | `tests/unit/ai/test_graph.py::test_agent_node_binds_tools` | LLM.bind_tools() called with tool list |
| ToolNode executes tool calls | T-003 | `tests/integration/ai/test_graph_execution.py::test_tool_node_execution` | ToolNode receives tool_call and returns result |
| Conditional edges route correctly | T-004 | `tests/unit/ai/test_graph.py::test_conditional_edges_routing` | Routes to tools if tool_calls present, to END otherwise |
| @ai_tool decorator wraps service methods | T-005 | `tests/unit/ai/tools/test_decorator.py::test_decorator_wraps_service_method` | Decorator wraps function, preserves signature, injects context |
| Tool registry auto-discovers tools | T-006 | `tests/unit/ai/tools/test_registry.py::test_auto_discovery` | get_all_tools() returns all @ai_tool decorated functions |
| Context injection works | T-007 | `tests/integration/ai/tools/test_tool_execution.py::test_context_injection` | Tool receives ToolContext with db_session and user_id |
| RBAC enforced at tool level | T-008 | `tests/security/ai/test_tool_rbac.py::test_permission_denied` | Tool returns error if user lacks required permission |
| Existing tools migrated | T-009 | `tests/integration/ai/tools/test_existing_tools.py::test_migrated_tools` | Migrated tools return same results as original implementation |
| WebSocket streaming works | T-010 | `tests/integration/ai/test_streaming.py::test_websocket_streaming` | WebSocket receives tokens, tool calls, tool results |
| Checkpointer saves/restores state | T-011 | `tests/unit/ai/test_checkpointer.py::test_state_persistence` | State saved after first call, restored in second call |
| Agent invocation <500ms | T-012 | `tests/performance/ai/test_agent_performance.py::test_simple_query` | Simple query completes in <500ms (p50) |
| Streaming latency <100ms | T-013 | `tests/performance/ai/test_streaming_performance.py::test_first_token` | First token received in <100ms (p50) |
| Tool execution <100ms | T-014 | `tests/performance/ai/test_tool_performance.py::test_simple_tool` | Simple tool executes in <100ms (p50) |
| MyPy strict mode | T-015 | CI pipeline | `mypy app/ai/` returns zero errors |
| Ruff clean | T-016 | CI pipeline | `ruff check app/ai/` returns zero errors |
| 80%+ coverage | T-017 | CI pipeline | `pytest --cov=app/ai --cov-report=term-missing` shows ≥80% |
| Zero regression | T-018 | `tests/regression/ai/test_existing_functionality.py` | All existing AI chat tests pass |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests (tests/unit/ai/)
│   ├── test_state.py - AgentState TypedDict definition
│   ├── test_graph.py - StateGraph compilation, nodes, edges
│   ├── test_decorator.py - @ai_tool decorator logic
│   ├── test_registry.py - Tool registry auto-discovery
│   ├── test_types.py - ToolContext and ToolMetadata types
│   ├── test_checkpointer.py - State persistence
│   └── test_monitoring.py - Tool execution monitoring
├── Integration Tests (tests/integration/ai/)
│   ├── test_graph_execution.py - End-to-end graph execution
│   ├── test_streaming.py - WebSocket streaming with astream_events
│   ├── tools/
│   │   ├── test_tool_execution.py - Tool execution with context
│   │   ├── test_existing_tools.py - Migrated tools equivalence
│   │   └── test_tool_registry_integration.py - Registry integration
│   └── test_agent_service.py - AgentService integration
├── Performance Tests (tests/performance/ai/)
│   ├── test_agent_performance.py - Agent invocation latency
│   ├── test_streaming_performance.py - Streaming latency
│   └── test_tool_performance.py - Tool execution latency
├── Security Tests (tests/security/ai/)
│   └── test_tool_rbac.py - RBAC enforcement at tool level
└── Regression Tests (tests/regression/ai/)
    └── test_existing_functionality.py - Ensure no regression
```

### Test Cases (First 5)

| Test ID | Test Name | Criterion | Type | Expected Result |
| --- | --- | --- | --- | --- |
| T-001 | test_stategraph_compilation_creates_valid_graph | FR-1 | Unit | StateGraph(AgentState).compile() returns CompiledGraph |
| T-002 | test_agent_node_binds_tools_correctly | FR-1 | Unit | agent_node() calls llm.bind_tools() with tool list |
| T-003 | test_conditional_edges_route_to_tools_when_tool_calls_present | FR-1 | Unit | should_continue() returns "tools" if messages contain tool_calls |
| T-004 | test_conditional_edges_route_to_end_when_no_tool_calls | FR-1 | Unit | should_continue() returns "end" if messages lack tool_calls |
| T-005 | test_decorator_wraps_function_and_generates_schema | FR-2 | Unit | @ai_tool decorator preserves function signature and generates LangChain tool schema |

### Test Infrastructure Needs

**Fixtures needed:**
- `mock_llm_client` - Mock LLM for testing agent node without API calls
- `mock_db_session` - AsyncSession mock for tool execution
- `mock_user_context` - Mock user with permissions for RBAC testing
- `test_tool_registry` - Clean registry state for each test
- `sample_projects` - Pre-seeded project data for integration tests

**Mocks/stubs:**
- LLM client (avoid OpenAI API calls in tests)
- WebSocket connection (test streaming without real WebSocket)
- External dependencies (time, UUID generation)

**Database state:**
- Clean test database for each test
- Seed data for projects, users, permissions
- Isolation between tests (rollback or truncate)

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| Technical | Breaking existing AI chat functionality | Medium | High | Comprehensive regression test suite; feature flag for emergency disable; keep old code as reference during migration |
| Technical | LangGraph 1.0 API instability | Low | High | Domain expert validates patterns; pin to specific version (1.0.10+); monitor for breaking changes |
| Integration | Tool migration issues (service incompatibility) | Low | Medium | Migrate incrementally (1 tool at a time); validate tool equivalence; keep old implementation for comparison |
| Performance | Performance regression vs. current implementation | Low | Medium | Benchmark before/after; load testing; profile critical paths; optimize bottlenecks |
| Integration | WebSocket streaming issues with astream_events | Low | High | Thorough streaming tests; mock WebSocket for unit tests; monitor production closely |
| Technical | State persistence problems with checkpointer | Low | High | Comprehensive checkpointer tests; verify state restoration; add state migration logic if needed |
| Security | RBAC enforcement gaps at tool level | Low | High | Security review of all tools; test permission checking; audit tool access patterns |
| Knowledge | Team learning curve for LangGraph 1.0 | Medium | Medium | Domain expert available for guidance; pair programming; documentation and examples |

**Risk Mitigation Summary:**
- Domain expert availability significantly reduces LangGraph-related risks
- Full testing team enables comprehensive test coverage
- No timeline pressure allows thorough testing and validation
- High risk tolerance accepted for strategic investment

---

## Task Dependency Graph

```yaml
# Task Dependency Graph for E09-LANGGRAPH
# Defines task execution order for parallel DO-phase delegation

tasks:
  # Phase 1: Core LangGraph Refactoring
  - id: BE-P1-001
    name: "Define AgentState as TypedDict in state.py"
    agent: pdca-backend-do-executor
    dependencies: []
    group: phase-1-state

  - id: BE-P1-002
    name: "Create StateGraph structure in graph.py"
    agent: pdca-backend-do-executor
    dependencies: [BE-P1-001]
    group: phase-1-graph

  - id: BE-P1-003
    name: "Implement agent node with bind_tools()"
    agent: pdca-backend-do-executor
    dependencies: [BE-P1-002]
    group: phase-1-graph

  - id: BE-P1-004
    name: "Integrate ToolNode from langgraph.prebuilt"
    agent: pdca-backend-do-executor
    dependencies: [BE-P1-003]
    group: phase-1-graph

  - id: BE-P1-005
    name: "Add MemorySaver checkpointer"
    agent: pdca-backend-do-executor
    dependencies: [BE-P1-004]
    group: phase-1-graph

  - id: BE-P1-006
    name: "Implement streaming with astream_events()"
    agent: pdca-backend-do-executor
    dependencies: [BE-P1-005]
    group: phase-1-streaming

  - id: BE-P1-007
    name: "Test core graph execution (unit + integration)"
    agent: pdca-backend-do-executor
    dependencies: [BE-P1-006]
    group: phase-1-tests
    kind: test

  # Phase 2: Tool Standardization
  - id: BE-P2-001
    name: "Implement @ai_tool decorator"
    agent: pdca-backend-do-executor
    dependencies: []
    group: phase-2-decorator

  - id: BE-P2-002
    name: "Define ToolContext and ToolMetadata types"
    agent: pdca-backend-do-executor
    dependencies: [BE-P2-001]
    group: phase-2-decorator

  - id: BE-P2-003
    name: "Implement tool registry with auto-discovery"
    agent: pdca-backend-do-executor
    dependencies: [BE-P2-002]
    group: phase-2-registry

  - id: BE-P2-004
    name: "Migrate list_projects tool (wraps ProjectService.get_projects)"
    agent: pdca-backend-do-executor
    dependencies: [BE-P2-003]
    group: phase-2-migration

  - id: BE-P2-005
    name: "Migrate get_project tool (wraps ProjectService.get_project)"
    agent: pdca-backend-do-executor
    dependencies: [BE-P2-004]
    group: phase-2-migration

  - id: BE-P2-006
    name: "Test tool layer (unit + integration)"
    agent: pdca-backend-do-executor
    dependencies: [BE-P2-005]
    group: phase-2-tests
    kind: test

  # Phase 3: Migration & Expansion
  - id: BE-P3-001
    name: "Implement graph visualization export"
    agent: pdca-backend-do-executor
    dependencies: [BE-P1-007, BE-P2-006]
    group: phase-3-features

  - id: BE-P3-002
    name: "Add tool execution monitoring"
    agent: pdca-backend-do-executor
    dependencies: [BE-P2-006]
    group: phase-3-features

  - id: BE-P3-003
    name: "Create CRUD tool template (examples for ProjectService, WBEService)"
    agent: pdca-backend-do-executor
    dependencies: [BE-P2-006]
    group: phase-3-templates

  - id: BE-P3-004
    name: "Create Change Order tool template (examples for ChangeOrderService)"
    agent: pdca-backend-do-executor
    dependencies: [BE-P2-006]
    group: phase-3-templates

  - id: BE-P3-005
    name: "Create Analysis tool template (examples for EVMService, ForecastService)"
    agent: pdca-backend-do-executor
    dependencies: [BE-P2-006]
    group: phase-3-templates

  - id: BE-P3-006
    name: "Integration and regression testing"
    agent: pdca-backend-do-executor
    dependencies: [BE-P3-001, BE-P3-002, BE-P3-003, BE-P3-004, BE-P3-005]
    group: phase-3-tests
    kind: test

  # Phase 4: Testing & Documentation
  - id: BE-P4-001
    name: "Performance benchmarking (agent, streaming, tools)"
    agent: pdca-backend-do-executor
    dependencies: [BE-P3-006]
    group: phase-4-perf
    kind: test

  - id: BE-P4-002
    name: "Security testing for RBAC enforcement"
    agent: pdca-backend-do-executor
    dependencies: [BE-P3-006]
    group: phase-4-security
    kind: test

  - id: BE-P4-003
    name: "Create Architecture Decision Record"
    agent: pdca-backend-do-executor
    dependencies: [BE-P4-001, BE-P4-002]
    group: phase-4-docs

  - id: BE-P4-004
    name: "Create Tool Development Guide"
    agent: pdca-backend-do-executor
    dependencies: [BE-P4-003]
    group: phase-4-docs

  - id: BE-P4-005
    name: "Update API documentation"
    agent: pdca-backend-do-executor
    dependencies: [BE-P4-004]
    group: phase-4-docs

  - id: BE-P4-006
    name: "Create Troubleshooting Guide"
    agent: pdca-backend-do-executor
    dependencies: [BE-P4-005]
    group: phase-4-docs

  - id: BE-P4-007
    name: "Final quality gates (MyPy, Ruff, coverage)"
    agent: pdca-backend-do-executor
    dependencies: [BE-P4-006]
    group: phase-4-final
    kind: test
```

**Dependency Analysis:**

**Level 0 (Can run in parallel):**
- BE-P1-001 (State definition)
- BE-P2-001 (Decorator implementation)

**Level 1:**
- BE-P1-002 (Graph structure - depends on BE-P1-001)
- BE-P2-002 (Tool types - depends on BE-P2-001)

**Level 2:**
- BE-P1-003 (Agent node - depends on BE-P1-002)
- BE-P2-003 (Tool registry - depends on BE-P2-002)

**Level 3:**
- BE-P1-004 (ToolNode integration - depends on BE-P1-003)
- BE-P2-004 (Migrate list_projects - depends on BE-P2-003)

**Level 4:**
- BE-P1-005 (Checkpointer - depends on BE-P1-004)
- BE-P2-005 (Migrate get_project - depends on BE-P2-004)

**Level 5:**
- BE-P1-006 (Streaming - depends on BE-P1-005)
- BE-P2-006 (Tool tests - depends on BE-P2-005)

**Level 6:**
- BE-P1-007 (Graph tests - depends on BE-P1-006)
- BE-P3-001 (Visualization - depends on BE-P1-007, BE-P2-006)
- BE-P3-002 (Monitoring - depends on BE-P2-006)
- BE-P3-003 (CRUD template - depends on BE-P2-006)
- BE-P3-004 (Change Order template - depends on BE-P2-006)
- BE-P3-005 (Analysis template - depends on BE-P2-006)

**Level 7:**
- BE-P3-006 (Integration tests - depends on all BE-P3-* tasks)
- BE-P4-001 (Performance - depends on BE-P3-006)
- BE-P4-002 (Security - depends on BE-P3-006)

**Level 8:**
- BE-P4-003 (ADR - depends on BE-P4-001, BE-P4-002)

**Level 9:**
- BE-P4-004 (Tool guide - depends on BE-P4-003)

**Level 10:**
- BE-P4-005 (API docs - depends on BE-P4-004)

**Level 11:**
- BE-P4-006 (Troubleshooting - depends on BE-P4-005)

**Level 12:**
- BE-P4-007 (Final gates - depends on BE-P4-006)

---

## Integration Points

### Existing Service Layer Integration

**ProjectService:**
- File: `backend/app/services/project.py`
- Methods to wrap:
  - `get_projects()` - List/search projects (already wrapped by existing tool)
  - `get_project()` - Get single project (already wrapped by existing tool)
  - `create_project()` - Create new project (future tool)
  - `update_project()` - Update project (future tool)
- Integration pattern: `@ai_tool` decorator injects `db_session` and `user_id`, calls service method

**CostElementService:**
- File: `backend/app/services/cost_element_service.py`
- Methods to wrap:
  - `get_cost_elements()` - List cost elements (future tool)
  - `get_cost_element()` - Get single cost element (future tool)
  - `create_cost_element()` - Create cost element (future tool)
- Integration pattern: Same as ProjectService

**ChangeOrderService:**
- File: `backend/app/services/change_order_service.py`
- Methods to wrap:
  - `create_change_order()` - Create change order (future tool)
  - `get_change_order()` - Get change order (future tool)
  - `generate_draft()` - Generate draft (future tool)
- Integration pattern: Same as ProjectService

**WBEService:**
- File: `backend/app/services/wbe.py`
- Methods to wrap:
  - `get_wbes()` - List WBEs (future tool)
  - `get_wbe()` - Get single WBE (future tool)
  - `create_wbe()` - Create WBE (future tool)
- Integration pattern: Same as ProjectService

### RBAC System Integration

**Current RBAC:**
- File: `backend/app/core/rbac.py`
- Permission-based access control
- Service methods already check permissions

**Tool-Level RBAC:**
- `@ai_tool` decorator accepts `permissions` parameter
- Decorator checks permissions BEFORE calling service method
- Double layer: decorator checks, service also checks (defense in depth)
- Tool metadata includes required permissions for documentation

### Database Integration

**Existing Database:**
- PostgreSQL 15+ with EVCS versioning
- AsyncPG with optimized pooling
- Alembic migrations

**State Persistence:**
- LangGraph `MemorySaver` checkpointer
- Stores conversation state in PostgreSQL
- Reuses existing database connection
- No new migrations required (uses existing AI tables)

### WebSocket Integration

**Current WebSocket:**
- File: `backend/app/api/routes/ai_chat.py`
- Endpoint: `/api/v1/chat/ws/{conversation_id}`
- Protocol: Custom message types (token, tool_call, tool_result, error, complete)

**Streaming with LangGraph:**
- Use `app.astream_events()` for detailed event streaming
- Map LangGraph events to WebSocket message types:
  - `on_chat_model_stream` → WSTokenMessage
  - `on_tool_start` → WSToolCallMessage
  - `on_tool_end` → WSToolResultMessage
  - `on_error` → WSErrorMessage
  - `on_end` → WSCompleteMessage

---

## File Creation/Modification List

### Files to Create

**Core LangGraph:**
- `backend/app/ai/state.py` - AgentState TypedDict definition
- `backend/app/ai/graph.py` - StateGraph structure, nodes, edges

**Tool Layer:**
- `backend/app/ai/tools/decorator.py` - @ai_tool decorator implementation
- `backend/app/ai/tools/registry.py` - Tool registry with auto-discovery
- `backend/app/ai/tools/types.py` - ToolContext, ToolMetadata types
- `backend/app/ai/tools/project_tools.py` - Project tools (migrated)
- `backend/app/ai/tools/templates/crud_template.py` - CRUD tool template
- `backend/app/ai/tools/templates/change_order_template.py` - Change Order tool template
- `backend/app/ai/tools/templates/analysis_template.py` - Analysis tool template

**Monitoring & Debugging:**
- `backend/app/ai/monitoring.py` - Tool execution monitoring
- `backend/app/ai/visualization.py` - Graph visualization export

**Tests:**
- `tests/unit/ai/test_state.py` - AgentState tests
- `tests/unit/ai/test_graph.py` - StateGraph tests
- `tests/unit/ai/test_decorator.py` - Decorator tests
- `tests/unit/ai/tools/test_registry.py` - Registry tests
- `tests/unit/ai/tools/test_decorator.py` - Decorator tests
- `tests/unit/ai/tools/test_types.py` - Types tests
- `tests/unit/ai/test_checkpointer.py` - Checkpointer tests
- `tests/integration/ai/test_graph_execution.py` - Graph execution tests
- `tests/integration/ai/test_streaming.py` - Streaming tests
- `tests/integration/ai/tools/test_tool_execution.py` - Tool execution tests
- `tests/integration/ai/tools/test_existing_tools.py` - Migrated tools tests
- `tests/performance/ai/test_agent_performance.py` - Agent performance
- `tests/performance/ai/test_streaming_performance.py` - Streaming performance
- `tests/performance/ai/test_tool_performance.py` - Tool performance
- `tests/security/ai/test_tool_rbac.py` - RBAC tests
- `tests/regression/ai/test_existing_functionality.py` - Regression tests

**Documentation:**
- `docs/02-architecture/decisions/009-langgraph-rewrite.md` - ADR for LangGraph rewrite
- `docs/02-architecture/ai/tool-development-guide.md` - Tool development guide
- `docs/02-architecture/ai/troubleshooting.md` - Troubleshooting guide

### Files to Modify

**Core AI:**
- `backend/app/ai/agent_service.py` - Refactor to use StateGraph, update streaming logic
- `backend/app/ai/tools/__init__.py` - Replace with registry-based tool discovery

**Tests:**
- `backend/tests/conftest.py` - Add AI-related fixtures (mock_llm, mock_tools, etc.)

**Documentation:**
- `docs/02-architecture/ai/api-reference.md` - Update with new public interfaces

### Files to Delete

None - keeping old implementation as reference during migration

---

## Rollback Strategy

### Feature Flag Approach

**Implementation:**
- Add feature flag in `backend/app/core/config.py`: `USE_LANGGRAPH_AGENT = True`
- Check flag in `AgentService.__init__()`:
  - If `True`: Use new StateGraph implementation
  - If `False`: Use old custom loop implementation
- Set flag via environment variable: `USE_LANGGRAPH_AGENT=true`

**Rollback Procedure:**
1. Set environment variable: `USE_LANGGRAPH_AGENT=false`
2. Restart backend service
3. System reverts to old implementation
4. No database changes required

### Database Rollback

**State Persistence:**
- LangGraph checkpointer uses separate table(s) from conversation messages
- If rollback needed, new checkpointer tables can be dropped
- Existing conversation messages in `ai_conversation_messages` table untouched

**Migration:**
- No schema migrations required for this iteration
- Checkpointer creates its own schema on first run

### Code Rollback

**Git Branch Strategy:**
- Create feature branch: `feature/langgraph-rewrite`
- Keep old implementation tagged: `BEFORE_LANGGRAPH_REWRITE`
- If critical issues arise:
  1. Revert to `BEFORE_LANGGRAPH_REWRITE` tag
  2. Hotfix old implementation if needed
  3. Re-approach LangGraph migration with lessons learned

**Graceful Degradation:**
- If StateGraph fails to compile, log error and fall back to old implementation
- If tool execution fails, return error message to user
- If streaming fails, fall back to non-streaming response

---

## Definition of Done

### Overall Iteration Completion Criteria

**Code Implementation:**
- [ ] All 28 tasks completed (Phase 1-4)
- [ ] StateGraph compiles and executes successfully
- [ ] @ai_tool decorator wraps service methods correctly
- [ ] Tool registry auto-discovers all tools
- [ ] Both existing tools migrated to new pattern
- [ ] WebSocket streaming works with astream_events()
- [ ] Checkpointer saves and restores state
- [ ] Graph visualization export works
- [ ] Tool execution monitoring implemented
- [ ] Tool templates created for CRUD, Change Orders, Analysis

**Testing:**
- [ ] 80%+ test coverage for agent (`app/ai/`)
- [ ] 80%+ test coverage for tools (`app/ai/tools/`)
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] All performance benchmarks passing (<500ms agent, <100ms streaming, <100ms tools)
- [ ] All security tests passing (RBAC enforcement)
- [ ] All regression tests passing (zero functionality breakage)

**Code Quality:**
- [ ] Zero MyPy errors (strict mode)
- [ ] Zero Ruff errors
- [ ] All code follows project coding standards
- [ ] All functions have type hints
- [ ] All public functions have docstrings

**Documentation:**
- [ ] Architecture Decision Record created and approved
- [ ] Tool Development Guide created and reviewed by domain expert
- [ ] API documentation updated
- [ ] Troubleshooting guide created
- [ ] Code examples tested and working

**Review:**
- [ ] Code review approved by domain expert
- [ ] Security review completed (RBAC enforcement)
- [ ] Performance review completed (benchmarks met)
- [ ] Architecture review completed (scalability confirmed)

**Deployment Readiness:**
- [ ] Feature flag implemented and tested
- [ ] Rollback procedure documented and tested
- [ ] Monitoring and logging in place
- [ ] Error handling comprehensive
- [ ] Known issues documented

### Phase 1: Core LangGraph Refactoring (5 points)

**Definition of Done:**
- [ ] `AgentState` defined as `TypedDict` in `backend/app/ai/state.py`
- [ ] `StateGraph` created in `backend/app/ai/graph.py`
- [ ] Agent node implemented with `bind_tools()`
- [ ] `ToolNode` from `langgraph.prebuilt` integrated
- [ ] Conditional edges implemented for routing
- [ ] `MemorySaver` checkpointer added
- [ ] Streaming implemented with `app.astream_events()`
- [ ] Unit tests for graph compilation pass
- [ ] Unit tests for agent node pass
- [ ] Unit tests for ToolNode integration pass
- [ ] Integration tests for full graph execution pass
- [ ] Streaming tests pass
- [ ] 80%+ test coverage for graph module

### Phase 2: Tool Standardization (3 points)

**Definition of Done:**
- [ ] `@ai_tool` decorator implemented in `backend/app/ai/tools/decorator.py`
- [ ] Tool registry implemented in `backend/app/ai/tools/registry.py`
- [ ] `ToolContext` and `ToolMetadata` types defined
- [ ] `list_projects` tool migrated (wraps `ProjectService.get_projects()`)
- [ ] `get_project` tool migrated (wraps `ProjectService.get_project()`)
- [ ] Unit tests for decorator pass
- [ ] Unit tests for registry pass
- [ ] Integration tests for tool execution pass
- [ ] Regression tests show migrated tools produce same results
- [ ] 80%+ test coverage for tools module
- [ ] Developer documentation for creating new tools

### Phase 3: Migration & Expansion (3 points)

**Definition of Done:**
- [ ] Graph visualization export works
- [ ] Tool execution monitoring implemented
- [ ] CRUD tool template created with examples
- [ ] Change Order tool template created with examples
- [ ] Analysis tool template created with examples
- [ ] All integration tests pass
- [ ] All regression tests pass
- [ ] Performance benchmarks meet targets
- [ ] Load tests pass

### Phase 4: Testing & Documentation (2 points)

**Definition of Done:**
- [ ] Performance benchmarks complete and passing
- [ ] Security tests complete and passing
- [ ] Architecture Decision Record created and approved
- [ ] Tool Development Guide created and reviewed
- [ ] API documentation updated
- [ ] Troubleshooting guide created
- [ ] Zero MyPy errors
- [ ] Zero Ruff errors
- [ ] 80%+ coverage maintained
- [ ] All tests passing
- [ ] Team training completed

---

## Documentation References

### Required Reading

**Architecture Documentation:**
- [Architecture Overview](/home/nicola/dev/backcast_evs/docs/02-architecture/README.md)
- [Backend Coding Standards](/home/nicola/dev/backcast_evs/docs/02-architecture/backend/coding-standards.md)
- [API Conventions](/home/nicola/dev/backcast_evs/docs/02-architecture/cross-cutting/api-conventions.md)
- [Security Practices](/home/nicola/dev/backcast_evs/docs/02-architecture/cross-cutting/security-practices.md)

**Product Documentation:**
- [Sprint Backlog](/home/nicola/dev/backcast_evs/docs/03-project-plan/sprint-backlog.md)
- [Product Glossary](/home/nicola/dev/backcast_evs/docs/01-product-scope/glossary.md)

### Code References

**Key Implementation Files:**
- [Agent Service](/home/nicola/dev/backcast_evs/backend/app/ai/agent_service.py) - Current implementation (919 lines)
- [Tools Implementation](/home/nicola/dev/backcast_evs/backend/app/ai/tools/__init__.py) - Current tools (229 lines)
- [LLM Client](/home/nicola/dev/backcast_evs/backend/app/ai/llm_client.py) - LLM client factory
- [AI Schemas](/home/nicola/dev/backcast_evs/backend/app/models/schemas/ai.py) - Pydantic schemas

**Service Layer (to wrap):**
- [ProjectService](/home/nicola/dev/backcast_evs/backend/app/services/project.py) - Project operations
- [CostElementService](/home/nicola/dev/backcast_evs/backend/app/services/cost_element_service.py) - Cost element operations
- [ChangeOrderService](/home/nicola/dev/backcast_evs/backend/app/services/change_order_service.py) - Change order operations
- [WBEService](/home/nicola/dev/backcast_evs/backend/app/services/wbe.py) - WBE operations

**Test Patterns:**
- [Test Configuration](/home/nicola/dev/backcast_evs/backend/tests/conftest.py) - Fixtures and test setup
- [Example Unit Test](/home/nicola/dev/backcast_evs/backend/tests/unit/ai/test_llm_client.py) - AI unit test pattern
- [Example Integration Test](/home/nicola/dev/backcast_evs/backend/tests/integration/test_projects.py) - Integration test pattern

**External References:**
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph 1.0 Reference](https://langchain-ai.github.io/langgraph/reference/)
- [LangChain Core Tools](https://python.langchain.com/docs/modules/tools/)

---

## Prerequisites

### Technical Prerequisites

- [x] Python 3.12+ installed
- [x] PostgreSQL 15+ running
- [x] Database migrations applied
- [x] Dependencies installed (LangGraph 1.0.10+, langchain-core>=0.3.0)
- [x] Test database configured
- [x] WebSocket test client available

### Documentation Prerequisites

- [x] Analysis phase approved
- [x] Architecture docs reviewed
- [x] LangGraph domain expert available
- [x] Service layer patterns understood
- [x] RBAC system understood

### Environmental Prerequisites

- [x] Development environment configured
- [x] CI/CD pipeline available
- [x] Test data seeding scripts ready
- [x] Performance benchmarking tools available

---

## Next Steps: Proceed to DO Phase

This PLAN phase is complete. The implementation plan is ready for DO phase execution:

1. **Backend DO Executor** will execute Phase 1 tasks (Core LangGraph Refactoring)
2. **Backend DO Executor** will execute Phase 2 tasks (Tool Standardization)
3. **Backend DO Executor** will execute Phase 3 tasks (Migration & Expansion)
4. **Backend DO Executor** will execute Phase 4 tasks (Testing & Documentation)

**DO Phase Instructions:**
- Follow TDD: Write tests first, watch them fail, implement, watch them pass
- Use the task dependency graph to parallelize work where possible
- Create feature branch: `feature/langgraph-rewrite`
- Run quality gates after each task: MyPy, Ruff, coverage
- Update task status in project tracking

**CHECK Phase Instructions:**
- Verify all success criteria met
- Run full test suite
- Check code quality metrics
- Validate performance benchmarks
- Review documentation completeness

**PLAN Phase Complete** ✓

This plan provides a comprehensive, actionable roadmap for implementing the LangGraph Agent Enhancement with clear success criteria, task dependencies, and quality gates. The DO phase can now proceed with confidence.
