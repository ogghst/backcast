# Plan: Split Coding Standards

## Goal Description

Split the monolithic `docs/02-architecture/coding-standards.md` into domain-specific documents:

- `docs/02-architecture/backend/coding-standards.md`
- `docs/02-architecture/frontend/coding-standards.md`

This improves clarity and maintainability by separating concerns.

## Proposed Changes

### Documentation

#### [NEW] [backend/coding-standards.md](file:///home/nicola/dev/backcast_evs/docs/02-architecture/backend/coding-standards.md)

Will contain:

- Core/Common principles (Backend perspective)
- Section 3: Backend Standards
- Section 6: Architecture Patterns (Backend applicable)
- Section 7: Quality Gates (Backend applicable)
- Section 9: Common Pitfalls (Backend)

#### [NEW] [frontend/coding-standards.md](file:///home/nicola/dev/backcast_evs/docs/02-architecture/frontend/coding-standards.md)

Will contain:

- Core/Common principles (Frontend perspective)
- Section 4: Frontend Standards
- Section 6: Architecture Patterns (Frontend applicable, e.g., RBAC)
- Section 7: Quality Gates (Frontend applicable)
- Section 8: Navigation Patterns
- Section 9: Common Pitfalls (Frontend)

#### [DELETE] [coding-standards.md](file:///home/nicola/dev/backcast_evs/docs/02-architecture/coding-standards.md)

Original file will be removed.

#### [MODIFY] References

Update links in:

- `docs/02-architecture/README.md`
- `docs/04-pdca-prompts/` (references file)
- `docs/04-pdca-prompts/` (templates)
- `docs/02-architecture/code-review-checklist.md`

## Verification Plan

### Automated Tests

- None (Documentation change only)

### Manual Verification

- Verify links in `docs/04-pdca-prompts/_references.md` work.
- Verify separation of concerns by reading new files.
