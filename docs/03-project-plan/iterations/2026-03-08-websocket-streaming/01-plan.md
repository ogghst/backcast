# Plan: E09-U10 WebSocket Streaming for Real-Time AI Responses

**Created:** 2026-03-08
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** FastAPI Native WebSocket with Simple JSON Protocol

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: FastAPI Native WebSocket with Simple JSON message protocol
- **Architecture**:
  - Backend: Replace HTTP POST `/api/v1/ai/chat/chat` with WebSocket `/api/v1/ai/chat/stream`
  - Frontend: Native browser WebSocket API (no additional libraries)
  - Protocol: Simple JSON with event types (`token`, `tool_call`, `tool_result`, `complete`, `error`)
  - Authentication: JWT token validation during WebSocket handshake
  - Authorization: RBAC permission `ai-chat` enforced on connection
- **Key Decisions**:
  - No backward compatibility - HTTP POST endpoint will be removed entirely
  - Error handling optimized for UX: partial message + error event for mid-stream failures
  - No per-user connection limits
  - Testing via browser (manual/integration tests)

### Success Criteria

**Functional Criteria:**

- [ ] WebSocket connection established within 1 second VERIFIED BY: Browser DevTools Network tab timing
- [ ] First token appears within 2 seconds of message send VERIFIED BY: Visual observation and timestamp logging
- [ ] Subsequent tokens stream with maximum 500ms delay VERIFIED BY: Visual observation and console logging
- [ ] Progressive message rendering displays tokens as they arrive VERIFIED BY: UI visual feedback during generation
- [ ] Typing indicator displayed during AI generation VERIFIED BY: UI component state
- [ ] Tool execution results streamed in real-time VERIFIED BY: UI display of tool calls
- [ ] User can cancel generation mid-stream via cancel button VERIFIED BY: WebSocket close event
- [ ] Automatic reconnection with exponential backoff VERIFIED BY: Network interruption simulation
- [ ] Complete message persisted to database after streaming VERIFIED BY: Database query and session reload
- [ ] Session continuity maintained across WebSocket connections VERIFIED BY: Session history preservation
- [ ] JWT authentication validated during WebSocket handshake VERIFIED BY: Connection rejection for invalid tokens
- [ ] RBAC permission `ai-chat` enforced on connection VERIFIED BY: Connection rejection for unauthorized users
- [ ] Error messages displayed inline for failures VERIFIED BY: UI error state and toast notifications
- [ ] HTTP POST endpoint removed and replaced with WebSocket VERIFIED BY: API route inspection and 404 response

**Technical Criteria:**

- [ ] Performance: First token < 2s, subsequent tokens < 500ms delay VERIFIED BY: Browser DevTools and console timing logs
- [ ] Security: JWT token validation and RBAC enforcement VERIFIED BY: Authenticated and unauthorized connection tests
- [ ] Code Quality: Backend - MyPy strict mode (zero errors), Ruff (zero errors), 80%+ test coverage VERIFIED BY: CI pipeline
- [ ] Code Quality: Frontend - TypeScript strict mode, ESLint clean, 80%+ test coverage VERIFIED BY: CI pipeline
- [ ] Concurrency: System handles 50+ concurrent WebSocket connections VERIFIED BY: Load testing

**TDD Criteria:**

- [ ] All tests written before implementation code
- [ ] Each test failed first (documented in DO phase log)
- [ ] Test coverage >= 80%
- [ ] Tests follow Arrange-Act-Assert pattern

### Scope Boundaries

**In Scope:**

- WebSocket endpoint implementation replacing HTTP POST
- Token-level streaming from OpenAI API
- Tool execution result streaming
- Database persistence after complete message assembly
- Frontend WebSocket hook with reconnection logic
- Progressive message rendering in UI
- Typing indicator and cancel button
- Error handling and propagation
- JWT authentication and RBAC authorization
- Browser-based testing (manual/integration)

**Out of Scope:**

- Backward compatibility with HTTP POST endpoint
- Per-user connection limits
- Automated unit tests for WebSocket (browser-based testing only)
- Message protocol versioning
- WebSocket compression
- Server-sent events (SSE) fallback
- Multimodal input/output (binary streaming)

