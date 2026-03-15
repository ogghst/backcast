# Plan: Frontend AI Configuration UI

**Created:** 2026-03-07
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 2 - Separate Admin Pages per Resource

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 2 - Separate Admin Pages per Resource
- **Architecture**: Dedicated admin pages following existing pattern with feature-based organization
- **Key Decisions**:
  - Routes: `/admin/ai-providers` and `/admin/ai-assistants` (separate pages)
  - Model Management: Separate modal for AI models (accessed from provider list)
  - Tool Display: Show ALL tools with disabled tooltips for unimplemented ones
  - API Key Display: Show asterisks (`****`) for masked encrypted values
  - RBAC Permissions: Use `ai-config-read`, `ai-config-create`, `ai-config-update`, `ai-config-delete`

### Success Criteria

**Functional Criteria:**

- [ ] Admin users can view list of AI providers with type, name, base URL, and active status VERIFIED BY: Visual inspection test
- [ ] Admin users can create new AI providers with type (openai/azure/ollama), name, and base URL VERIFIED BY: Integration test
- [ ] Admin users can edit existing AI providers VERIFIED BY: Integration test
- [ ] Admin users can delete AI providers with confirmation dialog VERIFIED BY: Integration test
- [ ] Admin users can activate/deactivate providers VERIFIED BY: Unit test
- [ ] Admin users can view provider API keys with masked values (`****`) VERIFIED BY: Visual regression test
- [ ] Admin users can set/update API key values through secure input VERIFIED BY: Integration test
- [ ] Admin users can delete API keys VERIFIED BY: Integration test
- [ ] Admin users can view models available for each provider VERIFIED BY: Integration test
- [ ] Admin users can create model entries (model_id, display_name) VERIFIED BY: Integration test
- [ ] Admin users can activate/deactivate models VERIFIED BY: Unit test
- [ ] Admin users can view list of AI assistants VERIFIED BY: Visual inspection test
- [ ] Admin users can create assistants with name, description, model selection, system prompt, temperature, max_tokens VERIFIED BY: Integration test
- [ ] Admin users can select allowed tools via checkboxes (all tools shown, unimplemented disabled) VERIFIED BY: Unit test
- [ ] Admin users can edit existing assistants VERIFIED BY: Integration test
- [ ] Admin users can delete assistants with confirmation VERIFIED BY: Integration test
- [ ] All CRUD operations are protected with appropriate RBAC permissions VERIFIED BY: Authorization test

**Technical Criteria:**

- [ ] Performance: Page load time < 500ms, API response caching configured VERIFIED BY: Performance measurement
- [ ] Security: API keys never exposed in console logs or network responses (backend masks) VERIFIED BY: Security audit
- [ ] Type Safety: Full TypeScript strict mode compliance, zero `any` types in new code VERIFIED BY: TypeScript compiler
- [ ] Code Quality: ESLint clean (zero errors), 80%+ test coverage VERIFIED BY: CI pipeline
- [ ] Query Caching: TanStack Query properly configured with queryKeys factory VERIFIED BY: Code review

**Business Criteria:**

- [ ] Admin users can independently configure AI providers without developer intervention VERIFIED BY: User acceptance test
- [ ] Configuration changes are reflected immediately in the system VERIFIED BY: Integration test
- [ ] UI consistency matches existing admin pages for familiar user experience VERIFIED BY: Visual comparison

### Scope Boundaries

**In Scope:**

- AI Provider management (list, create, edit, delete, activate/deactivate)
- AI Provider API key management (view masked, set, delete)
- AI Model management per provider (list, create, edit, delete, activate/deactivate)
- AI Assistant configuration (list, create, edit, delete, activate/deactivate)
- Tool permission selection for assistants
- RBAC enforcement on all operations
- TanStack Query integration with proper caching
- Query keys factory integration
- Type definitions for AI entities
- Route setup for new admin pages
- Unit tests for components and hooks
- Integration tests for API interactions

**Out of Scope:**

- E09-U11: Frontend AI chat interface (separate iteration)
- Real-time validation of API keys (backend validates on use)
- Provider-specific configuration UI beyond generic key-value pairs
- Advanced assistant features like file uploads or image handling
- API usage analytics or cost tracking
- Multi-language support for assistant prompts
- Conversation history management (chat interface feature)
- Streaming responses (chat interface feature)

---

## Work Decomposition

### Task Breakdown

