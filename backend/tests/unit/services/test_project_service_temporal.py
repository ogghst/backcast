"""Unit tests for time-travel list operations in ProjectService."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.project import ProjectCreate
from app.services.project import ProjectService


class TestProjectServiceTemporalList:
    """Test ProjectService.get_projects() with as_of parameter."""

    @pytest.mark.asyncio
    async def test_get_projects_as_of_deleted_item(
        self, db_session: AsyncSession
    ) -> None:
        """Test retrieving a deleted project by querying a time before deletion."""
        service = ProjectService(db_session)
        actor_id = uuid4()

        # 1. Create Project at t1
        t1 = datetime.now(UTC) - timedelta(hours=2)
        project_in = ProjectCreate(
            name="Temporal Project",
            code="TEMP01",
            budget=Decimal("10000.00"),
            status="Active",
            control_date=t1,
        )

        # We manually control the creation time using control_date
        project_v1 = await service.create_project(project_in, actor_id=actor_id)
        project_id = project_v1.project_id

        # 2. Delete Project at t3
        t3 = datetime.now(UTC) - timedelta(hours=1)
        await service.delete_project(
            project_id=project_id, actor_id=actor_id, control_date=t3
        )

        # 3. Query at t2 (between t1 and t3) -> Should find it
        t2 = t1 + timedelta(minutes=30)

        # Verify t2 is indeed before t3
        assert t2 < t3

        projects_past, total_past = await service.get_projects(as_of=t2)

        # Assert found
        assert total_past == 1
        assert len(projects_past) == 1
        assert projects_past[0].project_id == project_id
        assert projects_past[0].name == "Temporal Project"

        # 4. Query at t4 (after deletion) -> Should NOT find it
        t4 = datetime.now(UTC)
        projects_future, total_future = await service.get_projects(as_of=t4)

        # Assert not found
        # Note: We filter by checking if our specific project is in the list,
        # as other tests might leave data in DB
        found_future = any(p.project_id == project_id for p in projects_future)
        assert not found_future

        # 5. Query current (no as_of) -> Should NOT find it
        projects_current, _ = await service.get_projects()
        found_current = any(p.project_id == project_id for p in projects_current)
        assert not found_current
