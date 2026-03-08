# Plan: AI Integration Phase 1

**Created:** 2026-03-07  
**Based on:** [00-analysis.md](./00-analysis.md)  
**Approved Option:** LangGraph Component with OpenAI-compatible LLM Configuration

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: LangGraph orchestration with database-backed UI-configurable AI Providers and Assistant Configurations, and read-only project listing tools.
- **Architecture**:
  - API and Service layers for AI config and Chat.
  - LLM Client layer wrapping OpenAI/compatible endpoints.
  - LangGraph to orchestrate tool calling and LLM interactions.
- **Key Decisions**:
  - WebSocket streaming is deferred. Frontend implementation is deferred (Backend API only).
  - Configuration stored in relational database tables.
  - Testing uses TDD with mock LLM responses. Integration tests with real LLMs are deferred.

### Success Criteria

**Functional Criteria:**

- [ ] Admin can configure AI providers via API VERIFIED BY: Unit Tests
- [ ] Admin can set API keys securely (encrypted storage) VERIFIED BY: Unit Tests
- [ ] Admin can create assistant configs with tool permissions VERIFIED BY: Unit Tests
- [ ] User can send natural language message and receive response VERIFIED BY: Unit Tests (mocked)
- [ ] AI can list projects using `list_projects` tool VERIFIED BY: Unit Tests (mocked)
- [ ] RBAC enforced for all tool operations VERIFIED BY: Unit Tests

**Technical Criteria:**

- [ ] Security: API Keys are not exposed in logs or API responses VERIFIED BY: Code Review & Validation Tests
- [ ] Code Quality: mypy strict + ruff clean VERIFIED BY: CI pipeline

**Business Criteria:**

- [ ] AI functionality is established at the backend level, ready for frontend integration VERIFIED BY: API functionality

### Scope Boundaries

**In Scope:**

- Database schema migration for AI tables.
- Services for configuring AI providers and assistants.
- LangGraph orchestration service.
- Read-only Project list tool for the agent.
- API endpoints for configuration and chat.

**Out of Scope:**

- WebSocket streaming.
- Frontend integration.
- Additional tools (WBE, Cost Element, EVM).
- Integration tests calling real LLMs.

---

## Work Decomposition

### Task Breakdown

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | --- | --- | --- | --- | --- |
| 1 | Add LLM dependencies | `backend/pyproject.toml` | None | Poetry install succeeds | Low |
| 2 | Create DB schema & migrations | `alembic/versions/*_create_ai_tables.py`, `app/models/domain/ai_provider.py` | Task 1 | Alembic upgrade succeeds | Med |
| 3 | Create schemas & Config CRUD Service | `app/models/schemas/ai.py`, `app/services/ai_config_service.py` | Task 2 | Config operations and encryption verified | Med |
| 4 | Seed Data for Configs | `seed/ai_providers.json`, `seed/ai_assistant_configs.json` | Task 3 | Seeder inserts records correctly | Low |
| 5 | Implement LLM Client | `app/ai/llm_client.py` | Task 3 | Client handles completion requests | Med |
| 6 | Implement Project Tool | `app/ai/tools/__init__.py` | None | Tool lists projects accurately | Low |
| 7 | LangGraph Agent Service | `app/ai/agent_service.py` | Task 5, 6 | Agent routes correctly and uses tools | High |
| 8 | Config & Chat API Routes | `app/api/routes/ai_chat.py`, `app/api/routes/ai_config.py` | Task 3, 7 | API endpoints return expected responses | Med |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| --- | --- | --- | --- |
| Admin can configure AI providers | T-001 | `tests/unit/services/test_ai_config.py` | Create, read, update provider |
| API keys are encrypted securely | T-002 | `tests/unit/services/test_ai_config.py` | Verify encryption in DB, masked in API |
| Chat with Mock LLM | T-003 | `tests/unit/ai/test_agent_service.py` | Agent correctly formats and returns response |
| Agent calls project list tool | T-004 | `tests/unit/ai/test_agent_service.py` | Tool executes and returns project data |
| RBAC check on API and Tools | T-005 | `tests/unit/api/test_ai_routes.py` | Missing permissions yield 403 Forbidden |

---

## Test Specification

### Test Hierarchy

```text
├── Unit Tests
│   ├── tests/unit/services/test_ai_config.py
│   ├── tests/unit/ai/test_llm_client.py
│   ├── tests/unit/ai/test_agent_service.py
│   └── tests/unit/api/test_ai_routes.py
```

### Test Cases (first 5)

| Test ID | Test Name | Criterion | Type | Verification |
| --- | --- | --- | --- | --- |
| T-001 | test_create_ai_provider | Admin configure | Unit | Success |
| T-002 | test_provider_key_encryption | Secure API | Unit | Success |
| T-003 | test_agent_chat_routing | Chat response | Unit | Success |
| T-004 | test_agent_tool_execution | List projects tool | Unit | Success |
| T-005 | test_chat_api_rbac_enforcement | RBAC enforced | Unit | Success |

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| Technical | API key exposure in logs/API | Low | High | Mask in API, mark as encrypted in DB, avoid logging |
| Security | Tool permission bypass | Low | High | Enforce RBAC at tool execution level, not just API |
| Technical | Infinite tool call loops | Med | Med | Set max 5 iterations in LangGraph loop |
| Technical | LLM timeout | Med | Med | Add 30s timeout with graceful fallback/error msg |

---

## Documentation References

### Required Reading

- Coding Standards: [`backend/coding-standards.md`](../../02-architecture/backend/coding-standards.md)
- Architecture: [`01-bounded-contexts.md`](../../02-architecture/01-bounded-contexts.md)
- Requirements: [`functional-requirements.md`](../../01-product-scope/functional-requirements.md)

### Code References

- Backend pattern: `backend/app/core/base/base.py` (SimpleEntityBase)
- Service pattern: `backend/app/services/department.py`

---

## Prerequisites

### Technical

- [ ] Database migrations applied
- [ ] Dependencies installed
- [ ] Environment configured

### Documentation

- [x] Analysis phase approved
- [x] Architecture docs reviewed