| #   | Task                                               | Files                                                                                                                            | Dependencies  | Success Criteria                                                                                                                                           | Complexity |
| --- | -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| 1   | Regenerate OpenAPI client with AI endpoints        | `frontend/src/api/generated/`                                                                                                    | None          | AI configuration types available in generated client; TypeScript compilation succeeds                                                                      | Low        |
| 2   | Add AI query keys to centralized factory           | `frontend/src/api/queryKeys.ts`                                                                                                  | Task 1        | Query keys for providers, models, assistants follow factory pattern; TypeScript types export correctly                                                      | Low        |
| 3   | Create AI-specific type definitions                | `frontend/src/features/ai/types.ts`                                                                                              | Task 1        | Types export correctly; match backend Pydantic schemas; no `any` types                                                                                     | Low        |
| 4   | Implement provider API hooks                       | `frontend/src/features/ai/api/useAIProviders.ts`                                                                                 | Task 2, 3     | List, detail, create, update, delete hooks work; mutations invalidate cache; toast notifications on success/error                                         | Medium     |
| 5   | Implement model API hooks                          | `frontend/src/features/ai/api/useAIModels.ts`                                                                                    | Task 2, 3     | List by provider, create hooks work; proper cache invalidation                                                                                             | Medium     |
| 6   | Implement assistant API hooks                      | `frontend/src/features/ai/api/useAIAssistants.ts`                                                                                | Task 2, 3     | List, detail, create, update, delete hooks work; mutations invalidate cache                                                                                | Medium     |
| 7   | Create AIProviderModal component                   | `frontend/src/features/ai/components/AIProviderModal.tsx`                                                                        | Task 3        | Form validates provider_type, name, base_url; create/edit modes work; follows UserModal pattern                                                            | Medium     |
| 8   | Create AIProviderConfigModal component             | `frontend/src/features/ai/components/AIProviderConfigModal.tsx`                                                                  | Task 3, 4     | Form shows existing keys masked; allows setting new values; delete confirmation; secure password input                                                     | Medium     |
| 9   | Create AIModelModal component                      | `frontend/src/features/ai/components/AIModelModal.tsx`                                                                           | Task 3, 5     | Form validates model_id, display_name; create/edit modes work                                                                                              | Low        |
| 10  | Create AIAssistantModal component                  | `frontend/src/features/ai/components/AIAssistantModal.tsx`                                                                       | Task 3, 6     | Form validates all fields; tool checkboxes work (all shown, unimplemented disabled); model selection dropdown; temperature/max_tokens sliders                 | High       |
| 11  | Create AIProviderList component                    | `frontend/src/features/ai/components/AIProviderList.tsx`                                                                         | Task 4, 7, 8  | Table displays providers correctly; edit/delete/configure buttons work; RBAC respected; follows StandardTable pattern                                      | High       |
| 12  | Create AIAssistantList component                   | `frontend/src/features/ai/components/AIAssistantList.tsx`                                                                        | Task 6, 10    | Table displays assistants correctly; edit/delete buttons work; RBAC respected; model names display correctly                                              | Medium     |
| 13  | Create AIProviderManagement page                   | `frontend/src/pages/admin/AIProviderManagement.tsx`                                                                              | Task 11       | Page renders correctly; follows DepartmentManagement pattern; "Add Provider" button works; all modals integrate properly                                  | Medium     |
| 14  | Create AIAssistantManagement page                  | `frontend/src/pages/admin/AIAssistantManagement.tsx`                                                                             | Task 12       | Page renders correctly; follows DepartmentManagement pattern; "Add Assistant" button works; modal integrates properly                                    | Medium     |
| 15  | Add routes for new admin pages                     | `frontend/src/routes/index.tsx`                                                                                                  | Task 13, 14   | Routes accessible at `/admin/ai-providers` and `/admin/ai-assistants`; protected routes work                                                               | Low        |
| 16  | Create feature barrel exports                      | `frontend/src/features/ai/api/index.ts`, `frontend/src/features/ai/components/index.ts`, `frontend/src/features/ai/index.ts` | All prior     | All exports accessible; clean import paths                                                                                                                | Low        |
| 17  | Write unit tests for hooks                         | `frontend/src/features/ai/api/__tests__/`                                                                                        | Task 4, 5, 6  | All hooks have tests; coverage >= 80%; mock service layer correctly                                                                                        | Medium     |
| 18  | Write unit tests for components                    | `frontend/src/features/ai/components/__tests__/`                                                                                 | Task 7-12     | All components have tests; user interactions covered; RBAC behavior tested; coverage >= 80%                                                               | High       |
| 19  | Write integration tests for API interactions       | `frontend/src/features/ai/__tests__/integration/`                                                                                | Task 4-6      | CRUD operations tested with MSW; error handling tested; loading states tested                                                                             | Medium     |
| 20  | Final verification and cleanup                     | All files                                                                                                                        | All tasks     | ESLint clean; TypeScript strict mode passes; all tests pass; manual smoke test completed                                                                  | Low        |

