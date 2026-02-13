# Iteration: Enhance WBE Creation Form (Context Inheritance & UX)

## Goal

Improve the WBE management experience by ensuring hierarchy context is inherited automatically and parent information is displayed clearly and read-only.

## Success Criteria

- [ ] WBE creation from Project page defaults to "Project Root".
- [ ] WBE creation from WBE page defaults to the current WBE as parent.
- [ ] Parent field is visible and read-only in both Create and Edit modes.
- [ ] Parent Name is displayed instead of UUID.
- [ ] WBE creation is contextualized to a project.

## Plan

1. **Backend**: Update `WBERead` schema and `WBEService` to provide `parent_name`.
2. **Frontend**: Update `WBEModal` to display parent info read-only.
3. **Frontend**: Update `ProjectDetailPage` and `WBEDetailPage` to pass parent context.
4. **Verification**: Manual and automated tests.
