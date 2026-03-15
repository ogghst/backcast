# Plan: AI Assistant Management Test Coverage to 80%+

**Created:** 2026-03-14
**Based on:** `00-analysis.md` (Option 1: Comprehensive Coverage Sprint)
**Estimated Effort:** 15-20 story points
**Target:** 80%+ test coverage across all AI Assistant Management components

---

## Phase 1: Scope & Success Criteria

### 1.1 Approved Approach Summary

**Selected Option:** Option 1 - Comprehensive Coverage Sprint

**Architecture:**
- Systematic test coverage improvement across all AI components
- Prioritized by business impact and current coverage gaps
- TDD approach: test specifications defined here, tests written in DO phase
- Fix failing tests first, then add new coverage

**Key Decisions:**
1. Fix 7 failing tests (related to `@ai_tool` decorator refactor) before adding new tests
2. Prioritize critical paths: agent service, RBAC, configuration, chat API
3. Use existing test fixtures and patterns from `tests/conftest.py`
4. Mock external dependencies (OpenAI API, database)
5. Focus on behavior testing, not implementation details

### 1.2 Success Criteria (Measurable)

**Functional Criteria:**

- [ ] All 7 currently failing tests pass VERIFIED BY: `pytest tests/unit/ai/tools/test_ai_tool_decorator.py tests/unit/ai/tools/test_rbac_tool_node.py tests/api/routes/test_ai_config_tools.py`
- [ ] `app/ai/agent_service.py` coverage ≥ 80% VERIFIED BY: `pytest --cov=app/ai/agent_service.py`
- [ ] `app/services/ai_config_service.py` coverage ≥ 80% VERIFIED BY: `pytest --cov=app/services/ai_config_service.py`
- [ ] `app/api/routes/ai_chat.py` coverage ≥ 80% VERIFIED BY: `pytest --cov=app/api/routes/ai_chat.py`
- [ ] `app/ai/tools/rbac_tool_node.py` coverage ≥ 80% VERIFIED BY: `pytest --cov=app/ai/tools/rbac_tool_node.py`
- [ ] Tool template coverage ≥ 60% VERIFIED BY: `pytest --cov=app/ai/tools/templates/`
- [ ] Overall AI component coverage ≥ 80% VERIFIED BY: `pytest --cov=app/ai --cov=app/services/ai_config_service --cov=app/api/routes/ai_config --cov=app/api/routes/ai_chat`

**Technical Criteria:**

- [ ] MyPy strict mode: 0 errors VERIFIED BY: `mypy app/ai/ app/services/ai_config_service.py app/api/routes/ai_*.py`
- [ ] Ruff linting: 0 errors VERIFIED BY: `ruff check app/ai/ app/services/ai_config_service.py app/api/routes/ai_*.py`
- [ ] All tests pass VERIFIED BY: `pytest tests/unit/ai/ tests/unit/services/test_ai_config_service.py tests/api/routes/`
- [ ] Test isolation VERIFIED BY: Tests pass when run individually and in suite
- [ ] Test performance VERIFIED BY: Full suite completes in < 3 minutes

**TDD Criteria:**

- [ ] Test specifications defined in this PLAN phase ✅ (this document)
- [ ] Tests written before implementation code (DO phase)
- [ ] Each test follows Arrange-Act-Assert pattern (DO phase)
- [ ] Tests are independent and repeatable (DO phase)

### 1.3 Scope Boundaries

**In Scope:**

- All AI Assistant Management components in `app/ai/`, `app/services/ai_config_service.py`, `app/api/routes/ai_*.py`
- Unit tests for services, agents, tools
- Integration tests for API routes
- Fixing 7 currently failing tests
- Adding new test cases to reach 80%+ coverage

**Out of Scope:**

- Frontend AI chat UI tests (separate epic)
- End-to-end UI testing with real LLM APIs
- Performance/load testing (separate test suite)
- Security penetration testing (separate test suite)
- Refactoring production code (only test changes)

---

## Phase 2: Work Decomposition

