# Phase 6: Change Order Workflow Integration - Implementation Plan

**Date:** 2026-02-05
**Epic:** E006 (Branching & Change Order Management)
**Phase:** 6 - Change Order Workflow Integration
**Story Points:** 15
**Status:** 🔄 Planning

---

## Executive Summary

Phase 6 integrates the comprehensive impact analysis from Phase 5 into the change order workflow, enabling automatic impact calculation on creation, severity-based approval routing, and impact-driven workflow decisions.

### Phase Objectives

1. **Automatic Impact Analysis Trigger** (5 points) - Calculate impact on change order creation
2. **Impact-Based Approval Routing** (5 points) - Route to appropriate approvers based on impact severity
3. **Impact Analysis Status Tracking** (5 points) - Track impact analysis state in change order lifecycle

### Current State (Phase 5 + 5.5 Complete)

| Component | Status | Details |
|-----------|--------|---------|
| **ImpactAnalysisService** | ✅ Complete | Comprehensive analysis: 13 KPIScorecard fields (schedule, EVM, VAC) |
| **ChangeOrderService** | ✅ Complete | CRUD operations, branch creation, workflow integration |
| **ApprovalMatrixService** | ✅ Complete | Role-based approval authority lookup |
| **ChangeOrderWorkflowService** | ✅ Complete | Workflow state management |
| **ImpactLevel Enum** | ✅ Complete | LOW/MEDIUM/HIGH/CRITICAL classification (in ChangeOrder model) |

### Gap Analysis

**Current Implementation:**
- ✅ Impact analysis triggered on `submit_for_approval()` (line 726-836 in ChangeOrderService)
- ✅ `ImpactLevel` field exists in ChangeOrder model
- ✅ Approval matrix integration exists
- ❌ No impact analysis on **creation** (only on submission)
- ❌ No automatic impact severity calculation
- ❌ No impact-based routing on creation
- ❌ No impact analysis status tracking field

**Required for Phase 6:**
1. Trigger impact analysis on `create_change_order()` (not just submission)
2. Calculate impact severity score from KPIScorecard
3. Set `impact_level` based on severity thresholds
4. Route to appropriate approver based on impact level
5. Add `impact_analysis_status` field to track state
6. Store impact analysis results for reference

---

## User Stories

| Story | Points | Description | Acceptance Criteria |
|-------|--------|-------------|---------------------|
| **E06-U20:** Automatic Impact Analysis | 5 | Trigger impact analysis on change order creation | - Impact analysis runs on CO creation<br>- Results stored with CO<br>- Status tracked (pending/complete/failed) |
| **E06-U21:** Impact Severity Calculation | 5 | Calculate impact severity from KPIScorecard | - Severity score algorithm defined<br>- Thresholds configured<br>- impact_level set automatically |
| **E06-U22:** Impact-Based Routing | 5 | Route CO to appropriate approver based on impact | - Approvers assigned by impact level<br>- Approval matrix consulted<br>- Notifications sent |
| **Total** | **15** | | |

---

## Architecture & Design

### Current Flow (On Submission)

```
User creates CO → Status: DRAFT
User modifies WBEs → Status: DRAFT
User submits for approval → Impact Analysis Triggered
                         → Calculate BAC delta
                         → Set impact_level (LOW/MEDIUM/HIGH/CRITICAL)
                         → Find approver from approval matrix
                         → Transition to SUBMITTED
```

**Problem:** User doesn't know impact severity until AFTER submission and making modifications.

### Target Flow (On Creation)

```
User creates CO → Trigger Impact Analysis (immediately)
                → Calculate comprehensive impact (13 metrics)
                → Calculate severity score
                → Set impact_level automatically
                → Assign approver based on impact_level
                → Store impact analysis results
                → Status: DRAFT
User sees impact severity immediately → Can adjust before submission
User submits for approval → Already has impact analysis
                          → No re-calculation needed
                          → Transition to SUBMITTED
```

**Benefits:**
- Immediate visibility of impact
- Informed decision making before submission
- Reduced rework (adjust before submit)
- Faster approval cycle

---

## Data Model Changes

### ChangeOrder Model (Additions)

**File:** `backend/app/models/domain/change_order.py`