---

## Work Decomposition

### Task Breakdown

| #   | Task                                                 | Files                                                                       | Dependencies  | Success Criteria                                                                                                                                                               | Complexity |
| --- | ---------------------------------------------------- | --------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- |
| 1   | Create WebSocket message schemas                     | backend/app/models/schemas/ai.py                                            | None          | Schemas validate successfully for all message types (token, tool_call, tool_result, complete, error)                                                                             | Low        |
| 2   | Add WebSocket route with authentication              | backend/app/api/routes/ai_chat.py                                           | Task 1        | WebSocket connection accepts authenticated users, rejects unauthenticated/unauthorized, logs lifecycle events                                                                  | Medium     |
| 3   | Implement streaming method in AgentService           | backend/app/ai/agent_service.py                                             | None          | chat_stream() method yields tokens as they arrive from OpenAI API, handles tool execution in loop, persists complete message after streaming                                    | High       |
| 4   | Verify LLM client streaming support                  | backend/app/ai/llm_client.py                                                | None          | AsyncOpenAI client supports stream=True parameter, error handling for streaming failures                                                                                      | Low        |
| 5   | Remove HTTP POST endpoint                            | backend/app/api/routes/ai_chat.py                                           | Task 2        | POST /api/v1/ai/chat/chat route removed, returns 404, WebSocket endpoint is only chat entry point                                                                              | Low        |
| 6   | Create frontend WebSocket types                      | frontend/src/features/ai/types.ts                                            | None          | TypeScript types defined for WebSocket messages, event types, and hook configuration                                                                                           | Low        |
| 7   | Implement WebSocket hook                             | frontend/src/features/ai/chat/hooks/useStreamingChat.ts                     | Task 6        | Hook manages WebSocket connection lifecycle, handles message types, implements exponential backoff reconnection, provides callbacks for UI updates                            | High       |
| 8   | Update MessageList for progressive rendering         | frontend/src/features/ai/chat/components/MessageList.tsx                    | Task 6        | Component displays partial/streaming messages, shows typing indicator during generation, animates token appearance, auto-scrolls to latest content                             | Medium     |
| 9   | Update MessageInput with cancel button              | frontend/src/features/ai/chat/components/MessageInput.tsx                   | Task 7        | Component shows cancel button during generation, handles cancel event (closes WebSocket), disables input during streaming                                                        | Medium     |
| 10  | Update ChatInterface to use streaming hook           | frontend/src/features/ai/chat/components/ChatInterface.tsx                  | Task 7        | Component replaces useSendMessage with useStreamingChat, manages streaming message state, passes callbacks to child components                                                  | Medium     |
| 11  | Remove old HTTP POST chat hook                       | frontend/src/features/ai/chat/api/useChat.ts                                | Task 10       | useSendMessage hook removed or marked deprecated, no references in ChatInterface                                                                                                | Low        |
| 12  | Browser-based integration testing                    | Manual testing checklist execution                                          | All tasks     | All testing scenarios pass, edge cases handled, performance criteria met, error scenarios validated                                                                             | High       |

### Test-to-Requirement Traceability

