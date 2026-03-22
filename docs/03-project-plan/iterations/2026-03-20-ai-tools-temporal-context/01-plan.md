# Plan: AI Tools Temporal Context Integration

**Created:** 2026-03-20
**Based on:** [`00-analysis.md`](./00-analysis.md)
**Approved Option:** Option 1 - Minimal Extension

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 - Minimal Extension
- **Architecture**: Extend existing ToolContext dataclass and WebSocket protocol with temporal parameters (as_of, branch_name, branch_mode). Update all versioned entity tools to use temporal params from context. Frontend reads from Time Machine store on every WebSocket message.
- **Key Decisions**:
  - Strict enforcement: AI ONLY sees data in temporal context (cannot query outside)
  - Both fields: branch_id (UUID for session) AND branch_name (string for temporal)
  - System prompt mentions temporal context only when relevant
  - Service layer handles validation (no new validation code)
  - Only versioned entity tools use temporal context

### Success Criteria

**Functional Criteria:**

- [ ] AI tools receive temporal parameters (as_of, branch_name, branch_mode) on every WebSocket message VERIFIED BY: Integration test T-004
- [ ] AI tools use temporal parameters when querying versioned entities VERIFIED BY: Integration tests T-005, T-006
- [ ] AI responses mention temporal context when branch != "main" or as_of is set VERIFIED BY: Unit test T-003
- [ ] Frontend sends temporal params from Time Machine store on every message VERIFIED BY: Frontend test T-007
- [ ] Default values applied correctly (as_of=None, branch="main", branch_mode="merged") VERIFIED BY: Unit tests T-001, T-002
- [ ] Backward compatible: existing AI chat works without temporal params VERIFIED BY: Integration test T-008

**Technical Criteria:**

- [ ] Performance: Temporal parameter overhead < 5ms per request VERIFIED BY: Performance benchmark
- [ ] Code Quality: MyPy strict mode (zero errors) VERIFIED BY: CI pipeline
- [ ] Code Quality: Ruff (zero errors) VERIFIED BY: CI pipeline
- [ ] Code Quality: ESLint (zero errors) VERIFIED BY: CI pipeline
- [ ] Test Coverage: ≥ 80% for modified code VERIFIED BY: Coverage report

**TDD Criteria:**

- [ ] All tests written before implementation code VERIFIED BY: DO phase log
- [ ] Each test failed first (documented in DO phase) VERIFIED BY: DO phase log
- [ ] Tests follow Arrange-Act-Assert pattern VERIFIED BY: Code review

### Scope Boundaries

**In Scope:**

- Backend: ToolContext extension (3 new fields)
- Backend: WSChatRequest schema extension (3 new fields)
- Backend: AgentService temporal param extraction and system prompt integration
- Backend: Project tools update (list_projects, get_project)
- Frontend: WebSocket client extension to send temporal params
- Testing: Unit tests for ToolContext, WSChatRequest, system prompt
- Testing: Integration tests for temporal isolation (as_of, branch, branch_mode)
- Testing: Frontend tests for WebSocket message structure

**Out of Scope:**

- WBE tools (deferred - only project tools in scope)
- Cost element tools (deferred)
- Change order tools (deferred)
- Budget tools (deferred)
- Forecast tools (deferred)
- Database migrations (no schema changes needed)
- Time Machine component UI changes (already implemented)
- Validation logic (service layer handles this)
- Non-versioned entity tools (user settings, AI configs)

---

## Work Decomposition

### Task Breakdown