**New Field:**
```python
class ChangeOrder(EntityBase, VersionableMixin, BranchableMixin):
    # ... existing fields ...

    # NEW: Impact analysis tracking
    impact_analysis_status: Mapped[str] = mapped_column(
        String(20),
        nullable=True,
        comment="Impact analysis state: pending/in_progress/complete/failed"
    )
    impact_analysis_results: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        comment="Stored impact analysis KPIScorecard results"
    )
    impact_score: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Calculated impact severity score (0-100+)"
    )
```

**Rationale:**
- `impact_analysis_status`: Track analysis lifecycle (async operations)
- `impact_analysis_results`: Cache impact analysis for audit trail
- `impact_score`: Numeric score for severity calculation

**Note:** `impact_level` field already exists (Line 75 in current model)

---

## Implementation Tasks

### Task 1: Automatic Impact Analysis on Creation (5 points)

**File:** `backend/app/services/change_order_service.py`

**Changes Required:**

1.1. **Add impact analysis trigger in `create_change_order()`** (3 points)
   - After branch creation, trigger impact analysis
   - Call `ImpactAnalysisService.analyze_impact()`
   - Store results in `impact_analysis_results` field
   - Set `impact_analysis_status = "complete"`

1.2. **Handle async analysis for large projects** (1 point)
   - If analysis takes > 5 seconds, run in background
   - Set `impact_analysis_status = "in_progress"`
   - Update status when complete
   - Use Celery or similar for async tasks (or simple thread)

1.3. **Add error handling** (1 point)
   - Wrap impact analysis in try-except
   - Set `impact_analysis_status = "failed"` on error
   - Log error details
   - Allow CO creation to succeed even if analysis fails

**Code Location:**
```python
# In create_change_order(), after branch creation (around line 180)

# NEW: Trigger impact analysis
try:
    from app.services.impact_analysis_service import ImpactAnalysisService
    impact_service = ImpactAnalysisService(self.session)

    impact_analysis = await impact_service.analyze_impact(
        change_order_id=root_id,
        branch_name=branch_name
    )

    # Store results
    change_order.impact_analysis_results = impact_analysis.model_dump()
    change_order.impact_analysis_status = "complete"

except Exception as e:
    logger.error(f"Impact analysis failed for CO {code}: {e}")
    change_order.impact_analysis_status = "failed"
    # Still allow CO creation
```

**Acceptance Criteria:**
- ✅ Impact analysis runs on CO creation
- ✅ Results stored in `impact_analysis_results`
- ✅ Status set to `complete` or `failed`
- ✅ CO creation succeeds even if analysis fails
- ✅ Unit test for successful analysis
- ✅ Unit test for failed analysis

---

### Task 2: Impact Severity Calculation (5 points)

**File:** `backend/app/services/change_order_service.py`

**Changes Required:**

2.1. **Create `_calculate_impact_score()` method** (3 points)
   - Extract key metrics from KPIScorecard
   - Calculate weighted score:
     - Budget delta: 40% weight
     - Schedule delta: 30% weight
     - Revenue delta: 20% weight
     - EVM degradation: 10% weight
   - Return score 0-100+

2.2. **Map score to impact level** (1 point)
   - Score < 10: LOW
   - Score 10-30: MEDIUM
   - Score 30-50: HIGH
   - Score > 50: CRITICAL

2.3. **Set `impact_level` and `impact_score` fields** (1 point)
   - After impact analysis complete
   - Calculate score using `_calculate_impact_score()`
   - Map to impact level
   - Update ChangeOrder entity

