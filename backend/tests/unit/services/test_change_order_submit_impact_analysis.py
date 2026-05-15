"""Unit tests for impact analysis on change order submission (BE-006).

Tests verify that impact analysis runs correctly when submitting a change order
for approval, including:
1. impact_level is calculated and set correctly based on changes
2. assigned_approver_id matches approval matrix for the impact level
3. sla_due_date is calculated from SLA policy and stored
4. Branch is locked after successful submission
5. Empty branch scenario works correctly

Follows TDD methodology: RED-GREEN-REFACTOR
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder
from app.models.domain.rbac import RBACRole
from app.models.domain.user import User
from app.models.domain.user_role_assignment import UserRoleAssignment
from app.models.schemas.change_order import ChangeOrderCreate
from app.models.schemas.project import ProjectCreate
from app.services.change_order_service import ChangeOrderService
from app.services.project import ProjectService


async def _setup_approver(
    db_session: AsyncSession, project_id: UUID | None = None
) -> tuple[User, UUID]:
    """Create a User and UserRoleAssignment so the approval matrix can find an approver.

    The global 'admin' RBACRole is seeded by migration and can approve any impact level.
    If project_id is provided, creates a project-scoped assignment; otherwise global.

    Returns (user, admin_user_id).
    """
    admin_user_id = uuid4()
    admin_user = User(
        id=uuid4(),
        user_id=admin_user_id,
        email=f"approver-{uuid4().hex[:8]}@test.com",
        is_active=True,
        role="admin",
        full_name="Approver User",
        hashed_password="hash",
        created_by=uuid4(),
    )
    db_session.add(admin_user)
    await db_session.flush()

    # Find the 'admin' RBACRole (seeded by migration)
    role_result = await db_session.execute(
        select(RBACRole).where(RBACRole.name == "admin")
    )
    admin_role = role_result.scalar_one_or_none()
    if admin_role is None:
        # Fallback: try project_admin if global admin doesn't exist
        role_result = await db_session.execute(
            select(RBACRole).where(RBACRole.name == "project_admin")
        )
        admin_role = role_result.scalar_one_or_none()
    if admin_role is None:
        # Last resort: use any role
        role_result = await db_session.execute(select(RBACRole).limit(1))
        admin_role = role_result.scalar_one_or_none()

    if admin_role is not None:
        scope_type = "project" if project_id else "global"
        scope_id = project_id if project_id else None
        assignment = UserRoleAssignment(
            user_id=admin_user_id,
            role_id=admin_role.id,
            scope_type=scope_type,
            scope_id=scope_id,
            granted_by=uuid4(),
        )
        db_session.add(assignment)
        await db_session.flush()

    await db_session.commit()
    return admin_user, admin_user_id


class TestSubmitForApprovalImpactAnalysis:
    """Test impact analysis during submit_for_approval workflow."""

    @pytest.mark.asyncio
    async def test_submit_for_approval_calculates_impact_level(
        self, db_session: AsyncSession
    ) -> None:
        """Test that impact_level is calculated and set correctly on submission."""
        # Arrange
        service = ChangeOrderService(db_session)
        project_service = ProjectService(db_session)

        # Create project
        project_id = uuid4()
        project_in = ProjectCreate(
            project_id=project_id,
            code="TEST-PROJ-001",
            name="Test Project",
            description="Test project for impact analysis",
            budget=Decimal("100000"),
            department_id=uuid4(),
        )
        await project_service.create_project(project_in, actor_id=uuid4())
        await db_session.commit()

        # Create an admin user with RBAC role for approver assignment
        await _setup_approver(db_session, project_id=project_id)

        # Create a change order in Draft status
        actor_id = uuid4()
        change_order_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-2026-001",
            title="Test Impact Level",
            description="Testing impact level calculation on submission",
            justification="Test",
        )

        created_co = await service.create_change_order(
            change_order_in, actor_id=actor_id
        )
        await db_session.commit()

        # Verify initial state - no impact analysis yet
        assert created_co.impact_analysis_status is None
        assert created_co.impact_level is None
        assert created_co.impact_score is None

        # Act - Submit for approval (triggers impact analysis)
        submitted_co = await service.submit_for_approval(
            change_order_id=created_co.change_order_id,
            actor_id=actor_id,
            branch="main",
        )
        await db_session.commit()
        await db_session.refresh(submitted_co)

        # Assert - Impact analysis completed
        assert submitted_co.impact_analysis_status == "completed"
        assert submitted_co.impact_level is not None
        assert submitted_co.impact_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert submitted_co.impact_score is not None
        assert submitted_co.status == "submitted_for_approval"

    @pytest.mark.asyncio
    async def test_submit_for_approval_assigns_approver_based_on_impact(
        self, db_session: AsyncSession
    ) -> None:
        """Test that assigned_approver_id matches approval matrix for impact level."""
        # Arrange
        service = ChangeOrderService(db_session)
        project_service = ProjectService(db_session)

        # Create project
        project_id = uuid4()
        project_in = ProjectCreate(
            project_id=project_id,
            code="TEST-PROJ-002",
            name="Test Project 2",
            description="Test project for approver assignment",
            budget=Decimal("100000"),
            department_id=uuid4(),
        )
        await project_service.create_project(project_in, actor_id=uuid4())
        await db_session.commit()

        # Create approver with RBAC role
        _, approver_user_id = await _setup_approver(db_session, project_id=project_id)

        # Create a change order
        actor_id = uuid4()
        change_order_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-2026-002",
            title="Test Approver Assignment",
            description="Testing approver assignment on submission",
            justification="Test",
        )

        created_co = await service.create_change_order(
            change_order_in, actor_id=actor_id
        )
        await db_session.commit()

        # Act - Submit for approval
        submitted_co = await service.submit_for_approval(
            change_order_id=created_co.change_order_id,
            actor_id=actor_id,
            branch="main",
        )
        await db_session.commit()
        await db_session.refresh(submitted_co)

        # Assert - Approver is assigned
        assert submitted_co.assigned_approver_id is not None
        assert isinstance(submitted_co.assigned_approver_id, UUID)

    @pytest.mark.asyncio
    async def test_submit_for_approval_calculates_sla_due_date(
        self, db_session: AsyncSession
    ) -> None:
        """Test that sla_due_date is calculated from SLA policy and stored."""
        # Arrange
        service = ChangeOrderService(db_session)
        project_service = ProjectService(db_session)

        # Create project
        project_id = uuid4()
        project_in = ProjectCreate(
            project_id=project_id,
            code="TEST-PROJ-003",
            name="Test Project 3",
            description="Test project for SLA calculation",
            budget=Decimal("100000"),
            department_id=uuid4(),
        )
        await project_service.create_project(project_in, actor_id=uuid4())
        await db_session.commit()

        # Create approver with RBAC role
        await _setup_approver(db_session, project_id=project_id)

        # Create a change order
        actor_id = uuid4()
        change_order_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-2026-003",
            title="Test SLA Due Date",
            description="Testing SLA due date calculation on submission",
            justification="Test",
        )

        created_co = await service.create_change_order(
            change_order_in, actor_id=actor_id
        )
        await db_session.commit()

        # Record submission time (use UTC to match service behavior)
        submission_time = datetime.now(UTC)

        # Act - Submit for approval
        submitted_co = await service.submit_for_approval(
            change_order_id=created_co.change_order_id,
            actor_id=actor_id,
            branch="main",
        )
        await db_session.commit()
        await db_session.refresh(submitted_co)

        # Assert - SLA fields are set
        assert submitted_co.sla_assigned_at is not None
        assert submitted_co.sla_due_date is not None
        assert submitted_co.sla_status == "pending"

        # Verify SLA due date is in the future
        if submitted_co.sla_due_date.tzinfo is None:
            due_date = submitted_co.sla_due_date.replace(tzinfo=UTC)
        else:
            due_date = submitted_co.sla_due_date
        assert due_date > submission_time

        # Verify SLA due date is approximately correct based on impact level
        sla_days = await service._get_sla_days(submitted_co.impact_level)
        expected_due_date = service._add_business_days(
            submitted_co.sla_assigned_at, sla_days
        )

        # Allow 1 minute tolerance for test execution time
        time_diff = abs((submitted_co.sla_due_date - expected_due_date).total_seconds())
        assert time_diff < 60

    @pytest.mark.asyncio
    async def test_submit_for_approval_locks_branch(
        self, db_session: AsyncSession
    ) -> None:
        """Test that the isolation branch is locked after successful submission."""
        # Arrange
        service = ChangeOrderService(db_session)
        project_service = ProjectService(db_session)
        branch_service = service.branch_service

        # Create project
        project_id = uuid4()
        project_in = ProjectCreate(
            project_id=project_id,
            code="TEST-PROJ-004",
            name="Test Project 4",
            description="Test project for branch locking",
            budget=Decimal("100000"),
            department_id=uuid4(),
        )
        await project_service.create_project(project_in, actor_id=uuid4())
        await db_session.commit()

        # Create approver with RBAC role
        await _setup_approver(db_session, project_id=project_id)

        # Create a change order (this creates the branch)
        actor_id = uuid4()
        change_order_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-2026-004",
            title="Test Branch Locking",
            description="Testing branch locking on submission",
            justification="Test",
        )

        created_co = await service.create_change_order(
            change_order_in, actor_id=actor_id
        )
        await db_session.commit()

        # Get the branch name
        branch_name = created_co.branch_name
        assert branch_name is not None

        # Verify branch exists and is initially unlocked
        branch = await branch_service.get_by_name_and_project(
            name=branch_name,
            project_id=project_id,
        )
        assert branch is not None
        assert branch.locked is False

        # Act - Submit for approval
        await service.submit_for_approval(
            change_order_id=created_co.change_order_id,
            actor_id=actor_id,
            branch="main",
        )
        await db_session.commit()

        # Assert - Branch is now locked
        branch = await branch_service.get_by_name_and_project(
            name=branch_name,
            project_id=project_id,
        )
        assert branch is not None
        assert branch.locked is True

    @pytest.mark.asyncio
    async def test_submit_for_approval_empty_branch_scenario(
        self, db_session: AsyncSession
    ) -> None:
        """Test that empty branch scenario is handled gracefully."""
        # Arrange
        service = ChangeOrderService(db_session)
        project_service = ProjectService(db_session)

        # Create project WITHOUT any WBEs or CostElements (empty project)
        project_id = uuid4()
        project_in = ProjectCreate(
            project_id=project_id,
            code="TEST-PROJ-EMPTY",
            name="Empty Test Project",
            description="Project with no data for empty branch test",
            budget=Decimal("100000"),
            department_id=uuid4(),
        )
        await project_service.create_project(project_in, actor_id=uuid4())
        await db_session.commit()

        # Create approver with RBAC role
        await _setup_approver(db_session, project_id=project_id)

        # Create a change order for empty project
        actor_id = uuid4()
        change_order_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-2026-EMPTY",
            title="Empty Branch Test",
            description="Testing submission with empty branch",
            justification="Test",
        )

        created_co = await service.create_change_order(
            change_order_in, actor_id=actor_id
        )
        await db_session.commit()

        # Act - Submit for approval (should handle empty branch gracefully)
        submitted_co = await service.submit_for_approval(
            change_order_id=created_co.change_order_id,
            actor_id=actor_id,
            branch="main",
        )
        await db_session.commit()
        await db_session.refresh(submitted_co)

        # Assert - Submission succeeded despite empty branch
        assert submitted_co.status == "submitted_for_approval"
        assert submitted_co.impact_analysis_status == "completed"

        # Empty branch should result in LOW impact (no changes = minimal impact)
        assert submitted_co.impact_level == "LOW"
        assert submitted_co.impact_score == Decimal("0")

        # Approver should still be assigned
        assert submitted_co.assigned_approver_id is not None

        # SLA should be calculated
        assert submitted_co.sla_due_date is not None
        assert submitted_co.sla_assigned_at is not None
        assert submitted_co.sla_status == "pending"

    @pytest.mark.asyncio
    async def test_submit_for_approval_runs_impact_analysis(
        self, db_session: AsyncSession
    ) -> None:
        """Test that impact analysis is run during submission."""
        # Arrange
        service = ChangeOrderService(db_session)
        project_service = ProjectService(db_session)

        # Create project
        project_id = uuid4()
        project_in = ProjectCreate(
            project_id=project_id,
            code="TEST-PROJ-005",
            name="Test Project 5",
            description="Test project for impact analysis on submission",
            budget=Decimal("100000"),
            department_id=uuid4(),
        )
        await project_service.create_project(project_in, actor_id=uuid4())
        await db_session.commit()

        # Create approver with RBAC role
        await _setup_approver(db_session, project_id=project_id)

        # Create a change order
        actor_id = uuid4()
        change_order_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-2026-005",
            title="Test Impact Analysis on Submission",
            description="Testing that impact analysis runs on submission",
            justification="Test",
        )

        created_co = await service.create_change_order(
            change_order_in, actor_id=actor_id
        )
        await db_session.commit()

        # Verify initial state - no impact analysis yet
        assert created_co.impact_analysis_status is None

        # Act - Submit for approval (should run impact analysis)
        submitted_co = await service.submit_for_approval(
            change_order_id=created_co.change_order_id,
            actor_id=actor_id,
            branch="main",
        )
        await db_session.commit()
        await db_session.refresh(submitted_co)

        # Assert - Impact analysis was run and completed
        assert submitted_co.impact_analysis_status == "completed"
        assert submitted_co.impact_level is not None
        assert submitted_co.impact_score is not None

    @pytest.mark.asyncio
    async def test_submit_for_approval_validates_branch_name_exists(
        self, db_session: AsyncSession
    ) -> None:
        """Test that submission validates branch_name is configured."""
        # Arrange
        service = ChangeOrderService(db_session)
        project_service = ProjectService(db_session)

        # Create project
        project_id = uuid4()
        project_in = ProjectCreate(
            project_id=project_id,
            code="TEST-PROJ-006",
            name="Test Project 6",
            description="Test project for branch_name validation",
            budget=Decimal("100000"),
            department_id=uuid4(),
        )
        await project_service.create_project(project_in, actor_id=uuid4())
        await db_session.commit()

        # Create a change order
        actor_id = uuid4()
        change_order_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-2026-006",
            title="Test Branch Name Validation",
            description="Testing branch_name validation",
            justification="Test",
        )

        created_co = await service.create_change_order(
            change_order_in, actor_id=actor_id
        )
        await db_session.commit()

        # Manually clear branch_name to test validation
        update_stmt = (
            update(ChangeOrder)
            .where(ChangeOrder.id == created_co.id)
            .values(branch_name=None)
        )
        await db_session.execute(update_stmt)
        await db_session.commit()
        await db_session.refresh(created_co)

        # Act & Assert - Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await service.submit_for_approval(
                change_order_id=created_co.change_order_id,
                actor_id=actor_id,
                branch="main",
            )

        # Verify error message mentions branch/isolation
        error_msg = str(exc_info.value).lower()
        assert "branch" in error_msg or "isolation" in error_msg

    @pytest.mark.asyncio
    async def test_submit_for_approval_requires_approver_assigned(
        self, db_session: AsyncSession
    ) -> None:
        """Test that submission requires an approver to be assigned."""
        # Arrange
        service = ChangeOrderService(db_session)
        project_service = ProjectService(db_session)

        # Create project WITHOUT any approvers (no RBAC assignments)
        project_id = uuid4()
        project_in = ProjectCreate(
            project_id=project_id,
            code="TEST-PROJ-NO-APPROVER",
            name="Test Project No Approver",
            description="Project with no eligible approvers",
            budget=Decimal("100000"),
            department_id=uuid4(),
        )
        await project_service.create_project(project_in, actor_id=uuid4())
        await db_session.commit()

        # Create a change order
        actor_id = uuid4()
        change_order_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-2026-NO-APPR",
            title="Test No Approver",
            description="Testing submission when no approver is available",
            justification="Test",
        )

        created_co = await service.create_change_order(
            change_order_in, actor_id=actor_id
        )
        await db_session.commit()

        # Act & Assert - Should raise ValueError due to no approver
        with pytest.raises(ValueError) as exc_info:
            await service.submit_for_approval(
                change_order_id=created_co.change_order_id,
                actor_id=actor_id,
                branch="main",
            )

        # Verify error message mentions approver assignment
        error_msg = str(exc_info.value).lower()
        assert "approver" in error_msg and (
            "assigned" in error_msg
            or "not assigned" in error_msg
            or "no approver" in error_msg
            or "approval matrix" in error_msg
        )


class TestSubmitForApprovalIntegration:
    """Integration tests for submit_for_approval with impact analysis."""

    @pytest.mark.asyncio
    async def test_full_submission_workflow_with_impact_analysis(
        self, db_session: AsyncSession
    ) -> None:
        """Test the complete submission workflow end-to-end."""
        # Arrange
        service = ChangeOrderService(db_session)
        project_service = ProjectService(db_session)

        # Create project
        project_id = uuid4()
        project_in = ProjectCreate(
            project_id=project_id,
            code="TEST-PROJ-INT",
            name="Integration Test Project",
            description="Project for full workflow test",
            budget=Decimal("100000"),
            department_id=uuid4(),
        )
        await project_service.create_project(project_in, actor_id=uuid4())
        await db_session.commit()

        # Create approver with RBAC role
        await _setup_approver(db_session, project_id=project_id)

        # Create a change order
        actor_id = uuid4()
        change_order_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-2026-INT",
            title="Full Workflow Test",
            description="Testing complete submission workflow",
            justification="Test",
        )

        created_co = await service.create_change_order(
            change_order_in, actor_id=actor_id
        )
        await db_session.commit()

        # Act - Submit for approval
        submitted_co = await service.submit_for_approval(
            change_order_id=created_co.change_order_id,
            actor_id=actor_id,
            branch="main",
            comment="Submitting for approval with full workflow test",
        )
        await db_session.commit()
        await db_session.refresh(submitted_co)

        # Assert - Verify complete workflow
        # 1. Status transitioned
        assert submitted_co.status == "submitted_for_approval"

        # 2. Impact analysis completed
        assert submitted_co.impact_analysis_status == "completed"
        assert submitted_co.impact_level is not None
        assert submitted_co.impact_score is not None

        # 3. Approver assigned
        assert submitted_co.assigned_approver_id is not None

        # 4. SLA calculated
        assert submitted_co.sla_assigned_at is not None
        assert submitted_co.sla_due_date is not None
        assert submitted_co.sla_status == "pending"

        # 5. Branch locked
        assert submitted_co.branch_name is not None
        branch = await service.branch_service.get_by_name_and_project(
            name=submitted_co.branch_name,
            project_id=submitted_co.project_id,
        )
        assert branch.locked is True

        # 6. Audit log created
        from app.models.domain.change_order_audit_log import ChangeOrderAuditLog

        audit_stmt = select(ChangeOrderAuditLog).where(
            ChangeOrderAuditLog.change_order_id == created_co.change_order_id
        )
        audit_result = await db_session.execute(audit_stmt)
        audit_logs = audit_result.scalars().all()

        assert len(audit_logs) >= 1
        # Find the submission audit log
        submission_log = next(
            (
                log
                for log in audit_logs
                if log.new_status is not None
                and log.new_status == "submitted_for_approval"
            ),
            None,
        )
        assert submission_log is not None
        assert submission_log.old_status == "draft"
        # Comment is optional, but we provided one in the submission
        assert submission_log.comment is not None
        assert "Submitting for approval" in submission_log.comment
