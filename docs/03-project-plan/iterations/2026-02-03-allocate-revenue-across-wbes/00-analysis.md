# Analysis: E04-U04 - Allocate Revenue across WBEs

**Created:** 2026-02-03
**User Story:** E04-U04 - Allocate Revenue across WBEs
**Epic:** E004 (Project Structure Management)
**Story Points:** 5
**Business Value:** MEDIUM - Revenue tracking

---

## Clarified Requirements

### Functional Requirements

**FR 5.1 - Revenue Allocation:**
The system shall enable users to assign total project revenue and distribute it across WBEs based on contracted values for each machine or deliverable. Revenue allocation must be captured at the WBE level and further distributed to cost elements based on the planned value of work assigned to each department.

**FR 15.4 - Validation Rules:**
Revenue allocations must equal total project contract value (exact match required).

**FR 8.1 - Change Order Support:**
Change orders must support modifications to revenues. When a change order is approved and implemented, the system shall update the affected WBE budgets, cost element allocations, and revenue assignments accordingly.

**Acceptance Criteria:**
1. Allocate revenue amounts to WBEs
2. Revenue validation rules (revenue allocations must equal total project contract value)
3. Versioning support

### Non-Functional Requirements

- **Performance:** Validation queries must complete in <200ms
- **Data Integrity:** Revenue allocations must maintain referential integrity with project contract value
- **Audit Trail:** All revenue changes must be tracked via EVCS versioning
- **Branch Isolation:** Revenue allocations must support change order branch workflows

### Constraints

- **Exact Match Validation:** Revenue allocations across all WBEs in a project must sum exactly to the project's contract_value
- **EVCS Architecture:** Must respect existing bitemporal versioning patterns (TemporalBase, BranchableMixin)
- **Backward Compatibility:** Existing WBE records without revenue_allocation must default to 0
- **Decimal Precision:** Financial values use DECIMAL(15, 2) for currency precision

---

## Context Discovery

### Product Scope

**Relevant User Stories:**
- E04-U04 (current): Allocate Revenue across WBEs
- E004-U01: Create/Manage Projects (with contract_value)
- E004-U02: Create/Manage WBEs (with budget_allocation)

**Business Requirements:**
- Projects have a `contract_value` field (nullable Decimal)
- WBEs currently have `budget_allocation` but no `revenue_allocation`
- Revenue tracking is essential for EVM calculations and profit analysis
- Change orders require revenue modifications in isolated branches

### Architecture Context

**Bounded Contexts Involved:**
- **Project & WBE Management** (Context 5): Core entity models and APIs
- **Change Order Processing** (Context 7): Branch isolation for revenue modifications
- **EVM Calculations & Reporting** (Context 8): Consumer of revenue data for performance metrics

**Existing Patterns to Follow:**
1. **Field Addition Pattern:** Add `revenue_allocation` DECIMAL(15, 2) field to WBE model (similar to `budget_allocation`)
2. **Schema Evolution:** Create Alembic migration with nullable default=0 for backward compatibility
3. **Validation Pattern:** Service-layer validation before create/update operations (see cost_registration_service.py)
4. **Versioning Support:** Leverage existing TemporalBase + BranchableMixin (no new infrastructure needed)
5. **Frontend Form Pattern:** Add InputNumber field to WBEModal.tsx (similar to budget_allocation)

**Architectural Constraints:**
- **MyPy Strict Mode:** All type hints must be explicit, no `Any` types
- **Pydantic Schemas:** All API changes require schema updates (WBECreate, WBEUpdate, WBERead)
- **RBAC:** Reuses existing `wbe-create`, `wbe-update` permissions
- **Time Machine:** Frontend must support control_date injection for time-travel queries

### Codebase Analysis

**Backend:**

**Existing Related Models:**
- `/home/nicola/dev/backcast_evs/backend/app/models/domain/project.py` - Project model with `contract_value: Decimal | None` field
- `/home/nicola/dev/backcast_evs/backend/app/models/domain/wbe.py` - WBE model with `budget_allocation: Decimal` field