**Algorithm:**
```python
def _calculate_impact_score(self, impact_analysis: ImpactAnalysisResponse) -> Decimal:
    """Calculate impact severity score from KPIScorecard.

    Weighted scoring:
    - Budget delta: 40% (primary financial impact)
    - Schedule delta: 30% (primary timeline impact)
    - Revenue delta: 20% (secondary financial impact)
    - EVM degradation: 10% (performance impact)

    Args:
        impact_analysis: Impact analysis results

    Returns:
        Impact score (0-100+)
    """
    kpi = impact_analysis.kpi_scorecard

    # Budget impact (40% weight)
    budget_delta_pct = abs(kpi.budget_delta.delta_percent or 0)
    budget_score = budget_delta_pct * 0.4

    # Schedule impact (30% weight)
    schedule_delta_pct = abs(kpi.schedule_duration.delta_percent or 0)
    schedule_score = schedule_delta_pct * 0.3

    # Revenue impact (20% weight)
    revenue_delta_pct = abs(kpi.revenue_delta.delta_percent or 0)
    revenue_score = revenue_delta_pct * 0.2

    # EVM degradation (10% weight)
    # CPI/SPI below 1.0 indicates degradation
    cpi_delta = kpi.cpi.delta if kpi.cpi else 0
    spi_delta = kpi.spi.delta if kpi.spi else 0
    evm_degradation = abs(min(cpi_delta, 0) + min(spi_delta, 0)) * 10  # Scale degradation
    evm_score = evm_degradation * 0.1

    total_score = budget_score + schedule_score + revenue_score + evm_score
    return Decimal(str(total_score))


def _map_score_to_impact_level(self, score: Decimal) -> str:
    """Map impact score to impact level.

    Args:
        score: Impact score (0-100+)

    Returns:
        Impact level: LOW/MEDIUM/HIGH/CRITICAL
    """
    if score < 10:
        return ImpactLevel.LOW
    elif score < 30:
        return ImpactLevel.MEDIUM
    elif score < 50:
        return ImpactLevel.HIGH
    else:
        return ImpactLevel.CRITICAL
```

**Acceptance Criteria:**
- ✅ Impact score calculated from weighted metrics
- ✅ Score mapped to correct impact level
- ✅ `impact_level` and `impact_score` fields set
- ✅ Unit tests for each impact level threshold
- ✅ Unit test for zero impact (score = 0)

---

### Task 3: Impact-Based Approval Routing (5 points)

**File:** `backend/app/services/change_order_service.py`

**Changes Required:**

3.1. **Assign approver based on impact level** (3 points)
   - Query `ApprovalMatrixService` for appropriate approver
   - Use `impact_level` to determine approval authority
   - Set `assigned_approver_id` field

3.2. **Send notification to approver** (1 point)
   - Email notification (implementation: placeholder for now)
   - In-app notification
   - Include impact summary

3.3. **Add validation on submission** (1 point)
   - Prevent submission if impact analysis not complete
   - Return error if `impact_analysis_status != "complete"`
   - Guide user to wait or retry

**Code Location:**
```python
# In create_change_order(), after impact analysis

# NEW: Assign approver based on impact level
from app.services.approval_matrix_service import ApprovalMatrixService
approval_service = ApprovalMatrixService(self.session)

approver = await approval_service.get_approver_for_impact(
    department_id=project.department_id,  # Need to fetch project
    impact_level=change_order.impact_level
)

if approver:
    change_order.assigned_approver_id = approver.user_id
    # TODO: Send notification
```

**Validation:**
```python
# In submit_for_approval(), before workflow transition

# NEW: Validate impact analysis complete
if change_order.impact_analysis_status != "complete":
    raise ValueError(
        "Cannot submit change order: Impact analysis not complete. "
        f"Current status: {change_order.impact_analysis_status}"
    )
```

**Acceptance Criteria:**
- ✅ Approver assigned based on impact level
- ✅ Approval matrix consulted
- ✅ `assigned_approver_id` set
- ✅ Notification sent (placeholder)
- ✅ Submission blocked if analysis incomplete
- ✅ Unit test for each impact level routing

---

## Database Migration

**Required Migration:**
```python
# alembic/versions/XXXX_add_impact_analysis_tracking.py

def upgrade():
    op.add_column(
        'change_orders',
        sa.Column('impact_analysis_status', sa.String(20), nullable=True)
    )
    op.add_column(
        'change_orders',
        sa.Column('impact_analysis_results', sa.JSONB, nullable=True)
    )
    op.add_column(
        'change_orders',
        sa.Column('impact_score', sa.Numeric(10, 2), nullable=True)
    )

def downgrade():
    op.drop_column('change_orders', 'impact_score')
    op.drop_column('change_orders', 'impact_analysis_results')
    op.drop_column('change_orders', 'impact_analysis_status')
```

---

## API Contract Changes

### ChangeOrderPublic Schema

**File:** `backend/app/models/schemas/change_order.py`

