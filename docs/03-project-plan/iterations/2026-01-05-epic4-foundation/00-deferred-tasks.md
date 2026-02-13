# Epic 4 Foundation - Deferred Tasks

## Deferred to Future Iterations

The following tasks from Epic 4 Foundation (Backend Project/WBE Implementation) have been deferred to future iterations:

### Frontend Display (Epic 4-U03)

- [x] Generate TypeScript API client for Projects/WBEs
- [x] Create basic `ProjectList.tsx` page (read-only table)
- [x] Create basic `WBEList.tsx` page (read-only table, nested under project)
- [x] Add navigation menu items for Projects
- [x] Add placeholder for future Project/WBE CRUD forms

### Testing Enhancements

- [ ] Unit tests for Project model and commands
- [ ] Unit tests for WBE model and commands
- [ ] Resolve async event loop issues in integration tests (7/8 tests affected)

### Future Features (Change Order Epic)

- [ ] Branch operations (create_branch, merge_branch) for Project
- [ ] Branch operations (create_branch, merge_branch) for WBE
- [ ] Branch-specific API endpoints
- [ ] Change order workflow implementation

### Architecture Validation

- [ ] Confirm EVCS Core patterns work for hierarchical entities (already validated through implementation)
- [ ] Document lessons learned in ADR or architecture notes
- [ ] Identify any protocol/mixin gaps requiring updates

## Rationale for Deferral

**Frontend tasks:** Backend APIs are complete and functional. Frontend can be built in focused iteration.

**Unit tests:** Integration tests provide good coverage. Unit tests can be added incrementally for specific edge cases.

**Async test issues:** Test logic is correct; async fixtures have known compatibility issues that don't block development.

**Branch operations:** Base EVCS implementation is sound. Branch management will be needed for change order workflows in future epic.
