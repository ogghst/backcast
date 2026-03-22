# Plan: AI Tool Risk Categorization and Execution Modes

**Created:** 2026-03-22
**Status:** PLAN COMPLETE - Ready for DO Phase
**Approved Option:** Option 1 - LangGraph Interrupt-Based Human-in-the-Loop

---

## Phase 1: Scope & Success Criteria

### 1.1 Approved Approach Summary

**Selected Option:** Option 1 - LangGraph Interrupt-Based Human-in-the-Loop

**Architecture:**
- Leverages LangGraph's native `interrupt()` mechanism for pausing execution
- Risk checking integrated into RBACToolNode alongside permission checks
- Non-blocking approval workflow via WebSocket messages
- Three execution modes: safe (low-risk only), standard (approval for critical), expert (all tools)

**Key Decisions:**
1. Use LangGraph interrupts for human-in-the-loop (native pattern, future-proof)
2. Non-blocking approvals (other chat sessions continue working)
3. Backward compatible default (tools without risk_level default to "high")
4. No database schema changes (use code annotations only)
5. Type-safe WebSocket protocol with discriminated unions

### 1.2 Success Criteria (Measurable)

**Functional Criteria:**

- [x] **FR-1: Tool Risk Categorization** VERIFIED BY: Unit tests for ToolMetadata.risk_level field
- [x] **FR-2: Execution Mode Selection** VERIFIED BY: Integration test for mode filtering logic
- [x] **FR-3: Approval Workflow** VERIFIED BY: E2E test for critical tool approval in standard mode
- [x] **FR-4: Mode Persistence** VERIFIED BY: Integration test for localStorage persistence
- [x] **FR-5: Visual Indicators** VERIFIED BY: E2E test for mode badge and tool risk display
- [x] **FR-6: RBAC Integration** VERIFIED BY: Integration test for combined RBAC + risk checks
- [x] **FR-7: WebSocket Protocol** VERIFIED BY: Integration test for approval_request/response messages
- [x] **FR-8: Audit Logging** VERIFIED BY: Unit tests for audit log entries

**Technical Criteria:**

- [x] **Performance: Risk check overhead < 10ms** VERIFIED BY: Benchmark test in DO phase
- [x] **Security: Approval tokens cryptographically signed, 5-minute timeout** VERIFIED BY: Unit tests
- [x] **Code Quality: MyPy strict + Ruff clean** VERIFIED BY: CI pipeline
- [x] **Backward Compatibility: Existing tools without risk_level default to "high"** VERIFIED BY: Integration test

**TDD Criteria:**

- [x] All tests written **before** implementation code (documented in DO phase log)
- [x] Each test failed first (RED phase documented)
- [x] Test coverage ≥90% for new code (measured by pytest-cov)
- [x] Tests follow Arrange-Act-Assert pattern

### 1.3 Scope Boundaries

**In Scope:**
- ToolMetadata extension with risk_level field
- ExecutionMode enum (safe, standard, expert)
- LangGraph interrupt-based approval workflow
- WebSocket approval message types (approval_request, approval_response)
- Frontend execution mode selector and approval dialog
- Visual indicators for mode and tool risk
- Audit logging for tool executions and approvals
- All existing tools annotated with appropriate risk levels

**Out of Scope:**
- Database schema changes (use code annotations only)
- User preference backend storage (use localStorage for now)
- Group approval workflows
- Approval delegation
- Approval policies/rules engine
- Multi-user approval management UI

---

## Phase 2: Work Decomposition