### Test-to-Requirement Traceability

| Acceptance Criterion                                                          | Test ID | Test File                                                     | Expected Behavior                                                                                                                                                       |
| ----------------------------------------------------------------------------- | ------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Admin can view list of AI providers                                           | T-001   | `frontend/src/features/ai/components/__tests__/AIProviderList.test.tsx` | Component renders without crashing; table displays provider data from API; loading state shows correctly                                                               |
| Admin can create new AI providers                                             | T-002   | `frontend/src/features/ai/api/__tests__/useAIProviders.test.ts`      | Mutation hook calls create API; success toast fires; cache invalidates; list refreshes with new provider                                                               |
| Admin can edit existing AI providers                                          | T-003   | `frontend/src/features/ai/api/__tests__/useAIProviders.test.ts`      | Mutation hook calls update API with correct ID; success toast fires; detail query updates                                                                               |
| Admin can delete AI providers with confirmation                               | T-004   | `frontend/src/features/ai/components/__tests__/AIProviderList.test.tsx` | Delete button triggers modal confirmation; confirmed delete calls mutation; provider removed from list                                                                 |
| Admin can activate/deactivate providers                                       | T-005   | `frontend/src/features/ai/api/__tests__/useAIProviders.test.ts`      | Update mutation with is_active field toggles status; UI reflects change                                                                                                 |
| Admin can view provider API keys with masked values                           | T-006   | `frontend/src/features/ai/components/__tests__/AIProviderConfigModal.test.tsx` | Modal displays `****` for encrypted values; plain values show unmasked                                                                                                  |
| Admin can set/update API key values                                           | T-007   | `frontend/src/features/ai/api/__tests__/useAIProviders.test.ts`      | Config mutation calls set API; password input masks value; success toast fires                                                                                          |
| Admin can delete API keys                                                     | T-008   | `frontend/src/features/ai/components/__tests__/AIProviderConfigModal.test.tsx` | Delete button removes key; confirmation modal shown; list refreshes                                                                                                     |
| Admin can view models for each provider                                       | T-009   | `frontend/src/features/ai/api/__tests__/useAIModels.test.ts`         | List hook filters by provider_id; models display in modal or inline                                                                                                    |
| Admin can create model entries                                                | T-010   | `frontend/src/features/ai/api/__tests__/useAIModels.test.ts`         | Create mutation includes provider_id from context; model appears in list                                                                                                |
| Admin can activate/deactivate models                                          | T-011   | `frontend/src/features/ai/api/__tests__/useAIModels.test.ts`         | Update mutation toggles is_active; list reflects change                                                                                                                 |
| Admin can view list of AI assistants                                          | T-012   | `frontend/src/features/ai/components/__tests__/AIAssistantList.test.tsx` | Table displays assistant data; model names resolve correctly; tool badges show                                                                                          |
| Admin can create assistants with all fields                                   | T-013   | `frontend/src/features/ai/api/__tests__/useAIAssistants.test.ts`     | Create mutation sends all fields; validation catches invalid ranges (temperature, max_tokens)                                                                          |
| Admin can select allowed tools via checkboxes                                 | T-014   | `frontend/src/features/ai/components/__tests__/AIAssistantModal.test.tsx` | All available tools shown; unimplemented tools disabled with tooltip; selected tools sent in allowed_tools array                                                        |
| Admin can edit existing assistants                                            | T-015   | `frontend/src/features/ai/api/__tests__/useAIAssistants.test.ts`     | Update mutation pre-fills form; changes save correctly                                                                                                                  |
| Admin can delete assistants                                                   | T-016   | `frontend/src/features/ai/components/__tests__/AIAssistantList.test.tsx` | Delete button shows confirmation; confirmed delete removes assistant                                                                                                    |
| All CRUD operations protected with RBAC                                       | T-017   | `frontend/src/features/ai/components/__tests__/rbac.test.tsx`         | Buttons hidden without permissions; API calls fail with 403 without permissions; `<Can>` component wraps actions correctly                                              |
| Query caching configured correctly                                            | T-018   | `frontend/src/features/ai/__tests__/integration/caching.test.tsx`     | List queries cache responses; mutations invalidate correct cache keys; stale data refetches on window focus                                                             |
| TypeScript strict mode compliance                                             | T-019   | (TypeScript compiler)                                          | All new files compile without errors; no implicit any; correct type exports                                                                                             |
| Code quality standards met                                                    | T-020   | (ESLint + Vitest)                                             | ESLint passes with zero errors; test coverage >= 80%; all tests pass                                                                                                    |

