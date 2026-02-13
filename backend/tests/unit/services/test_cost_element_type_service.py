"""Unit tests for Cost Element Type Service."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.cost_element_type import CostElementType
from app.models.schemas.cost_element_type import (
    CostElementTypeCreate,
    CostElementTypeUpdate,
)
from app.models.schemas.department import DepartmentCreate
from app.services.cost_element_type_service import CostElementTypeService
from app.services.department import DepartmentService


class TestCostElementTypeServiceCreate:
    """Test CostElementTypeService.create() method."""

    @pytest.mark.asyncio
    async def test_create_cost_element_type_success(
        self, db_session: AsyncSession
    ) -> None:
        """Test successfully creating a cost element type."""
        # Arrange - Create a department first
        dept_service = DepartmentService(db_session)
        dept_in = DepartmentCreate(
            name="Mechanical Engineering", code="MECH", is_active=True
        )
        dept = await dept_service.create_department(dept_in, actor_id=uuid4())

        # Create cost element type
        service = CostElementTypeService(db_session)
        type_in = CostElementTypeCreate(
            code="MECH-INST",
            name="Mechanical Installation",
            description="Mechanical installation work",
            department_id=dept.department_id,
        )
        actor_id = uuid4()

        # Act
        created_type = await service.create(type_in, actor_id=actor_id)

        # Assert
        assert created_type is not None
        assert created_type.code == "MECH-INST"
        assert created_type.name == "Mechanical Installation"
        assert created_type.department_id == dept.department_id
        assert created_type.cost_element_type_id is not None
        assert created_type.created_by == actor_id

    @pytest.mark.asyncio
    async def test_create_cost_element_type_tracks_actor(
        self, db_session: AsyncSession
    ) -> None:
        """Test that cost element type creation tracks the actor_id."""
        # Arrange
        dept_service = DepartmentService(db_session)
        dept_in = DepartmentCreate(name="Electrical", code="ELEC", is_active=True)
        dept = await dept_service.create_department(dept_in, actor_id=uuid4())

        service = CostElementTypeService(db_session)
        type_in = CostElementTypeCreate(
            code="ELEC-INST",
            name="Electrical Installation",
            department_id=dept.department_id,
        )
        actor_id = uuid4()

        # Act
        created_type = await service.create(type_in, actor_id=actor_id)

        # Assert - created_by should match actor_id
        assert created_type.created_by == actor_id

        # Verify at database level
        stmt = select(CostElementType).where(CostElementType.id == created_type.id)
        db_record = (await db_session.execute(stmt)).scalar_one()
        assert db_record.created_by == actor_id


class TestCostElementTypeServiceUpdate:
    """Test CostElementTypeService.update() method."""

    @pytest.mark.asyncio
    async def test_update_creates_new_version(self, db_session: AsyncSession) -> None:
        """Test updating a cost element type creates a new version."""
        # Arrange
        dept_service = DepartmentService(db_session)
        dept_in = DepartmentCreate(name="Software", code="SW", is_active=True)
        dept = await dept_service.create_department(dept_in, actor_id=uuid4())

        service = CostElementTypeService(db_session)
        type_in = CostElementTypeCreate(
            code="SW-DEV",
            name="Software Development",
            department_id=dept.department_id,
        )
        v1 = await service.create(type_in, actor_id=uuid4())
        type_id = v1.cost_element_type_id
        v1_id = v1.id  # Capture ID before update

        # Act - Update the name
        update_in = CostElementTypeUpdate(name="Software Development & Testing")
        actor_id_2 = uuid4()
        v2 = await service.update(type_id, update_in, actor_id=actor_id_2)

        # Assert
        await db_session.refresh(v2)  # Ensure v2 is loaded
        assert v2.id != v1_id  # New version has different row ID
        assert v2.cost_element_type_id == type_id  # Same root ID
        assert v2.name == "Software Development & Testing"
        assert v2.code == "SW-DEV"  # Unchanged field persists
        assert v2.created_by == actor_id_2  # New version tracks new actor

        # Verify old version still exists in DB (closed)
        stmt = select(CostElementType).where(CostElementType.id == v1_id)
        old_version = (await db_session.execute(stmt)).scalar_one()
        assert old_version.name == "Software Development"


class TestCostElementTypeServiceDelete:
    """Test CostElementTypeService.soft_delete() method."""

    @pytest.mark.asyncio
    async def test_soft_delete_cost_element_type(
        self, db_session: AsyncSession
    ) -> None:
        """Test soft deleting a cost element type."""
        # Arrange
        dept_service = DepartmentService(db_session)
        dept_in = DepartmentCreate(name="Operations", code="OPS", is_active=True)
        dept = await dept_service.create_department(dept_in, actor_id=uuid4())

        service = CostElementTypeService(db_session)
        type_in = CostElementTypeCreate(
            code="OPS-MAINT",
            name="Operations Maintenance",
            department_id=dept.department_id,
        )
        created_type = await service.create(type_in, actor_id=uuid4())
        type_id = created_type.cost_element_type_id

        # Act
        actor_id_delete = uuid4()
        await service.soft_delete(type_id, actor_id=actor_id_delete)

        # Assert - Query directly to get the soft-deleted version
        # (get_by_id filters out deleted items)
        stmt = (
            select(CostElementType)
            .where(CostElementType.cost_element_type_id == type_id)
            .order_by(CostElementType.valid_time.desc())
            .limit(1)
        )
        deleted = (await db_session.execute(stmt)).scalar_one()
        assert deleted is not None
        assert deleted.is_deleted is True
        assert deleted.deleted_by == actor_id_delete
