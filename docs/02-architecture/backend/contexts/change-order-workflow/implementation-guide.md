# Change Order Workflow Implementation Guide

**Last Updated:** 2026-04-11
**Owner:** Backend Team
**Related:** [Workflow Architecture](architecture.md)

---

## Purpose

This guide provides implementation details, code examples, and usage patterns for the Change Order Workflow Validation system. It complements the [architecture document](architecture.md) with practical implementation guidance.

---

## Table of Contents

1. [Basic Workflow Operations](#basic-workflow-operations)
2. [State Machine Usage](#state-machine-usage)
3. [Validation Patterns](#validation-patterns)
4. [Audit Logging](#audit-logging)
5. [Control Date Validation](#control-date-validation)
6. [Error Handling](#error-handling)
7. [Testing Workflow](#testing-workflow)
8. [Common Patterns](#common-patterns)

---

## Basic Workflow Operations

### Submitting for Approval

The submission workflow calculates financial impact, assigns an approver, sets an SLA deadline, and locks the branch.

```python
from app.services.change_order_workflow_service import ChangeOrderWorkflowService
from sqlalchemy.ext.asyncio import AsyncSession

async def submit_change_order(
    change_order_id: UUID,
    actor_id: UUID,
    db_session: AsyncSession,
) -> ChangeOrder:
    """Submit a change order for approval."""
    workflow = ChangeOrderWorkflowService()

    # Submit for approval
    # This will:
    # 1. Calculate financial impact level
    # 2. Assign approver based on impact level
    # 3. Set SLA deadline
    # 4. Lock the branch
    # 5. Create audit log entry
    updated_co = await workflow.submit_for_approval(
        change_order_id=change_order_id,
        actor_id=actor_id,
        db_session=db_session,
    )

    print(f"Status: {updated_co.status}")  # "Submitted for Approval"
    print(f"Impact Level: {updated_co.impact_level}")  # "MEDIUM"
    print(f"Approver: {updated_co.assigned_approver_id}")  # UUID
    print(f"SLA Due: {updated_co.sla_due_date}")  # datetime

    return updated_co
```

### Approving a Change Order

Approval validates user authority and transitions to "Approved" status.

```python
async def approve_change_order(
    change_order_id: UUID,
    approver_id: UUID,
    comments: str | None,
    db_session: AsyncSession,
) -> ChangeOrder:
    """Approve a change order."""
    workflow = ChangeOrderWorkflowService()

    # Approve with optional comments
    approved_co = await workflow.approve_change_order(
        change_order_id=change_order_id,
        actor_id=approver_id,
        comments=comments,
        db_session=db_session,
    )

    print(f"Status: {approved_co.status}")  # "Approved"

    return approved_co
```

### Rejecting a Change Order

Rejection validates authority, clears SLA fields, and unlocks the branch.

```python
async def reject_change_order(
    change_order_id: UUID,
    rejecter_id: UUID,
    comments: str | None,
    db_session: AsyncSession,
) -> ChangeOrder:
    """Reject a change order."""
    workflow = ChangeOrderWorkflowService()

    # Reject with optional comments
    rejected_co = await workflow.reject_change_order(
        change_order_id=change_order_id,
        actor_id=rejecter_id,
        comments=comments,
        db_session=db_session,
    )

    print(f"Status: {rejected_co.status}")  # "Rejected"
    print(f"SLA Due Date: {rejected_co.sla_due_date}")  # None (cleared)

    return rejected_co
```

---

## State Machine Usage

### Checking Valid Transitions

```python
async def check_transitions(current_status: str) -> list[str]:
    """Get valid next states from current status."""
    workflow = ChangeOrderWorkflowService()

    # Get all valid transitions
    transitions = await workflow.get_available_transitions(current_status)

    print(f"From '{current_status}', can go to: {transitions}")
    # From 'Draft', can go to: ['Submitted for Approval']
    # From 'Under Review', can go to: ['Approved', 'Rejected']

    return transitions
```

### Validating Transitions

```python
async def validate_transition(
    from_status: str,
    to_status: str,
) -> bool:
    """Check if a transition is valid."""
    workflow = ChangeOrderWorkflowService()

    is_valid = await workflow.is_valid_transition(from_status, to_status)

    if not is_valid:
        print(f"Invalid transition: {from_status} → {to_status}")
        return False

    print(f"Valid transition: {from_status} → {to_status}")
    return True
```

### Checking Edit Permission

```python
async def can_edit_change_order(status: str) -> bool:
    """Check if CO can be edited in current status."""
    workflow = ChangeOrderWorkflowService()

    can_edit = await workflow.can_edit_on_status(status)

    print(f"Can edit in '{status}': {can_edit}")
    # Can edit in 'Draft': True
    # Can edit in 'Submitted for Approval': False
    # Can edit in 'Rejected': True

    return can_edit
```

### Branch Locking Checks

```python
async def check_branch_locking(
    from_status: str,
    to_status: str,
) -> tuple[bool, bool]:
    """Check if transition locks/unlocks branch."""
    workflow = ChangeOrderWorkflowService()

    should_lock = await workflow.should_lock_on_transition(from_status, to_status)
    should_unlock = await workflow.should_unlock_on_transition(from_status, to_status)

    print(f"Transition {from_status} → {to_status}:")
    print(f"  Lock branch: {should_lock}")
    print(f"  Unlock branch: {should_unlock}")

    return should_lock, should_unlock
```

---

## Validation Patterns

### Approver Authority Validation

```python
from app.services.approval_matrix_service import ApprovalMatrixService

async def validate_approval_authority(
    user: User,
    change_order: ChangeOrder,
    db_session: AsyncSession,
) -> bool:
    """Validate if user can approve this change order."""
    approval_service = ApprovalMatrixService(db_session)

    # Check authority
    can_approve = await approval_service.can_approve(user, change_order)

    if not can_approve:
        # Get details for error message
        user_authority = approval_service.get_user_authority_level(user)
        required_authority = approval_service.get_authority_for_impact(
            change_order.impact_level
        )

        print(f"Authority check failed:")
        print(f"  User authority: {user_authority}")
        print(f"  Required authority: {required_authority}")

        return False

    return True
```

### Getting Approval Information

```python
async def get_approval_info(
    change_order: ChangeOrder,
    db_session: AsyncSession,
) -> dict[str, Any]:
    """Get comprehensive approval information."""
    approval_service = ApprovalMatrixService(db_session)

    return {
        "impact_level": change_order.impact_level,
        "required_authority": approval_service.get_authority_for_impact(
            change_order.impact_level
        ),
        "assigned_approver_id": change_order.assigned_approver_id,
        "sla_assigned_at": change_order.sla_assigned_at,
        "sla_due_date": change_order.sla_due_date,
        "sla_status": change_order.sla_status,
    }
```

### SLA Deadline Calculation

```python
from app.services.sla_service import SLAService
from datetime import UTC, datetime

def calculate_sla_deadline_example() -> None:
    """Calculate SLA deadline for a change order."""
    sla_service = SLAService(db_session)

    # Calculate deadline from impact level and start time
    impact_level = "MEDIUM"
    submission_time = datetime.now(UTC)

    deadline = sla_service.calculate_sla_deadline(impact_level, submission_time)

    print(f"Impact Level: {impact_level}")
    print(f"Submission Time: {submission_time}")
    print(f"SLA Deadline: {deadline}")  # 5 business days later
```

---

## Audit Logging

### Creating Audit Entries

```python
from app.models.domain.change_order_audit_log import ChangeOrderAuditLog

async def create_audit_entry(
    change_order_id: UUID,
    old_status: str,
    new_status: str,
    actor_id: UUID,
    comment: str | None,
    db_session: AsyncSession,
) -> ChangeOrderAuditLog:
    """Create an audit log entry for a status transition."""
    audit_entry = ChangeOrderAuditLog(
        change_order_id=change_order_id,
        old_status=old_status,
        new_status=new_status,
        comment=comment,
        changed_by=actor_id,
    )

    db_session.add(audit_entry)
    await db_session.flush()

    return audit_entry
```

### Querying Audit History

```python
from sqlalchemy import select
from app.models.domain.change_order_audit_log import ChangeOrderAuditLog

async def get_audit_history(
    change_order_id: UUID,
    db_session: AsyncSession,
) -> list[ChangeOrderAuditLog]:
    """Get audit history for a change order."""
    stmt = (
        select(ChangeOrderAuditLog)
        .where(ChangeOrderAuditLog.change_order_id == change_order_id)
        .order_by(ChangeOrderAuditLog.changed_at.asc())
    )

    result = await db_session.execute(stmt)
    audit_logs = result.scalars().all()

    return audit_logs
```

---

## Control Date Validation

### Validating Control Date Sequence

```python
from app.services.change_order_workflow_validation import ControlDateValidator

async def validate_control_date(
    change_order_id: UUID,
    new_control_date: datetime,
    db_session: AsyncSession,
) -> bool:
    """Validate control date sequence."""
    validator = ControlDateValidator()

    try:
        await validator.validate_control_date_sequence(
            change_order_id=change_order_id,
            new_control_date=new_control_date,
            session=db_session,
        )
        print("Control date sequence is valid")
        return True

    except ControlDateSequenceViolationError as e:
        print(f"Control date violation: {e}")
        return False
```

### Getting Last Operation Control Date

```python
async def get_last_control_date(
    change_order_id: UUID,
    db_session: AsyncSession,
) -> datetime | None:
    """Get the control date of the most recent operation."""
    validator = ControlDateValidator()

    last_control_date = await validator.get_last_operation_control_date(
        change_order_id=change_order_id,
        session=db_session,
    )

    if last_control_date:
        print(f"Last operation control date: {last_control_date}")
    else:
        print("No prior operations found")

    return last_control_date
```

---

## Error Handling

### Handling Workflow Errors

```python
from app.services.change_order_workflow_validation import ControlDateSequenceViolationError

async def safe_workflow_operation(
    change_order_id: UUID,
    actor_id: UUID,
    db_session: AsyncSession,
) -> ChangeOrder | None:
    """Handle workflow operations with proper error handling."""
    workflow = ChangeOrderWorkflowService()

    try:
        # Attempt workflow operation
        result = await workflow.submit_for_approval(
            change_order_id=change_order_id,
            actor_id=actor_id,
            db_session=db_session,
        )
        return result

    except ControlDateSequenceViolationError as e:
        print(f"Control date violation: {e}")
        print("Please use a control_date >= last operation's control_date")
        return None

    except ValueError as e:
        print(f"Validation error: {e}")
        print("Common causes:")
        print("  - Change order not in Draft status")
        print("  - No eligible approver found")
        print("  - Invalid state transition")
        return None

    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

### Handling Authority Errors

```python
async def safe_approval(
    change_order_id: UUID,
    approver_id: UUID,
    db_session: AsyncSession,
) -> ChangeOrder | None:
    """Handle approval with authority error handling."""
    workflow = ChangeOrderWorkflowService()

    try:
        result = await workflow.approve_change_order(
            change_order_id=change_order_id,
            actor_id=approver_id,
            comments=None,
            db_session=db_session,
        )
        return result

    except ValueError as e:
        error_msg = str(e)
        if "does not have sufficient authority" in error_msg:
            print("Authority check failed!")
            print("User's role does not permit approving this impact level")
            return None
        raise
```

---

## Testing Workflow

### Unit Test Example

```python
import pytest
from app.services.change_order_workflow_service import ChangeOrderWorkflowService

@pytest.mark.asyncio
async def test_workflow_transitions():
    """Test workflow state transitions."""
    workflow = ChangeOrderWorkflowService()

    # Test Draft → Submitted for Approval
    assert await workflow.is_valid_transition("Draft", "Submitted for Approval")

    # Test invalid transition
    assert not await workflow.is_valid_transition("Draft", "Approved")

    # Test branch locking
    assert await workflow.should_lock_on_transition(
        "Draft", "Submitted for Approval"
    )

    # Test editing permissions
    assert await workflow.can_edit_on_status("Draft")
    assert not await workflow.can_edit_on_status("Submitted for Approval")
```

### Integration Test Example

```python
@pytest.mark.asyncio
async def test_submit_approval_workflow(db_session: AsyncSession):
    """Test full submission workflow."""
    # Create change order
    co = await create_test_change_order(db_session)

    # Submit for approval
    workflow = ChangeOrderWorkflowService()
    updated_co = await workflow.submit_for_approval(
        change_order_id=co.change_order_id,
        actor_id=test_user_id,
        db_session=db_session,
    )

    # Assertions
    assert updated_co.status == "Submitted for Approval"
    assert updated_co.impact_level is not None
    assert updated_co.assigned_approver_id is not None
    assert updated_co.sla_due_date is not None

    # Check audit log
    stmt = select(ChangeOrderAuditLog).where(
        ChangeOrderAuditLog.change_order_id == co.change_order_id
    )
    result = await db_session.execute(stmt)
    audit_logs = result.scalars().all()

    assert len(audit_logs) == 1
    assert audit_logs[0].old_status == "Draft"
    assert audit_logs[0].new_status == "Submitted for Approval"
```

---

## Common Patterns

### Pattern 1: Workflow with Transaction Management

```python
async def execute_workflow_operation(
    change_order_id: UUID,
    actor_id: UUID,
    db_session: AsyncSession,
) -> ChangeOrder:
    """Execute workflow operation with transaction management."""
    workflow = ChangeOrderWorkflowService()

    try:
        # Perform workflow operation
        result = await workflow.submit_for_approval(
            change_order_id=change_order_id,
            actor_id=actor_id,
            db_session=db_session,
        )

        # Commit transaction
        await db_session.commit()

        return result

    except Exception as e:
        # Rollback on error
        await db_session.rollback()
        raise
```

### Pattern 2: Status Check Before Operation

```python
async def safe_submit_with_status_check(
    change_order_id: UUID,
    actor_id: UUID,
    db_session: AsyncSession,
) -> ChangeOrder:
    """Submit with pre-flight status check."""
    from app.services.change_order_service import ChangeOrderService

    co_service = ChangeOrderService(db_session)
    workflow = ChangeOrderWorkflowService()

    # Get current CO
    current_co = await co_service.get_as_of(change_order_id, branch="main")

    # Check if can edit
    can_edit = await workflow.can_edit_on_status(current_co.status)

    if not can_edit:
        raise ValueError(
            f"Cannot submit CO in status '{current_co.status}'. "
            f"Only Draft COs can be submitted."
        )

    # Proceed with submission
    return await workflow.submit_for_approval(
        change_order_id=change_order_id,
        actor_id=actor_id,
        db_session=db_session,
    )
```

### Pattern 3: Batch Operations with Control Dates

```python
async def batch_submit_with_control_dates(
    change_order_ids: list[UUID],
    actor_id: UUID,
    base_control_date: datetime,
    db_session: AsyncSession,
) -> list[ChangeOrder]:
    """Submit multiple COs with sequential control dates."""
    workflow = ChangeOrderWorkflowService()
    results = []

    for idx, co_id in enumerate(change_order_ids):
        # Calculate control date for this operation
        control_date = base_control_date + timedelta(minutes=idx)

        try:
            result = await workflow.submit_for_approval(
                change_order_id=co_id,
                actor_id=actor_id,
                db_session=db_session,
            )
            results.append(result)

        except ControlDateSequenceViolationError:
            print(f"Skipped CO {co_id} due to control date violation")
            continue

    return results
```

---

## Code Locations Reference

### Workflow Services
- `app/services/change_order_workflow_service.py` - State machine and workflow orchestration
- `app/services/change_order_workflow_validation.py` - Control date sequence validation

### Supporting Services
- `app/services/approval_matrix_service.py` - Approver authority validation
- `app/services/sla_service.py` - SLA deadline calculation
- `app/services/financial_impact_service.py` - Impact level calculation

### Models
- `app/models/domain/change_order.py` - Change Order entity with status field
- `app/models/domain/change_order_audit_log.py` - Audit log model

### API Routes
- `app/api/routes/change_orders.py` - Workflow endpoints

### Tests
- `tests/unit/services/test_change_order_workflow_service.py` - Unit tests
- `tests/unit/services/test_change_order_workflow_validation.py` - Validation tests
- `tests/integration/test_change_order_workflow_full_temporal.py` - Integration tests

---

## See Also

- [Workflow Architecture](architecture.md) - System architecture and design
- [EVCS Implementation Guide](../evcs-core/evcs-implementation-guide.md) - Versioning patterns
- [Temporal Query Reference](../../cross-cutting/temporal-query-reference.md) - Time travel queries