| #   | Task                                  | Files                                                        | Dependencies     | Success Criteria                                                                          | Complexity |
| --- | ------------------------------------- | ------------------------------------------------------------ | ---------------- | ----------------------------------------------------------------------------------------- | ---------- |
| BE-001 | Extend ToolContext dataclass        | `/backend/app/ai/tools/types.py`                            | None             | ToolContext compiles, mypy passes, existing tests pass                                   | Low        |
| BE-002 | Extend WSChatRequest schema         | `/backend/app/models/schemas/ai.py`                         | None             | Schema compiles, optional fields have defaults                                           | Low        |
| BE-003 | Update AgentService chat_stream     | `/backend/app/ai/agent_service.py`                          | BE-001, BE-002   | Temporal params extracted, ToolContext receives params, backward compatible              | Medium     |
| BE-004 | Add system prompt temporal context  | `/backend/app/ai/agent_service.py`                          | BE-003           | System prompt includes context when relevant, excludes for defaults                      | Medium     |
| BE-005 | Update project tools (list_projects) | `/backend/app/ai/tools/project_tools.py`                    | BE-001           | list_projects uses temporal params, defaults applied, mypy passes                        | Low        |
| BE-006 | Update project tools (get_project)  | `/backend/app/ai/tools/project_tools.py`                    | BE-001           | get_project uses temporal params, defaults applied, mypy passes                           | Low        |
| FE-001 | Extend frontend WebSocket types     | `/frontend/src/features/ai/chat/types.ts`                    | None             | TypeScript types extended, no type errors                                                 | Low        |
| FE-002 | Update sendMessage to include temporal params | `/frontend/src/features/ai/chat/api/useStreamingChat.ts` | FE-001           | Temporal params read from Time Machine store, sent with every message                     | Medium     |
| TEST-001 | Write ToolContext unit tests       | `/backend/tests/ai/tools/test_temporal_context.py` (new)   | BE-001           | Tests pass, coverage ≥ 80%, temporal params verified                                     | Low        |
| TEST-002 | Write system prompt unit tests     | `/backend/tests/ai/test_system_prompt.py` (new)            | BE-004           | Tests pass, temporal context included/excluded correctly                                  | Low        |
| TEST-003 | Write temporal isolation integration tests | `/backend/tests/api/routes/integration/test_ai_temporal_integration.py` (new) | BE-005, BE-006 | Tests pass, as_of filtering works, branch isolation works, branch_mode works             | Medium     |
| TEST-004 | Write frontend temporal tests      | `/frontend/tests/ai/temporalContext.test.ts` (new)         | FE-002           | Tests pass, temporal params sent correctly, defaults handled                              | Low        |
| QA-001 | Backend quality checks             | All backend files                                           | All BE tasks     | Ruff zero errors, MyPy zero errors, tests pass                                           | Low        |
| QA-002 | Frontend quality checks             | All frontend files                                           | All FE tasks     | ESLint zero errors, tests pass, coverage ≥ 80%                                           | Low        |

**Task Ordering Principles:**

1. Backend foundation first (ToolContext, WSChatRequest)
2. Service layer before tools (AgentService before project_tools)
3. Frontend types before implementation (types.ts before useStreamingChat.ts)
4. Tests written alongside implementation (TDD)
5. Quality checks after all implementation

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File                                                   | Expected Behavior |
| -------------------- | ------- | ----------------------------------------------------------- | ----------------- |
| AI tools receive temporal params on every message | T-004 | `tests/api/routes/integration/test_ai_temporal_integration.py` | WebSocket message includes as_of, branch_name, branch_mode |
| AI tools use temporal params for queries | T-005, T-006 | `tests/api/routes/integration/test_ai_temporal_integration.py` | Service layer called with temporal params, data filtered correctly |
| AI responses mention temporal context when relevant | T-003 | `tests/ai/test_system_prompt.py` | System prompt includes temporal note for non-main/historical |
| Frontend sends temporal params from Time Machine | T-007 | `frontend/tests/ai/temporalContext.test.ts` | WebSocket.send() called with as_of, branch_name, branch_mode from store |
| Default values applied correctly | T-001, T-002 | `tests/ai/tools/test_temporal_context.py` | None values handled, defaults to "main", "merged", None |
| Backward compatible | T-008 | `tests/api/routes/integration/test_ai_temporal_integration.py` | Missing temporal params doesn't break chat |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests
│   ├── ToolContext temporal params (T-001, T-002)
│   └── System prompt temporal context (T-003)
├── Integration Tests
│   ├── Temporal parameter propagation (T-004)
│   ├── Historical date filtering (T-005)
│   ├── Branch isolation (T-006)
│   └── Backward compatibility (T-008)
└── Frontend Tests
    └── WebSocket temporal params (T-007)