---

## Test Specification

### Test Hierarchy

```
frontend/src/features/ai/
├── api/
│   └── __tests__/
│       ├── useAIProviders.test.ts
│       ├── useAIModels.test.ts
│       └── useAIAssistants.test.ts
├── components/
│   └── __tests__/
│       ├── AIProviderModal.test.tsx
│       ├── AIProviderConfigModal.test.tsx
│       ├── AIModelModal.test.tsx
│       ├── AIAssistantModal.test.tsx
│       ├── AIProviderList.test.tsx
│       ├── AIAssistantList.test.tsx
│       └── rbac.test.tsx
└── __tests__/
    └── integration/
        ├── provider-workflow.test.tsx
        ├── assistant-workflow.test.tsx
        └── caching.test.tsx
```

### Test Cases (first 8 critical tests)

| Test ID | Test Name                                                  | Criterion | Type         | Verification                                                                                                                                                     |
| ------- | ---------------------------------------------------------- | --------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-001   | `test_ai_provider_list_renders_provider_data_from_api`     | AC-1      | Component    | Component renders table; data from useList hook displays correctly; loading state shows skeleton                                                                 |
| T-002   | `test_use_ai_providers_create_mutation_calls_api_and_invalidates_cache` | AC-2      | Hook (Unit)  | useCreate returns mutation; mutation calls service.create; onSuccess invalidates queries; success toast fires                                                    |
| T-003   | `test_ai_provider_modal_validation_requires_name_and_type` | AC-2      | Component    | Form validation fails without name; fails without provider_type; passes with both fields                                                                       |
| T-004   | `test_ai_provider_config_modal_masks_encrypted_api_keys`   | AC-6      | Component    | Config with is_encrypted=true displays `****`; config with is_encrypted=false displays actual value                                                             |
| T-005   | `test_ai_assistant_modal_shows_all_tools_with_disabled_unimplemented` | AC-14     | Component    | All tools in TOOL_REGISTRY render; unimplemented tools have disabled=true and tooltip; implemented tools are clickable                                         |
| T-006   | `test_ai_assistant_modal_temperature_validates_range_0_to_2` | AC-13     | Component    | Input accepts 0.5; input accepts 2.0; input rejects 2.5 with validation error                                                                                    |
| T-007   | `test_ai_provider_list_delete_button_requires_confirmation` | AC-4      | Component    | Clicking delete shows modal; cancel closes modal; confirm calls mutation                                                                                        |
| T-008   | `test_use_ai_assistants_create_with_allowed_tools_array`   | AC-13     | Hook (Unit)  | Create mutation sends allowed_tools as array; selected tools persist after creation                                                                              |

### Test Infrastructure Needs

**Fixtures needed:**

```typescript
// frontend/src/features/ai/__tests__/fixtures.ts
export const mockProviders = [
  { id: "1", provider_type: "openai", name: "OpenAI", base_url: "https://api.openai.com/v1", is_active: true, created_at: "2026-03-01", updated_at: "2026-03-01" },
  { id: "2", provider_type: "azure", name: "Azure OpenAI", base_url: null, is_active: false, created_at: "2026-03-01", updated_at: "2026-03-01" },
];

export const mockModels = [
  { id: "1", provider_id: "1", model_id: "gpt-4", display_name: "GPT-4", is_active: true, created_at: "2026-03-01", updated_at: "2026-03-01" },
];

export const mockAssistants = [
  { id: "1", name: "Project Helper", description: "Helps with project management", model_id: "1", system_prompt: "You are helpful", temperature: 0.7, max_tokens: 2000, allowed_tools: ["list_projects"], is_active: true, created_at: "2026-03-01", updated_at: "2026-03-01" },
];

export const mockConfigs = [
  { id: "1", provider_id: "1", key: "api_key", value: "****", is_encrypted: true, created_at: "2026-03-01", updated_at: "2026-03-01" },
];
```

**Mocks/stubs:**

