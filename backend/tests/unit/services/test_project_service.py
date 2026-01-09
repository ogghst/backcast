"""Unit tests for ProjectService."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.project import ProjectCreate, ProjectUpdate
from app.services.project import ProjectService


class TestProjectServiceCreate:
    """Test ProjectService.create_project() method."""

    @pytest.mark.asyncio
    async def test_create_project_success(self, db_session: AsyncSession) -> None:
        """Test successfully creating a project."""
        service = ProjectService(db_session)
        project_in = ProjectCreate(
            name="Alpha Project",
            code="ALPHA",
            budget=Decimal("100000.00"),
            status="Draft",
        )

        # Act
        created_project = await service.create_project(project_in, actor_id=uuid4())

        # Assert
        assert created_project is not None
        assert created_project.name == "Alpha Project"
        assert created_project.code == "ALPHA"
        assert created_project.budget == Decimal("100000.00")


class TestProjectServiceGetProjects:
    """Test ProjectService.get_projects() method with search and filters."""

    @pytest.mark.asyncio
    async def test_get_projects_basic_pagination(
        self, db_session: AsyncSession
    ) -> None:
        """Test basic pagination without search or filters."""
        service = ProjectService(db_session)

        # Create test projects
        for i in range(5):
            await service.create_project(
                ProjectCreate(
                    name=f"Project {i}",
                    code=f"PROJ{i}",
                    budget=Decimal("10000.00"),
                    status="Active",
                ),
                actor_id=uuid4(),
            )

        # Act
        projects, total = await service.get_projects(skip=0, limit=10)

        # Assert
        assert len(projects) == 5
        assert total == 5

    @pytest.mark.asyncio
    async def test_get_projects_with_search(self, db_session: AsyncSession) -> None:
        """Test searching projects by code or name."""
        service = ProjectService(db_session)

        # Create test projects
        await service.create_project(
            ProjectCreate(
                name="Alpha Project", code="ALPHA", budget=Decimal("10000.00")
            ),
            actor_id=uuid4(),
        )
        await service.create_project(
            ProjectCreate(name="Beta Project", code="BETA", budget=Decimal("20000.00")),
            actor_id=uuid4(),
        )
        await service.create_project(
            ProjectCreate(
                name="Gamma Project", code="GAMMA", budget=Decimal("30000.00")
            ),
            actor_id=uuid4(),
        )

        # Act: Search by name
        projects, total = await service.get_projects(search="Alpha")

        # Assert
        assert len(projects) == 1
        assert total == 1
        assert projects[0].name == "Alpha Project"

        # Act: Search by code
        projects, total = await service.get_projects(search="BETA")

        # Assert
        assert len(projects) == 1
        assert total == 1
        assert projects[0].code == "BETA"

        # Act: Search partial match
        projects, total = await service.get_projects(search="Project")

        # Assert
        assert len(projects) == 3
        assert total == 3

    @pytest.mark.asyncio
    async def test_get_projects_with_status_filter(
        self, db_session: AsyncSession
    ) -> None:
        """Test filtering projects by status."""
        service = ProjectService(db_session)

        # Create test projects with different statuses
        await service.create_project(
            ProjectCreate(
                name="Active Project 1",
                code="ACT1",
                budget=Decimal("10000.00"),
                status="Active",
            ),
            actor_id=uuid4(),
        )
        await service.create_project(
            ProjectCreate(
                name="Active Project 2",
                code="ACT2",
                budget=Decimal("20000.00"),
                status="Active",
            ),
            actor_id=uuid4(),
        )
        await service.create_project(
            ProjectCreate(
                name="Draft Project",
                code="DRAFT1",
                budget=Decimal("30000.00"),
                status="Draft",
            ),
            actor_id=uuid4(),
        )

        # Act: Filter by Active status
        projects, total = await service.get_projects(filters="status:Active")

        # Assert
        assert len(projects) == 2
        assert total == 2
        assert all(p.status == "Active" for p in projects)

        # Act: Filter by Draft status
        projects, total = await service.get_projects(filters="status:Draft")

        # Assert
        assert len(projects) == 1
        assert total == 1
        assert projects[0].status == "Draft"

    @pytest.mark.asyncio
    async def test_get_projects_with_multiple_status_filter(
        self, db_session: AsyncSession
    ) -> None:
        """Test filtering projects by multiple status values (IN clause)."""
        service = ProjectService(db_session)

        # Create test projects
        await service.create_project(
            ProjectCreate(
                name="Active Project",
                code="ACT",
                budget=Decimal("10000.00"),
                status="Active",
            ),
            actor_id=uuid4(),
        )
        await service.create_project(
            ProjectCreate(
                name="Draft Project",
                code="DRAFT",
                budget=Decimal("20000.00"),
                status="Draft",
            ),
            actor_id=uuid4(),
        )
        await service.create_project(
            ProjectCreate(
                name="Closed Project",
                code="CLOSED",
                budget=Decimal("30000.00"),
                status="Closed",
            ),
            actor_id=uuid4(),
        )

        # Act: Filter by Active OR Draft
        projects, total = await service.get_projects(filters="status:Active,Draft")

        # Assert
        assert len(projects) == 2
        assert total == 2
        assert {p.status for p in projects} == {"Active", "Draft"}

    @pytest.mark.asyncio
    async def test_get_projects_with_search_and_filter(
        self, db_session: AsyncSession
    ) -> None:
        """Test combining search and filters."""
        service = ProjectService(db_session)

        # Create test projects
        await service.create_project(
            ProjectCreate(
                name="Alpha Active",
                code="ALPHA",
                budget=Decimal("10000.00"),
                status="Active",
            ),
            actor_id=uuid4(),
        )
        await service.create_project(
            ProjectCreate(
                name="Alpha Draft",
                code="ALPHA2",
                budget=Decimal("20000.00"),
                status="Draft",
            ),
            actor_id=uuid4(),
        )
        await service.create_project(
            ProjectCreate(
                name="Beta Active",
                code="BETA",
                budget=Decimal("30000.00"),
                status="Active",
            ),
            actor_id=uuid4(),
        )

        # Act: Search for "Alpha" AND filter by "Active"
        projects, total = await service.get_projects(
            search="Alpha", filters="status:Active"
        )

        # Assert
        assert len(projects) == 1
        assert total == 1
        assert projects[0].name == "Alpha Active"

    @pytest.mark.asyncio
    async def test_get_projects_with_sorting(self, db_session: AsyncSession) -> None:
        """Test sorting projects by different fields."""
        service = ProjectService(db_session)

        # Create test projects
        await service.create_project(
            ProjectCreate(
                name="Charlie", code="C", budget=Decimal("30000.00"), status="Active"
            ),
            actor_id=uuid4(),
        )
        await service.create_project(
            ProjectCreate(
                name="Alpha", code="A", budget=Decimal("10000.00"), status="Active"
            ),
            actor_id=uuid4(),
        )
        await service.create_project(
            ProjectCreate(
                name="Beta", code="B", budget=Decimal("20000.00"), status="Active"
            ),
            actor_id=uuid4(),
        )

        # Act: Sort by name ascending
        projects, total = await service.get_projects(
            sort_field="name", sort_order="asc"
        )

        # Assert
        assert len(projects) == 3
        assert [p.name for p in projects] == ["Alpha", "Beta", "Charlie"]

        # Act: Sort by name descending
        projects, total = await service.get_projects(
            sort_field="name", sort_order="desc"
        )

        # Assert
        assert [p.name for p in projects] == ["Charlie", "Beta", "Alpha"]

        # Act: Sort by code ascending
        projects, total = await service.get_projects(
            sort_field="code", sort_order="asc"
        )

        # Assert
        assert [p.code for p in projects] == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_get_projects_invalid_filter_field_raises_error(
        self, db_session: AsyncSession
    ) -> None:
        """Test that invalid filter field raises ValueError."""
        service = ProjectService(db_session)

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid filter field"):
            await service.get_projects(filters="invalid_field:value")

    @pytest.mark.asyncio
    async def test_get_projects_invalid_sort_field_raises_error(
        self, db_session: AsyncSession
    ) -> None:
        """Test that invalid sort field raises ValueError."""
        service = ProjectService(db_session)

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid sort field"):
            await service.get_projects(sort_field="invalid_field")

    @pytest.mark.asyncio
    async def test_get_projects_pagination_with_filters(
        self, db_session: AsyncSession
    ) -> None:
        """Test pagination works correctly with filters."""
        service = ProjectService(db_session)

        # Create 10 active projects
        for i in range(10):
            await service.create_project(
                ProjectCreate(
                    name=f"Active {i}",
                    code=f"ACT{i}",
                    budget=Decimal("10000.00"),
                    status="Active",
                ),
                actor_id=uuid4(),
            )

        # Create 5 draft projects
        for i in range(5):
            await service.create_project(
                ProjectCreate(
                    name=f"Draft {i}",
                    code=f"DRAFT{i}",
                    budget=Decimal("10000.00"),
                    status="Draft",
                ),
                actor_id=uuid4(),
            )

        # Act: Get first page of Active projects (5 per page)
        projects, total = await service.get_projects(
            skip=0, limit=5, filters="status:Active"
        )

        # Assert
        assert len(projects) == 5
        assert total == 10  # Total active projects

        # Act: Get second page
        projects, total = await service.get_projects(
            skip=5, limit=5, filters="status:Active"
        )

        # Assert
        assert len(projects) == 5
        assert total == 10


class TestProjectServiceUpdate:
    """Test ProjectService.update_project() method."""

    @pytest.mark.asyncio
    async def test_update_project_creates_new_version(
        self, db_session: AsyncSession
    ) -> None:
        """Test updating a project creates a new version."""
        service = ProjectService(db_session)
        project_in = ProjectCreate(
            name="Original Name",
            code="PROJ1",
            budget=Decimal("10000.00"),
            status="Draft",
        )

        # Create initial
        v1 = await service.create_project(project_in, actor_id=uuid4())
        project_id = v1.project_id

        # Act
        update_in = ProjectUpdate(name="Updated Name")
        v2 = await service.update_project(v1.project_id, update_in, actor_id=uuid4())

        # Assert
        await db_session.refresh(v1)
        assert v2.id != v1.id  # New version ID
        assert v2.project_id == project_id  # Same root ID
        assert v2.name == "Updated Name"


class TestProjectServiceDelete:
    """Test ProjectService.delete_project() method."""

    @pytest.mark.asyncio
    async def test_delete_project_soft_deletes(self, db_session: AsyncSession) -> None:
        """Test deleting a project soft-deletes current version."""
        service = ProjectService(db_session)
        project_in = ProjectCreate(
            name="To Delete",
            code="DEL",
            budget=Decimal("10000.00"),
            status="Active",
        )

        # Create
        v1 = await service.create_project(project_in, actor_id=uuid4())
        project_id = v1.project_id

        # Act
        await service.delete_project(project_id, actor_id=uuid4())

        # Assert: Deleted projects should not appear in get_projects
        projects, total = await service.get_projects()
        assert not any(p.project_id == project_id for p in projects)

        # Assert: get_by_code should not return deleted project
        result = await service.get_by_code("DEL")
        assert result is None
