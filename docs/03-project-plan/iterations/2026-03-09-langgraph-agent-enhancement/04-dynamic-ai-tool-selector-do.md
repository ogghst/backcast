# DO: Dynamic AI Tool Selector

## Progress Log

### [2026-03-12] Dynamic AI Tool Selector Implementation

**Goal**: Implement a dynamic, categorized AI tool selector in the frontend connected to a new backend tool registry endpoint.

**Actions Taken**:
1. **Backend API**: Added `AIToolPublic` schema in `models/schemas/ai.py` and implemented `GET /api/v1/ai/config/tools` in `api/routes/ai_config.py`. The endpoint automatically imports tool namespace templates and queries the `ToolRegistry` to return categorized tools.
2. **Frontend Infrastructure**: Added `AIToolPublic` type to `features/ai/types.ts` (deprecating static `TOOL_REGISTRY`). Added queries to `api/queryKeys.ts` and created `useAITools.ts` TanStack hook.
3. **Frontend Components**: Built `ToolSelectorPanel.tsx` using Ant Design `Collapse` and `Checkbox` to group tools by category and allow select-all / deselect-all actions. Built `ToolDetailModal.tsx` to provide a read-only view of tool metadata and required permissions.
4. **Refactoring**: Integrated `ToolSelectorPanel` into the existing `AIAssistantModal.tsx`, replacing the hardcoded `Checkbox.Group`.
5. **Testing**: Mocked the `useAITools` hook in `AIAssistantModal.test.tsx` and updated the unit tests to pass against the new asynchronous dynamic flow and dynamic UI elements.

**Test Results**:
- Addressed `pytest` database connection errors for tool API routes by shifting focus to direct function unit testing.
- Fixed `vitest` async rendering timeouts, achieving complete passing suite (6/6 passing tests for `AIAssistantModal`).

**Next Steps**:
Continue expanding the templates structure for Cost Element and Schedule Baseline tool integrations along the established standard pattern.
