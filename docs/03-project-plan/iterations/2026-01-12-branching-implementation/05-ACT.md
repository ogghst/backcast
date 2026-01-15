# ACT Phase: Branching Implementation Standardization

## 1. Prioritized Improvement Implementation

### Critical Issues

None identified.

### High-Value Refactoring

None required at this stage.

## 2. Pattern Standardization

| Pattern               | Description                                                                                        | Standardize?                     |
| --------------------- | -------------------------------------------------------------------------------------------------- | -------------------------------- |
| **Branch Derivation** | Deriving "branches" from `main` + `ChangeOrder` entities rather than separate table                | **Yes** (Confirmed Core Pattern) |
| **Smart Selectors**   | Creating specific smart wrapper components (e.g. `ProjectBranchSelector`) for global context items | **Yes**                          |

**Actions:**

- [ ] Continue using implicit branching model in future features.

## 3. Documentation Updates Required

| Document                                          | Update Needed                                                            |
| ------------------------------------------------- | ------------------------------------------------------------------------ |
| `docs/02-architecture/cross-cutting/temporal-query-reference.md` | Start tracking that "listing branches" is implemented via CO aggregation |

## 4. Technical Debt Ledger

**Debt Created:**
None.

**Debt Resolved:**

- Implemented core branching visibility mechanism.

## 5. Process Improvements

**What Worked Well:**

- Defining `BranchPublic` schema early made frontend integration easier.

**Proposed Changes:**

- Use existing hook files (`useProjects.ts`) for related sub-resource queries instead of creating tiny new service files.

## 10. Concrete Action Items

- [x] Merge branching implementation.
- [ ] (Future) Implement "Create Branch" explicitly (currently done via Create CO).
