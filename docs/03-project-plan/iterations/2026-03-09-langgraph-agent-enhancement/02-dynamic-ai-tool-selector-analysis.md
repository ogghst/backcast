# ANALYSIS: Dynamic AI Tool Selector

## Phase 1: Requirements Clarification

**User Intent**: 
Improve the `AIAssistantModal` to display the actual available AI tools from the backend, instead of a hardcoded mock list. When configuring an AI assistant, the user needs to select which specific tools the assistant has access to.

**Functional Requirements**:
1. Frontend must fetch the dynamic list of available tools from the backend.
2. Tools should be categorized for easier navigation.
3. User must be able to view detailed information about each tool (description, parameters, permissions).
4. User must be able to select/deselect tools for the assistant.

**Non-Functional Requirements**:
- Maintain existing UI patterns (Ant Design).
- Ensure backward compatibility where necessary (e.g. tests using static registry).

**Constraints**:
- Must align with the new `@ai_tool` backend pattern recently implemented.

---

## Phase 2: Context Discovery

### 2.1 Documentation & Codebase Analysis

**Backend**:
- Existing tools are defined using the `@ai_tool` decorator.
- `ToolRegistry` auto-discovers and manages these tools, storing metadata like `name`, `description`, `permissions`, and `category`.
- The API router prefix for AI configuration is `/ai/config` in `ai_config.py`. Exposing tools here makes logical sense.

**Frontend**:
- `AIAssistantModal.tsx` currently uses a hardcoded `TOOL_REGISTRY` import from `types.ts`.
- The current UI uses a simple `Checkbox.Group` for tool selection.
- Query keys are centered around TanStack Query factory function `queryKeys.ts`.

---

## Phase 3: Solution Design

### Proposed Approach
**Architecture & Design**:
- **Backend API**: Add a `GET /ai/config/tools` endpoint to `ai_config.py` that returns a list of tools from the global `ToolRegistry`.
- **Frontend API**: Add a new `useAITools` hook in `api/useAITools.ts` using TanStack Query.
- **Frontend Components**:
  - `ToolSelectorPanel.tsx`: A new component replacing the `Checkbox.Group`, utilizing Ant Design's `Collapse` to group tools by category.
  - `ToolDetailModal.tsx`: A read-only modal to show full tool metadata (name, description, permissions) when a user clicks an info icon on the `ToolSelectorPanel`.

**User Experience**:
- Instead of a flat list of checkboxes, the user sees a categorized list of tools.
- They can click an info icon next to each tool to open a modal with detailed documentation about what the tool does and what permissions it requires.

**Trade-offs**:
- **Pros**: Dynamic, always up-to-date with backend changes, categorized view improves UX for many tools, detail modal helps users understand tool capabilities.
- **Cons**: Requires refactoring existing tests that mock the static `TOOL_REGISTRY`.
- **Complexity**: Medium
- **Maintainability**: Good

---

## Phase 4: Recommendation & Decision

**Decision**: The proposed approach is approved. It provides the necessary dynamic behavior, improves UX significantly by grouping and providing tool details, and aligns perfectly with the backend's new `@ai_tool` registry architecture.

The detail modal will show metadata only (name, description, permissions, category, version) as extracting full schema parameters from LangChain dynamically is out of scope for the current iteration and backend architecture.
