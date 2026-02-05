"""Unit tests for ChangeOrderService."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.change_order import ChangeOrderCreate, ChangeOrderUpdate
from app.services.change_order_service import ChangeOrderService


class TestChangeOrderServiceCreate:
    """Test ChangeOrderService.create_change_order() method."""

    @pytest.mark.asyncio
    async def test_create_change_order_success(self, db_session: AsyncSession) -> None:
        """Test successfully creating a change order.

        Acceptance Criteria:
        - Change Order created with Draft status
        - Correct project_id association
        - All metadata fields populated
        - Auto-branch created (co-{code})
        """
        # Arrange
        service = ChangeOrderService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        change_order_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-2026-001",
            title="Add Additional Safety Sensors",
            description="Add emergency stop buttons to all conveyor systems",
            justification="Updated safety regulations require additional emergency stops",
            effective_date=datetime(2026, 2, 1),
        )

        # Act
        created_co = await service.create_change_order(
            change_order_in, actor_id=actor_id
        )

        # Assert
        assert created_co is not None
        assert created_co.project_id == project_id
        assert created_co.code == "CO-2026-001"
        assert created_co.title == "Add Additional Safety Sensors"
        assert created_co.status == "Draft"
        assert created_co.branch == "main"  # Initial version on main
        assert created_co.created_by == actor_id
        # change_order_id should be a UUID (auto-generated)
        assert created_co.change_order_id is not None

    @pytest.mark.asyncio
    async def test_create_change_order_control_date_single_row(
        self, db_session: AsyncSession
    ) -> None:
        """Test creating a change order with explicit control_date creates single row.

        Verifies:
        - Only 1 row created (no auto-branch duplication)
        - valid_time starts at control_date
        """
        # Arrange
        from zoneinfo import ZoneInfo

        from sqlalchemy import text

        service = ChangeOrderService(db_session)
        project_id = uuid4()
        actor_id = uuid4()
        control_date = datetime(2025, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

        co_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-TIME-TEST",
            title="Time Test",
            control_date=control_date,
        )

        # Act
        created_co = await service.create_change_order(
            co_in, actor_id=actor_id
        )

        # Assert
        stmt = text(
            "SELECT branch, valid_time FROM change_orders WHERE change_order_id = :co_id"
        )
        result = await db_session.execute(stmt, {"co_id": created_co.change_order_id})
        rows = result.fetchall()

        assert len(rows) == 1
        assert rows[0].branch == "main"
        assert rows[0].valid_time.lower == control_date


class TestChangeOrderServiceUpdate:
    """Test ChangeOrderService.update_change_order() method."""

    @pytest.mark.asyncio
    async def test_update_change_order_metadata(self, db_session: AsyncSession) -> None:
        """Test updating change order metadata creates new version.

        Acceptance Criteria:
        - Update creates new version
        - Same root change_order_id
        - Metadata fields updated
        """
        # Arrange
        service = ChangeOrderService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        # Create initial CO
        co_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-2026-001",
            title="Original Title",
            description="Original description",
            justification="Original justification",
            effective_date=datetime(2026, 2, 1),
        )

        v1 = await service.create_change_order(co_in, actor_id=actor_id)
        root_id = v1.change_order_id
        v1_id = v1.id

        # Act - Update metadata
        update_in = ChangeOrderUpdate(
            title="Updated Title",
            description="Updated description",
        )
        v2 = await service.update_change_order(root_id, update_in, actor_id=actor_id)

        # Assert
        assert v2.id != v1_id  # New version ID
        assert v2.change_order_id == root_id  # Same root ID
        assert v2.title == "Updated Title"
        assert v2.description == "Updated description"
        assert v2.justification == "Original justification"  # Unchanged


class TestChangeOrderServiceDelete:
    """Test ChangeOrderService.delete_change_order() method."""

    @pytest.mark.asyncio
    async def test_delete_change_order_soft_deletes(
        self, db_session: AsyncSession
    ) -> None:
        """Test deleting a change order soft-deletes current version.

        Acceptance Criteria:
        - Soft delete performed
        - CO marked as deleted
        - Can still retrieve history
        """
        # Arrange
        service = ChangeOrderService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        co_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-2026-001",
            title="To Delete",
            description="This will be deleted",
            justification="Testing",
            effective_date=datetime(2026, 2, 1),
        )

        v1 = await service.create_change_order(co_in, actor_id=actor_id)
        root_id = v1.change_order_id

        # Act
        await service.delete_change_order(root_id, actor_id=actor_id)

        # Assert: Deleted COs should not appear in list
        cos, total = await service.get_change_orders(project_id=project_id)
        assert not any(co.change_order_id == root_id for co in cos)


class TestChangeOrderServiceGetCurrent:
    """Test ChangeOrderService.get_current() method with temporal queries."""

    @pytest.mark.asyncio
    async def test_get_current_with_future_control_date(
        self, db_session: AsyncSession
    ) -> None:
        """Test that get_current() finds Change Order with future control_date.

        Regression test for 404 error after creating Change Order with future effective_date.

        When a Change Order is created with a future control_date (via effective_date),
        get_current() should still find it using the open upper bound pattern.

        Acceptance Criteria:
        - Change Order with future control_date is created successfully
        - get_current() returns the Change Order (no 404)
        - get_current_by_code() also returns the Change Order
        """
        from datetime import timedelta, timezone

        # Arrange
        service = ChangeOrderService(db_session)
        project_id = uuid4()
        user_id = uuid4()

        # Create Change Order with future control_date
        future_date = datetime.now(timezone.utc) + timedelta(days=90)
        co_in = ChangeOrderCreate(
            code="CO-2026-FUTURE",
            project_id=project_id,
            title="Future CO",
            control_date=future_date,  # Future date
            status="Draft",
        )

        # Act
        created = await service.create_change_order(co_in, user_id)
        await db_session.commit()

        # Assert - Verify get_current finds it (using open upper bound pattern)
        found = await service.get_current(created.change_order_id, branch="main")
        assert found is not None
        assert found.code == "CO-2026-FUTURE"
        assert found.change_order_id == created.change_order_id

        # Assert - Verify get_current_by_code also works
        found_by_code = await service.get_current_by_code("CO-2026-FUTURE", branch="main")
        assert found_by_code is not None
        assert found_by_code.change_order_id == created.change_order_id

    @pytest.mark.asyncio
    async def test_get_current_with_past_control_date(
        self, db_session: AsyncSession
    ) -> None:
        """Test that get_current() finds Change Order with past control_date.

        Acceptance Criteria:
        - Change Order with past control_date is created successfully
        - get_current() returns the Change Order
        """
        from datetime import timedelta, timezone

        # Arrange
        service = ChangeOrderService(db_session)
        project_id = uuid4()
        user_id = uuid4()

        # Create Change Order with past control_date
        past_date = datetime.now(timezone.utc) - timedelta(days=30)
        co_in = ChangeOrderCreate(
            code="CO-2026-PAST",
            project_id=project_id,
            title="Past CO",
            control_date=past_date,  # Past date
            status="Draft",
        )

        # Act
        created = await service.create_change_order(co_in, user_id)
        await db_session.commit()

        # Assert
        found = await service.get_current(created.change_order_id, branch="main")
        assert found is not None
        assert found.code == "CO-2026-PAST"

    @pytest.mark.asyncio
    async def test_get_current_returns_latest_version(
        self, db_session: AsyncSession
    ) -> None:
        """Test that get_current() returns the latest version when multiple exist.

        Acceptance Criteria:
        - Initial version is created
        - Update creates a new version
        - get_current() returns the latest version
        """
        from datetime import timedelta, timezone

        # Arrange
        service = ChangeOrderService(db_session)
        project_id = uuid4()
        user_id = uuid4()

        # Create initial version
        co_in1 = ChangeOrderCreate(
            code="CO-2026-MULTI",
            project_id=project_id,
            title="Initial",
            control_date=datetime.now(timezone.utc) - timedelta(days=10),
            status="Draft",
        )
        created1 = await service.create_change_order(co_in1, user_id)
        initial_id = created1.id
        co_id = created1.change_order_id  # Store ID before commit

        # Act - Update to create new version
        co_update = ChangeOrderUpdate(
            title="Updated Title",
            control_date=datetime.now(timezone.utc),
        )
        updated = await service.update_change_order(
            co_id,
            co_update,
            user_id,
            branch="main",
        )
        await db_session.commit()

        # Assert - get_current returns the updated version
        found = await service.get_current(co_id, branch="main")
        assert found is not None
        assert found.title == "Updated Title"
        assert found.id != initial_id  # Different version ID
