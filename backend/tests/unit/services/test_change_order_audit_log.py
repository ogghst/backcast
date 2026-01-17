"""Tests for Change Order audit log and comment storage.

Test module for verifying that status transition comments are stored in the audit trail.
"""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order_audit_log import ChangeOrderAuditLog
from app.models.schemas.change_order import ChangeOrderCreate, ChangeOrderUpdate
from app.services.change_order_service import ChangeOrderService


class TestChangeOrderAuditLog:
    """Test suite for Change Order audit log and comment storage."""

    @pytest.mark.asyncio
    async def test_status_transition_with_comment_succeeds(
        self, db_session: AsyncSession
    ):
        """Test that status transition with comment succeeds (audit log is created)."""
        service = ChangeOrderService(db_session)

        # Create a Change Order
        co_create = ChangeOrderCreate(
            code="CO-001",
            project_id=uuid4(),
            title="Test Change Order",
            status="Draft",
        )
        co = await service.create_change_order(co_create, actor_id=uuid4())
        # Capture ID before entity might be expired
        co_id = co.change_order_id

        # Update status with comment - should create audit log entry
        comment = "Ready for review"
        co_update = ChangeOrderUpdate(
            status="Submitted for Approval",
            comment=comment,
        )
        updated_co = await service.update_change_order(
            co_id, co_update, actor_id=uuid4()
        )

        # Verify the update succeeded
        assert updated_co.status == "Submitted for Approval"

        # Query to verify audit log entry was created
        # Note: We use a fresh query to avoid session state issues
        stmt = select(ChangeOrderAuditLog).where(
            ChangeOrderAuditLog.change_order_id == co_id,
            ChangeOrderAuditLog.comment == comment,
        )

        result = await db_session.execute(stmt)
        audit_entry = result.scalar_one_or_none()

        # Verify audit log entry was created with correct data
        assert audit_entry is not None
        assert audit_entry.old_status == "Draft"
        assert audit_entry.new_status == "Submitted for Approval"
        assert audit_entry.comment == comment

    @pytest.mark.asyncio
    async def test_status_transition_without_comment_succeeds(
        self, db_session: AsyncSession
    ):
        """Test that status transition without comment succeeds (audit log has null comment)."""
        service = ChangeOrderService(db_session)

        # Create a Change Order
        co_create = ChangeOrderCreate(
            code="CO-002",
            project_id=uuid4(),
            title="Test Change Order 2",
            status="Draft",
        )
        co = await service.create_change_order(co_create, actor_id=uuid4())
        # Capture ID before entity might be expired
        co_id = co.change_order_id

        # Update status WITHOUT comment
        co_update = ChangeOrderUpdate(status="Submitted for Approval")
        updated_co = await service.update_change_order(
            co_id, co_update, actor_id=uuid4()
        )

        # Verify the update succeeded
        assert updated_co.status == "Submitted for Approval"

        # Verify audit entry exists with null comment
        stmt = select(ChangeOrderAuditLog).where(
            ChangeOrderAuditLog.change_order_id == co_id,
            ChangeOrderAuditLog.old_status == "Draft",
            ChangeOrderAuditLog.new_status == "Submitted for Approval",
        )

        result = await db_session.execute(stmt)
        audit_entry = result.scalar_one_or_none()

        assert audit_entry is not None
        assert audit_entry.comment is None

    @pytest.mark.asyncio
    async def test_multiple_status_transitions_create_audit_trail(
        self, db_session: AsyncSession
    ):
        """Test that multiple status transitions create complete audit trail."""
        service = ChangeOrderService(db_session)
        actor_id = uuid4()

        # Create a Change Order
        co_create = ChangeOrderCreate(
            code="CO-003",
            project_id=uuid4(),
            title="Test Change Order 3",
            status="Draft",
        )
        co = await service.create_change_order(co_create, actor_id=actor_id)
        # Capture ID before entity might be expired
        co_id = co.change_order_id

        # First transition: Draft -> Submitted for Approval
        await service.update_change_order(
            co_id,
            ChangeOrderUpdate(
                status="Submitted for Approval", comment="Ready for review"
            ),
            actor_id=actor_id,
        )

        # Second transition: Submitted for Approval -> Under Review
        await service.update_change_order(
            co_id,
            ChangeOrderUpdate(status="Under Review", comment="Starting review"),
            actor_id=actor_id,
        )

        # Third transition: Under Review -> Approved
        await service.update_change_order(
            co_id,
            ChangeOrderUpdate(status="Approved", comment="Looks good, approved"),
            actor_id=actor_id,
        )

        # Verify audit trail has all three transitions
        stmt = select(ChangeOrderAuditLog).where(
            ChangeOrderAuditLog.change_order_id == co_id
        )

        result = await db_session.execute(stmt)
        audit_entries = list(result.scalars().all())

        # Should have 3 audit entries for the 3 status transitions
        assert len(audit_entries) == 3

        # Verify status transitions
        transitions = [(e.old_status, e.new_status) for e in audit_entries]
        assert ("Draft", "Submitted for Approval") in transitions
        assert ("Submitted for Approval", "Under Review") in transitions
        assert ("Under Review", "Approved") in transitions

        # Verify comments
        comments = [e.comment for e in audit_entries]
        assert "Ready for review" in comments
        assert "Starting review" in comments
        assert "Looks good, approved" in comments
