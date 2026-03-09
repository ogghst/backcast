# PLAN: E09-U11 - Frontend AI Chat Interface

**Date:** 2026-03-08
**Epic:** E009 - AI Integration (Phase 3)
**User Story:** E09-U11
**Story Points:** 8

---

## 1. Implementation Overview

This plan follows the established frontend patterns from Phase 2 AI Configuration UI, using TanStack Query for state management and Ant Design for UI components.

### 1.1 Implementation Phases

| Phase | Tasks | Deliverable |
|-------|-------|-------------|
| 1 | Types & Query Keys | Foundation for API hooks |
| 2 | API Hooks | Data layer for chat operations |
| 3 | UI Components | Reusable chat components |
| 4 | Page Integration | Main chat interface page |
| 5 | Routing & Navigation | App integration |
| 6 | Testing & Quality | Verification & documentation |

---

## 2. File Structure

```
frontend/src/
├── api/
│   └── queryKeys.ts              # ADD: chat query keys
├── features/ai/
│   ├── types.ts                  # ADD: chat types
│   ├── chat/
│   │   ├── api/
│   │   │   ├── useChat.ts        # NEW: Send message hook
│   │   │   ├── useChatSessions.ts  # NEW: Session management
│   │   │   └── __tests__/
│   │   │       ├── useChat.test.tsx
│   │   │       └── useChatSessions.test.tsx
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx     # NEW: Main container
│   │   │   ├── SessionList.tsx       # NEW: Session sidebar
│   │   │   ├── MessageList.tsx       # NEW: Message display
│   │   │   ├── MessageInput.tsx      # NEW: Input component
│   │   │   ├── AssistantSelector.tsx # NEW: Assistant dropdown
│   │   │   └── __tests__/
│   │   │       ├── ChatInterface.test.tsx
│   │   │       ├── SessionList.test.tsx
│   │   │       ├── MessageList.test.tsx
│   │   │       ├── MessageInput.test.tsx
│   │   │       └── AssistantSelector.test.tsx
│   │   └── index.ts              # NEW: Barrel exports
├── pages/
│   └── chat/
│       └── ChatInterface.tsx    # NEW: Page component
├── routes/
│   └── index.tsx                # MODIFY: Add /chat route
└── layouts/
    └── AppLayout.tsx            # MODIFY: Add nav link
```

---

## 3. Type Definitions

### 3.1 Add to `frontend/src/features/ai/types.ts`

```typescript
/**
 * AI Chat Types
 * Matches backend schemas in backend/app/models/schemas/ai.py
 */

export interface AIChatRequest {
  message: string;
  session_id?: string | null;
  assistant_config_id?: string | null;
}

export interface AIChatResponse {
  session_id: string;
  message: AIConversationMessagePublic;
  tool_calls?: Array<Record<string, any>>;
}

export interface AIConversationSessionPublic {
  id: string;
  user_id: string;
  assistant_config_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface AIConversationMessagePublic {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  tool_calls?: Array<Record<string, any>>;
  tool_results?: Record<string, any>;
  created_at: string;
}

// Helper types
export type MessageRole = "user" | "assistant" | "tool";

export interface ChatSession {
  id: string;
  title: string | null;
  assistantId: string;
  createdAt: string;
  updatedAt: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  toolCalls?: Array<Record<string, any>>;
  toolResults?: Record<string, any>;
  createdAt: string;
}
```

### 3.2 Add to `frontend/src/api/queryKeys.ts`

```typescript
// In the ai section, add:
ai: {
  all: ["ai"] as const,
  providers: { /* existing */ },
  assistants: { /* existing */ },
  chat: {
    all: ["ai", "chat"] as const,
    sessions: () => ["ai", "chat", "sessions"] as const,
    session: (id: string) => ["ai", "chat", "sessions", id] as const,
    messages: (sessionId: string) => ["ai", "chat", "sessions", sessionId, "messages"] as const,
  },
},
```

---

## 4. API Hooks Implementation

### 4.1 `useChatSessions.ts`

```typescript
/**
 * Chat Session API Hooks
 *
 * - useChatSessions(): List all user sessions
 * - useChatSession(): Get single session details
 * - useDeleteSession(): Delete a session
 */

const API_BASE = "/api/v1/ai/chat";

export interface UseChatSessionsOptions {
  enabled?: boolean;
}

export const useChatSessions = (options?: UseChatSessionsOptions) => {
  return useQuery<AIConversationSessionPublic[], Error>({
    queryKey: queryKeys.ai.chat.sessions(),
    queryFn: () => axios.get(`${API_BASE}/sessions`).then(r => r.data),
    ...options,
  });
};

export const useDeleteSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => axios.delete(`${API_BASE}/sessions/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.chat.sessions() });
      toast.success("Chat deleted");
    },
  });
};
```

### 4.2 `useChat.ts`

```typescript
/**
 * Chat Message API Hooks
 *
 * - useChatMessages(): Get messages for a session
 * - useSendMessage(): Send a message and get AI response
 */

export const useChatMessages = (sessionId: string) => {
  return useQuery<AIConversationMessagePublic[], Error>({
    queryKey: queryKeys.ai.chat.messages(sessionId),
    queryFn: () => axios.get(`${API_BASE}/sessions/${sessionId}/messages`).then(r => r.data),
    enabled: !!sessionId,
  });
};

