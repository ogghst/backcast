# Analysis: E09-U10 WebSocket Streaming for Real-Time AI Responses

**Created:** 2026-03-08
**Epic:** E009 - AI Integration
**User Story:** E09-U10 - WebSocket Streaming
**Priority:** High
**Status:** Analysis Complete

---

## Clarified Requirements

### Problem Statement

The current AI chat implementation uses HTTP POST requests, which creates a poor user experience for AI-generated responses. Users must wait for the complete LLM response before seeing any output, leading to:

1. **Perceived Latency:** Users experience delays of 5-30 seconds with no visual feedback during LLM generation
2. **Poor UX:** No indication that the system is working until the complete response arrives
3. **No Interruption Capability:** Users cannot cancel in-progress generations
4. **Limited Interactivity:** Cannot display progressive content or intermediate tool results

### Functional Requirements

**FR-WS-001:** The system shall provide a WebSocket endpoint for real-time AI chat message streaming.

**FR-WS-002:** The WebSocket shall stream AI response content incrementally as tokens are generated.

**FR-WS-003:** The WebSocket shall support bidirectional communication:
- Client sends: Chat messages with session context
- Server streams: Progressive content chunks, tool calls, and status updates

**FR-WS-004:** The WebSocket shall maintain session continuity for conversation history.

**FR-WS-005:** The WebSocket shall support authentication via JWT token during connection handshake.

**FR-WS-006:** The WebSocket shall allow clients to disconnect gracefully mid-stream.

**FR-WS-007:** The system shall persist complete messages to the database after streaming completes.

**FR-WS-008:** The frontend shall display streamed content progressively with typing indicators.

**FR-WS-009:** The system shall handle WebSocket connection failures with automatic reconnection logic.

**FR-WS-010:** The WebSocket shall propagate tool execution results in real-time during the agent loop.

### Non-Functional Requirements

**NFR-WS-001 (Performance):** First token shall appear within 2 seconds of message send.

**NFR-WS-002 (Latency):** Subsequent tokens shall stream with maximum 500ms delay between chunks.

**NFR-WS-003 (Concurrency):** System shall support 50+ concurrent WebSocket connections per server instance.

**NFR-WS-004 (Reliability):** WebSocket connections shall handle network interruptions with exponential backoff reconnection.

**NFR-WS-005 (Security):** WebSocket connections shall validate JWT tokens and enforce RBAC permissions.

**NFR-WS-006 (Compatibility):** No backward compatibility required - HTTP POST endpoint to be removed.

**NFR-WS-007 (Observability):** WebSocket lifecycle events (connect, disconnect, error) shall be logged.

### Constraints

**Constraint-WS-001:** HTTP POST endpoint shall be removed and replaced with WebSocket only (no backward compatibility required).

**Constraint-WS-002:** Must use FastAPI's native WebSocket support (no additional WebSocket libraries).

**Constraint-WS-003:** Simple JSON message protocol (no structured protocol like JSON-RPC).

**Constraint-WS-004:** Database persistence must occur after complete message assembly, not during streaming.

**Constraint-WS-005:** WebSocket implementation must not break existing session management logic.

**Constraint-WS-006:** Must respect existing RBAC permission `ai-chat` for WebSocket connections.

**Constraint-WS-007:** Error handling optimized for UX experience (partial message + error event for mid-stream failures).

---

## Protocol Decision Rationale

**Decision:** Use Simple JSON message protocol over WebSocket.

After evaluating Simple JSON vs JSON-RPC protocols, Simple JSON was chosen for the following reasons:

1. **Streaming-First Design:** WebSocket streaming is inherently event-based, not request/response oriented. JSON-RPC is designed for request/response patterns with explicit IDs, which adds unnecessary complexity for a streaming use case.

2. **Simplicity & Development Speed:** Simple JSON requires minimal boilerplate and is easier to implement correctly. No need for request ID tracking, response routing, or protocol state machines.