### 2.1 Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|--------------|------------------|------------|
| **Phase 1: Backend Foundation** |
| 1.1 | Add RiskLevel enum and ExecutionMode enum to types.py | `backend/app/ai/tools/types.py` | None | Enums compile, MyPy strict passes | Low |
| 1.2 | Extend ToolMetadata with risk_level field | `backend/app/ai/tools/types.py` | 1.1 | Field defaults to "high", to_dict() includes it | Low |
| 1.3 | Update @ai_tool decorator with risk_level parameter | `backend/app/ai/tools/__init__.py` | 1.2 | Decorator accepts risk_level, attaches to metadata | Medium |
| 1.4 | Annotate all existing tools with risk levels | `backend/app/ai/tools/templates/*.py` | 1.3 | All tools have risk_level in metadata | Medium |
| 1.5 | Add unit tests for risk categorization | `backend/tests/unit/ai/tools/test_risk_categorization.py` | 1.4 | Tests for enum, metadata, decorator pass | Low |
| **Phase 2: Risk Checking** |
| 2.1 | Add execution_mode to ToolContext | `backend/app/ai/tools/types.py` | 1.2 | Field accessible in context | Low |
| 2.2 | Create RiskCheckNode for LangGraph | `backend/app/ai/tools/risk_check_node.py` | 2.1 | Node filters tools based on mode + risk | High |
| 2.3 | Integrate risk check into RBACToolNode | `backend/app/ai/tools/rbac_tool_node.py` | 2.2 | Risk check runs alongside permission check | High |
| 2.4 | Add ExecutionMode validation schemas | `backend/app/models/schemas/ai.py` | 1.1 | Pydantic validates execution_mode in WSChatRequest | Low |
| 2.5 | Add integration tests for risk checking | `backend/tests/integration/ai/test_risk_checking.py` | 2.3 | Tests for mode filtering, risk validation pass | Medium |
| **Phase 3: Approval Workflow** |
| 3.1 | Create InterruptNode with LangGraph interrupts | `backend/app/ai/tools/interrupt_node.py` | 2.3 | Node pauses graph on critical tools in standard mode | High |
| 3.2 | Add WebSocket approval message schemas | `backend/app/models/schemas/ai.py` | None | WSApprovalRequestMessage, WSApprovalResponseMessage defined | Low |
| 3.3 | Implement approval handling in AgentService | `backend/app/ai/agent_service.py` | 3.1, 3.2 | chat_stream handles approval_request/response | High |
| 3.4 | Add approval timeout and audit logging | `backend/app/ai/tools/approval_audit.py` | 3.3 | Approvals timeout after 5min, audit logs written | Medium |
| 3.5 | Add integration tests for approval flow | `backend/tests/integration/ai/test_approval_workflow.py` | 3.4 | E2E test for approval request → response → resume passes | High |
| **Phase 4: Frontend Implementation** |
| 4.1 | Add execution mode types to chat types | `frontend/src/features/ai/chat/types.ts` | 2.4 | TypeScript types match backend schemas | Low |
| 4.2 | Add execution mode selector to AIAssistantModal | `frontend/src/features/ai/components/AIAssistantModal.tsx` | 4.1 | Dropdown shows Safe/Standard/Expert, persists to localStorage | Medium |
| 4.3 | Create approval dialog component | `frontend/src/features/ai/components/ApprovalDialog.tsx` | 4.1 | Modal shows tool info, Approve/Reject buttons | Medium |
| 4.4 | Handle approval WebSocket messages | `frontend/src/features/ai/chat/api/useStreamingChat.ts` | 3.2, 4.3 | Hook processes approval_request, sends approval_response | High |
| 4.5 | Add visual indicators for mode and tool risk | `frontend/src/features/ai/components/ModeBadge.tsx` | 4.2 | Badge shows current mode, color-coded | Low |
| 4.6 | Add E2E tests with Playwright | `frontend/tests/e2e/ai/execution-modes.spec.ts` | 4.5 | Tests for mode selection, approval flow pass | Medium |
| **Phase 5: Documentation & Polish** |
| 5.1 | Update API documentation | `backend/docs/api/ai-tools.md` | 3.5 | OpenAPI spec includes new fields, messages | Low |
| 5.2 | Add user guide for execution modes | `docs/01-user-guide/ai-execution-modes.md` | 4.6 | Guide explains modes, when to use each | Low |
| 5.3 | Performance testing and optimization | `backend/tests/performance/test_risk_check_overhead.py` | 2.5 | Benchmark shows < 10ms overhead | Medium |
| 5.4 | Code review and refinement | All files | 5.3 | MyPy strict, Ruff clean, all tests pass | Medium |