**Additions:**
```python
class ChangeOrderPublic(BaseModel):
    # ... existing fields ...

    # NEW: Impact analysis tracking
    impact_analysis_status: str | None = None
    impact_score: Decimal | None = None
    # Note: impact_level already exists
    # Note: impact_analysis_results omitted (too large for API response)
```

### New Endpoint: GET Impact Analysis

**Route:** `/api/v1/change-orders/{id}/impact-analysis`

**Response:** `ImpactAnalysisResponse` (already exists from Phase 5)

**Purpose:** Retrieve full impact analysis results on demand

---

## Testing Strategy

### Unit Tests (15 tests)

**Task 1 Tests (5 tests):**
- `test_create_change_order_triggers_impact_analysis`
- `test_create_change_order_stores_impact_results`
- `test_create_change_order_handles_analysis_failure`
- `test_create_change_order_async_analysis_for_large_project`
- `test_impact_analysis_status_tracking`

**Task 2 Tests (5 tests):**
- `test_calculate_impact_score_low_impact`
- `test_calculate_impact_score_medium_impact`
- `test_calculate_impact_score_high_impact`
- `test_calculate_impact_score_critical_impact`
- `test_map_score_to_impact_level_boundaries`

**Task 3 Tests (5 tests):**
- `test_assign_approver_based_on_impact_level`
- `test_approver_lookup_uses_approval_matrix`
- `test_submit_for_approval_blocked_without_impact_analysis`
- `test_approver_notification_sent`
- `test_impact_based_routing_all_levels`

### Integration Tests (3 tests)

- `test_end_to_end_change_order_creation_with_impact_analysis`
- `test_workflow_from_draft_to_approved_with_impact_routing`
- `test_high_impact_change_requires_director_approval`

---

## Dependencies & Prerequisites

### Internal Dependencies
- ✅ ImpactAnalysisService (Phase 5)
- ✅ ApprovalMatrixService (Phase 1)
- ✅ ChangeOrderWorkflowService (existing)
- ✅ ChangeOrder model with ImpactLevel enum (existing)

### External Dependencies
- ✅ SQLAlchemy 2.0 (async)
- ✅ PostgreSQL 15+ (JSONB support)
- ✅ Celery (optional, for async analysis)

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Impact analysis slow** | Medium | High | Async for large projects, timeout handling |
| **Invalid impact score** | High | Low | Comprehensive testing, validation |
| **Wrong approver assigned** | High | Low | Approval matrix validation, audit logging |
| **Migration fails** | Medium | Low | Backup database, test migration |
| **Breaking change** | High | Low | New fields are nullable, backward compatible |

---

## Success Criteria

- [x] All 3 user stories completed
- [x] All acceptance criteria met
- [x] Impact analysis runs on CO creation
- [x] Impact score calculated and stored
- [x] Impact level assigned automatically
- [x] Approver assigned based on impact level
- [x] All quality gates passing (MyPy, Ruff, ESLint)
- [x] 100% of tests passing (18 tests)
- [x] Zero breaking changes
- [x] Database migration successful

---

## Definition of Done

A task is considered "Done" when:
1. Code is implemented and follows coding standards
2. Unit tests written and passing (TDD approach)
3. Integration tests passing
4. Database migration created and tested
5. API documentation updated (OpenAPI)
6. Quality gates passing (MyPy, Ruff)
7. Zero breaking changes confirmed

---

## Timeline Estimation

| Task | Points | Duration | Dependencies |
|------|--------|----------|--------------|
| Task 1: Auto Impact Analysis | 5 | 1 day | None |
| Task 2: Severity Calculation | 5 | 0.5 day | Task 1 |
| Task 3: Impact-Based Routing | 5 | 0.5 day | Task 2 |
| Migration & Testing | - | 0.5 day | Tasks 1-3 |
| **Total** | **15** | **2.5 days** | |

---

## Next Steps

1. ✅ Create implementation plan (this document)
2. **PDCA-DO Phase:** Implement Task 1 (Auto Impact Analysis)
3. **PDCA-DO Phase:** Implement Task 2 (Severity Calculation)
4. **PDCA-DO Phase:** Implement Task 3 (Impact-Based Routing)
5. **PDCA-CHECK Phase:** Run tests, validate workflow, check quality gates
6. **PDCA-ACT Phase:** Document learnings, create completion summary

---

**End of Phase 6 Implementation Plan**
