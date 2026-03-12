# PLAN: Dynamic AI Tool Selector

## Phase 1: Scope & Success Criteria

### 1.1 Approved Approach Summary

**Selected Option**: Dynamic Tool Fetching with Categorized Selector and Detail Modal
**Architecture**:
- Backend: Expose `GET /ai/config/tools` returning `AIToolPublic` schema.
- Frontend: New `useAITools` hook.
- Component 1: `ToolSelectorPanel.tsx` (handles category grouping and selection).
- Component 2: `ToolDetailModal.tsx` (shows full tool metadata).
- Refactor `AIAssistantModal` to use the new panel.

### 1.2 Success Criteria (Measurable)

**Functional Criteria:**
- [ ] Backend endpoint `/api/v1/ai/config/tools` returns a full list of registered tools with metadata. VERIFIED BY: Integration test.
- [ ] Frontend successfully fetches and groups tools by category. VERIFIED BY: Unit test.
- [ ] User can select/deselect tools in the `AIAssistantModal`. VERIFIED BY: Unit test / Manual verification.
- [ ] Clicking a tool's info icon opens the `ToolDetailModal` with correct data. VERIFIED BY: Unit test / Manual verification.

**Technical Criteria:**
- [ ] Code Quality: mypy strict + ruff clean VERIFIED BY: CI pipeline.
- [ ] Typescript tests pass. VERIFIED BY: CI pipeline.

### 1.3 Scope Boundaries

**In Scope:**
- Creating backend API endpoint for tools.
- Frontend custom hooks and query keys for tools.
- `ToolSelectorPanel` and `ToolDetailModal` components.
- Refactoring `AIAssistantModal.tsx` and updating its tests.

**Out of Scope:**
- Displaying exact tool parameter schemas in the UI (only description and permissions are in scope).
- Removing the `TOOL_REGISTRY` constant entirely from `types.ts` (it will be deprecated for backward compatibility of other unmodified tests, if any).

---

## Phase 2: Work Decomposition

### 2.1 Task Breakdown

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | --- | --- | --- | --- | --- |
| 1 | Backend: Add Tool API Route | `backend/app/models/schemas/ai.py`, `backend/app/api/routes/ai_config.py` | None | API returns tool list | Low |
| 2 | Frontend: API Infrastructure | `frontend/src/features/ai/types.ts`, `frontend/src/api/queryKeys.ts`, `frontend/src/features/ai/api/useAITools.ts`, `frontend/src/features/ai/api/index.ts` | Task 1 | Hook fetches data | Low |
| 3 | Frontend: Components | `frontend/src/features/ai/components/ToolDetailModal.tsx`, `frontend/src/features/ai/components/ToolSelectorPanel.tsx` | Task 2 | Components render correctly | Medium |
| 4 | Frontend: Modal Refactor | `frontend/src/features/ai/components/AIAssistantModal.tsx`, `frontend/src/features/ai/components/index.ts` | Task 3 | Form collects tool selection | Medium |
| 5 | Frontend: Tests | `frontend/src/features/ai/components/__tests__/AIAssistantModal.test.tsx` | Task 4 | Tests pass | Medium |

### 2.2 Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| --- | --- | --- | --- |
| Backend Endpoint Returns Tools | T-001 | `backend/tests/api/routes/test_ai_config.py` | Calling `/ai/config/tools` returns 200 list |
| Selector Shows Categories | T-002 | `frontend/src/features/ai/components/__tests__/AIAssistantModal.test.tsx` | Mocked tools grouped properly |
| Modal Edits Work | T-003 | `frontend/src/features/ai/components/__tests__/AIAssistantModal.test.tsx` | Selecting tool triggers form update |

---

## Phase 3: Test Specification

### 3.1 Test Cases

| Test ID | Test Name | Criterion | Type | Expected Result |
| --- | --- | --- | --- | --- |
| T-001 | `test_get_all_tools_returns_metadata` | AC-1 | Integration | Returns list matching `AIToolPublic` |
| T-002 | `test_tool_selector_groups_categories` | AC-2 | Unit | Rendered output shows category headers |
| T-003 | `test_tool_selector_updates_form_value` | AC-3 | Unit | Checkbox changes trigger `onChange(values)` |

---

## Phase 4: Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| Technical | Modifying API breaks existing tests | Low | Med | Use mock data in frontend tests |
| Integration | Backend `ToolRegistry` not populated before route hit | Med | High | Ensure all tool namespaces are imported in API file |

---

## Phase 5: Prerequisites & Dependencies

- [x] Analysis phase approved
- [x] Environment configured