3. **Better Performance:** Simple JSON messages are smaller (no `id`, `jsonrpc`, `method` fields), reducing bandwidth overhead for high-frequency token streaming.

4. **Easier Debugging:** Simple JSON is more human-readable and easier to debug in browser dev tools. No need to understand JSON-RPC semantics.

5. **No Complex Features Needed:** JSON-RPC features like batching, notifications, and named parameters are not required for streaming AI responses. The use case is unidirectional streaming with simple event types.

**Confirmed Approach:**
- FastAPI Native WebSocket
- Simple JSON message protocol with event types (`token`, `tool_call`, `tool_result`, `complete`, `error`)
- OpenAI streaming API
- No structured protocol like JSON-RPC

---

## Context Discovery

### Product Scope

**Relevant User Stories:**
- **E09-U04:** Natural language queries to AI assistant (depends on streaming for UX)
- **E09-U10:** WebSocket streaming for real-time responses (this story)
- **E09-U11:** Frontend AI chat interface (consumer of streaming API)

**Business Requirements:**
- Provide responsive, interactive AI chat experience
- Support long-running LLM generations without user frustration
- Enable real-time visibility into AI tool execution
- Maintain audit trail of all AI conversations

### Architecture Context

**Bounded Contexts Involved:**
1. **Context 10: AI/ML Integration** (Primary)
   - WebSocket Streamer component (defined in bounded contexts)
   - LangGraph Agent orchestration
   - Session management
   - Tool execution layer

2. **Context CC1: API Layer** (Cross-cutting)
   - WebSocket endpoint registration
   - Authentication/authorization via JWT
   - Error handling conventions

3. **Context F1: State & Data Management** (Frontend)
   - WebSocket client state management
   - Message buffering and rendering
   - Connection lifecycle management

**Existing Patterns to Follow:**
- FastAPI WebSocket dependency injection pattern
- JWT authentication via `get_current_active_user` dependency
- RBAC enforcement via `RoleChecker` dependency
- Agent service pattern for conversation orchestration
- Session persistence pattern in `AIConfigService`

**Architectural Constraints:**
- LangGraph agent loop must stream intermediate results
- OpenAI SDK supports streaming via `stream=True` parameter
- Frontend uses TanStack Query for server state (not applicable for WebSocket)
- Frontend uses Ant Design components for UI

### Codebase Analysis

**Backend:**

**Existing Related APIs:**
- `/home/nicola/dev/backcast_evs/backend/app/api/routes/ai_chat.py`
  - `POST /api/v1/ai/chat/chat` - HTTP endpoint (TO BE REPLACED by WebSocket)
  - `GET /api/v1/ai/chat/sessions` - List sessions
  - `GET /api/v1/ai/chat/sessions/{id}/messages` - Get messages
  - `DELETE /api/v1/ai/chat/sessions/{id}` - Delete session

**Data Models:**
- `/home/nicola/dev/backcast_evs/backend/app/models/domain/ai.py`
  - `AIConversationSession` - Session persistence
  - `AIConversationMessage` - Message persistence
  - `AIAssistantConfig` - Assistant configuration

**Similar Patterns:**
- No existing WebSocket implementation in the codebase
- FastAPI WebSocket documentation: https://fastapi.tiangolo.com/advanced/websockets/
- Authentication pattern: Use `Depends(get_current_active_user)` in WebSocket endpoint

**Agent Service:**
- `/home/nicola/dev/backcast_evs/backend/app/ai/agent_service.py`
  - `AgentService.chat()` - Current synchronous chat method
  - Uses OpenAI SDK with `await client.chat.completions.create()`
  - Needs modification to support streaming response

**Frontend:**

**Comparable Components:**
- `/home/nicola/dev/backcast_evs/frontend/src/features/ai/chat/components/ChatInterface.tsx`
  - Main chat interface component
  - Uses `useSendMessage` mutation hook
  - Manages session state and message display

