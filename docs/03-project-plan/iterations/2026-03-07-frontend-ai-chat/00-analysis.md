# Analysis: Frontend AI Configuration UI

**Created:** 2026-03-07
**Request:** Create frontend UI for AI configuration management (Epic E009, Phase 2: Frontend Configuration)
**Status:** ANALYSIS COMPLETE - Awaiting User Feedback

---

## 1. Clarified Requirements

### 1.1 Functional Requirements

**E09-U01: Configure AI Providers**
- List all AI providers (OpenAI, Azure, Ollama)
- Create new provider with type, name, base URL
- Update provider settings
- Delete provider
- Activate/deactivate provider

**E09-U02: Manage API Keys**
- List config keys for a provider
- Set API key values (secure input, masked display)
- Mark keys as encrypted (default for API keys)
- Delete config keys

**E09-U03: Manage AI Models**
- List models available for a provider
- Create model entries (model_id, display_name)
- Activate/deactivate models

**E09-U03: Configure AI Assistants**
- List all assistant configurations
- Create assistant with name, description, model selection
- Configure system prompt, temperature, max_tokens
- Select allowed tools (checkboxes)
- Activate/deactivate assistants

**Scope Clarification:**
- This iteration covers AI Configuration UI ONLY (admin interface)
- E09-U11 (Chat Interface) is a SEPARATE iteration with its own analysis

### 1.2 Non-Functional Requirements

- **Type Safety:** Full TypeScript strict mode compliance
- **Performance:** Efficient caching with TanStack Query
- **Security:** RBAC enforcement with `<Can>` component
- **UX:** Consistent with existing admin pages
- **Accessibility:** Ant Design components (ARIA compliant)
- **Code Quality:** ESLint clean, 80%+ test coverage

### 1.3 Constraints

- **Backend APIs:** Must use existing `/api/v1/ai/config/*` endpoints (Phase 1 complete)
- **OpenAPI Client:** Need to regenerate OpenAPI client to include AI endpoints
- **Permission Names:** Backend uses `ai-config-read`, `ai-config-write`, etc.
- **Non-Versioned Entities:** AI config uses `SimpleBase` (not versioned)
- **No WebSocket:** Real-time streaming not needed for config UI

---

## 2. Context Discovery

### 2.1 Product Scope

**Relevant User Stories:**
- E09-U01: Configure AI providers (OpenAI, Azure, local) - In Scope
- E09-U02: Manage API keys securely (encrypted storage) - In Scope
- E09-U03: Create/configure AI assistants with tool permissions - In Scope
- E09-U11: Frontend AI chat interface - **OUT OF SCOPE** (separate iteration)

**Business Requirements:**
- Admin-only configuration interface
- Secure handling of API keys (masked display)
- Multi-provider support from start
- Tool permission management for assistants

### 2.2 Architecture Context

**Bounded Contexts:**
- AI/ML Integration Context (new)
- Admin/Configuration Context (existing)
- Authentication/Authorization Context (existing)

**Existing Patterns to Follow:**
- Feature module structure: `frontend/src/features/{domain}/`
- API layer with custom hooks: `api/use{Resource}.ts`
- Component organization: `components/` for modals and lists
- Page-level components in `pages/admin/`
- Barrel exports via `index.ts`

**Architectural Constraints:**
- Must use TanStack Query for server state
- Must use Ant Design components
- Must enforce RBAC with `<Can>` component
- Must follow queryKeys factory pattern
- AI entities are NON-versioned (use `useCrud`, not `useVersionedCrud`)

### 2.3 Codebase Analysis

**Backend:**

**Existing Related APIs:**
- `backend/app/api/routes/ai_config.py` - All AI configuration endpoints
- `backend/app/models/schemas/ai.py` - Pydantic schemas
- `backend/app/services/ai_config_service.py` - AI configuration service

**Data Models:**
Key schema types from `backend/app/models/schemas/ai.py`:

- `AIProviderPublic`: id, provider_type, name, base_url, is_active, created_at, updated_at
- `AIProviderConfigPublic`: id, provider_id, key, value (***MASKED*** if encrypted), is_encrypted, created_at, updated_at
- `AIModelPublic`: id, provider_id, model_id, display_name, is_active, created_at, updated_at
- `AIAssistantConfigPublic`: id, name, description, model_id, system_prompt, temperature, max_tokens, allowed_tools, is_active, created_at, updated_at

**Frontend:**

**Comparable Components:**

