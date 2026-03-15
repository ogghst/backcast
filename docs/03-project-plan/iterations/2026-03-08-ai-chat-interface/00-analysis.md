# ANALYSIS: E09-U11 - Frontend AI Chat Interface

**Date:** 2026-03-08
**Epic:** E009 - AI Integration (Phase 3)
**User Story:** E09-U11
**Story Points:** 8

---

## 1. Problem Statement

Users need a natural language interface to interact with AI assistants for querying project data and receiving AI-powered insights. The backend chat API is complete (Phase 1), and AI configuration UI is complete (Phase 2), but there is no user-facing chat interface.

---

## 2. Requirements Analysis

### 2.1 Functional Requirements

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-1 | Display chat interface with message list and input | Must Have | User Story |
| FR-2 | Select AI assistant from active configurations | Must Have | User Story |
| FR-3 | Display conversation session history in sidebar | Must Have | User Story |
| FR-4 | Create new chat sessions | Must Have | User Story |
| FR-5 | Delete existing chat sessions | Must Have | User Story |
| FR-6 | Display loading states during AI processing | Must Have | User Story |
| FR-7 | Handle API errors gracefully | Must Have | Non-Functional |
| FR-8 | Persist conversation history | Must Have | Backend |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target | Source |
|----|-------------|--------|--------|
| NFR-1 | TypeScript strict mode | 0 errors | Project Standards |
| NFR-2 | ESLint clean | 0 errors | Project Standards |
| NFR-3 | Test coverage | 80%+ | Project Standards |
| NFR-4 | RBAC enforcement | ai-chat permission | Security |
| NFR-5 | Responsive design | Mobile-friendly | UX |

---

## 3. Backend API Analysis

### 3.1 Available Endpoints

Source: `backend/app/api/routes/ai_chat.py`

| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| POST | `/api/v1/ai/chat/chat` | ai-chat | Send message, get response |
| GET | `/api/v1/ai/chat/sessions` | ai-chat | List user's sessions |
| GET | `/api/v1/ai/chat/sessions/{id}/messages` | ai-chat | Get session history |
| DELETE | `/api/v1/ai/chat/sessions/{id}` | ai-chat | Delete session |

### 3.2 Request/Response Schemas

Source: `backend/app/models/schemas/ai.py`

```typescript
// POST /api/v1/ai/chat/chat
interface AIChatRequest {
  message: string;           // min 1, max 10000 chars
  session_id?: string | null;     // null = new session
  assistant_config_id?: string | null; // Required for new sessions
}

interface AIChatResponse {
  session_id: string;
  message: AIConversationMessagePublic;
  tool_calls?: Array<Record<string, any>>;
}

// GET /api/v1/ai/chat/sessions
interface AIConversationSessionPublic {
  id: string;
  user_id: string;
  assistant_config_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

// GET /api/v1/ai/chat/sessions/{id}/messages
interface AIConversationMessagePublic {
  id: string;
  session_id: string;
  role: string;  // "user" | "assistant" | "tool"
  content: string;
  tool_calls?: Array<Record<string, any>>;
  tool_results?: Record<string, any>;
  created_at: string;
}
```

### 3.3 API Behavior Notes

1. **New Sessions**: Send `session_id: null` with `assistant_config_id`
2. **Existing Sessions**: Send `session_id` without `assistant_config_id`
3. **Session Ownership**: Users can only access their own sessions
4. **Assistant Validation**: Only active assistants can be used
5. **Message Roles**: `user`, `assistant`, `tool` (for tool call results)

---

## 4. Frontend Pattern Analysis

### 4.1 Existing AI Feature Structure

Source: `frontend/src/features/ai/`

```
ai/
├── api/
│   ├── useAIProviders.ts      # CRUD hooks pattern
│   ├── useAIAssistants.ts     # CRUD hooks pattern
│   └── __tests__/             # Test files
├── components/
│   ├── AIProviderList.tsx
│   ├── AIAssistantList.tsx
│   └── __tests__/
└── types.ts                   # Type definitions
```

### 4.2 API Hook Pattern (from useAIProviders.ts)