```

### Test Cases

| Test ID | Test Name                                                | Criterion | Type            | Expected Result |
| ------- | -------------------------------------------------------- | --------- | --------------- | --------------- |
| T-001   | `test_toolcontext_with_temporal_params_accepts_values`  | AC-5      | Unit            | ToolContext stores as_of, branch_name, branch_mode |
| T-002   | `test_toolcontext_defaults_to_none`                      | AC-5      | Unit            | ToolContext defaults to None for new fields |
| T-003   | `test_system_prompt_includes_temporal_context_when_branch_not_main` | AC-3 | Unit | Prompt includes "[TEMPORAL CONTEXT]" section with branch name |
| T-003b  | `test_system_prompt_includes_temporal_context_when_as_of_set` | AC-3 | Unit | Prompt includes date in "as of MMMM DD, YYYY" format |
| T-003c  | `test_system_prompt_excludes_temporal_context_for_defaults` | AC-3 | Unit | Prompt excludes "[TEMPORAL CONTEXT]" for main/now/merged |
| T-004   | `test_websocket_propagates_temporal_params`              | AC-1      | Integration     | AgentService.chat_stream() receives as_of, branch_name, branch_mode |
| T-005   | `test_ai_respects_historical_date_as_of`                 | AC-2      | Integration     | Project data filtered to state as_of date (old version shown) |
| T-006   | `test_ai_respects_branch_isolation_isolated_mode`        | AC-2      | Integration     | Only branch-specific data shown in isolated mode |
| T-006b  | `test_ai_respects_branch_mode_merged`                    | AC-2      | Integration     | Combined data from main + branch shown in merged mode |
| T-007   | `test_frontend_sends_temporal_params_from_time_machine`  | AC-1      | Frontend Unit   | WebSocket message includes as_of, branch_name, branch_mode from store |
| T-007b  | `test_frontend_sends_defaults_for_current_state`         | AC-5      | Frontend Unit   | WebSocket message includes null/main/merged for "now" state |
| T-008   | `test_backward_compatibility_missing_temporal_params`    | AC-6      | Integration     | Chat works normally when temporal params not sent |

### Test Infrastructure Needs

**Fixtures needed:**
- `mock_tool_context`: Factory for creating ToolContext with temporal params
- `db_session_with_projects`: Session with seeded project data at different timestamps
- `websocket_client_mock`: Mock WebSocket for testing message structure

**Mocks/stubs:**
- Time Machine store (frontend)
- WebSocket connection (integration tests)

**Database state:**
- Projects created/updated at different timestamps (for as_of testing)
- Projects in different branches (for branch isolation testing)

---

## Task Dependency Graph

```yaml
# Task Dependency Graph for AI Tools Temporal Context Integration
# This graph enables parallel execution by PDCA orchestrator

tasks:
  # Backend Foundation
  - id: BE-001
    name: "Extend ToolContext dataclass with temporal fields"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Extend WSChatRequest schema with temporal fields"
    agent: pdca-backend-do-executor
    dependencies: []

  # Service Layer (depends on foundation)
  - id: BE-003
    name: "Update AgentService to extract and pass temporal params"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002]

  - id: BE-004
    name: "Add temporal context to system prompt"
    agent: pdca-backend-do-executor
    dependencies: [BE-003]

  # Tool Updates (depend on ToolContext)
  - id: BE-005
    name: "Update list_projects tool to use temporal params"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-006
    name: "Update get_project tool to use temporal params"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  # Frontend Foundation (can run in parallel with backend)
  - id: FE-001
    name: "Extend frontend WebSocket types for temporal params"
    agent: pdca-frontend-do-executor
    dependencies: []

  # Frontend Implementation (depends on types)
  - id: FE-002
    name: "Update sendMessage to read from Time Machine store"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  # Testing (Unit tests can run after implementation)
  - id: TEST-001
    name: "Write ToolContext unit tests"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]
    kind: test

  - id: TEST-002
    name: "Write system prompt unit tests"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]
    kind: test

  # Integration tests (must run sequentially, share database)
  - id: TEST-003
    name: "Write temporal isolation integration tests"
    agent: pdca-backend-do-executor
    dependencies: [BE-005, BE-006]
    kind: test

  - id: TEST-004
    name: "Write frontend temporal context tests"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]
    kind: test

  # Quality Checks (run after all implementation)
  - id: QA-001
    name: "Backend quality checks (ruff, mypy, tests)"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002, BE-003, BE-004, BE-005, BE-006, TEST-001, TEST-002, TEST-003]

  - id: QA-002
    name: "Frontend quality checks (eslint, tests, coverage)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002, TEST-004]
