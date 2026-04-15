# Bug Fix: Project-Level Budget Threshold Validation

## Issue Summary

**Critical Bug:** Project-level budget threshold validation was NOT working during cost registration submission.

**User's Test Results:**
- Project: VBM-ALB-2026
- Budget threshold configured: 80% (via Admin tab)
- Cost registration added: moved cost element from 78% to 92% of budget
- **EXPECTED:** Budget warning upon submission (should trigger at 80%)
- **ACTUAL:** NO warning appeared during submission
- **ONLY WARNING:** Cost element detail page shows "over 90%" warning (inconsistent with 80% setting)

## Root Cause Analysis

The `validate_budget_status()` method in `CostRegistrationService` was only checking **individual cost element budget usage**, not **project-level budget aggregation**.

### Original Behavior (BUGGY):
```python
# OLD CODE - Only checked cost element budget
budget_status = await self.get_budget_status(
    cost_element_id=cost_element_id, as_of=None, branch=branch
)

# Compared cost element % (e.g., 92%) against project threshold (e.g., 80%)
if budget_status.percentage < threshold:
    return None
```

### Problem:
- If a cost element had a large budget (e.g., €470K), spending 92% (€432K) would trigger a warning
- But the **project budget** (€620K) with total spend (€600K = 96.77%) was never checked
- This meant users could exceed the project budget threshold without any warning

## Solution Implemented

### 1. Added Project-Level Budget Status Calculation

**File:** `backend/app/services/cost_registration_service.py`

**New Method:** `get_project_budget_status()`
- Calculates total spend across **all cost elements** in the project
- Joins: Project → WBE → CostElement → CostRegistration
- Returns: `ProjectBudgetStatus` with project_budget, total_spend, remaining, percentage

```python
async def get_project_budget_status(
    self, project_id: UUID, branch: str = "main"
) -> ProjectBudgetStatus:
    """Get project-level budget status (aggregated across all cost elements)."""
    # Get project budget
    project = await self._get_project(project_id, branch)
    project_budget = project.budget

    # Calculate total spend across all cost elements
    total_spend_stmt = (
        select(func.sum(CostRegistration.amount))
        .join(CostElement, CostRegistration.cost_element_id == CostElement.cost_element_id)
        .join(WBE, CostElement.wbe_id == WBE.wbe_id)
        .where(WBE.project_id == project_id, ...)
    )
    total_spend = await self.session.execute(total_spend_stmt)

    # Calculate percentage
    percentage = (total_spend / project_budget * 100) if project_budget > 0 else 0

    return ProjectBudgetStatus(
        project_id=project_id,
        project_budget=project_budget,
        total_spend=total_spend,
        remaining=project_budget - total_spend,
        percentage=percentage,
    )
```

### 2. Updated Validation Logic

**Modified Method:** `validate_budget_status()`

```python
async def validate_budget_status(
    self,
    cost_element_id: UUID,
    project_id: UUID,
    user_id: UUID,
    branch: str = "main",
) -> BudgetWarning | None:
    """Validate budget status and return warning if threshold exceeded.

    Checks if the PROJECT's total budget usage exceeds the project's
    warning threshold (aggregated across all cost elements).
    """
    # Get project budget settings
    settings_service = ProjectBudgetSettingsService(self.session)
    threshold = await settings_service.get_warning_threshold(project_id)

    # Get PROJECT-level budget status (aggregated across all cost elements)
    project_budget_status = await self.get_project_budget_status(
        project_id=project_id, branch=branch
    )

    # Check if threshold exceeded
    if project_budget_status.percentage < threshold:
        return None

    # Threshold exceeded - create warning
    return BudgetWarning(
        exceeds_threshold=True,
        threshold_percent=threshold,
        current_percent=project_budget_status.percentage,
        message=(
            f"Project budget usage at {project_budget_status.percentage:.1f}% "
            f"exceeds warning threshold of {threshold:.1f}% "
            f"(€{project_budget_status.total_spend:,.2f} of €{project_budget_status.project_budget:,.2f})"
        ),
    )
```

## Verification

### Database Query (VBM-ALB-2026 Project):
```sql
SELECT 
    p.name as project_name,
    p.budget as project_budget,
    pbs.warning_threshold_percent,
    COALESCE(SUM(cr.amount), 0) as total_project_spend,
    ROUND((COALESCE(SUM(cr.amount), 0) / p.budget * 100)::numeric, 2) as project_budget_percentage
FROM projects p
LEFT JOIN project_budget_settings pbs ON p.project_id = pbs.project_id
LEFT JOIN wbes w ON w.project_id = p.project_id
LEFT JOIN cost_elements ce ON ce.wbe_id = w.wbe_id
LEFT JOIN cost_registrations cr ON cr.cost_element_id = ce.cost_element_id
WHERE p.project_id = 'b735cfca-d6d6-49e9-ac59-d26654807dd9'
GROUP BY p.project_id, p.name, p.budget, pbs.warning_threshold_percent;
```

**Result:**
- Project Budget: €620,000
- Warning Threshold: 80%
- Total Project Spend: €600,000
- Project Budget Percentage: 96.77%
- **Status: WARNING: Exceeds threshold** ✓

### Test Coverage

**File:** `backend/tests/unit/services/test_project_budget_validation.py`

8 comprehensive tests covering:
1. Project budget status aggregation across cost elements
2. Project-level validation (not cost-element level)
3. Warning when below threshold
4. Custom threshold usage
5. Threshold exactly at limit
6. **Exact bug scenario reproduction**
7. Multiple cost elements aggregation
8. Default threshold (80%) when no custom settings

**Test Results:** All 8 tests pass ✓

## Impact

### Before Fix:
- Only validated individual cost element budgets
- Project-level threshold was ignored
- Users could exceed project budget without warnings
- Inconsistent behavior (cost element page showed different threshold)

### After Fix:
- Validates total project spend against project budget
- Respects project-level threshold configured in Admin tab
- Shows accurate warning with total spend vs project budget
- Consistent behavior across all interfaces

## Files Modified

1. **backend/app/services/cost_registration_service.py**
   - Added `ProjectBudgetStatus` model
   - Added `get_project_budget_status()` method
   - Updated `validate_budget_status()` to use project-level validation
   - Added `Project` import for project queries

2. **backend/tests/unit/services/test_project_budget_validation.py** (NEW)
   - Comprehensive test suite for project-level validation
   - Includes exact bug scenario reproduction

## Deployment Notes

- No database migrations required (uses existing schema)
- No API changes (response format unchanged)
- Backward compatible (existing cost registrations unaffected)
- Quality checks passed: Ruff ✓, MyPy ✓

## Related Documentation

- Project Budget Settings: `backend/app/services/project_budget_settings_service.py`
- Budget Settings Widget: Admin tab in frontend
- Cost Registration API: `backend/app/api/routes/cost_registrations.py`