- MSW (Mock Service Worker) handlers for AI API endpoints
- TanStack Query wrapper for testing hooks
- Ant Design theme provider for component tests
- Mock auth context for RBAC tests

**Database state:**

- Not applicable for frontend tests (use MSW)
- Backend tests should seed providers, models, assistants, configs

---

## Risk Assessment

| Risk Type   | Description                                                                 | Probability | Impact       | Mitigation                                                                                                                                                         |
| ----------- | --------------------------------------------------------------------------- | ----------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Technical   | OpenAPI client generation fails or produces incompatible types               | Medium      | High         | Run generation as first DO step; if fails, manually create type definitions matching backend schemas                                                               |
| Integration  | Backend permission names differ from frontend (`ai-config-read` vs `ai:read`) | Low         | High         | Verify exact permission names with backend team before implementation; use constants for permission names                                                           |
| Integration  | Tool registry not defined or incomplete                                      | Medium      | Medium       | Start with minimal tool list; define TOOL_REGISTRY constant in frontend; coordinate with backend on available tools                                               |
| UX          | API key masking UX confusing (users think they lost the key)                | Low         | Medium       | Add help text explaining masking; show "Last updated" timestamp; add tooltip explaining security                                                                   |
| Technical   | TanStack Query cache invalidation causes stale data                          | Low         | Medium       | Follow queryKeys factory pattern; use explicit invalidation in mutations; test cache behavior with integration tests                                              |
| Performance  | Large number of tools slows down assistant modal render                      | Low         | Low          | Virtualize tool list if > 50 items; lazy load tool definitions; current tool count is small (< 10)                                                                |
| Security    | API keys exposed in browser console or network tab                           | Low         | High         | Backend must mask values (already implemented); frontend never logs sensitive data; verify with browser DevTools during testing                                  |

---

## Documentation References

### Required Reading

- **Coding Standards:** `/home/nicola/dev/backcast_evs/docs/02-architecture/coding-standards.md`
- **Frontend Architecture:** `/home/nicola/dev/backcast_evs/docs/02-architecture/frontend-architecture.md`
- **Epic E009:** `/home/nicola/dev/backcast_evs/docs/03-project-plan/epics.md#epic-9-ai-integration-e009`
- **Backend Phase 1 Plan:** `/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-03-05-ai-integration/01-plan.md`
- **Glossary:** `/home/nicola/dev/backcast_evs/docs/01-product-scope/glossary.md`

### Code References

**Frontend Patterns:**

- **Modal Pattern:** `/home/nicola/dev/backcast_evs/frontend/src/features/users/components/UserModal.tsx`
- **Admin Page Pattern:** `/home/nicola/dev/backcast_evs/frontend/src/pages/admin/DepartmentManagement.tsx`
- **CRUD Hook Factory:** `/home/nicola/dev/backcast_evs/frontend/src/hooks/useCrud.ts`
- **Query Keys Factory:** `/home/nicola/dev/backcast_evs/frontend/src/api/queryKeys.ts`
- **RBAC Component:** `/home/nicola/dev/backcast_evs/frontend/src/components/auth/Can.tsx`

**Backend API (for reference):**

- **AI Routes:** `/home/nicola/dev/backcast_evs/backend/app/api/routes/ai_config.py`
- **AI Schemas:** `/home/nicola/dev/backcast_evs/backend/app/models/schemas/ai.py`
- **OpenAPI Spec:** Run `cd backend && uv run python -m app.main` then access `http://localhost:8000/openapi.json`

**Test Patterns:**

- **Component Test Example:** `/home/nicola/dev/backcast_evs/frontend/src/features/users/components/__tests__/UserModal.test.tsx`
- **Hook Test Example:** `/home/nicola/dev/backcast_evs/frontend/src/hooks/__tests__/useCrud.test.ts`
- **MSW Setup:** `/home/nicola/dev/backcast_evs/frontend/src/mocks/handlers.ts`

---

## Prerequisites

### Technical

- [ ] Backend AI configuration endpoints deployed and accessible
- [ ] OpenAPI spec includes AI endpoints (`/api/v1/ai/config/*`)
- [ ] Frontend dependencies installed (`cd frontend && npm install`)
- [ ] Test database configured (for backend integration tests if needed)
- [ ] MSW (Mock Service Worker) set up in frontend test environment

### Documentation

- [x] Analysis phase approved (00-analysis.md complete)
- [ ] Backend Phase 1 implementation complete and verified
- [ ] Permission names verified with backend team
- [ ] Tool registry defined (list of available tools)