| Acceptance Criterion                                          | Test ID | Test File/Method                                      | Expected Behavior                                                                                                                                            |
| ------------------------------------------------------------- | ------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| WebSocket connection established within 1 second              | T-001   | Browser DevTools Network timing                      | WebSocket connection to `/api/v1/ai/chat/stream` completes in < 1s                                                                                            |
| First token appears within 2 seconds of message send          | T-002   | Browser console timing logs + visual observation      | First token event received < 2s after sending message                                                                                                        |
| Subsequent tokens stream with maximum 500ms delay             | T-003   | Browser console timing logs + visual observation      | Token events arrive with < 500ms intervals                                                                                                                   |
| Progressive message rendering displays tokens as they arrive  | T-004   | MessageList component state inspection                | Message content updates incrementally as token events received                                                                                               |
| Typing indicator displayed during AI generation               | T-005   | MessageList component visual inspection               | Typing animation visible from message send until complete event                                                                                              |
| Tool execution results streamed in real-time                  | T-006   | MessageList tool call display + console logs          | Tool call and tool_result events display in UI as they occur                                                                                                 |
| User can cancel generation mid-stream via cancel button       | T-007   | Cancel button click + WebSocket close event           | Clicking cancel closes WebSocket, generation stops, partial message displayed with error indicator                                                             |
| Automatic reconnection with exponential backoff               | T-008   | Network tab disable/enable + console logs             | After network interruption, WebSocket reconnects with delays: 1s, 2s, 4s, 8s, 15s (max)                                                                      |
| Complete message persisted to database after streaming        | T-009   | Database query + session messages API call            | After complete event, message appears in session history with full content                                                                                   |
| Session continuity maintained across WebSocket connections    | T-010   | Reconnect to existing session + history inspection    | Connecting with existing session_id preserves conversation history                                                                                           |
| JWT authentication validated during WebSocket handshake       | T-011   | Connection with invalid/missing token                 | Connection rejected with 401/403, error message displayed                                                                                                     |
| RBAC permission `ai-chat` enforced on connection              | T-012   | Connection by user without `ai-chat` permission       | Connection rejected with 403, access denied message displayed                                                                                                 |
| Error messages displayed inline for failures                  | T-013   | Simulate error during generation + UI inspection      | Error event triggers toast notification and inline error message                                                                                             |
| HTTP POST endpoint removed and replaced with WebSocket        | T-014   | API route inspection + POST attempt                   | POST /api/v1/ai/chat/chat returns 404, WebSocket is only available endpoint                                                                                   |

---

## Test Specification

### Test Hierarchy

```
Backend (Browser-Based Testing)
├── WebSocket Connection Tests
│   ├── Valid JWT authentication
│   ├── Invalid/missing JWT rejection
│   ├── RBAC permission enforcement
│   └── Connection lifecycle logging
├── Streaming Tests
│   ├── Token streaming from OpenAI API
│   ├── First token < 2s latency
│   ├── Subsequent tokens < 500ms interval
│   └── Tool execution result streaming
├── Persistence Tests
│   ├── Complete message database save
│   └── Session history preservation
└── Error Handling Tests
    ├── Mid-stream failure with partial message
    ├── Network interruption handling
    └── Invalid message protocol handling

Frontend (Browser-Based Testing)
├── Hook Tests
│   ├── WebSocket connection management
│   ├── Message type handling
│   ├── Exponential backoff reconnection
│   └── Callback execution
├── Component Tests
│   ├── MessageList progressive rendering
│   ├── Typing indicator display
│   ├── Cancel button functionality
│   └── Error message display
└── Integration Tests
    ├── End-to-end message flow
    ├── Session continuity
    └── Error recovery
```

### Test Cases (Browser-Based Testing)

| Test ID | Test Name                                                     | Criterion | Type         | Verification Method                                                                                   |
| ------- | ------------------------------------------------------------- | --------- | ------------ | ----------------------------------------------------------------------------------------------------- |
| T-001   | WebSocket connection establishes with valid JWT               | AC-1      | Integration   | Browser DevTools Network tab shows WebSocket upgrade success, timing < 1s                            |
| T-002   | First token arrives within 2 seconds                          | AC-2      | Integration   | Console timestamp logs show first token event < 2s after message send                                |
| T-003   | Token streaming maintains < 500ms intervals                   | AC-3      | Integration   | Console logs show token events arriving with < 500ms gaps                                            |
| T-004   | Progressive rendering updates UI incrementally                | AC-4      | Integration   | Visual observation of message content appearing token-by-token                                       |
| T-005   | Typing indicator shows during generation                      | AC-5      | Component     | MessageList displays typing animation from send until complete                                      |
| T-006   | Tool calls and results stream in real-time                    | AC-6      | Integration   | UI displays tool execution events as they occur during generation                                    |
| T-007   | Cancel button stops generation mid-stream                     | AC-7      | Integration   | Clicking cancel closes WebSocket, generation stops, partial message preserved                        |
| T-008   | Exponential backoff reconnection works after network failure  | AC-8      | Integration   | Disable network, wait, re-enable: observe reconnection delays (1s, 2s, 4s, 8s, 15s max)            |
| T-009   | Complete message persists to database                         | AC-9      | Integration   | After streaming, query session messages API: complete message saved with full content                |
| T-010   | Session continuity across reconnects                          | AC-10     | Integration   | Reconnect with existing session_id: conversation history preserved                                   |
| T-011   | Invalid JWT rejected at handshake                             | AC-11     | Integration   | Connect with invalid token: connection closes with 401, error displayed                               |
| T-012   | Missing ai-chat permission rejected                           | AC-12     | Integration   | User without ai-chat permission: connection closes with 403, access denied shown                     |
| T-013   | Error during generation displays inline error                 | AC-13     | Integration   | Trigger error during streaming: error event shows toast + inline message                             |
| T-014   | HTTP POST endpoint returns 404                                | AC-14     | Integration   | POST to /api/v1/ai/chat/chat returns 404, WebSocket is only available endpoint                       |