| Feature | Reference File | Pattern Used |
|---------|---------------|--------------|
| User Management | `frontend/src/features/users/components/UserModal.tsx` | Modal with Form |
| Department Management | `frontend/src/pages/admin/DepartmentManagement.tsx` | Full page with table + modal |
| Change Order List | `frontend/src/features/change-orders/components/ChangeOrderList.tsx` | Table with actions |
| Custom Hooks | `frontend/src/hooks/useCrud.ts` | `createResourceHooks` factory |

**State Management:**
- TanStack Query for server state (all API calls)
- Zustand for client state (auth, preferences, time machine)

**Routing Structure:**
Admin pages follow pattern: `/admin/{resource}`

Proposed AI routes:
- `/admin/ai-providers` - AI provider management
- `/admin/ai-assistants` - AI assistant configuration

---

## 3. Solution Options

### Option 1: Single Unified AI Admin Page

**Architecture & Design:**

One comprehensive admin page at `/admin/ai` with tabbed interface:

```
┌─────────────────────────────────────────────────────┐
│ AI Configuration                             [Admin]│
├─────────────────────────────────────────────────────┤
│ [Providers] [Assistants]                             │
├─────────────────────────────────────────────────────┤
│                                                       │
│ Provider List:                                       │
│ ┌─────────────────────────────────────────────────┐ │
│ │ OpenAI (active)    [Configure] [Edit] [Delete]  │ │
│ │ Azure (inactive)   [Configure] [Edit] [Delete]  │ │
│ │ [+ Add Provider]                                │ │
│ └─────────────────────────────────────────────────┘ │
│                                                       │
│ Assistant List:                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Project Helper (gpt-4)  [Edit] [Delete]         │ │
│ │ [+ Add Assistant]                               │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Single entry point<br>- Context switching between tabs<br>- Shared state possible |
| Cons            | - Complex component with multiple concerns<br>- Harder to navigate directly to specific section |
| Complexity      | Medium                     |
| Maintainability | Good                       |

---

### Option 2: Separate Admin Pages per Resource (RECOMMENDED)

**Architecture & Design:**

Dedicated admin pages following existing pattern:

```
Admin Menu:
├── Users
├── Departments
├── Cost Element Types
├── AI Providers      <-- NEW
└── AI Assistants     <-- NEW
```

**UX Design:**
- `/admin/ai-providers` - Provider list with API key management
- `/admin/ai-assistants` - Assistant configuration list
- Direct navigation to each resource
- Follows existing admin page pattern

**Implementation:**
- Files:
  - `frontend/src/pages/admin/AIProviderManagement.tsx`
  - `frontend/src/pages/admin/AIAssistantManagement.tsx`
- Components in `frontend/src/features/ai/`
- API hooks following `useChangeOrders` pattern

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Consistent with existing pattern<br>- Clear separation of concerns<br>- Easier direct navigation<br>- Simpler components |
| Cons            | - More files to maintain<br>- Need to navigate between pages |
| Complexity      | Low                        |
| Maintainability | Excellent                  |

---

### Option 3: Hybrid Approach with Nested Routes

**Architecture & Design:**

Parent route with nested child routes:

```
/admin/ai
├── /admin/ai/providers
├── /admin/ai/providers/:id/models
└── /admin/ai/assistants
```

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Scalable for future AI features<br>- Clear hierarchy<br>- Good for deep linking |
| Cons            | - More complex routing setup<br>- Overkill for current scope |
| Complexity      | Medium-High                |
| Maintainability | Good                       |

---

## 4. Comparison Summary

| Criteria           | Option 1 (Unified) | Option 2 (Separate) | Option 3 (Hybrid) |
| ------------------ | ------------------ | ------------------- | ----------------- |
| Development Effort | 3-4 days           | 2-3 days            | 4-5 days          |
| UX Quality         | Good               | Excellent           | Good              |
| Flexibility        | Medium             | High                | Very High         |
| Consistency        | Low (new pattern)  | High (follows existing) | Medium      |
| Best For           | Simple AI config   | Current scope       | Future expansion  |

---

## 5. Recommendation

**I recommend Option 2: Separate Admin Pages per Resource**

**Rationale:**

1. **Pattern Consistency:** Follows existing admin page structure (DepartmentManagement, UserList)
2. **Separation of Concerns:** Each page has a single responsibility
3. **Lower Complexity:** No need for tabs, nested routes, or layout components
4. **Better Code Splitting:** Separate routes enable automatic code splitting
5. **Future Flexibility:** Easy to add more AI configuration resources later
6. **Easier Testing:** Each page can be tested independently

---

## 6. Implementation File Structure

```
frontend/src/
├── features/
│   └── ai/
│       ├── api/
│       │   ├── useAIProviders.ts      # Provider CRUD hooks
│       │   ├── useAIModels.ts         # Model CRUD hooks
│       │   ├── useAIAssistants.ts     # Assistant CRUD hooks
│       │   └── index.ts
│       ├── components/
│       │   ├── AIProviderModal.tsx    # Create/edit provider
│       │   ├── AIProviderConfigModal.tsx  # Set API keys
│       │   ├── AIModelModal.tsx       # Create/edit model
│       │   ├── AIAssistantModal.tsx   # Create/edit assistant
│       │   ├── AIProviderList.tsx     # Provider table
│       │   ├── AIAssistantList.tsx    # Assistant table
│       │   └── index.ts
│       ├── types.ts                   # AI-specific types
│       └── index.ts
├── pages/
│   └── admin/
│       ├── AIProviderManagement.tsx   # Provider admin page
│       └── AIAssistantManagement.tsx  # Assistant admin page
├── api/
│   └── queryKeys.ts                   # Add AI query keys
└── routes/
    └── index.tsx                      # Add admin routes
