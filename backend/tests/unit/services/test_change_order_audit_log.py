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
            status="draft",
        )
        co = await service.create_change_order(co_create, actor_id=uuid4())
        # Capture ID before entity might be expired
        co_id = co.change_order_id

        # Update status with comment - should create audit log entry
        comment = "Ready for review"
        co_update = ChangeOrderUpdate(
            status="submitted_for_approval",
            comment=comment,
        )
        updated_co = await service.update_change_order(
            co_id, co_update, actor_id=uuid4()
        )

        # Verify the update succeeded
        assert updated_co.status == "submitted_for_approval"

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
        assert audit_entry.old_status == "draft"
        assert audit_entry.new_status == "submitted_for_approval"
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
            status="draft",
        )
        co = await service.create_change_order(co_create, actor_id=uuid4())
        # Capture ID before entity might be expired
        co_id = co.change_order_id

        # Update status WITHOUT comment
        co_update = ChangeOrderUpdate(status="submitted_for_approval")
        updated_co = await service.update_change_order(
            co_id, co_update, actor_id=uuid4()
        )

        # Verify the update succeeded
        assert updated_co.status == "submitted_for_approval"

        # Verify audit entry exists with null comment
        stmt = select(ChangeOrderAuditLog).where(
            ChangeOrderAuditLog.change_order_id == co_id,
            ChangeOrderAuditLog.old_status == "draft",
            ChangeOrderAuditLog.new_status == "submitted_for_approval",
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
            status="draft",
        )
        co = await service.create_change_order(co_create, actor_id=actor_id)
        # Capture ID before entity might be expired
        co_id = co.change_order_id

        # First transition: Draft -> submitted_for_approval
        await service.update_change_order(
            co_id,
            ChangeOrderUpdate(
                status="submitted_for_approval", comment="Ready for review"
            ),
            actor_id=actor_id,
        )

        # Second transition: submitted_for_approval -> under_review
        await service.update_change_order(
            co_id,
            ChangeOrderUpdate(status="under_review", comment="Starting review"),
            actor_id=actor_id,
        )

        # Third transition: under_review -> Approved
        await service.update_change_order(
            co_id,
            ChangeOrderUpdate(status="approved", comment="Looks good, approved"),
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
        assert ("draft", "submitted_for_approval") in transitions
        assert ("submitted_for_approval", "under_review") in transitions
        assert ("under_review", "approved") in transitions

        # Verify comments
        comments = [e.comment for e in audit_entries]
        assert "Ready for review" in comments
        assert "Starting review" in comments
        assert "Looks good, approved" in comments
