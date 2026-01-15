# Sprint 6: Cost Elements & Financial Structure

**Goal:** Complete project hierarchy and enable budget allocation
**Status:** 🔄 Partially Complete
**Story Points:** 26
**Last Updated:** 2026-01-14

**Stories:**

- [x] E04-U03: Create cost elements within WBEs (departmental budgets)
- [ ] E04-U04: Allocate revenue across WBEs
- [ ] E04-U05: Allocate budgets to cost elements

**Tasks:**

- [x] **S06-T01:** Implement Cost element CRUD with versioning
- [ ] **S06-T02:** Create Budget allocation endpoints
- [ ] **S06-T03:** Implement Revenue allocation logic
- [ ] **S06-T04:** Implement Budget validation rules

**Business Logic:**

- Total WBE budgets ≤ project budget
- Cost element budgets ≤ WBE allocation
- Revenue allocations reconcile to contract value

**Implementation Progress:**

- ✅ Cost Element entity implemented with full EVCS support
- ✅ Cost Element CRUD endpoints created
- ✅ Extended to BranchableService for branch support
- ✅ Frontend components for Cost Element management
- ⏳ Budget allocation endpoints pending
- ⏳ Revenue allocation logic pending
- ⏳ Budget validation rules pending

**Remaining Work:**

- Budget allocation endpoints and business logic
- Revenue allocation system
- Budget validation rules and constraints
- Financial tracking and reporting foundation

**Documentation:**

- See [Cost Elements Implementation](../../iterations/2026-01-09-frontend-filter-type-safety/01-PLAN.md)