### Test Infrastructure Needs

**Browser Testing Setup:**

- Chrome DevTools for WebSocket inspection and timing
- Network throttling for reconnection testing
- Console logging for token timing measurements
- Multiple user accounts for permission testing (one with ai-chat, one without)

**Test Data:**

- Valid JWT token for authenticated user with ai-chat permission
- Invalid JWT token for authentication rejection tests
- User account without ai-chat permission for authorization tests
- Existing conversation session for continuity tests
- Test assistant configuration with tools enabled

**Manual Testing Checklist:**

1. Open browser DevTools to Network tab
2. Navigate to AI chat interface
3. Select an assistant
4. Send a message
5. Verify WebSocket connection established
6. Verify progressive token rendering
7. Verify typing indicator display
8. Test tool execution (e.g., "List projects")
9. Test cancel button during generation
10. Test reconnection (disable/enable network)
11. Test error handling (trigger error during generation)
12. Test session continuity (reload page, continue conversation)
13. Test authentication (connect with invalid token)
14. Test authorization (user without ai-chat permission)
15. Verify HTTP POST returns 404

---

## Risk Assessment

| Risk Type   | Description                                                 | Probability | Impact   | Mitigation                                                                                                                                                      |
| ----------- | ----------------------------------------------------------- | ----------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Technical   | WebSocket connection state management complexity            | Medium      | High     | Implement clear state machine (connecting, connected, disconnecting, disconnected), use TypeScript discriminated unions for state types                         |
| Technical   | Authentication over WebSocket (JWT token in handshake)       | Low         | High     | Use query parameter for token, validate in FastAPI WebSocket endpoint before accepting connection, close immediately on auth fail                              |
| Technical   | Database persistence race conditions if user disconnects early | Medium      | Medium   | Ensure complete message is assembled in memory before DB write, use try-finally to persist partial content if disconnected mid-stream                           |
| Technical   | OpenAI streaming API changes breaking compatibility          | Low         | Medium   | Pin OpenAI SDK version, abstract streaming interface behind chat_stream() method, document streaming protocol                                                   |
| Technical   | Frontend reconnection logic complexity with exponential backoff | Medium      | Medium   | Implement standard exponential backoff with max retry limit, add reconnection state visibility for debugging                                                    |
| Integration | Session continuity across WebSocket connections              | Medium      | High     | Always send session_id in first message, reuse existing session logic from AIConfigService, validate session ownership on each message                          |
| Integration | Tool execution result streaming timing issues                | Low         | Medium   | Stream tool_call events immediately, stream tool_result events as they complete, buffer final AI response until all tools done                                   |
| Security    | Message size limits causing memory exhaustion                | Low         | High     | Implement max message size validation in WebSocket endpoint, reject messages exceeding limit (e.g., 100KB)                                                      |
| Security    | Authorization bypass via WebSocket                           | Low         | High     | Enforce RBAC permission check on connection, validate session ownership for each message, log all authorization checks                                          |

---

## Documentation References

### Required Reading

- Coding Standards: `docs/02-architecture/coding-standards.md`
- API Conventions: `docs/02-architecture/cross-cutting/api-conventions.md`
- Security Practices: `docs/02-architecture/cross-cutting/security-practices.md`
- Bounded Contexts - Section 10: AI/ML Integration: `docs/02-architecture/01-bounded-contexts.md#10-aiml-integration`
- User Story E09-U10: `docs/01-product-scope/functional-requirements.md#126-ai-integration`