**Service Layer:**
- `/home/nicola/dev/backcast_evs/backend/app/services/wbe.py` - WBEService with create_wbe() and update_wbe() methods
- Validation pattern reference: `/home/nicola/dev/backcast_evs/backend/app/services/cost_registration_service.py` (lines 95-96 show removed validation for warnings)

**API Routes:**
- `/home/nicola/dev/backcast_evs/backend/app/api/routes/wbes.py` - WBE endpoints (create, update, list, get)
- Uses `WBEPublic` schema for responses

**Similar Patterns:**
- **Budget allocation field** exists at line 65 of wbe.py: `budget_allocation: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), default=0)`
- **Validation approach**: Cost registration service previously had budget validation (commented out at lines 95-96)
- **Schema validation**: WBECreate/WBEUpdate schemas in `/home/nicola/dev/backcast_evs/backend/app/models/schemas/wbe.py` use Decimal types with ge=0 constraints

**Frontend:**

**Comparable Components:**
- `/home/nicola/dev/backcast_evs/frontend/src/features/wbes/components/WBEModal.tsx` - WBE create/edit form
- Budget allocation field at lines 107-118 shows InputNumber with Euro formatting

**State Management:**
- TanStack Query for server state (WBE mutations via useWBEs hooks)
- Time Machine context for control_date injection
- Query keys factory pattern for cache invalidation

**API Hooks:**
- `/home/nicola/dev/backcast_evs/frontend/src/features/wbes/api/useWBEs.test.tsx` - Test patterns for create/update mutations
- Control_date injection pattern verified at lines 36-58 (create) and 82-103 (update)

---

## Solution Options

### Option 1: Service-Layer Validation with Error Enforcement

**Architecture & Design:**
Add `revenue_allocation` DECIMAL(15, 2) field to WBE model (nullable, default=0). Implement validation in WBEService.create_wbe() and update_wbe() methods to query all WBEs for the project and enforce exact match with project.contract_value. Raise ValueError if validation fails.

**UX Design:**
- User enters revenue_allocation in WBE modal (next to budget_allocation)
- Real-time validation warning when sum ≠ contract_value (frontend computed)
- Backend blocks save when validation fails (HTTP 400 with error message)
- User must adjust allocations or update project contract value

**Implementation:**

**Backend Changes:**
1. **Model** (`wbe.py`): Add `revenue_allocation: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=True, default=None)`
2. **Migration**: Create Alembic migration to add column with nullable=True
3. **Schemas** (`wbe.py` schemas): Add `revenue_allocation: Decimal = Field(None, ge=0)` to WBEBase, WBECreate, WBEUpdate, WBERead
4. **Service** (`wbe.py` service): Add `_validate_revenue_allocation()` method called in create_wbe() and update_wbe()
5. **API Routes**: No changes needed (schema-driven validation)

**Frontend Changes:**
1. **Modal** (`WBEModal.tsx`): Add revenue_allocation InputNumber field (copy budget_allocation pattern)
2. **Validation**: Add Form-level validation to warn when sum != contract_value (requires fetching project data)
3. **Types**: Regenerate OpenAPI client to include new field
4. **Tests**: Update WBEModal tests for new field

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | Strict data integrity, clear error messages, follows existing pattern, prevents invalid data |
| Cons            | Blocks save workflow, requires WBE-level validation query (N+1 on batch), contract_value must be set before revenue allocation |
| Complexity      | Low                        |
| Maintainability | Good                       |
| Performance     | Validation query on every create/update (<50ms with indexed project_id) |

---

### Option 2: Service-Layer Validation with Warning-Only Mode

**Architecture & Design:**
Same as Option 1, but validation only emits a warning (logged) instead of blocking the operation. Allows users to save WBEs with mismatched revenue allocations but provides clear feedback.

**UX Design:**
- User enters revenue_allocation in WBE modal
- Backend validation warning logged but save succeeds
- Frontend displays warning banner when sum ≠ contract_value
- Dashboard shows "Revenue Mismatch: Allocated €X of €Y contract value"

