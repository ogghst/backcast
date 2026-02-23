"""Unit tests for ApprovalMatrixService.

Following TDD RED-GREEN-REFACTOR cycle.

Tests approval authority validation and approver assignment for change orders
based on financial impact levels and user roles.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder, ImpactLevel
from app.models.domain.user import User
from app.services.approval_matrix_service import ApprovalMatrixService


class TestGetUserAuthorityLevel:
    """Test get_user_authority_level method."""

    @pytest.mark.asyncio
    async def test_admin_has_critical_authority(self, db_session: AsyncSession) -> None:
        """RED: Admin role should have CRITICAL authority."""
        # Arrange
        service = ApprovalMatrixService(db_session)
        user = User(
            user_id=uuid4(),
            email="admin@example.com",
            hashed_password="hash",
            full_name="Admin User",
            role="admin",
            is_active=True,
            created_by=uuid4(),
        )

        # Act
        authority = service.get_user_authority_level(user)

        # Assert
        assert authority == "CRITICAL"

    @pytest.mark.asyncio
    async def test_manager_has_high_authority(self, db_session: AsyncSession) -> None:
        """RED: Manager role should have HIGH authority."""
        # Arrange
        service = ApprovalMatrixService(db_session)
        user = User(
            user_id=uuid4(),
            email="manager@example.com",
            hashed_password="hash",
            full_name="Manager User",
            role="manager",
            is_active=True,
            created_by=uuid4(),
        )

        # Act
        authority = service.get_user_authority_level(user)

        # Assert
        assert authority == "HIGH"

    @pytest.mark.asyncio
    async def test_viewer_has_low_authority(self, db_session: AsyncSession) -> None:
        """RED: Viewer role should have LOW authority."""
        # Arrange
        service = ApprovalMatrixService(db_session)
        user = User(
            user_id=uuid4(),
            email="viewer@example.com",
            hashed_password="hash",
            full_name="Viewer User",
            role="viewer",
            is_active=True,
            created_by=uuid4(),
        )

        # Act
        authority = service.get_user_authority_level(user)

        # Assert
        assert authority == "LOW"


class TestGetAuthorityForImpact:
    """Test get_authority_for_impact method."""

    @pytest.mark.asyncio
    async def test_low_impact_requires_low_authority(
        self, db_session: AsyncSession
    ) -> None:
        """RED: LOW impact should require LOW authority."""
        # Arrange
        service = ApprovalMatrixService(db_session)

        # Act
        authority = service.get_authority_for_impact(ImpactLevel.LOW)

        # Assert
        assert authority == "LOW"

    @pytest.mark.asyncio
    async def test_medium_impact_requires_medium_authority(
        self, db_session: AsyncSession
    ) -> None:
        """RED: MEDIUM impact should require MEDIUM authority."""
        # Arrange
        service = ApprovalMatrixService(db_session)

        # Act
        authority = service.get_authority_for_impact(ImpactLevel.MEDIUM)

        # Assert
        assert authority == "MEDIUM"

    @pytest.mark.asyncio
    async def test_high_impact_requires_high_authority(
        self, db_session: AsyncSession
    ) -> None:
        """RED: HIGH impact should require HIGH authority."""
        # Arrange
        service = ApprovalMatrixService(db_session)

        # Act
        authority = service.get_authority_for_impact(ImpactLevel.HIGH)

        # Assert
        assert authority == "HIGH"

    @pytest.mark.asyncio
    async def test_critical_impact_requires_critical_authority(
        self, db_session: AsyncSession
    ) -> None:
        """RED: CRITICAL impact should require CRITICAL authority."""
        # Arrange
        service = ApprovalMatrixService(db_session)

        # Act
        authority = service.get_authority_for_impact(ImpactLevel.CRITICAL)

        # Assert
        assert authority == "CRITICAL"

    @pytest.mark.asyncio
    async def test_invalid_impact_raises_error(self, db_session: AsyncSession) -> None:
        """RED: Invalid impact level should raise ValueError."""
        # Arrange
        service = ApprovalMatrixService(db_session)

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid impact level"):
            service.get_authority_for_impact("INVALID")


class TestCanApprove:
    """Test can_approve method."""

    @pytest.mark.asyncio
    async def test_admin_can_approve_critical_impact(
        self, db_session: AsyncSession
    ) -> None:
        """RED: Admin should be able to approve CRITICAL impact."""
        # Arrange
        service = ApprovalMatrixService(db_session)
        admin = User(
            user_id=uuid4(),
            email="admin@example.com",
            hashed_password="hash",
            full_name="Admin User",
            role="admin",
            is_active=True,
            created_by=uuid4(),
        )
        db_session.add(admin)
        await db_session.flush()

        change_order = ChangeOrder(
            change_order_id=uuid4(),
            code="CO-001",
            project_id=uuid4(),
            title="Test Change",
            status="Submitted",
            impact_level=ImpactLevel.CRITICAL,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Act
        can_approve = await service.can_approve(admin, change_order)

        # Assert
        assert can_approve is True

    @pytest.mark.asyncio
    async def test_viewer_cannot_approve_critical_impact(
        self, db_session: AsyncSession
    ) -> None:
        """RED: Viewer should not be able to approve CRITICAL impact."""
        # Arrange
        service = ApprovalMatrixService(db_session)
        viewer = User(
            user_id=uuid4(),
            email="viewer@example.com",
            hashed_password="hash",
            full_name="Viewer User",
            role="viewer",
            is_active=True,
            created_by=uuid4(),
        )
        db_session.add(viewer)
        await db_session.flush()

        change_order = ChangeOrder(
            change_order_id=uuid4(),
            code="CO-001",
            project_id=uuid4(),
            title="Test Change",
            status="Submitted",
            impact_level=ImpactLevel.CRITICAL,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Act
        can_approve = await service.can_approve(viewer, change_order)

        # Assert
        assert can_approve is False

    @pytest.mark.asyncio
    async def test_manager_can_approve_medium_impact(
        self, db_session: AsyncSession
    ) -> None:
        """RED: Manager should be able to approve MEDIUM impact."""
        # Arrange
        service = ApprovalMatrixService(db_session)
        manager = User(
            user_id=uuid4(),
            email="manager@example.com",
            hashed_password="hash",
            full_name="Manager User",
            role="manager",
            is_active=True,
            created_by=uuid4(),
        )
        db_session.add(manager)
        await db_session.flush()

        change_order = ChangeOrder(
            change_order_id=uuid4(),
            code="CO-001",
            project_id=uuid4(),
            title="Test Change",
            status="Submitted",
            impact_level=ImpactLevel.MEDIUM,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Act
        can_approve = await service.can_approve(manager, change_order)

        # Assert
        assert can_approve is True

    @pytest.mark.asyncio
    async def test_inactive_user_cannot_approve(self, db_session: AsyncSession) -> None:
        """RED: Inactive user should not be able to approve regardless of role."""
        # Arrange
        service = ApprovalMatrixService(db_session)
        admin = User(
            user_id=uuid4(),
            email="admin@example.com",
            hashed_password="hash",
            full_name="Admin User",
            role="admin",
            is_active=False,  # Inactive
            created_by=uuid4(),
        )
        db_session.add(admin)
        await db_session.flush()

        change_order = ChangeOrder(
            change_order_id=uuid4(),
            code="CO-001",
            project_id=uuid4(),
            title="Test Change",
            status="Submitted",
            impact_level=ImpactLevel.LOW,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Act
        can_approve = await service.can_approve(admin, change_order)

        # Assert
        assert can_approve is False


class TestGetApproverForImpact:
    """Test get_approver_for_impact method."""

    @pytest.mark.asyncio
    async def test_get_approver_for_low_impact(self, db_session: AsyncSession) -> None:
        """RED: LOW impact should return manager-level approver."""
        # Arrange
        service = ApprovalMatrixService(db_session)

        # Create a manager (HIGH authority can approve LOW)
        manager = User(
            user_id=uuid4(),
            email="manager@example.com",
            hashed_password="hash",
            full_name="Manager User",
            role="manager",
            is_active=True,
            created_by=uuid4(),
        )
        db_session.add(manager)

        # Create a viewer (LOW authority)
        viewer = User(
            user_id=uuid4(),
            email="viewer@example.com",
            hashed_password="hash",
            full_name="Viewer User",
            role="viewer",
            is_active=True,
            created_by=uuid4(),
        )
        db_session.add(viewer)

        await db_session.flush()

        # Act
        approver_id = await service.get_approver_for_impact(uuid4(), ImpactLevel.LOW)

        # Assert - should return an active user with sufficient authority
        assert approver_id is not None
        assert isinstance(approver_id, UUID)

    @pytest.mark.asyncio
    async def test_get_approver_for_critical_impact(
        self, db_session: AsyncSession
    ) -> None:
        """RED: CRITICAL impact should return admin-level approver."""
        # Arrange
        service = ApprovalMatrixService(db_session)

        # Create an admin (CRITICAL authority)
        admin = User(
            user_id=uuid4(),
            email="admin@example.com",
            hashed_password="hash",
            full_name="Admin User",
            role="admin",
            is_active=True,
            created_by=uuid4(),
        )
        db_session.add(admin)

        await db_session.flush()

        # Act
        approver_id = await service.get_approver_for_impact(
            uuid4(), ImpactLevel.CRITICAL
        )

        # Assert
        assert approver_id is not None
        assert isinstance(approver_id, UUID)

    @pytest.mark.asyncio
    async def test_get_approver_returns_none_when_no_eligible_users(
        self, db_session: AsyncSession
    ) -> None:
        """RED: Should return None when no eligible approvers exist."""
        # Arrange
        service = ApprovalMatrixService(db_session)

        # No users in database
        await db_session.flush()

        # Act
        approver_id = await service.get_approver_for_impact(uuid4(), ImpactLevel.HIGH)

        # Assert
        assert approver_id is None


class TestGetApprovalInfo:
    """Test get_approval_info method."""

    @pytest.mark.asyncio
    async def test_get_approval_info_for_pending_change_order(
        self, db_session: AsyncSession
    ) -> None:
        """RED: Get complete approval information for a change order."""
        # Arrange
        service = ApprovalMatrixService(db_session)

        # Create an admin user
        admin = User(
            user_id=uuid4(),
            email="admin@example.com",
            hashed_password="hash",
            full_name="Admin User",
            role="admin",
            is_active=True,
            created_by=uuid4(),
        )
        db_session.add(admin)
        await db_session.flush()

        # Create a change order
        change_order = ChangeOrder(
            change_order_id=uuid4(),
            code="CO-001",
            project_id=uuid4(),
            title="Test Change",
            description="Test description",
            status="Submitted",
            impact_level=ImpactLevel.HIGH,
            assigned_approver_id=admin.id,  # Use admin.id (PK) not user_id for FK
            sla_assigned_at=datetime.now(UTC),
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Act
        approval_info = await service.get_approval_info(
            change_order.change_order_id, admin
        )

        # Assert
        assert approval_info is not None
        assert approval_info["change_order_id"] == change_order.change_order_id
        assert approval_info["impact_level"] == ImpactLevel.HIGH
        assert approval_info["required_authority"] == "HIGH"
        assert "can_approve" in approval_info
        assert "user_authority" in approval_info
        assert approval_info["user_authority"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_get_approval_info_returns_none_for_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """RED: Should return None when change order not found."""
        # Arrange
        service = ApprovalMatrixService(db_session)
        user = User(
            user_id=uuid4(),
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User",
            role="viewer",
            is_active=True,
            created_by=uuid4(),
        )

        # Act
        approval_info = await service.get_approval_info(uuid4(), user)

        # Assert
        assert approval_info is None