- `/home/nicola/dev/backcast_evs/frontend/src/features/ai/chat/components/MessageInput.tsx`
  - Text input for sending messages
  - Loading state management

- `/home/nicola/dev/backcast_evs/frontend/src/features/ai/chat/components/MessageList.tsx`
  - Displays chat messages
  - Shows loading indicator during pending operations

**State Management:**
- Current: TanStack Query `useMutation` for HTTP POST
- New: Native browser WebSocket API (no additional libraries)

**Routing Structure:**
- Chat interface accessible via `/chat` route
- No WebSocket-specific routing needed (same UI, different transport)

---

## Architecture & Design

**Overview:** FastAPI Native WebSocket + OpenAI Streaming with Simple JSON Protocol

**Architecture & Design:**

**Backend:**
- Replace HTTP POST endpoint with WebSocket endpoint `/api/v1/ai/chat/stream`
- Use FastAPI's native `WebSocket` class with dependency injection for auth
- Modify `AgentService.chat()` to support streaming mode
- Use OpenAI SDK's `stream=True` parameter for token-level streaming
- Create async generator function to yield chunks as they arrive
- Send simple JSON messages over WebSocket with event types: `token`, `tool_call`, `complete`, `error`

**Frontend:**
- Create new `useStreamingChat` hook using native `WebSocket` API
- Implement progressive message rendering in `MessageList` component
- Add streaming indicator (typing animation) during generation
- Store partial responses in component state before persistence
- Buffer and display tokens as they arrive
- Handle connection lifecycle (connect, message, error, close)

**Message Protocol:**
```json
// Client -> Server
{
  "type": "chat",
  "message": "user message",
  "session_id": "uuid or null",
  "assistant_config_id": "uuid"
}

// Server -> Client (streaming)
{
  "type": "token",
  "content": "partial text",
  "session_id": "uuid"
}

{
  "type": "tool_call",
  "tool": "list_projects",
  "args": {...}
}

{
  "type": "tool_result",
  "tool": "list_projects",
  "result": [...]
}

{
  "type": "complete",
  "session_id": "uuid",
  "message_id": "uuid"
}

{
  "type": "error",
  "message": "error details"
}
```

**UX Design:**
- User sees typing indicator immediately after sending message
- AI response appears progressively token-by-token (like ChatGPT)
- Tool calls shown as they execute with intermediate results
- User can cancel generation via cancel button (closes WebSocket)
- Error messages displayed inline if generation fails

**Implementation Details:**

**Backend Components:**
1. WebSocket route in `ai_chat.py`:
```python
@router.websocket("/chat/stream")
async def chat_stream(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    # Authenticate via token
    # Accept connection
    # Stream responses
```

2. `AgentService.chat_stream()` method:
```python
async def chat_stream(
    self,
    message: str,
    assistant_config: AIAssistantConfig,
    session_id: UUID | None,
    user_id: UUID,
    websocket: WebSocket
) -> None:
    # Use OpenAI streaming
    # Yield tokens to websocket
    # Handle tool calls
    # Persist final message
```

3. `LLMClientFactory` to support streaming clients

**Frontend Components:**
1. WebSocket hook `frontend/src/features/ai/chat/api/useStreamingChat.ts`:
```typescript
export const useStreamingChat = (config: {
  sessionId?: string;
  assistantId: string;
  onToken: (token: string) => void;
  onComplete: (message: ChatMessage) => void;
  onError: (error: Error) => void;
}) => {
  // WebSocket connection management
  // Reconnection logic
  // Message sending
}
```

2. Update `MessageList.tsx` to display streaming messages
3. Update `ChatInterface.tsx` to use streaming hook
4. Add cancel button to `MessageInput.tsx`

---

## Confirmation of Approach