**Implementation:**

**Backend Changes:**
- Same as Option 1, but `_validate_revenue_allocation()` returns warning status instead of raising ValueError
- Add optional `validate_revenue: bool = True` parameter to create/update methods for flexible enforcement
- Add new service method `get_revenue_allocation_status(project_id)` returning summary (allocated, contract_value, variance)

**Frontend Changes:**
- Same as Option 1, plus display warning banner on project detail page
- Add Revenue Status card to EVM dashboard

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | Flexible workflow, supports incremental data entry, clear visibility, allows change order workflows in progress |
| Cons            | Requires additional status endpoint, risk of data inconsistency if warnings ignored |
| Complexity      | Medium                     |
| Maintainability | Good                       |
| Performance     | Same as Option 1           |

---

### Option 3: Database Constraint with Application-Layer Validation

**Architecture & Design:**
Add `revenue_allocation` field plus a trigger or check constraint to enforce revenue_sum = contract_value at database level. Application layer provides user-friendly validation messages before hitting constraint.

**UX Design:**
- Same as Option 1 (strict enforcement)
- Database provides hard guarantee of data integrity
- Application layer catches constraint violations and formats user-friendly messages

**Implementation:**

**Backend Changes:**
1. **Model/Schema**: Same as Option 1
2. **Migration**: Add column + trigger function to validate on INSERT/UPDATE
3. **Service**: Add try/except to catch constraint violations and convert to ValueError
4. **API Routes**: Handle constraint violation exceptions (HTTP 400)

**Frontend Changes:**
- Same as Option 1

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | Database-level integrity guarantee, prevents direct SQL bypass, strongest data protection |
| Cons            | PostgreSQL triggers add complexity, harder to maintain, less flexible for edge cases, requires migration rollback procedure for triggers |
| Complexity      | High                       |
| Maintainability | Fair (trigger logic in database) |
| Performance     | Trigger execution overhead (negligible) |

---

## Comparison Summary

| Criteria           | Option 1 (Error)            | Option 2 (Warning)           | Option 3 (DB Constraint)    |
| ------------------ | --------------------------- | ---------------------------- | --------------------------- |
| Development Effort | 3-4 hours                   | 5-6 hours                    | 8-10 hours                  |
| UX Quality         | Strict but clear            | Flexible with visibility     | Strict with clear errors    |
| Flexibility        | Low (blocks save)           | High (allows mismatch)       | Low (blocks save)           |
| Data Integrity     | High (service-level)        | Medium (warning only)        | Very High (DB-level)        |
| Maintenance        | Easy (Python-only)          | Easy (Python-only)           | Complex (SQL + Python)       |
| Best For           | Production enforce mode     | Development/change orders    | Critical financial systems  |

---

## Recommendation

**I recommend Option 1 (Service-Layer Validation with Error Enforcement)** for the following reasons:

1. **Aligns with FR 15.4:** "Revenue allocations = Total project contract value (exact match required)" - this requirement states exact match is mandatory, not optional

2. **Follows Existing Pattern:** The codebase has precedent for strict validation (cost_registration_service.py previously had budget validation, commented out for business reasons). For revenue, the business requirement is clear: exact match required.

3. **Simplicity:** Pure Python implementation, no database triggers, easier to test and maintain

4. **Clear User Communication:** ValueError with message like "Total revenue allocation (€150,000) does not match project contract value (€160,000). Difference: €10,000" provides actionable feedback

5. **Performance Acceptable:** Single query to sum revenue allocations per project with indexed project_id field will be <50ms

6. **Change Order Support:** Branch isolation ensures validation only applies within a branch. Users can modify allocations in `co-{id}` branch without affecting main branch until merge.

**Alternative Consideration:**
Option 2 (Warning-Only) could be considered for future enhancement if the business identifies workflows where incremental revenue allocation is needed (e.g., large projects with WBEs added over time). This could be implemented as a configurable feature: `strict_revenue_validation = True/False` at project or system level.