### Environment

- [ ] Backend server running locally or accessible via VPN
- [ ] PostgreSQL database running
- [ ] Frontend dev server ready (`npm run dev`)
- [ ] Test environment configured (`npm test` passes)

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Verify backend AI endpoints and regenerate OpenAPI client"
    agent: backend-developer
    dependencies: []

  - id: FE-001
    name: "Add AI query keys to centralized factory"
    agent: pdca-frontend-do-executor
    dependencies: [BE-001]

  - id: FE-002
    name: "Create AI-specific type definitions"
    agent: pdca-frontend-do-executor
    dependencies: [BE-001]

  - id: FE-003
    name: "Implement provider API hooks"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002]

  - id: FE-004
    name: "Implement model API hooks"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002]

  - id: FE-005
    name: "Implement assistant API hooks"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001, FE-002]

  - id: FE-006
    name: "Create AIProviderModal component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]

  - id: FE-007
    name: "Create AIProviderConfigModal component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002, FE-003]

  - id: FE-008
    name: "Create AIModelModal component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]

  - id: FE-009
    name: "Create AIAssistantModal component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]

  - id: FE-010
    name: "Create AIProviderList component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003, FE-006, FE-007]

  - id: FE-011
    name: "Create AIAssistantList component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-005, FE-009]

  - id: FE-012
    name: "Create AIProviderManagement page"
    agent: pdca-frontend-do-executor
    dependencies: [FE-010]

  - id: FE-013
    name: "Create AIAssistantManagement page"
    agent: pdca-frontend-do-executor
    dependencies: [FE-011]

  - id: FE-014
    name: "Add routes for new admin pages"
    agent: pdca-frontend-do-executor
    dependencies: [FE-012, FE-013]

  - id: FE-015
    name: "Create feature barrel exports"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003, FE-004, FE-005, FE-006, FE-007, FE-008, FE-009, FE-010, FE-011]

  - id: TEST-001
    name: "Write unit tests for hooks"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003, FE-004, FE-005]
    kind: test
    group: frontend-tests

  - id: TEST-002
    name: "Write unit tests for components"
    agent: pdca-frontend-do-executor
    dependencies: [FE-006, FE-007, FE-008, FE-009, FE-010, FE-011]
    kind: test
    group: frontend-tests

  - id: TEST-003
    name: "Write integration tests for API interactions"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003, FE-004, FE-005]
    kind: test
    group: frontend-tests

  - id: TEST-004
    name: "Final verification and cleanup"
    agent: pdca-frontend-do-executor
    dependencies: [FE-014, FE-015, TEST-001, TEST-002, TEST-003]
    kind: test
    group: frontend-tests
```

**Execution Notes:**

1. **Parallel Execution Opportunities:**
   - FE-001 and FE-002 can run in parallel after BE-001 completes
   - FE-003, FE-004, FE-005 can run in parallel after FE-001/FE-002
   - FE-006, FE-008, FE-009 can run in parallel after FE-002
   - FE-007 must wait for FE-003
   - FE-010 must wait for FE-003, FE-006, FE-007
   - FE-011 must wait for FE-005, FE-009
   - FE-012 and FE-013 can run in parallel after their respective list components

2. **Test Serialization:**
   - All TEST tasks are in the `frontend-tests` group and should execute sequentially
   - This ensures database state is not corrupted by concurrent test runs

3. **Critical Path:**
   - BE-001 → FE-001 → FE-003 → FE-007 → FE-010 → FE-012 → FE-014 → TEST-004
   - Estimated critical path duration: 2-3 days

---

## Output

**File:** `/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-03-07-frontend-ai-chat/01-plan.md`

**Template:** `/home/nicola/dev/backcast_evs/docs/04-pdca-prompts/_templates/01-plan-template.md`

---

## Key Principles

1. **Define WHAT, not HOW**: This plan specifies test specifications and acceptance criteria, not implementation code
2. **Measurable**: All success criteria are objectively verifiable through tests or measurements
3. **Sequential**: Tasks are ordered with clear dependencies; parallel execution is explicitly identified
4. **Traceable**: Every acceptance criterion maps to one or more test specifications with IDs
5. **Actionable**: Each task has clear success criteria and file locations for DO phase execution

> [!NOTE]
> This plan drives the DO phase. Tests are **specified** here but **implemented** in DO following RED-GREEN-REFACTOR. The Task Dependency Graph enables parallel execution by orchestrator agents.