```typescript
// API client functions
const providerApi = {
  list: async (params?): Promise<T[]> => { ... },
  detail: async (id): Promise<T> => { ... },
  create: async (data): Promise<T> => { ... },
  update: async (id, data): Promise<T> => { ... },
  delete: async (id): Promise<void> => { ... },
};

// TanStack Query hooks
export const useAIProviders = (params?, options?) => { ... };
export const useCreateAIProvider = (options?) => { ... };
// etc.
```

### 4.3 Query Key Pattern (from frontend/src/api/queryKeys.ts)

```typescript
export const queryKeys = {
  ai: {
    all: ["ai"] as const,
    providers: { ... },
    assistants: { ... },
    // Add chat keys here
  },
};
```

### 4.4 Component Pattern (from AIAssistantList.tsx)

- Use Ant Design components (List, Modal, etc.)
- TanStack Query for data fetching
- Toast notifications via sonner
- TypeScript strict types

---

## 5. Dependencies

### 5.1 Resolved Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Backend chat API | ✅ Complete | Phase 1 |
| AI configuration UI | ✅ Complete | Phase 2 |
| User authentication | ✅ Complete | Existing |
| RBAC system | ✅ Complete | ai-chat permission exists |

### 5.2 Technical Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| @tanstack/react-query | Existing | Data fetching |
| antd | Existing | UI components |
| axios | Existing | HTTP client |
| sonner | Existing | Toast notifications |
| react-router-dom | Existing | Routing |

---

## 6. Design Considerations

### 6.1 UX Patterns

**ChatGPT-like Interface:**
- Sidebar: Session history (collapsible on mobile)
- Main area: Message list + input
- Top bar: Assistant selector
- Auto-scroll to latest message
- Loading indicators during AI processing

**Mobile Responsiveness:**
- Drawer for session list
- Full-width message input
- Touch-friendly buttons

### 6.2 State Management

**URL State:**
- `sessionId` as URL param for direct linking
- `assistantId` as URL param for pre-selection

**Local State:**
- Current session ID
- Selected assistant
- Message list (from API + optimistic updates)

### 6.3 Error Handling

- Network errors: Toast notification
- Validation errors: Inline or toast
- Rate limiting: Display message to user
- Session not found: Redirect to new chat

---

## 7. Component Structure

```
frontend/src/features/ai/chat/
├── api/
│   ├── useChat.ts              # Send message hook
│   ├── useChatSessions.ts      # List/load sessions
│   └── __tests__/              # Hook tests
├── components/
│   ├── ChatInterface.tsx       # Main container
│   ├── SessionList.tsx         # Sidebar component
│   ├── MessageList.tsx         # Message display
│   ├── MessageInput.tsx        # Input component
│   ├── AssistantSelector.tsx   # Dropdown
│   └── __tests__/              # Component tests
└── types.ts                    # Chat types (extend existing)
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

| Component/Hook | Coverage Goal | Key Test Cases |
|----------------|---------------|----------------|
| useChat | 90% | Send message, loading state, error handling |
| useChatSessions | 90% | List sessions, pagination, filtering |
| useChatMessages | 90% | Load messages, empty state |
| SessionList | 80% | Render, select, delete |
| MessageList | 80% | Render messages, auto-scroll |
| MessageInput | 80% | Send on enter, validation |
| AssistantSelector | 80% | Render, filter active |
| ChatInterface | 80% | Integration flow |

### 8.2 Integration Tests

- Full chat flow (create session, send message, receive response)
- Session switching
- Error recovery
- Permission checks

---

## 9. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| AI responses may be slow | User experience | Show loading indicator |
| Tool calls may fail | Data integrity | Graceful error display |
| Session state conflicts | Data consistency | Optimistic updates with rollback |
| Mobile UX issues | Accessibility | Responsive design testing |

---

## 10. Success Criteria

- [ ] User can access chat interface at `/chat` route
- [ ] User can select from available AI assistants
- [ ] User can send messages and receive responses
- [ ] Conversation history persists across sessions
- [ ] User can create new conversations
- [ ] User can delete old conversations
- [ ] RBAC enforced (ai-chat permission required)
- [ ] TypeScript strict mode passing (0 errors)
- [ ] 80%+ test coverage

---

## 11. Next Steps

Proceed to **PLAN Phase** to create detailed implementation plan including:
1. File structure and component hierarchy
2. API hook implementation details
3. Component prop contracts
4. Test file structure
5. Route configuration