```

---

## 7. Key Design Decisions

### 7.1 OpenAPI Client Generation

**Status:** AI endpoints not in current OpenAPI client

**Action Required:** Run `npm run generate-client` after backend deployment

### 7.2 Query Keys Factory

Add to `frontend/src/api/queryKeys.ts`:

```typescript
ai: {
  all: ["ai"] as const,
  providers: {
    all: ["ai", "providers"] as const,
    list: () => ["ai", "providers", "list"] as const,
    detail: (id: string) => ["ai", "providers", id] as const,
  },
  models: {
    byProvider: (providerId: string) =>
      ["ai", "models", "provider", providerId] as const,
  },
  assistants: {
    all: ["ai", "assistants"] as const,
    list: () => ["ai", "assistants", "list"] as const,
    detail: (id: string) => ["ai", "assistants", id] as const,
  },
}
```

### 7.3 RBAC Permissions

- `ai-config-read` - View AI configuration
- `ai-config-write` - Create/edit AI configuration
- `ai-config-delete` - Delete AI configuration

---

## 8. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| OpenAPI client not regenerated | HIGH | Medium | Run generation as first DO step |
| Permission names mismatch | MEDIUM | Low | Verify with backend before implementing |
| API key exposure in logs | HIGH | Low | Backend masks encrypted values |
| Tool permissions unclear | LOW | Medium | Start with list_projects only |

---

## 9. Success Criteria

### Must Have (MVP)

- [ ] Admin can view list of AI providers
- [ ] Admin can create/edit/delete AI providers
- [ ] Admin can set/view API keys (masked in display)
- [ ] Admin can create/edit/delete AI models per provider
- [ ] Admin can create/edit/delete AI assistants
- [ ] Admin can select allowed tools for assistants
- [ ] All actions protected with RBAC
- [ ] TanStack Query caching configured correctly
- [ ] ESLint clean, TypeScript strict
- [ ] Unit tests (80%+ coverage)

---

## 10. Decision Questions

Before proceeding to PLAN phase, please confirm:

1. **Route Structure:** Do you approve `/admin/ai-providers` and `/admin/ai-assistants` as separate routes? (Option 2)

2. **Model Management:** Should models be managed inline within the provider modal, or as a separate modal? (Recommend: separate modal)

3. **Tool Permissions:** Should the assistant modal show ALL available tools, or only those currently implemented? (Recommend: Show all with disabled tooltips)

4. **API Key Display:** Should masked API keys show asterisks (`****`) or a placeholder like `[Encrypted]`? (Recommend: asterisks)

---

## 11. Next Steps

### Pending User Approval

1. Review this analysis document
2. Answer decision questions above
3. Approve recommended approach (Option 2)

### After Approval

1. **PLAN Phase:** Create detailed implementation plan
2. **DO Phase:** Implement following TDD
3. **CHECK Phase:** Verify all tests pass
4. **ACT Phase:** Update documentation

---

## 12. References

- [Epic E009: AI Integration](../../epics.md#epic-9-ai-integration-e009)
- [Backend Phase 1 Analysis](../2026-03-05-ai-integration/00-analysis.md)
- [Frontend Admin Page Pattern](../../../../frontend/src/pages/admin/DepartmentManagement.tsx)
- [Query Keys Factory](../../../../frontend/src/api/queryKeys.ts)