**Confirmed Technical Stack:**
- **Backend:** FastAPI native WebSocket with OpenAI streaming API
- **Frontend:** Native browser WebSocket API (no additional libraries)
- **Protocol:** Simple JSON with event types (`token`, `tool_call`, `tool_result`, `complete`, `error`)
- **Authentication:** JWT token validation during WebSocket handshake
- **Authorization:** RBAC permission `ai-chat` enforced on connection

This approach provides the best user experience for real-time AI chat while maintaining architectural alignment with the bounded contexts design and keeping implementation complexity manageable.

---

## Decision Questions

**All decision questions have been resolved:**

1. ~~**Backward Compatibility Strategy:** Should we maintain HTTP POST endpoint indefinitely or deprecate after WebSocket is stable?~~
   - **RESOLVED:** Remove HTTP POST endpoint entirely, replace with WebSocket only

2. ~~**WebSocket Library:** Should we use native browser WebSocket API or add a library like `socket.io-client` for better reconnection handling?~~
   - **RESOLVED:** Use native browser WebSocket API (no additional libraries)

3. ~~**Message Protocol:** Should we use a simple JSON message format or adopt a structured protocol like JSON-RPC or WebSocket subprotocol?~~
   - **RESOLVED:** Simple JSON message protocol

4. ~~**Error Handling:** How should we handle mid-stream LLM errors? Partial message + error event, or rollback and error only?~~
   - **RESOLVED:** Optimize for UX - send partial message + error event for mid-stream failures

5. ~~**Connection Limits:** Should we implement WebSocket connection limits per user to prevent abuse?~~
   - **RESOLVED:** No connection limits per user

6. ~~**Testing Strategy:** How do we test WebSocket endpoints in automated tests? Mock WebSocket server or integration tests?~~
   - **RESOLVED:** Test using browser (manual/browser-based testing)

---

## Dependencies & Risks

### Dependencies

**E09-U10 Depends On:**
- None (can be implemented independently)

**Stories Depending on E09-U10:**
- E09-U08: AI-Assisted CRUD Tools (benefits from streaming for better UX)
- E09-U09: Change Order AI (benefits from streaming for long generations)
- E09-U07: Project Assessment (benefits from streaming for long reports)
- E09-MULTIMODAL: Multimodal Input/Output (requires WebSocket for binary streaming)

### Technical Risks

**Risk-WS-001: Connection State Management**
- **Impact:** High
- **Mitigation:** Implement robust connection lifecycle management with clear state machine (connecting, connected, disconnecting, disconnected)
- **Contingency:** Fallback to HTTP POST if WebSocket fails

**Risk-WS-002: Authentication Over WebSocket**
- **Impact:** High
- **Mitigation:** Validate JWT token in WebSocket handshake, use query parameter or subprotocol
- **Contingency:** Close connection immediately if auth fails

**Risk-WS-003: Database Persistence Race Conditions**
- **Impact:** Medium
- **Mitigation:** Ensure complete message is assembled before DB write, use transactions
- **Contingency:** Log errors and retry persistence

**Risk-WS-004: OpenAI Streaming API Changes**
- **Impact:** Medium
- **Mitigation:** Use stable OpenAI SDK version, abstract streaming interface
- **Contingency:** Fallback to non-streaming if API changes

**Risk-WS-005: Frontend Reconnection Complexity**
- **Impact:** Medium
- **Mitigation:** Implement exponential backoff reconnection with max retry limit
- **Contingency:** Show error message and manual reconnect button

**Risk-WS-006: Browser Compatibility**
- **Impact:** Low
- **Mitigation:** WebSocket API supported in all modern browsers, add polyfill if needed
- **Contingency:** Fallback to HTTP POST for older browsers

### Security Considerations

**Security-WS-001: Message Size Limits**
- Implement max message size to prevent memory exhaustion

**Security-WS-002: Authorization Validation**
- Validate `ai-chat` permission on connection
- Validate session ownership for each message

**Security-WS-003: Input Sanitization**
- Sanitize all user input before sending to LLM
- Validate message protocol structure