export const useSendMessage = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: AIChatRequest) =>
      axios.post<AIChatResponse>(`${API_BASE}/chat`, request),
    onSuccess: (response) => {
      // Invalidate messages query for the session
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.chat.messages(response.data.session_id),
      });
      // Invalidate sessions list (for updated timestamps)
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.chat.sessions() });
    },
  });
};
```

---

## 5. Component Specifications

### 5.1 `AssistantSelector.tsx`

**Props:**
```typescript
interface AssistantSelectorProps {
  value?: string;
  onChange: (assistantId: string) => void;
  disabled?: boolean;
}
```

**Behavior:**
- Dropdown using Ant Design `<Select>`
- Filter to show only `is_active: true` assistants
- Display assistant name + description
- Show loading state while fetching

### 5.2 `SessionList.tsx`

**Props:**
```typescript
interface SessionListProps {
  currentSessionId?: string;
  onSessionSelect: (sessionId: string) => void;
  onNewChat: () => void;
}
```

**Behavior:**
- List using Ant Design `<List>` or `<Menu>`
- Display session title (or "New Chat" + date)
- Highlight current session
- Delete button with confirmation
- "New Chat" button at top

### 5.3 `MessageList.tsx`

**Props:**
```typescript
interface MessageListProps {
  messages: ChatMessage[];
  loading?: boolean;
}
```

**Behavior:**
- Scrollable container
- User messages: right-aligned, blue background
- Assistant messages: left-aligned, gray background
- Tool messages: special styling
- Auto-scroll to bottom on new messages
- Empty state illustration

### 5.4 `MessageInput.tsx`

**Props:**
```typescript
interface MessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  loading?: boolean;
  placeholder?: string;
}
```

**Behavior:**
- `<Input.TextArea>` with auto-resize
- Send button (disabled when empty/loading)
- Enter to send, Shift+Enter for newline
- Character counter (max 10000)

### 5.5 `ChatInterface.tsx` (Main Container)

**State:**
```typescript
const [selectedAssistantId, setSelectedAssistantId] = useState<string>();
const [currentSessionId, setCurrentSessionId] = useState<string>();
```

**Behavior:**
- Fetch sessions on mount
- Fetch messages when session selected
- Handle send message flow
- Create new session on first message
- Handle session switching

---

## 6. Page Implementation

### 6.1 `pages/chat/ChatInterface.tsx`

```typescript
import { ChatInterface } from "@/features/ai/chat";

export const ChatInterfacePage = () => {
  return <ChatInterface />;
};
```

### 6.2 Route Configuration

Add to `routes/index.tsx`:
```typescript
import { ChatInterfacePage } from "@/pages/chat/ChatInterface";

{
  path: "/chat",
  element: (
    <ProtectedRoute permission="ai-chat">
      <ChatInterfacePage />
    </ProtectedRoute>
  ),
}
```

### 6.3 Navigation Link

Add to `layouts/AppLayout.tsx`:
- Add "AI Chat" link to navigation menu
- Icon: MessageOutlined or CommentOutlined

---

## 7. Testing Plan

### 7.1 Test File Structure

```
__tests__/
├── useChat.test.tsx          # Hook tests
├── useChatSessions.test.tsx  # Hook tests
├── AssistantSelector.test.tsx
├── SessionList.test.tsx
├── MessageList.test.tsx
├── MessageInput.test.tsx
└── ChatInterface.test.tsx
```

### 7.2 Test Coverage Targets

| Component | Target | Key Scenarios |
|-----------|--------|---------------|
| API Hooks | 90% | Success, error, loading, cache |
| AssistantSelector | 80% | Render, select, filter, empty |
| SessionList | 80% | Render, select, delete, new chat |
| MessageList | 80% | Render, scroll, empty, tool messages |
| MessageInput | 80% | Send, validation, keyboard |
| ChatInterface | 80% | Full flow, error handling |

### 7.3 Test Utilities

Create `frontend/src/features/ai/chat/test-utils.tsx`:
```typescript
export const mockSession: AIConversationSessionPublic = { ... };
export const mockMessage: AIConversationMessagePublic = { ... };
export const mockAssistant: AIAssistantPublic = { ... };
export const renderWithQuery = (component) => { ... };
```

---

## 8. Implementation Checklist

### Phase 1: Foundation
- [ ] Add chat types to `frontend/src/features/ai/types.ts`
- [ ] Add chat query keys to `frontend/src/api/queryKeys.ts`

### Phase 2: API Hooks
- [ ] Create `useChatSessions.ts` with tests
- [ ] Create `useChat.ts` with tests
- [ ] Write hook tests (90%+ coverage)

### Phase 3: Components
- [ ] Create `AssistantSelector.tsx` with tests
- [ ] Create `SessionList.tsx` with tests
- [ ] Create `MessageList.tsx` with tests
- [ ] Create `MessageInput.tsx` with tests

### Phase 4: Integration
- [ ] Create `ChatInterface.tsx` (main container)
- [ ] Create `pages/chat/ChatInterface.tsx`
- [ ] Add route to `routes/index.tsx`
- [ ] Add navigation link to `AppLayout.tsx`

### Phase 5: Quality
- [ ] TypeScript: 0 errors
- [ ] ESLint: 0 errors
- [ ] Tests: 80%+ coverage
- [ ] Manual testing checklist

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| TypeScript errors | 0 | `npx tsc --noEmit` |
| ESLint errors | 0 | `npm run lint` |
| Test coverage | 80%+ | `npm run test:coverage` |
| Functional tests | Pass | Manual testing |

---

## 10. Risk Mitigation

| Risk | Plan |
|------|------|
| API changes | Follow backend OpenAPI spec |
| State complexity | Keep local state minimal, rely on TanStack Query |
| Performance | Pagination for sessions (future iteration) |
| Mobile UX | Responsive design with drawer |

---

## 11. Next Steps

Proceed to **DO Phase** to implement following RED-GREEN-REFACTOR TDD methodology:

1. **RED**: Write failing tests for each component/hook
2. **GREEN**: Make tests pass with minimal implementation
3. **REFACTOR**: Improve code quality while keeping tests green

Execute implementation checklist in order, completing each phase before moving to the next.