### 2.1 Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|---|---|---|---|---|
| **Phase 1: Fix Failing Tests** |
| 1.1 | Update `@ai_tool` decorator tests for new LangChain behavior | `tests/unit/ai/tools/test_ai_tool_decorator.py` | None | All 4 decorator tests pass | Medium |
| 1.2 | Update RBAC tool node tests for new implementation | `tests/unit/ai/tools/test_rbac_tool_node.py` | None | Both RBAC tests pass | Medium |
| 1.3 | Fix AI tools API test for updated schema format | `tests/api/routes/test_ai_config_tools.py` | 1.1, 1.2 | Tools schema test passes | Low |
| **Phase 2: Critical Path Coverage** |
| 2.1 | Add agent service orchestration tests | `tests/unit/ai/test_agent_service.py` | 1.1-1.3 | Coverage 11.6% → 80%+ | High |
| 2.2 | Add agent service error handling tests | `tests/unit/ai/test_agent_service.py` | 2.1 | Timeout, retry, error paths | High |
| 2.3 | Add AI config service CRUD tests | `tests/unit/services/test_ai_config_service.py` | None | Coverage 42.2% → 80%+ | Medium |
| 2.4 | Add AI config service encryption tests | `tests/unit/services/test_ai_config_service.py` | 2.3 | Encrypt/decrypt edge cases | Medium |
| 2.5 | Add chat API endpoint tests | `tests/api/routes/ai_chat/test_chat.py` (new) | 2.1, 2.3 | Coverage 22.8% → 80%+ | Medium |
| 2.6 | Add WebSocket streaming tests | `tests/api/routes/ai_chat/test_websocket.py` | 2.5 | Connection, message flow | High |
| 2.7 | Add RBAC tool node permission tests | `tests/unit/ai/tools/test_rbac_tool_node.py` | 1.2 | Coverage 32.5% → 80%+ | Medium |
| **Phase 3: Tool Template Coverage** |
| 3.1 | Add CRUD template tool tests | `tests/unit/ai/tools/test_crud_template.py` | None | Coverage 21.7% → 60%+ | Medium |
| 3.2 | Add change order template tests | `tests/unit/ai/tools/test_change_order_template.py` | None | Coverage 20.7% → 60%+ | Medium |
| 3.3 | Add analysis template tests | `tests/unit/ai/tools/test_analysis_template.py` | None | Coverage 17.7% → 60%+ | Medium |
| **Phase 4: Edge Cases & Verification** |
| 4.1 | Add LLM client error handling tests | `tests/unit/ai/test_llm_client.py` | None | Timeout, 503, invalid response | Low |
| 4.2 | Run full test suite and verify coverage | All test files | All above | Overall 80%+ coverage | Low |
| 4.3 | Run MyPy and Ruff quality checks | All source/test files | 4.2 | Zero errors | Low |

**Task Dependencies:**
```
1.1 ──┐
1.2 ──┼──> 1.3 ──┐
1.3 ──┘        │
                ├──> 2.1 ──> 2.2 ──┐
2.3 ────────────┤                │
                ├──> 2.5 ──> 2.6 ┤
2.7 ────────────┘                │
                                 ├──> 3.1 ──┐
3.2 ─────────────────────────────┤          ├──> 4.1 ──> 4.2 ──> 4.3
3.3 ─────────────────────────────┘          │
                                            │
2.4 ────────────────────────────────────────┘
```

### 2.2 Test-to-Requirement Traceability

#### Phase 1: Fix Failing Tests

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---------------------|---------|-----------|-------------------|
| All 7 failing tests pass | T-FIX-01 | `test_ai_tool_decorator.py::TestAIToolDecoratorErrorPaths::test_tool_context_type_fallback` | Decorator accepts context-like objects with matching attributes |
| All 7 failing tests pass | T-FIX-02 | `test_ai_tool_decorator.py::TestAIToolDecoratorErrorPaths::test_tool_missing_context_returns_error` | Decorator returns error when required context missing |
| All 7 failing tests pass | T-FIX-03 | `test_ai_tool_decorator.py::TestToLangChainToolBackwardCompatibility::test_to_langchain_tool_with_metadata_wraps_function` | LangChain tool wrapper includes metadata |
| All 7 failing tests pass | T-FIX-04 | `test_ai_tool_decorator.py::TestToLangChainToolBackwardCompatibility::test_to_langchain_tool_with_no_metadata_uses_function_name` | Tool without metadata uses function name |
| All 7 failing tests pass | T-FIX-05 | `test_rbac_tool_node.py::TestRBACToolNode::test_rbac_tool_node_permission_denied` | RBAC node denies unauthorized tool execution |
| All 7 failing tests pass | T-FIX-06 | `test_rbac_tool_node.py::TestRBACToolNode::test_rbac_tool_node_permission_granted` | RBAC node allows authorized tool execution |
| All 7 failing tests pass | T-FIX-07 | `test_ai_config_tools.py::test_getting_ai_tools_list_returns_valid_schemas` | AI tools API returns valid tool schemas |