**Implementation Order for Option 1:**
1. Backend migration (add column)
2. Backend schemas + service validation
3. Backend tests (unit + integration)
4. Frontend modal + validation UI
5. Frontend tests
6. Regenerate OpenAPI client
7. End-to-end testing

---

## Decision Questions

1. **Is the exact match requirement absolute or should there be flexibility for incremental allocation?**
   - If absolute: Option 1
   - If flexible: Option 2

2. **Should contract_value be mandatory before revenue allocation is allowed?**
   - Current model allows `contract_value: Decimal | None`
   - Recommendation: Make contract_value required in ProjectCreate or allow revenue allocation only when contract_value is set

3. **Should we add a "Validate Revenue" button on project detail page for bulk validation?**
   - Could provide proactive validation before user attempts WBE create/update
   - Would require additional service method and API endpoint

4. **Should revenue validation be configurable per project (strict vs. warning mode)?**
   - Adds flexibility but increases complexity
   - Could be implemented as project.settings.revenue_validation_mode

---

## Risk Assessment

**Technical Risks:**
- **Migration Complexity:** Low - Simple column addition with default value
- **Performance Impact:** Low - Single sum query with existing index
- **Data Integrity:** High - Service-layer validation provides strong guarantee
- **Breaking Changes:** None - Backward compatible with nullable field

**Business Risks:**
- **Workflow Disruption:** Medium - Users must set contract_value before allocating revenue
  - Mitigation: Add clear error message guiding user to update project first
- **Change Order Complexity:** Low - Branch isolation prevents conflicts
  - Mitigation: Ensure validation applies to current branch only

**Testing Risks:**
- **Edge Cases:** Empty WBE list (sum=0), project with no contract_value (None)
  - Mitigation: Add explicit handling in validation logic
- **Decimal Precision:** Rounding errors in sum calculation
  - Mitigation: Use Decimal.quantize() for comparison

---

## Validation Requirements

### Backend Validation Logic

```python
async def _validate_revenue_allocation(
    self,
    project_id: UUID,
    branch: str = "main",
    exclude_wbe_id: UUID | None = None,  # Exclude current WBE during update
) -> None:
    """Validate total revenue allocation matches project contract value.

    Args:
        project_id: Project to validate
        branch: Branch to check (default: "main")
        exclude_wbe_id: Optional WBE ID to exclude (for update validation)

    Raises:
        ValueError: If total allocations do not match contract value
    """
    from decimal import Decimal
    from sqlalchemy import select, func as sql_func
    from app.models.domain.project import Project

    # Get project contract value
    project_stmt = select(Project.contract_value).where(
        Project.project_id == project_id,
        Project.branch == branch,
    )
    project_result = await self.session.execute(project_stmt)
    contract_value = project_result.scalar_one_or_none()

    # Allow validation to pass if contract_value not set
    if contract_value is None:
        return

    # Sum current revenue allocations
    from typing import cast
    stmt = select(
        sql_func.sum(cast(Any, WBE).revenue_allocation)
    ).where(
        WBE.project_id == project_id,
        WBE.branch == branch,
        cast(Any, WBE).deleted_at.is_(None),
    )

    # Exclude current WBE for update scenarios
    if exclude_wbe_id:
        stmt = stmt.where(WBE.wbe_id != exclude_wbe_id)

    result = await self.session.execute(stmt)
    total_allocated = result.scalar() or Decimal(0)

    # Validate exact match (quantize to 2 decimal places)
    if total_allocated.quantize(Decimal("0.01")) != contract_value.quantize(Decimal("0.01")):
        difference = contract_value - total_allocated
        raise ValueError(
            f"Total revenue allocation (€{total_allocated:,.2f}) does not match "
            f"project contract value (€{contract_value:,.2f}). "
            f"Difference: €{difference:,.2f}"
        )
```

### Edge Cases to Handle