```

**Execution Levels:**
- **Level 0** (can run immediately): BE-001, BE-002, FE-001
- **Level 1**: BE-003, BE-005, BE-006, FE-002
- **Level 2**: BE-004, TEST-001, TEST-004
- **Level 3**: TEST-002, TEST-003
- **Level 4**: QA-001, QA-002

**Parallelization Opportunities:**
- Backend (BE-001, BE-002) and Frontend (FE-001) foundation can run in parallel
- Tool updates (BE-005, BE-006) can run in parallel
- Unit tests (TEST-001, TEST-002, TEST-004) can run in parallel
- Integration tests (TEST-003) must run sequentially due to database

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --------- | ----------- | ----------- | ------ | ---------- |
| Technical | Breaking existing AI chat functionality | Low | High | All new fields optional with defaults; backward compatibility test (T-008) |
| Technical | Type errors with temporal params (MyPy) | Medium | Medium | Follow existing patterns; run mypy after each task |
| Integration | Frontend-backend schema mismatch | Low | Medium | TypeScript types match Pydantic schema exactly |
| Integration | Time Machine store integration issues | Low | Medium | Store already exists; use getter methods directly |
| Performance | Temporal query overhead | Low | Low | Service layer already optimized; no new queries added |
| UX | AI mentions temporal context too often | Medium | Medium | System prompt instructs "ONLY when materially affects answer" |
| Testing | Flaky integration tests with database | Medium | Medium | Use proper test isolation; seed data consistently |

---

## Documentation References

### Required Reading

- Coding Standards: `/docs/02-architecture/coding-standards.md`
- Temporal Query Reference: `/docs/02-architecture/cross-cutting/temporal-query-reference.md`
- EVCS Architecture: `/docs/02-architecture/bounded-contexts/versioning/README.md`
- AI Chat System: `/docs/02-architecture/bounded-contexts/ai-chat/README.md`

### Code References

- Backend pattern (TemporalService): `/backend/app/core/versioning/service.py`
- Frontend pattern (Time Machine): `/frontend/src/stores/useTimeMachineStore.ts`
- Tool pattern (project_tools): `/backend/app/ai/tools/project_tools.py`
- Test pattern (conftest.py): `/backend/tests/conftest.py`

### Related Features

- AI Chat System (implemented)
- Time Machine Component (implemented)
- EVCS Temporal Queries (implemented)
- WebSocket Protocol (implemented)

---

## Prerequisites

### Technical

- [x] Database migrations applied (none needed for this feature)
- [x] Dependencies installed (backend uv sync, frontend npm install)
- [x] Environment configured (dev servers running)

### Documentation

- [x] Analysis phase approved
- [x] Architecture docs reviewed (temporal queries, EVCS)
- [x] AI tools pattern understood (InjectedToolArg)

---

## Summary

| Phase | Tasks | Estimated Time | Parallelizable |
| ----- | ----- | -------------- | -------------- |
| Backend Foundation | 4 | 2 hours | Partial (BE-001, BE-002 parallel) |
| Tool Updates | 2 | 1 hour | Yes (BE-005, BE-006 parallel) |
| Frontend Integration | 2 | 1 hour | Sequential (FE-001 → FE-002) |
| Testing | 4 | 3 hours | Partial (unit tests parallel, integration sequential) |
| Quality Checks | 2 | 0.5 hours | Yes (backend + frontend parallel) |
| **Total** | **14** | **7.5 hours** | **~40% parallelizable** |

**Critical Path:** BE-001 → BE-003 → BE-004 → TEST-002 → QA-001

**Parallel Opportunities:**
- Backend foundation + Frontend foundation
- Tool updates (BE-005, BE-006)
- Unit tests (TEST-001, TEST-002, TEST-004)
- Quality checks (QA-001, QA-002)

---

## Output

**File**: `docs/03-project-plan/iterations/2026-03-20-ai-tools-temporal-context/01-plan.md`

**Status**: Ready for DO Phase

**Next Steps**:
1. DO Phase: Execute tasks using pdca-backend-do-executor and pdca-frontend-do-executor
2. CHECK Phase: Run tests, verify all success criteria met
3. ACT Phase: Standardize temporal context patterns for future tools

---

**PLAN PHASE COMPLETE**