**Note:** No per-user connection limits required per user requirements.

---

## Success Criteria

### Completion Criteria

**Backend:**
- [ ] WebSocket endpoint `/api/v1/ai/chat/stream` implemented
- [ ] JWT authentication via query parameter or header
- [ ] RBAC permission `ai-chat` enforced on connection
- [ ] Token-level streaming from OpenAI API
- [ ] Tool execution results streamed in real-time
- [ ] Complete message persistence after streaming
- [ ] Error handling and propagation to client
- [ ] Connection lifecycle logging
- [ ] Tests: WebSocket connection, authentication, streaming, errors

**Frontend:**
- [ ] `useStreamingChat` hook implemented
- [ ] Progressive message rendering in UI
- [ ] Typing indicator during generation
- [ ] Cancel button for interrupting generation
- [ ] Reconnection logic with exponential backoff
- [ ] Error display for failures
- [ ] Fallback to HTTP POST if WebSocket unavailable
- [ ] Tests: Hook, component integration, error scenarios

**Integration:**
- [ ] End-to-end flow working (send message -> stream response -> display)
- [ ] Session continuity maintained across WebSocket connections
- [ ] HTTP POST endpoint removed and replaced with WebSocket
- [ ] No regression in existing chat functionality

### User Acceptance Criteria

**UAC-WS-001:** As a user, I want to see AI responses appear progressively so I don't have to wait for the complete response.

**UAC-WS-002:** As a user, I want to see a typing indicator while the AI is generating a response.

**UAC-WS-003:** As a user, I want to cancel a long-running AI generation if I change my mind.

**UAC-WS-004:** As a user, I want the system to automatically reconnect if my network connection is interrupted.

**UAC-WS-005:** As a user, I want to see tool execution results in real-time (e.g., "Searching projects...").

**UAC-WS-006:** As a user, I want clear error messages if the AI generation fails.

### Performance Criteria

**Performance-WS-001:** First token appears within 2 seconds of sending message.

**Performance-WS-002:** Subsequent tokens stream with maximum 500ms delay.

**Performance-WS-003:** WebSocket connection established within 1 second.

**Performance-WS-004:** System handles 50+ concurrent WebSocket connections.

### Quality Gates

**Code Quality:**
- Backend: MyPy strict mode (zero errors), Ruff (zero errors), 80%+ test coverage
- Frontend: TypeScript strict mode, ESLint clean, 80%+ test coverage

**Documentation:**
- API documentation for WebSocket endpoint
- Message protocol specification
- Frontend integration guide
- Troubleshooting guide

---

## Implementation Recommendations

### Technical Approach

**Backend Implementation Steps:**

1. **Replace HTTP POST with WebSocket Route** (`backend/app/api/routes/ai_chat.py`)
   - Remove `POST /api/v1/ai/chat/chat` endpoint
   - Add `@router.websocket("/chat/stream")` endpoint
   - Implement WebSocket connection acceptance with JWT auth
   - Add connection lifecycle logging

2. **Create Streaming Agent Service** (`backend/app/ai/agent_service.py`)
   - Add `chat_stream()` method alongside existing `chat()` method
   - Use OpenAI SDK with `stream=True` parameter
   - Create async generator to yield tokens
   - Handle tool execution in loop
   - Persist complete message to database

3. **Update LLM Client** (`backend/app/ai/llm_client.py`)
   - Ensure AsyncOpenAI client supports streaming
   - Add error handling for streaming failures

4. **Browser-Based Testing** (Manual/Integration)
   - Test WebSocket connection in browser
   - Test authentication flow
   - Test token streaming visual feedback
   - Test tool execution feedback
   - Test error handling scenarios
   - Test session persistence

**Frontend Implementation Steps:**

1. **Create WebSocket Hook** (`frontend/src/features/ai/chat/api/useStreamingChat.ts`)
   - Implement native browser WebSocket connection management
   - Handle simple JSON message types (token, tool_call, complete, error)
   - Add reconnection logic with exponential backoff
   - Provide callback hooks for UI updates