### 2.2 Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|----------------------|---------|-----------|-------------------|
| **FR-1: Tool Risk Categorization** |
| All tools tagged with risk_level | T-001 | `backend/tests/unit/ai/tools/test_risk_categorization.py` | ToolMetadata has risk_level field, defaults to "high" |
| RiskLevel enum validates values | T-002 | `backend/tests/unit/ai/tools/test_risk_categorization.py` | Only "low", "high", "critical" accepted |
| @ai_tool decorator accepts risk_level | T-003 | `backend/tests/unit/ai/tools/test_risk_categorization.py` | Decorator attaches risk_level to _tool_metadata |
| **FR-2: Execution Mode Selection** |
| Safe mode filters critical tools | T-004 | `backend/tests/integration/ai/test_risk_checking.py` | Critical tools excluded from tool list |
| Standard mode allows with approval | T-005 | `backend/tests/integration/ai/test_risk_checking.py` | Critical tools require approval |
| Expert mode allows all tools | T-006 | `backend/tests/integration/ai/test_risk_checking.py` | All tools available without approval |
| **FR-3: Approval Workflow** |
| Critical tool triggers interrupt | T-007 | `backend/tests/integration/ai/test_approval_workflow.py` | Graph pauses, sends approval_request |
| User approval resumes execution | T-008 | `backend/tests/integration/ai/test_approval_workflow.py` | Tool executes after approval_response |
| User rejection skips tool | T-009 | `backend/tests/integration/ai/test_approval_workflow.py` | Tool returns error message |
| **FR-4: Mode Persistence** |
| Mode persists across sessions | T-010 | `frontend/tests/unit/ai/executionMode.test.ts` | localStorage saves/loads execution mode |
| **FR-5: Visual Indicators** |
| Mode badge shows current mode | T-011 | `frontend/tests/e2e/ai/execution-modes.spec.ts` | Badge displays, color-coded correctly |
| Tool risk indicator on execution | T-012 | `frontend/tests/e2e/ai/execution-modes.spec.ts` | Toast shows tool name + risk level |
| **FR-6: RBAC Integration** |
| Risk check runs after permission check | T-013 | `backend/tests/integration/ai/test_risk_checking.py` | Both checks must pass for execution |
| Permission denied bypasses risk check | T-014 | `backend/tests/integration/ai/test_risk_checking.py` | No risk check if permission denied |
| **FR-7: WebSocket Protocol** |
| approval_request message format | T-015 | `backend/tests/integration/ai/test_approval_workflow.py` | Message includes tool, args, approval_id |
| approval_response message format | T-016 | `backend/tests/integration/ai/test_approval_workflow.py` | Response includes approved/rejected + approval_id |
| **FR-8: Audit Logging** |
| Tool execution logged | T-017 | `backend/tests/unit/ai/tools/test_approval_audit.py` | Audit entry created on tool call |
| Approval logged | T-018 | `backend/tests/unit/ai/tools/test_approval_audit.py` | Audit entry includes user, decision, timestamp |
| **NFR-1: Performance** |
| Risk check overhead < 10ms | T-019 | `backend/tests/performance/test_risk_check_overhead.py` | Benchmark median < 10ms |

---

## Phase 3: Test Specification

### 3.1 Test Hierarchy

```text
├── Unit Tests (backend/tests/unit/ai/tools/)
│   ├── test_risk_categorization.py (T-001 to T-003)
│   ├── test_approval_audit.py (T-017, T-018)
│   └── test_execution_mode_validation.py
├── Integration Tests (backend/tests/integration/ai/)
│   ├── test_risk_checking.py (T-004 to T-006, T-013, T-014)
│   └── test_approval_workflow.py (T-007 to T-009, T-015, T-016)
├── Performance Tests (backend/tests/performance/)
│   └── test_risk_check_overhead.py (T-019)
├── Unit Tests (frontend/tests/unit/ai/)
│   └── executionMode.test.ts (T-010)
└── E2E Tests (frontend/tests/e2e/ai/)
    └── execution-modes.spec.ts (T-011, T-012)
```

### 3.2 Test Cases (First 5)