1. **Project without contract_value:** Skip validation (allow None)
2. **Empty WBE list:** Sum is 0, validation passes if contract_value = 0
3. **Update operation:** Exclude current WBE from sum to avoid double-counting
4. **Soft-deleted WBEs:** Exclude via `deleted_at.is_(None)` filter
5. **Branch isolation:** Validate only within current branch
6. **Decimal precision:** Use quantize(Decimal("0.01")) before comparison

---

## Test Strategy

### Backend Tests

**Unit Tests** (`tests/unit/services/test_wbe_service_revenue_validation.py`):
1. **Valid Allocation:** Create WBE with revenue that matches contract value → Success
2. **Invalid Allocation (Exceeds):** Total revenue > contract_value → ValueError
3. **Invalid Allocation (Under):** Total revenue < contract_value → ValueError
4. **Update Validation:** Modify WBE revenue to maintain exact match → Success
5. **Exclude Current WBE:** Update WBE should not count old value in sum
6. **No Contract Value:** Project with contract_value=None → Validation passes
7. **Branch Isolation:** Validate in branch A does not affect branch B
8. **Soft Deleted WBEs:** Deleted WBEs excluded from sum
9. **Decimal Precision:** Compare with quantized values

**Integration Tests** (`tests/integration/test_revenue_allocation_api.py`):
1. **Create WBE Flow:** POST /wbes with valid/invalid revenue_allocation
2. **Update WBE Flow:** PUT /wbes/{id} with revenue validation
3. **Batch Operations:** Multiple WBE creates in sequence
4. **Change Order Workflow:** Create branch, modify revenue, validate isolation

**Migration Tests**:
1. **Column Addition:** Verify revenue_allocation column exists
2. **Default Value:** Existing WBEs have revenue_allocation=None
3. **Rollback:** Migration can be rolled back cleanly

### Frontend Tests

**Unit Tests** (`WBEModal.test.tsx`):
1. **Field Rendering:** revenue_allocation field displays in modal
2. **Form Validation:** Decimal validation (ge=0) works
3. **Default Value:** Field defaults to 0 for new WBEs
4. **Edit Mode:** Existing revenue_allocation value loads correctly

**Integration Tests** (`RevenueAllocationFlow.test.tsx`):
1. **Create WBE with Revenue:** Modal submission with valid revenue
2. **Validation Error:** Display backend error when validation fails
3. **Update Revenue:** Modify existing allocation
4. **Project Summary:** Verify project detail page shows revenue totals

**E2E Tests** (Playwright):
1. **User creates project with contract value**
2. **User creates multiple WBEs with revenue allocations**
3. **System validates exact match on each save**
4. **User views project summary showing revenue breakdown**

---

## Success Criteria

### Functional Requirements Met
- ✅ Revenue can be allocated to WBEs via API and UI
- ✅ Validation ensures sum of allocations = project contract value
- ✅ Versioning works correctly (changes tracked in transaction_time)
- ✅ Branch isolation works (change order branches maintain separate allocations)

### Non-Functional Requirements Met
- ✅ API response time <200ms for validation query
- ✅ Data integrity maintained (no orphaned allocations)
- ✅ Audit trail complete (all changes in valid_time/transaction_time)
- ✅ Backward compatibility preserved (existing WBEs unaffected)

### Quality Standards Met
- ✅ MyPy strict mode: Zero errors
- ✅ Ruff linting: Zero errors
- ✅ Test coverage: ≥80% for new code
- ✅ ESLint: Zero errors (frontend)
- ✅ TypeScript strict mode: No type errors

### Documentation Completed
- ✅ API documentation updated (OpenAPI auto-generated)
- ✅ Database migration documented
- ✅ User guide updated (how to allocate revenue)
- ✅ Architecture decisions recorded (if applicable)

---

## Implementation Checklist

### Phase 1: Backend Foundation
- [ ] Add `revenue_allocation` column to WBE model
- [ ] Create Alembic migration
- [ ] Run migration and verify database schema
- [ ] Update WBEBase, WBECreate, WBEUpdate, WBERead schemas
- [ ] Add validation method to WBEService
- [ ] Integrate validation in create_wbe() method
- [ ] Integrate validation in update_wbe() method
- [ ] Add unit tests for validation logic
- [ ] Add integration tests for API endpoints
- [ ] Verify MyPy and Ruff pass

