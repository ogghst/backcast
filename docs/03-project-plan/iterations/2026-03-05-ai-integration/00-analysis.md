# Analysis: LangGraph AI Component & OpenAI-Compatible LLM Configuration

**Date:** 2026-03-05
**Status:** ANALYSIS COMPLETE - Awaiting User Feedback
**Iteration:** AI Integration Phase 1

---

## 1. Requirements Summary

### Source Documents
- `docs/01-product-scope/functional-requirements.md` - Section 12.6 (AI Integration)
- `docs/02-architecture/01-bounded-contexts.md` - Section 10 (AI/ML Integration)

### User-Specified Scope

| Requirement | Decision |
|-------------|----------|
| **LangGraph Component** | Included |
| **OpenAI-Compatible Configuration** | Included |
| **WebSocket Streaming** | DEFERRED |
| **Configuration Storage** | Database tables (UI-configurable) |
| **Provider Support** | Multi-provider from start (OpenAI, Azure, self-hosted) |
| **Frontend** | Backend only - frontend deferred |
| **Initial Tools** | Read-only: project list operations |
| **Testing Strategy** | TDD, real API config via seed data |
| **Integration Tests** | DEFERRED |

---

## 2. Current State Assessment

### 2.1 Existing Infrastructure

**Database Patterns:**
- `SimpleEntityBase` pattern for non-versioned config entities (`backend/app/core/base/base.py`)
- `TemporalService` for versioned entities with audit trail
- JSONB columns for flexible configuration storage
- Alembic migrations for schema changes

**Service Layer:**
- Standard CRUD services in `backend/app/services/`
- Dependency injection via `Depends(get_db)`
- RBAC enforcement via `RoleChecker`

**API Routes:**
- RESTful endpoints in `backend/app/api/routes/`
- Pydantic schemas for validation (`backend/app/models/schemas/`)

**Seed Data:**
- JSON-based seeding in `backend/seed/`
- `DataSeeder` class in `backend/app/db/seeder.py`

### 2.2 Gap Analysis

| Component | Current State | Required State |
|-----------|---------------|----------------|
| AI Provider Config | Does not exist | Database tables with CRUD |
| LLM Client | Does not exist | OpenAI-compatible client abstraction |
| LangGraph Integration | Does not exist | Agent orchestration with tools |
| Tool Layer | Does not exist | Project list tool (read-only) |
| Chat API | Does not exist | Chat endpoint with session management |
| Dependencies | Not installed | langchain-core, langgraph, openai |

---

## 3. Architecture Design

### 3.1 Database Schema (Non-Versioned)

```
┌─────────────────┐     ┌──────────────────────────┐
│  ai_providers   │────<│  ai_provider_configs     │
│  - id           │     │  - provider_id (FK)      │
│  - code         │     │  - config_key            │
│  - name         │     │  - config_value          │
│  - provider_type│     │  - is_encrypted          │
│  - base_url     │     └──────────────────────────┘
│  - is_active    │
└────────┬────────┘
         │
         │     ┌─────────────────┐     ┌────────────────────────┐
         └────<│  ai_models      │     │  ai_assistant_configs  │
              │  - provider_id   │────<│  - model_id (FK)       │
              │  - model_id      │     │  - name                │
              │  - display_name  │     │  - system_prompt       │
              │  - context_window│     │  - temperature         │
              │  - is_active     │     │  - tool_permissions    │
              └─────────────────┘     └────────────────────────┘
                                              │
                                              │
              ┌───────────────────────────────┘
              │
              ▼     ┌──────────────────────────┐
┌───────────────────│  ai_conversation_sessions│
│                   │  - user_id               │
│                   │  - assistant_config_id   │
│                   │  - project_id            │
│                   │  - branch                │
│                   └───────────┬──────────────┘
│                               │
│                               ▼
│                   ┌──────────────────────────┐
│                   │ai_conversation_messages  │
│                   │  - session_id (FK)       │
│                   │  - role                  │
│                   │  - content               │
│                   │  - tool_calls            │
│                   └──────────────────────────┘
```

### 3.2 Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                                 │
│  /api/v1/ai/providers  /api/v1/ai/assistants  /api/v1/ai/chat   │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────┐
│                      Service Layer                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │AIConfigService  │  │ AIAgentService  │  │    Tools        │  │
│  │ - CRUD config   │  │ - LangGraph     │  │ - list_projects │  │
│  │ - Encryption    │  │ - Tool calling  │  │ - get_project   │  │
│  └─────────────────┘  └────────┬────────┘  └─────────────────┘  │
│                                │                                 │
└────────────────────────────────┼────────────────────────────────┘
                                 │
┌────────────────────────────────┼────────────────────────────────┐
│                      LLM Client Layer                           │
│  ┌─────────────────────────────┴─────────────────────────────┐  │
│  │              OpenAICompatibleClient                        │  │
│  │  - OpenAI (api.openai.com)                                │  │
│  │  - Azure OpenAI (custom endpoint)                         │  │
│  │  - Ollama (localhost:11434)                               │  │
│  │  - Any OpenAI-compatible endpoint                         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Tool Execution Flow