| Test ID | Test Name | Criterion | Type | Expected Result |
|---------|-----------|-----------|------|-----------------|
| T-001 | `test_tool_metadata_has_risk_level_field` | FR-1 | Unit | ToolMetadata dataclass has risk_level: RiskLevel field |
| T-002 | `test_risk_level_enum_only_accepts_valid_values` | FR-1 | Unit | RiskLevel validates "low", "high", "critical" only |
| T-003 | `test_ai_tool_decorator_attaches_risk_level` | FR-1 | Unit | @ai_tool(risk_level="critical") sets _tool_metadata.risk_level |
| T-004 | `test_safe_mode_excludes_critical_tools` | FR-2 | Integration | RiskCheckNode filters out risk_level="critical" in safe mode |
| T-005 | `test_standard_mode_requires_approval_for_critical` | FR-2 | Integration | RiskCheckNode marks critical tools for approval in standard mode |

### 3.3 Test Infrastructure Needs

**Backend Fixtures (from existing conftest.py):**
- `db_session` - AsyncSession for database tests
- `test_user` - User model with role
- `test_project` - Project model for context
- `mock_rbac_service` - Mocked RBAC service

**New Fixtures Needed:**
- `tool_context_with_mode` - ToolContext with execution_mode
- `sample_tools_with_risk_levels` - List of tools with various risk levels
- `mock_websocket_connection` - Mock WebSocket for approval messages

**Frontend Testing:**
- Vitest for unit tests
- Playwright for E2E tests
- MSW (Mock Service Worker) for WebSocket mocking

---

## Phase 4: Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|-----------|-------------|-------------|--------|------------|
| **Technical** | LangGraph interrupt complexity (state resume, Command objects) | Medium | High | Prototype interrupt flow first with simple test case; reference LangGraph docs |
| **Technical** | WebSocket approval race conditions (multiple approvals) | Low | Medium | Use unique approval_id, timeout handling, idempotent responses |
| **Integration** | Breaking existing chat functionality | Low | High | Backward compatible default (risk_level="high"), comprehensive integration tests |
| **Integration** | Frontend state desync on approval | Medium | Medium | Use React Query for server state, optimistic UI updates |
| **Process** | Tool annotation errors (inconsistent risk levels) | Medium | Low | Automated linting rule to check risk_level on all @ai_tool decorators |
| **Process** | Time overrun (7 days → 10+ days) | Low | Medium | Daily standups, ready to cut to Option 2 if needed |

---

## Phase 5: Prerequisites & Dependencies

### Technical Prerequisites

- [x] Backend development environment set up (Python 3.12+, uv, PostgreSQL)
- [x] Frontend development environment set up (Node 20+, npm)
- [x] LangGraph 0.2+ installed (supports interrupts)
- [x] Existing test suite passes (baseline)

### Documentation Prerequisites

- [x] Analysis phase approved (Option 1 selected)
- [x] ADR-007: RBAC Service Design reviewed
- [x] LangGraph Human-in-the-Loop documentation reviewed
- [x] Existing RBACToolNode implementation understood

---

## Implementation Sequence (TDD Approach)

### Phase 1: Backend Foundation (Day 1-2)

```python
# 1. Write tests FIRST (RED phase)
# backend/tests/unit/ai/tools/test_risk_categorization.py
def test_tool_metadata_has_risk_level_field():
    # Arrange & Act & Assert
    metadata = ToolMetadata(
        name="test_tool",
        description="Test",
        permissions=["read"],
        risk_level=RiskLevel.CRITICAL
    )
    assert metadata.risk_level == RiskLevel.CRITICAL

# 2. Run tests → FAIL (no risk_level field)

# 3. Implement (GREEN phase)
# backend/app/ai/tools/types.py
class RiskLevel(str, Enum):
    LOW = "low"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ToolMetadata:
    # ... existing fields ...
    risk_level: RiskLevel = RiskLevel.HIGH  # Default to "high" (safe)

# 4. Run tests → PASS

# 5. Refactor (if needed)
# Add to_dict() extension for serialization
```

### Phase 2-5: Similar TDD Cycle

Each task follows: **Write test → Run → Fail → Implement → Pass → Refactor**

---

## API Contract Specifications

### WebSocket Messages