2. **Update Chat Interface** (`frontend/src/features/ai/chat/components/ChatInterface.tsx`)
   - Replace `useSendMessage` with `useStreamingChat`
   - Add streaming message state management
   - Add cancel button handler

3. **Update Message List** (`frontend/src/features/ai/chat/components/MessageList.tsx`)
   - Display partial/streaming messages
   - Show typing indicator
   - Animate token appearance

4. **Update Message Input** (`frontend/src/features/ai/chat/components/MessageInput.tsx`)
   - Add cancel button (visible only during generation)
   - Handle cancel event (close WebSocket)

5. **Browser-Based Testing** (Manual/Integration)
   - Test WebSocket connection in browser
   - Test message handling and display
   - Test reconnection logic
   - Test error scenarios

### Key Files to Modify

**Backend:**
- `/home/nicola/dev/backcast_evs/backend/app/api/routes/ai_chat.py` - Add WebSocket endpoint
- `/home/nicola/dev/backcast_evs/backend/app/ai/agent_service.py` - Add streaming method
- `/home/nicola/dev/backcast_evs/backend/app/ai/llm_client.py` - Verify streaming support
- `/home/nicola/dev/backcast_evs/backend/app/models/schemas/ai.py` - Add WebSocket message schemas

**Frontend:**
- `/home/nicola/dev/backcast_evs/frontend/src/features/ai/chat/api/useChat.ts` - Add streaming hook (or new file)
- `/home/nicola/dev/backcast_evs/frontend/src/features/ai/chat/components/ChatInterface.tsx` - Use streaming
- `/home/nicola/dev/backcast_evs/frontend/src/features/ai/chat/components/MessageList.tsx` - Display streaming
- `/home/nicola/dev/backcast_evs/frontend/src/features/ai/chat/components/MessageInput.tsx` - Add cancel

### Integration Points to Consider

**Authentication:**
- JWT token validation in WebSocket handshake
- Use query parameter `?token=jwt` or custom header
- Reuse existing `get_current_active_user` dependency

**Session Management:**
- WebSocket receives session_id in first message
- Reuse existing `AIConfigService` for session lookup
- Maintain session continuity across connections

**Tool Execution:**
- Stream tool call events as they execute
- Show intermediate results (e.g., "Searching projects...")
- Reuse existing tool infrastructure

**Error Handling:**
- Stream partial message + error event for mid-stream failures (optimized for UX)
- Log errors to backend
- Display user-friendly error messages

**Database Persistence:**
- Assemble complete message from streamed tokens
- Persist after streaming completes
- Handle race conditions if user disconnects early

---

## References

**Architecture Docs:**
- [Bounded Contexts - Section 10: AI/ML Integration](../../02-architecture/01-bounded-contexts.md#10-aiml-integration)
- [API Conventions](../../02-architecture/cross-cutting/api-conventions.md)
- [Security Practices](../../02-architecture/cross-cutting/security-practices.md)

**Related User Stories:**
- [E09-U04: Natural Language Queries](../../03-project-plan/epics.md#epic-9-ai-integration-e009)
- [E09-U11: Frontend AI Chat Interface](../../03-project-plan/epics.md#epic-9-ai-integration-e009)

**Functional Requirements:**
- [Section 12.6: AI Integration](../../01-product-scope/functional-requirements.md#126-ai-integration)

**Current Implementation:**
- Backend: `/home/nicola/dev/backcast_evs/backend/app/api/routes/ai_chat.py`
- Backend: `/home/nicola/dev/backcast_evs/backend/app/ai/agent_service.py`
- Frontend: `/home/nicola/dev/backcast_evs/frontend/src/features/ai/chat/`

**External References:**
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [OpenAI API Streaming](https://platform.openai.com/docs/api-reference/streaming)
- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
