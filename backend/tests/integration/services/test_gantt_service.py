"""Tests for GanttService."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.department import Department
from app.models.domain.project import Project
from app.models.domain.wbe import WBE
from app.models.schemas.cost_element import CostElementCreate
from app.models.schemas.cost_element_type import CostElementTypeCreate
from app.models.schemas.department import DepartmentCreate
from app.models.schemas.project import ProjectCreate
from app.models.schemas.wbe import WBECreate
from app.services.cost_element_service import CostElementService
from app.services.cost_element_type_service import CostElementTypeService
from app.services.department import DepartmentService
from app.services.gantt_service import GanttService
from app.services.project import ProjectService
from app.services.wbe import WBEService


@pytest.mark.asyncio
async def test_gantt_data_includes_wbes_without_cost_elements(
    db_session: AsyncSession,
) -> None:
    """Test that WBEs without cost elements are included in Gantt data.

    This test ensures the fix for the missing F5 issue, where WBEs with
    no valid cost elements were being filtered out of the Gantt hierarchy.
    """
    actor_id = uuid4()

    # Create Department and Cost Element Type
    dept_service = DepartmentService(db_session)
    dept_in = DepartmentCreate(
        code="TEST-DEPT",
        name="Test Department",
    )
    department = await dept_service.create_department(dept_in, actor_id=actor_id)

    cet_service = CostElementTypeService(db_session)
    cet_in = CostElementTypeCreate(
        code="TEST-TYPE",
        name="Test Type",
        department_id=department.department_id,
    )
    cost_element_type = await cet_service.create(cet_in, actor_id=actor_id)

    # Create Project
    project_service = ProjectService(db_session)
    project_in = ProjectCreate(
        code="TEST-PROJ",
        name="Test Project",
        description="Test project for Gantt",
    )
    project = await project_service.create_project(project_in, actor_id=actor_id)

    # Create WBE hierarchy: F1 -> F2 -> F3
    # F1 will have a cost element
    # F2 will NOT have a cost element (should still appear)
    # F3 will have a cost element
    wbe_service = WBEService(db_session)

    f1_in = WBECreate(
        project_id=project.project_id,
        code="F1",
        name="Fase 1",
        level=1,
    )
    f1 = await wbe_service.create_wbe(f1_in, actor_id=actor_id)

    f2_in = WBECreate(
        project_id=project.project_id,
        parent_wbe_id=f1.wbe_id,
        code="F2",
        name="Fase 2",
        level=2,
    )
    f2 = await wbe_service.create_wbe(f2_in, actor_id=actor_id)

    f3_in = WBECreate(
        project_id=project.project_id,
        parent_wbe_id=f2.wbe_id,
        code="F3",
        name="Fase 3",
        level=3,
    )
    f3 = await wbe_service.create_wbe(f3_in, actor_id=actor_id)

    # Only add cost elements for F1 and F3 (F2 has no cost element)
    ce_service = CostElementService(db_session)

    ce_f1_in = CostElementCreate(
        code="CE-F1",
        name="Cost Element F1",
        wbe_id=f1.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        budget_amount=Decimal("10000.00"),
        branch="main",
    )
    await ce_service.create_cost_element(ce_f1_in, actor_id=actor_id)

    ce_f3_in = CostElementCreate(
        code="CE-F3",
        name="Cost Element F3",
        wbe_id=f3.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        budget_amount=Decimal("5000.00"),
        branch="main",
    )
    await ce_service.create_cost_element(ce_f3_in, actor_id=actor_id)

    # Get Gantt data
    service = GanttService(db_session)
    result = await service.get_gantt_data(
        project_id=project.project_id,
        branch="main",
        mode="merged",
    )

    # Assert all WBEs are present
    assert len(result.items) == 3

    # Find WBEs in result
    f1_item = next((item for item in result.items if item.wbe_code == "F1"), None)
    f2_item = next((item for item in result.items if item.wbe_code == "F2"), None)
    f3_item = next((item for item in result.items if item.wbe_code == "F3"), None)

    # Assert all WBEs are present
    assert f1_item is not None
    assert f2_item is not None
    assert f3_item is not None

    # F1 and F3 should have cost element data
    assert f1_item.cost_element_id is not None
    assert f1_item.cost_element_code == "CE-F1"
    assert f3_item.cost_element_id is not None
    assert f3_item.cost_element_code == "CE-F3"

    # F2 should NOT have cost element data (but WBE data should be present)
    assert f2_item.cost_element_id is None
    assert f2_item.cost_element_code is None
    assert f2_item.cost_element_name is None
    assert f2_item.wbe_id == f2.wbe_id
    assert f2_item.wbe_code == "F2"
    assert f2_item.wbe_name == "Fase 2"
    assert f2_item.parent_wbe_id == f1.wbe_id
