# Sprint 7: Branching & Change Orders

**Goal:** Implement branch isolation and change order workflow
**Status:** 🔄 In Progress (Phase 1 Complete)
**Story Points:** 28
**Last Updated:** 2026-01-14

**Stories:**

- [x] E06-U01: Create change orders
- [x] E06-U02: Automatic branch creation for change orders (`co-{id}`)
- [🔄] E06-U03: Modify entities in branch (isolated from main) - Phase 2
- [ ] E06-U04: Compare branch to main (impact analysis) - Phase 3
- [ ] E06-U05: Merge approved change orders - Phase 4
- [ ] E06-U06: Lock/unlock branches - Phase 4
- [x] E06-U07: Merged view showing main + branch changes
- [ ] E06-U08: Delete/archive branches - Phase 4

**Tasks:**

- [x] **S07-T01:** Implement Branch creation and management
- [🔄] **S07-T02:** Create Change order workflow (Phases 1-4)
- [ ] **S07-T03:** Create Branch comparison endpoints (Phase 3)
- [ ] **S07-T04:** Implement Merge functionality (Phase 4)

**Features:**

- Deep copy on branch creation (`co-{short_id}`)
- Branch comparison with financial impact analysis
- Atomic merge operation
- Branch locking mechanism
- Branch mode with fallback (STRICT/MERGE) for preview

---

## Phase 1: Change Order Creation & Auto-Branch Management ✅ Complete

**Status:** ✅ Complete (2026-01-12)

**Delivered:**

- Change Order entity with full EVCS support
- 7 API endpoints (GET /change-orders, POST /change-orders, GET /change-orders/{id}, PUT /change-orders/{id}, DELETE /change-orders/{id}, GET /change-orders/{id}/history, POST /change-orders/{id}/approve)
- Automatic branch creation on CO creation (`co-{short_id}`)
- BranchableSoftDeleteCommand for branch-aware deletion
- Frontend components: ChangeOrderList, ChangeOrderModal
- Extended WBE and CostElement to BranchableService
- 200/208 tests passing (96% pass rate)
- 80.49% coverage (exceeds 80% target)

**Key Patterns Established:**

- BranchableService for automatic branch management
- BranchableSoftDeleteCommand for safe deletion across branches
- Time Machine React Query integration

**Documentation:**

- See [Change Orders Phase 1 - ACT](../../iterations/2026-01-11-change-orders-implementation/phase1/04-act.md)
- See [Branching Implementation](../../iterations/2026-01-12-branching-implementation/05-ACT.md)

---

## Phase 2: In-Branch Editing & Workflow States 🔄 In Progress

**Status:** 🔄 In Progress

**Planned Features:**

- Enable editing WBEs and Cost Elements on CO branches
- Implement workflow states: DRAFT → SUBMITTED → APPROVED/REJECTED
- Add branch locking during approval
- Create view mode toggle (Isolated/Merged)
- Workflow UI with state transitions

**Documentation:**

- See [Change Orders Phase 2](../../iterations/2026-01-11-change-orders-implementation/phase2/01-plan.md)

---

## Phase 3: Impact Analysis & Branch Comparison ⏳ Planned

**Status:** ⏳ Not Started

**Planned Features:**

- Compare branch to main (impact analysis)
- Financial impact calculations
- Entity diff visualization
- Comparison endpoints

---

## Phase 4: Merge Workflows & Approval Processes ⏳ Planned

**Status:** ⏳ Not Started

**Planned Features:**

- Merge approved change orders
- Lock/unlock branches
- Delete/archive branches
- Atomic merge operation
- Approval workflow UI

**Documentation:**

- See [Merge Isolation Strategies](../../iterations/2026-01-12-merge-isolation-strategies/01-plan.md)