#### Phase 2: Critical Path Coverage

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---------------------|---------|-----------|-------------------|
| Agent service ≥ 80% coverage | T-AGENT-01 | `test_agent_service.py::test_chat_creates_new_session` | New conversation session created when session_id is None |
| Agent service ≥ 80% coverage | T-AGENT-02 | `test_agent_service.py::test_chat_reuses_existing_session` | Existing session used when session_id provided |
| Agent service ≥ 80% coverage | T-AGENT-03 | `test_agent_service.py::test_chat_with_tool_calling` | Agent invokes tools when needed |
| Agent service ≥ 80% coverage | T-AGENT-04 | `test_agent_service.py::test_chat_streaming_response` | Streaming returns chunks incrementally |
| Agent service error paths | T-AGENT-05 | `test_agent_service.py::test_chat_timeout_returns_error` | Timeout after 30s returns error message |
| Agent service error paths | T-AGENT-06 | `test_agent_service.py::test_chat_llm_error_returns_error` | LLM API error propagates to user |
| Agent service error paths | T-AGENT-07 | `test_agent_service.py::test_chat_tool_error_returns_error` | Tool execution error returned in response |
| AI config service ≥ 80% coverage | T-CONFIG-01 | `test_ai_config_service.py::test_list_providers_filters_inactive` | list_providers respects include_inactive flag |
| AI config service ≥ 80% coverage | T-CONFIG-02 | `test_ai_config_service.py::test_create_provider_with_encryption` | API keys encrypted on creation |
| AI config service ≥ 80% coverage | T-CONFIG-03 | `test_ai_config_service.py::test_update_provider_modifies_fields` | Provider updates persist correctly |
| AI config service ≥ 80% coverage | T-CONFIG-04 | `test_ai_config_service.py::test_delete_provider_soft_delete` | Provider marked inactive (not hard deleted) |
| AI config service ≥ 80% coverage | T-CONFIG-05 | `test_ai_config_service.py::test_list_assistants_filters_by_active` | Only active assistants returned by default |
| AI config service ≥ 80% coverage | T-CONFIG-06 | `test_ai_config_service.py::test_create_assistant_validates_permissions` | Invalid tool permissions rejected |
| Encryption edge cases | T-CRYPTO-01 | `test_ai_config_service.py::test_decrypt_with_wrong_secret_raises_error` | Wrong SECRET_KEY raises ValueError |
| Encryption edge cases | T-CRYPTO-02 | `test_ai_config_service.py::test_encrypt_decrypt_roundtrip` | Encrypted value decrypts to original |
| Chat API ≥ 80% coverage | T-CHAT-01 | `test_chat.py::test_chat_endpoint_requires_auth` | 401 returned without valid token |
| Chat API ≥ 80% coverage | T-CHAT-02 | `test_chat.py::test_chat_validates_message_length` | Messages < 1 or > 10000 chars rejected |
| Chat API ≥ 80% coverage | T-CHAT-03 | `test_chat.py::test_chat_new_session_requires_assistant_id` | New session requires assistant_config_id |
| Chat API ≥ 80% coverage | T-CHAT-04 | `test_chat.py::test_chat_existing_session_validates_ownership` | User cannot access other users' sessions |
| Chat API ≥ 80% coverage | T-CHAT-05 | `test_chat.py::test_chat_inactive_assistant_rejected` | Inactive assistant returns 400 error |
| WebSocket streaming | T-WS-01 | `test_websocket.py::test_websocket_connection_authenticates` | WebSocket validates auth token |
| WebSocket streaming | T-WS-02 | `test_websocket.py::test_websocket_receives_messages` | Messages pushed to client in real-time |
| WebSocket streaming | T-WS-03 | `test_websocket.py::test_websocket_handles_disconnect` | Graceful disconnect on client close |
| RBAC tool node ≥ 80% coverage | T-RBAC-01 | `test_rbac_tool_node.py::test_rbac_check_called_before_execution` | Permission checked before tool runs |
| RBAC tool node ≥ 80% coverage | T-RBAC-02 | `test_rbac_tool_node.py::test_rbac_denied_returns_error_message` | Permission denied returns error ToolMessage |
| RBAC tool node ≥ 80% coverage | T-RBAC-03 | `test_rbac_tool_node.py::test_rbac_multiple_permissions_all_required` | All required permissions checked |
| RBAC tool node ≥ 80% coverage | T-RBAC-04 | `test_rbac_tool_node.py::test_rbac_no_permissions_allows_execution` | Tools without permissions execute freely |

#### Phase 3: Tool Template Coverage

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---------------------|---------|-----------|-------------------|
| CRUD template ≥ 60% coverage | T-TPL-CRUD-01 | `test_crud_template.py::test_list_projects_validates_pagination` | Limit max 100, skip validated |
| CRUD template ≥ 60% coverage | T-TPL-CRUD-02 | `test_crud_template.py::test_get_project_returns_404_for_invalid_id` | Invalid project_id returns error |
| CRUD template ≥ 60% coverage | T-TPL-CRUD-03 | `test_crud_template.py::test_create_project_validates_input` | Required fields validated |
| Change order template ≥ 60% coverage | T-TPL-CO-01 | `test_change_order_template.py::test_propose_change_order_validates_status` | Invalid status transition rejected |
| Change order template ≥ 60% coverage | T-TPL-CO-02 | `test_change_order_template.py::test_approve_change_order_checks_permission` | Approval requires permission |
| Analysis template ≥ 60% coverage | T-TPL-ANA-01 | `test_analysis_template.py::test_calculate_evm_metrics_validates_dates` | Invalid date ranges rejected |
| Analysis template ≥ 60% coverage | T-TPL-ANA-02 | `test_analysis_template.py::test_forecast_metrics_returns_projections` | Forecast returns future projections |