```
User Message → AIAgentService.chat()
                    │
                    ▼
            Build Message History
            (system + conversation)
                    │
                    ▼
            LLMClient.chat_completion()
            (with tools definition)
                    │
                    ▼
            ┌───────────────────┐
            │ Tool Calls?       │
            └─────────┬─────────┘
                 Yes  │   No
            ┌─────────┼─────────┐
            ▼                   ▼
    Execute Tools          Return Response
    (RBAC checked)              │
            │                   │
            ▼                   │
    Tool Results               │
            │                   │
            ▼                   │
    Re-call LLM ◄───────────────┘
    (with tool results)
            │
            ▼
    Return Final Response
```

---

## 4. Implementation Breakdown

### 4.1 Phase 1: Foundation (13 points)

| Task | File | Description |
|------|------|-------------|
| E09-U01 | `alembic/versions/*_create_ai_tables.py` | Database migration |
| E09-U01 | `app/models/domain/ai_provider.py` | Domain models |
| E09-U01 | `app/models/schemas/ai.py` | Pydantic schemas |
| E09-U02 | `app/services/ai_config_service.py` | Config CRUD + encryption |
| E09-U02 | `seed/ai_providers.json` | Provider seed data |
| E09-U03 | `seed/ai_assistant_configs.json` | Default assistant config |

### 4.2 Phase 2: Core Chat (16 points)

| Task | File | Description |
|------|------|-------------|
| E09-U04 | `app/ai/llm_client.py` | OpenAI-compatible client |
| E09-U04 | `app/ai/agent_service.py` | LangGraph orchestration |
| E09-U05 | `app/ai/tools/__init__.py` | Project tools |
| E09-U04 | `app/api/routes/ai_chat.py` | Chat endpoints |
| E09-U05 | `app/api/routes/ai_config.py` | Config endpoints |

### 4.3 Dependencies to Add

```toml
# backend/pyproject.toml
dependencies = [
    # ... existing ...
    "langchain-core>=0.3.0",
    "langgraph>=0.2.0",
    "openai>=1.50.0",
]
```

---

## 5. Key Patterns to Follow

### 5.1 SimpleEntityBase Pattern (for AI config)
Reference: `backend/app/core/base/base.py`

```python
class AIProvider(SimpleEntityBase):
    __tablename__ = "ai_providers"
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # ... no valid_time, transaction_time, branch fields
```

### 5.2 Service Layer Pattern
Reference: `backend/app/services/department.py`

```python
class AIConfigService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_provider(self, provider_id: UUID) -> AIProvider | None:
        return await self.session.get(AIProvider, provider_id)
```

### 5.3 API Route Pattern with RBAC
Reference: `backend/app/api/routes/departments.py`

```python
@router.get("", dependencies=[Depends(RoleChecker("ai-config-read"))])
async def list_providers(...) -> dict[str, Any]:
    ...
```

---

## 6. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| API key exposure in logs | HIGH | Mark as encrypted, mask in API responses, never log |
| Tool permission bypass | HIGH | Double-check RBAC in tool execution, not just route |
| LLM timeout | MEDIUM | 30s timeout with graceful error message |
| Infinite tool call loops | MEDIUM | Max 5 iterations in agent loop |
| Provider endpoint unavailable | LOW | Graceful degradation with error message |

---

## 7. Success Criteria

### Must Have (MVP)
- [ ] Admin can configure AI providers via API
- [ ] Admin can set API keys securely (encrypted storage)
- [ ] Admin can create assistant configs with tool permissions
- [ ] User can send natural language message and receive response
- [ ] AI can list projects using `list_projects` tool
- [ ] RBAC enforced for all tool operations
- [ ] All unit tests pass
- [ ] MyPy and Ruff checks pass

### Deferred
- [ ] WebSocket streaming
- [ ] Frontend integration
- [ ] Additional tools (WBE, Cost Element, EVM)
- [ ] Integration tests with real LLM

---

## 8. Questions for User Feedback

### Confirmed Decisions
1. ✅ **Scope**: LangGraph + OpenAI config only (WebSocket deferred)
2. ✅ **Configuration**: Database storage with UI management
3. ✅ **Multi-provider**: From start (OpenAI, Azure, self-hosted)
4. ✅ **Frontend**: Backend only for this iteration
5. ✅ **Initial Tools**: Project list (read-only)
6. ✅ **Testing**: TDD with mock responses

### No Further Questions
All requirements have been clarified through the user's initial feedback. Ready to proceed to PLAN phase.

---

## 9. Next Steps

1. **User Approval**: Review this analysis and approve approach
2. **PLAN Phase**: Create detailed implementation plan with file-by-file breakdown
3. **DO Phase**: Implement following TDD methodology
4. **CHECK Phase**: Verify all tests pass, run quality checks
5. **ACT Phase**: Update documentation, create sprint in project plan

---

## 10. References

- [Architecture: AI/ML Integration Context](../../02-architecture/01-bounded-contexts.md#10-aiml-integration)
- [Functional Requirements: AI Integration](../../01-product-scope/functional-requirements.md#126-ai-integration)
- [Epic Template](../epics.md)
- [Sprint Backlog Template](../sprint-backlog.md)