### Phase 2: Frontend Implementation
- [ ] Regenerate OpenAPI client
- [ ] Add revenue_allocation field to WBEModal.tsx
- [ ] Add Form.Item validation for decimal input
- [ ] Update WBEModal tests
- [ ] Add revenue allocation summary to ProjectDetail page
- [ ] Add integration tests for modal submission
- [ ] Verify ESLint and TypeScript pass

### Phase 3: Documentation & QA
- [ ] Update API documentation (review auto-generated OpenAPI)
- [ ] Write user guide for revenue allocation workflow
- [ ] Perform end-to-end testing
- [ ] Test change order workflow with revenue modifications
- [ ] Test branch isolation for revenue allocations
- [ ] Performance testing (validation query timing)
- [ ] Create release notes

### Phase 4: Deployment
- [ ] Code review and approval
- [ ] Merge to main branch
- [ ] Deploy backend migration
- [ ] Deploy frontend changes
- [ ] Smoke testing in production environment
- [ ] Monitor error logs for validation failures

---

## References

### Architecture Documentation
- [Bounded Contexts: Project & WBE Management](/home/nicola/dev/backcast_evs/docs/02-architecture/01-bounded-contexts.md#5-project--wbe-management)
- [Backend Coding Standards](/home/nicola/dev/backcast_evs/docs/02-architecture/backend/coding-standards.md)
- [Frontend Coding Standards](/home/nicola/dev/backcast_evs/docs/02-architecture/frontend/coding-standards.md)

### Product Scope
- [Functional Requirements: Section 5.1 - Revenue Allocation](/home/nicola/dev/backcast_evs/docs/01-product-scope/functional-requirements.md#51-revenue-allocation)
- [Functional Requirements: Section 8.1 - Change Order Support](/home/nicola/dev/backcast_evs/docs/01-product-scope/functional-requirements.md#81-change-order-processing)
- [Functional Requirements: Section 15.4 - Validation Rules](/home/nicola/dev/backcast_evs/docs/01-product-scope/functional-requirements.md#budget-allocation-validation)

### Code References
- WBE Model: `/home/nicola/dev/backcast_evs/backend/app/models/domain/wbe.py`
- WBE Service: `/home/nicola/dev/backcast_evs/backend/app/services/wbe.py`
- WBE Schemas: `/home/nicola/dev/backcast_evs/backend/app/models/schemas/wbe.py`
- WBE API Routes: `/home/nicola/dev/backcast_evs/backend/app/api/routes/wbes.py`
- WBE Modal: `/home/nicola/dev/backcast_evs/frontend/src/features/wbes/components/WBEModal.tsx`
- Validation Pattern Reference: `/home/nicola/dev/backcast_evs/backend/app/services/cost_registration_service.py`

### Related User Stories
- E004-U01: Create/Manage Projects (contract_value field)
- E004-U02: Create/Manage WBEs (budget_allocation field pattern)
- E004-U03: Allocate budgets to cost elements (similar validation pattern)

---

## Appendix: Database Migration Draft

```python
# File: alembic/versions/YYYYMMDD_add_revenue_allocation_to_wbes.py
"""Add revenue_allocation to wbes table.

Revision ID: add_revenue_allocation
Revises: (previous migration)
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_revenue_allocation'
down_revision = 'previous_migration_id'
branch_labels = None
depends_on = None


def upgrade():
    """Add revenue_allocation column to wbes table."""
    op.add_column(
        'wbes',
        sa.Column(
            'revenue_allocation',
            postgresql.NUMERIC(precision=15, scale=2),
            nullable=True,
            comment='Revenue allocated to this WBE from project contract value'
        )
    )


def downgrade():
    """Remove revenue_allocation column from wbes table."""
    op.drop_column('wbes', 'revenue_allocation')
```

---

**Document Status:** ✅ Ready for Review
**Next Phase:** PLAN (Create actionable tasks from this analysis)