### Code References

- Backend pattern: `backend/app/api/routes/ai_chat.py` (current HTTP POST to be replaced)
- Backend pattern: `backend/app/ai/agent_service.py` (AgentService.chat() to reference for streaming)
- Frontend pattern: `frontend/src/features/ai/chat/api/useChat.ts` (current HTTP hook to be replaced)
- Frontend pattern: `frontend/src/features/ai/chat/components/ChatInterface.tsx` (consumer of streaming)
- Test pattern: Browser DevTools WebSocket inspection (manual testing approach)

### External References

- FastAPI WebSocket Documentation: https://fastapi.tiangolo.com/advanced/websockets/
- OpenAI API Streaming: https://platform.openai.com/docs/api-reference/streaming
- MDN WebSocket API: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket

---

## Prerequisites

### Technical

- [x] Backend database migrations applied
- [x] Backend dependencies installed (uv sync)
- [x] Frontend dependencies installed (npm install)
- [x] Environment configured (JWT auth, RBAC setup)
- [x] AI assistant configuration exists in database
- [x] AI provider and model configured with valid credentials

### Documentation

- [x] Analysis phase approved (00-analysis.md complete)
- [ ] Architecture docs reviewed (bounded contexts, API conventions)
- [ ] FastAPI WebSocket documentation reviewed
- [ ] MDN WebSocket API documentation reviewed

---

## Task Dependency Graph

```yaml
# Task Dependency Graph for E09-U10 WebSocket Streaming
tasks:
  - id: BE-001
    name: "Create WebSocket message schemas in backend/app/models/schemas/ai.py"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Verify LLM client streaming support in backend/app/ai/llm_client.py"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-003
    name: "Implement streaming method in backend/app/ai/agent_service.py"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-004
    name: "Add WebSocket route with authentication in backend/app/api/routes/ai_chat.py"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-003]

  - id: BE-005
    name: "Remove HTTP POST endpoint from backend/app/api/routes/ai_chat.py"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: FE-001
    name: "Create frontend WebSocket types in frontend/src/features/ai/types.ts"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-002
    name: "Implement WebSocket hook in frontend/src/features/ai/chat/hooks/useStreamingChat.ts"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-003
    name: "Update MessageList for progressive rendering in frontend/src/features/ai/chat/components/MessageList.tsx"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-004
    name: "Update MessageInput with cancel button in frontend/src/features/ai/chat/components/MessageInput.tsx"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]

  - id: FE-005
    name: "Update ChatInterface to use streaming hook in frontend/src/features/ai/chat/components/ChatInterface.tsx"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002, FE-003, FE-004]

  - id: FE-006
    name: "Remove old HTTP POST chat hook from frontend/src/features/ai/chat/api/useChat.ts"
    agent: pdca-frontend-do-executor
    dependencies: [FE-005]

  - id: TEST-001
    name: "Execute browser-based integration testing using manual testing checklist"
    agent: pdca-backend-do-executor
    dependencies: [BE-005, FE-006]
    kind: test
```

---

## Key Principles

1. **Define WHAT, not HOW**: This plan specifies test cases and acceptance criteria, not implementation code. The DO phase will implement the actual WebSocket logic, streaming methods, and frontend components.

2. **Measurable**: All success criteria are objectively verifiable through browser DevTools, console logs, visual inspection, database queries, and API calls.

3. **Sequential**: Tasks are ordered with clear dependencies. Backend foundation (schemas, streaming, routes) must complete before frontend integration can begin.

4. **Traceable**: Every acceptance criterion maps to specific test specifications with expected behaviors and verification methods.

5. **Actionable**: Each task is clear enough for DO phase execution, with specific file paths and success criteria.

> [!NOTE]
> This plan drives the DO phase. Tests are **specified** here (test names, expected behaviors, verification methods) but will be **executed** in DO phase via browser-based manual testing. The DO phase will implement the WebSocket endpoint, streaming methods, frontend hook, and component updates following this plan.