#### Phase 4: Edge Cases

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---------------------|---------|-----------|-------------------|
| LLM client error handling | T-LLM-01 | `test_llm_client.py::test_client_timeout_after_30_seconds` | Timeout raises TimeoutError |
| LLM client error handling | T-LLM-02 | `test_llm_client.py::test_client_503_raises_connection_error` | 503 status raises ConnectionError |
| LLM client error handling | T-LLM-03 | `test_llm_client.py::test_client_invalid_response_raises_error` | Malformed response raises ValueError |

---

## Phase 3: Test Data & Fixtures

### 3.1 Required Fixtures

**Database Fixtures** (exist in `tests/conftest.py`):
- `db_session` - Async database session
- `test_user` - Authenticated user with role
- `admin_user` - Admin user for privileged operations

**AI Fixtures** (to be added):
- `mock_llm_client` - Mock OpenAI client with predefined responses
- `mock_tool_context` - ToolContext with mocked services
- `test_ai_provider` - Sample AI provider in database
- `test_ai_assistant` - Sample AI assistant config
- `test_ai_session` - Sample conversation session

### 3.2 Test Data Sets

**Provider Configurations:**
- OpenAI provider (production-like)
- Azure OpenAI provider
- Self-hosted provider (localhost)

**Assistant Configurations:**
- Read-only assistant (project-read permission)
- Full-access assistant (all permissions)
- Inactive assistant (for validation tests)

**Conversation Scenarios:**
- New session (no prior context)
- Existing session (with history)
- Multi-turn conversation with tool calls

---

## Phase 4: Quality Gates

### 4.1 Pre-Commit Checklist

Before committing test code:

- [ ] All new tests fail initially (RED phase)
- [ ] Implementation code added to make tests pass (GREEN phase)
- [ ] Code refactored if needed (REFACTOR phase)
- [ ] MyPy strict mode passes (0 errors)
- [ ] Ruff linting passes (0 errors)
- [ ] Tests pass individually (`pytest path/to/test.py::test_name`)
- [ ] Tests pass in suite (`pytest tests/`)

### 4.2 Coverage Verification

After each task:

```bash
# Check coverage for specific component
pytest tests/path/to/test.py --cov=app/component --cov-report=term-missing

# Verify overall coverage
pytest tests/unit/ai/ tests/unit/services/test_ai_config_service.py \
  tests/api/routes/ --cov=app/ai --cov=app/services/ai_config_service \
  --cov=app/api/routes/ai_config --cov=app/api/routes/ai_chat \
  --cov-report=term --cov-fail-under=80
```

### 4.3 Definition of Done

A task is complete when:

1. All specified tests pass
2. Component coverage target met
3. MyPy and Ruff checks pass
4. Code reviewed (if team workflow)
5. No regressions in existing tests

---

## Phase 5: Risk Mitigation

### 5.1 Identified Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Failing tests require deep understanding of LangGraph | Medium | High | Research LangGraph patterns first |
| Test fixtures insufficient for complex scenarios | Medium | Medium | Add fixtures incrementally |
| Mock LLM client doesn't match real behavior | Low | Low | Use LangChain's built-in mocks |
| Database state pollution between tests | High | Low | Use transaction rollback fixtures |
| Test suite becomes slow | Medium | Medium | Use mocks for external calls |

### 5.2 Contingency Plans

**If coverage target cannot be reached:**
- Document gaps and create tech debt ticket
- Prioritize critical paths over edge cases
- Consider lowering target to 75% with justification

**If tests prove flaky:**
- Add explicit waits/timeout handling
- Improve fixture isolation
- Use pytest markers for integration vs unit

---

## References

**Analysis Phase:**
- [00-analysis.md](./00-analysis.md) - Detailed component analysis and coverage gaps

**Test Infrastructure:**
- `tests/conftest.py` - Existing fixtures
- `tests/mocks/` - Test doubles
- [Backend Coding Standards](../../02-architecture/backend/coding-standards.md) - Test patterns

**Component Documentation:**
- `app/ai/agent_service.py` - LangGraph orchestration
- `app/services/ai_config_service.py` - Configuration CRUD
- `app/api/routes/ai_*.py` - API endpoints

**PDCA Prompts:**
- [PLAN Phase Prompt](../../04-pdca-prompts/plan-prompt.md) - PLAN methodology

---

**PLAN COMPLETE** - Ready to proceed to DO phase
