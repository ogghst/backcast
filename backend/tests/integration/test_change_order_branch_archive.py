"""Integration tests for Change Order Branch Archival (E06-U08).

Verifies that Change Order branches can be archived (soft-deleted) after the
Change Order is implemented or rejected, hiding them from active lists while
preserving them for history.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.branch_service import BranchService
from app.services.change_order_service import ChangeOrderService


@pytest.mark.usefixtures("db_session")
class TestChangeOrderBranchArchive:
    """Integration tests for Change Order Branch Archival."""

    @pytest.mark.asyncio
    async def test_archive_implemented_change_order(
        self, db_session: AsyncSession
    ) -> None:
        """Test archiving an implemented Change Order branch.

        Scenario:
        1. Create CO, approve, and merge it (Status: Implemented).
        2. Verify branch 'BR-{code}' is active.
        3. Archive the branch.
        4. Verify branch is hidden from active list.
        5. Verify branch is visible in time-travel query.
        """
        # Arrange
        actor_id = uuid4()
        project_id = uuid4()
        co_id = uuid4()
        co_code = "ARCH-001"
        branch_name = f"BR-{co_code}"

        co_service = ChangeOrderService(db_session)
        branch_service = BranchService(db_session)

        # 1. Create fully implemented CO
        # For speed, we simulate the implemented state by creating it directly
        # and checking the branch implementation separately if needed,
        # but here we mostly care about the Service's state validation logic.

        # However, to test the full flow including branch existence, we should
        # standard creation paths.

        # Create CO (Draft) -> creates branch
        # Create CO (Draft) -> creates branch
        from app.models.schemas.change_order import ChangeOrderCreate

        create_schema = ChangeOrderCreate(
            project_id=project_id,
            code=co_code,
            title="To Be Archived",
            description="Testing Archive",
            status="Draft",
        )

        created_co = await co_service.create_change_order(
            change_order_in=create_schema, actor_id=actor_id
        )
        co_id = created_co.change_order_id

        # Force status to Implemented (skipping full workflow for test isolation)
        # We need the status to be Implemented for the archive method to work.
        # We assume the branch exists because create_change_order created it.

        # Update status directly via internal update to bypass workflow strictly for setup
        # Or just update the DB model directly?
        # Service update is safer to ensure consistency.

        # Actually, let's use the proper service method but bypass workflow checks if possible?
        # Workflow enforces transitions. "Draft" -> "Implemented" is invalid.
        # So we update DB directly for setup speed, OR use proper transitions.
        # Let's use direct DB update to set "Implemented" to test the *Archive* logic specifically.

        co = await co_service.get_current(co_id)
        assert co is not None
        co.status = "Implemented"
        db_session.add(co)
        await db_session.commit()
        await db_session.refresh(co)

        # Verify branch exists and is active
        branch = await branch_service.get_by_name_and_project(branch_name, project_id)
        assert branch is not None
        assert branch.deleted_at is None

        # Capture time before archival
        # Ensure we have a distinct timestamp after creation/update
        import asyncio

        await asyncio.sleep(0.1)
        before_archive = datetime.now(UTC)
        await asyncio.sleep(0.1)

        # Act
        await co_service.archive_change_order_branch(
            change_order_id=co_id, actor_id=actor_id
        )

        # Assert

        # 1. Branch should be soft-deleted (not found by standard get)
        # get_by_name_and_project filters deleted_at is None
        from sqlalchemy.exc import NoResultFound

        with pytest.raises(NoResultFound):
            await branch_service.get_by_name_and_project(branch_name, project_id)

        # 2. Change Order should still exist (not archived itself)
        co_after = await co_service.get_current(co_id)
        assert co_after is not None
        assert co_after.status == "Implemented"

        # 3. Time travel: Branch should be visible in the past
        branch_past = await branch_service.get_by_name_as_of(
            branch_name, project_id, before_archive
        )
        assert branch_past is not None, "Branch should be visible in history"

    @pytest.mark.asyncio
    async def test_archive_active_change_order_fails(
        self, db_session: AsyncSession
    ) -> None:
        """Test that archiving an active (Draft) Change Order fails."""
        # Arrange
        actor_id = uuid4()
        project_id = uuid4()
        co_id = uuid4()
        co_code = "ARCH-002"

        co_service = ChangeOrderService(db_session)

        # Create CO (Draft)
        # Create CO (Draft)
        from app.models.schemas.change_order import ChangeOrderCreate

        create_schema = ChangeOrderCreate(
            project_id=project_id,
            code=co_code,
            title="Active CO",
            description="Should not archive",
            status="Draft",
        )

        created_co = await co_service.create_change_order(
            change_order_in=create_schema, actor_id=actor_id
        )
        co_id = created_co.change_order_id

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot archive active Change Order"):
            await co_service.archive_change_order_branch(
                change_order_id=co_id, actor_id=actor_id
            )
