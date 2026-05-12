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
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder
from app.models.domain.user import User
from app.models.schemas.change_order import ChangeOrderCreate
from app.models.schemas.project import ProjectCreate
from app.services.change_order_service import ChangeOrderService
from app.services.project import ProjectService


class TestSubmitForApprovalImpactAnalysis:
    """Test impact analysis during submit_for_approval workflow."""

    @pytest.mark.asyncio
    async def test_submit_for_approval_calculates_impact_level(
        self, db_session: AsyncSession
    ) -> None:
        """Test that impact_level is calculated and set correctly on submission.

        Acceptance Criteria:
        - Impact analysis runs during submit_for_approval
        - impact_level is set based on calculated impact score
        - impact_score is stored in the change order
        - impact_analysis_status is set to "completed"

        Context: BE-006 Task #1 - Impact level calculation on submission
        """
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

        # Create an admin user for approver assignment
        admin_user_id = uuid4()
        admin_user = User(
            id=uuid4(),
            user_id=admin_user_id,
            email="admin@test.com",
            is_active=True,
            role="admin",
            full_name="Admin User",
            hashed_password="hash",
            created_by=uuid4(),
        )
        db_session.add(admin_user)
        await db_session.commit()

        # Add admin as project member for approver assignment
        from app.models.domain.project_member import ProjectMember

        project_member = ProjectMember(
            project_id=project_id,
            user_id=admin_user_id,
            role="admin",
        )
        db_session.add(project_member)
        await db_session.commit()

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
        """Test that assigned_approver_id matches approval matrix for impact level.

        Acceptance Criteria:
        - After impact analysis, approver is fetched from ApprovalMatrix
        - assigned_approver_id is set on change order
        - Approver has sufficient authority for the calculated impact level

        Context: BE-006 Task #2 - Approver assignment based on impact level
        """
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

        # Create users with different roles
        admin_user_id = uuid4()
        director_user_id = uuid4()

        admin_user = User(
            id=uuid4(),
            user_id=admin_user_id,
            email="admin@test.com",
            is_active=True,
            role="admin",
            full_name="Admin User",
            hashed_password="hash",
            created_by=uuid4(),
        )
        director_user = User(
            id=uuid4(),
            user_id=director_user_id,
            email="director@test.com",
            is_active=True,
            role="director",
            full_name="Director User",
            hashed_password="hash",
            created_by=uuid4(),
        )
        db_session.add_all([admin_user, director_user])
        await db_session.commit()

        # Add users as project members
        from app.models.domain.project_member import ProjectMember

        admin_member = ProjectMember(
            project_id=project_id,
            user_id=admin_user_id,
            role="admin",
        )
        director_member = ProjectMember(
            project_id=project_id,
            user_id=director_user_id,
            role="director",
        )
        db_session.add_all([admin_member, director_member])
        await db_session.commit()

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

        # Verify the assigned approver is one of our project members
        assert submitted_co.assigned_approver_id in [admin_user_id, director_user_id]

    @pytest.mark.asyncio
    async def test_submit_for_approval_calculates_sla_due_date(
        self, db_session: AsyncSession
    ) -> None:
        """Test that sla_due_date is calculated from SLA policy and stored.

        Acceptance Criteria:
        - sla_due_date is calculated based on impact_level
        - SLA days are read from workflow configuration
        - sla_assigned_at is set to current time
        - sla_status is set to "pending"

        Context: BE-006 Task #3 - SLA due date calculation
        """
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

        # Create admin user
        admin_user_id = uuid4()
        admin_user = User(
            id=uuid4(),
            user_id=admin_user_id,
            email="admin@test.com",
            is_active=True,
            role="admin",
            full_name="Admin User",
            hashed_password="hash",
            created_by=uuid4(),
        )
        db_session.add(admin_user)
        await db_session.commit()

        # Add admin as project member
        from app.models.domain.project_member import ProjectMember

        project_member = ProjectMember(
            project_id=project_id,
            user_id=admin_user_id,
            role="admin",
        )
        db_session.add(project_member)
        await db_session.commit()

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
        # Note: submitted_co.sla_due_date may be naive or aware, normalize comparison
        if submitted_co.sla_due_date.tzinfo is None:
            due_date = submitted_co.sla_due_date.replace(tzinfo=UTC)
        else:
            due_date = submitted_co.sla_due_date
        assert due_date > submission_time

        # Verify SLA due date is approximately correct based on impact level
        # Get SLA days for the impact level
        sla_days = await service._get_sla_days(submitted_co.impact_level)
        expected_due_date = service._add_business_days(
            submitted_co.sla_assigned_at, sla_days
        )

        # Allow 1 minute tolerance for test execution time
        time_diff = abs(
            (submitted_co.sla_due_date - expected_due_date).total_seconds()
        )
        assert time_diff < 60  # Less than 1 minute difference

    @pytest.mark.asyncio
    async def test_submit_for_approval_locks_branch(
        self, db_session: AsyncSession
    ) -> None:
        """Test that the isolation branch is locked after successful submission.

        Acceptance Criteria:
        - Branch exists (created during CO creation)
        - Branch is locked after submission
        - Branch lock prevents concurrent modifications

        Context: BE-006 Task #4 - Branch locking on submission
        """
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

        # Create admin user
        admin_user_id = uuid4()
        admin_user = User(
            id=uuid4(),
            user_id=admin_user_id,
            email="admin@test.com",
            is_active=True,
            role="admin",
            full_name="Admin User",
            hashed_password="hash",
            created_by=uuid4(),
        )
        db_session.add(admin_user)
        await db_session.commit()

        # Add admin as project member
        from app.models.domain.project_member import ProjectMember

        project_member = ProjectMember(
            project_id=project_id,
            user_id=admin_user_id,
            role="admin",
        )
        db_session.add(project_member)
        await db_session.commit()

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
        # Re-fetch the branch to get the latest state
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
        """Test that empty branch scenario is handled gracefully.

        Acceptance Criteria:
        - Empty branch (no WBEs/CostElements) doesn't cause submission to fail
        - Impact analysis completes with LOW impact level for empty branch
        - Approver is assigned for LOW impact level
        - SLA is calculated correctly

        Context: BE-006 Task #5 - Empty branch scenario (covered in BE-005)

        This test verifies the integration of the empty branch handling
        with the submit_for_approval workflow.
        """
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

        # Create admin user
        admin_user_id = uuid4()
        admin_user = User(
            id=uuid4(),
            user_id=admin_user_id,
            email="admin@test.com",
            is_active=True,
            role="admin",
            full_name="Admin User",
            hashed_password="hash",
            created_by=uuid4(),
        )
        db_session.add(admin_user)
        await db_session.commit()

        # Add admin as project member
        from app.models.domain.project_member import ProjectMember

        project_member = ProjectMember(
            project_id=project_id,
            user_id=admin_user_id,
            role="admin",
        )
        db_session.add(project_member)
        await db_session.commit()

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
        # This should NOT raise an exception
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
        """Test that impact analysis is run during submission.

        Acceptance Criteria:
        - Impact analysis runs during submit_for_approval (not just on creation)
        - impact_analysis_status is set to "completed"
        - impact_level and impact_score are calculated

        Context: BE-006 - Impact analysis runs on submission

        Note: This test verifies that impact analysis IS run during submission,
        even if it wasn't run before or had a previous status.
        """
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

        # Create admin user
        admin_user_id = uuid4()
        admin_user = User(
            id=uuid4(),
            user_id=admin_user_id,
            email="admin@test.com",
            is_active=True,
            role="admin",
            full_name="Admin User",
            hashed_password="hash",
            created_by=uuid4(),
        )
        db_session.add(admin_user)
        await db_session.commit()

        # Add admin as project member
        from app.models.domain.project_member import ProjectMember

        project_member = ProjectMember(
            project_id=project_id,
            user_id=admin_user_id,
            role="admin",
        )
        db_session.add(project_member)
        await db_session.commit()

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
        """Test that submission validates branch_name is configured.

        Acceptance Criteria:
        - Raises ValueError if branch_name is None
        - Helpful error message explaining requirement
        - CO status remains unchanged

        Context: BE-006 - Validation requirement for branch_name
        """
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

        # Create admin user
        admin_user_id = uuid4()
        admin_user = User(
            id=uuid4(),
            user_id=admin_user_id,
            email="admin@test.com",
            is_active=True,
            role="admin",
            full_name="Admin User",
            hashed_password="hash",
            created_by=uuid4(),
        )
        db_session.add(admin_user)
        await db_session.commit()

        # Add admin as project member
        from app.models.domain.project_member import ProjectMember

        project_member = ProjectMember(
            project_id=project_id,
            user_id=admin_user_id,
            role="admin",
        )
        db_session.add(project_member)
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
        from sqlalchemy import update

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
        """Test that submission requires an approver to be assigned.

        Acceptance Criteria:
        - Raises ValueError if no approver can be found for the impact level
        - Helpful error message explaining requirement
        - CO status remains unchanged

        Context: BE-006 - Validation requirement for approver assignment

        This test verifies that submission fails when the approval matrix
        doesn't have any eligible approvers configured.
        """
        # Arrange
        service = ChangeOrderService(db_session)
        project_service = ProjectService(db_session)

        # Create project WITHOUT any project members (no eligible approvers)
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
        """Test the complete submission workflow end-to-end.

        Acceptance Criteria:
        - Impact analysis runs and completes successfully
        - Impact level is calculated based on actual changes
        - Approver is assigned based on impact level
        - SLA due date is calculated correctly
        - Branch is locked
        - Status transitions to "submitted_for_approval"
        - Audit log is created

        Context: BE-006 - Full workflow integration test
        """
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

        # Create admin user
        admin_user_id = uuid4()
        admin_user = User(
            id=uuid4(),
            user_id=admin_user_id,
            email="admin@test.com",
            is_active=True,
            role="admin",
            full_name="Admin User",
            hashed_password="hash",
            created_by=uuid4(),
        )
        db_session.add(admin_user)
        await db_session.commit()

        # Add admin as project member
        from app.models.domain.project_member import ProjectMember

        project_member = ProjectMember(
            project_id=project_id,
            user_id=admin_user_id,
            role="admin",
        )
        db_session.add(project_member)
        await db_session.commit()

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
        from sqlalchemy import select

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