```python
# New WebSocket message types

class WSApprovalRequestMessage(BaseModel):
    """Server → Client: Request approval for critical tool execution."""
    type: Literal["approval_request"]
    approval_id: str  # UUID for this approval request
    session_id: UUID
    tool_name: str
    tool_args: dict[str, Any]
    risk_level: Literal["critical"]
    expires_at: datetime  # 5 minutes from now

class WSApprovalResponseMessage(BaseModel):
    """Client → Server: User decision on approval request."""
    type: Literal["approval_response"]
    approval_id: str
    approved: bool
    user_id: UUID
    timestamp: datetime
```

### Pydantic Schema Changes

```python
# backend/app/models/schemas/ai.py

class WSChatRequest(BaseModel):
    # ... existing fields ...
    execution_mode: Literal["safe", "standard", "expert"] = Field(
        default="standard",
        description="AI tool execution mode"
    )

# frontend/src/features/ai/chat/types.ts
export type ExecutionMode = 'safe' | 'standard' | 'expert';

export interface ApprovalRequestMessage {
  type: 'approval_request';
  approval_id: string;
  session_id: string;
  tool_name: string;
  tool_args: Record<string, unknown>;
  risk_level: 'critical';
  expires_at: string;
}
```

---

## Data Flow Diagrams

### Approval Flow (Standard Mode, Critical Tool)

```text
User sends message (execution_mode="standard")
    ↓
AgentService.chat_stream()
    ↓
LangGraph Agent Node → selects critical tool
    ↓
RBACToolNode → checks permissions → PASS
    ↓
InterruptNode → detects critical tool + standard mode
    ↓
interrupt() → pauses graph execution
    ↓
Send WSApprovalRequestMessage via WebSocket
    ↓
Frontend: ApprovalDialog appears (non-blocking)
    ↓
User clicks "Approve" or "Reject"
    ↓
Send WSApprovalResponseMessage via WebSocket
    ↓
AgentService receives response
    ↓
IF approved: graph.invoke(resume_command) → tool executes
ELSE: Skip tool, return error message
```

---

## Deployment Plan

### Staging Deployment

1. **Feature Flag**: Add `FEATURE_EXECUTION_MODES` environment variable (default: false)
2. **Database Migration**: None (no schema changes)
3. **Backend Deploy**: Deploy to staging, enable feature flag
4. **Frontend Deploy**: Deploy to staging with mode selector
5. **QA Testing**: Manual testing of all execution modes
6. **Performance Testing**: Verify < 10ms overhead

### Production Deployment

1. **Monitoring**: Set up Datadog alerts for approval latency
2. **Feature Rollout**: Enable for 10% of users (canary)
3. **Monitor**: Check error rates, approval timeouts, user feedback
4. **Full Rollout**: Enable for 100% of users after 24h of stable metrics
5. **Documentation**: Publish user guide before rollout

---

## Rollback Plan

If critical issues discovered:

1. **Immediate**: Set `FEATURE_EXECUTION_MODES=false` in production
2. **Fallback**: System reverts to current behavior (all tools execute with RBAC only)
3. **Hotfix**: Address issue in staging, re-test
4. **Re-deploy**: Re-enable feature flag after fix verified

**Rollback Time:** < 5 minutes (feature flag toggle)

---

## Documentation References

- [Analysis Phase](./00-analysis.md) - Full analysis with 3 solution options
- [ADR-007: RBAC Service Design](/home/nicola/dev/backcast/docs/02-architecture/decisions/ADR-007-rbac-service.md)
- [LangGraph Human-in-the-Loop](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/)
- [Backend Coding Standards](/home/nicola/dev/backcast/docs/02-architecture/backend/coding-standards.md)

---

## Output

**File:** `docs/03-project-plan/iterations/2026-03-20-ai-tool-risk-categorization/01-plan.md`

**Status:** PLAN COMPLETE

**Next Phase:** DO - Execute tasks following TDD cycle (RED-GREEN-REFACTOR)

**Estimated Duration:** 5-7 days

**Team Capacity:** 1 full-stack developer

---

**Plan approved by:** [To be filled]

**Date:** [To be filled]
