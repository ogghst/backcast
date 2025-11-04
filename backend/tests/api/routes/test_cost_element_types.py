"""Tests for cost element types API."""
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import Department, DepartmentCreate
from tests.utils.cost_element_type import create_random_cost_element_type


def test_read_cost_element_types(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test reading list of active cost element types."""
    # Create some cost element types
    cet1 = create_random_cost_element_type(db)
    cet2 = create_random_cost_element_type(db)

    response = client.get(
        f"{settings.API_V1_STR}/cost-element-types/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert "data" in content
    assert "count" in content
    assert content["count"] >= 2

    # Verify the created types are in the response
    type_ids = [ce["cost_element_type_id"] for ce in content["data"]]
    assert str(cet1.cost_element_type_id) in type_ids
    assert str(cet2.cost_element_type_id) in type_ids

    # Verify all returned types are active
    for ce_type in content["data"]:
        assert ce_type["is_active"] is True


def test_read_cost_element_types_only_active(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test that only active cost element types are returned."""
    # Create active and inactive types
    active_type = create_random_cost_element_type(db)

    # Create an inactive type
    from app.models import CostElementType, CostElementTypeCreate

    inactive_cet = CostElementTypeCreate(
        type_code=f"inactive_{active_type.type_code}",
        type_name="Inactive Type",
        category_type="engineering_mechanical",
        display_order=99,
        is_active=False,
    )
    inactive_type = CostElementType.model_validate(inactive_cet)
    db.add(inactive_type)
    db.commit()
    db.refresh(inactive_type)

    response = client.get(
        f"{settings.API_V1_STR}/cost-element-types/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()

    # Verify inactive type is not in response
    type_ids = [ce["cost_element_type_id"] for ce in content["data"]]
    assert str(active_type.cost_element_type_id) in type_ids
    assert str(inactive_type.cost_element_type_id) not in type_ids


def test_read_cost_element_types_with_department(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test that cost element types include department info in response."""
    # Create a department
    dept_in = DepartmentCreate(
        department_code="TEST_API",
        department_name="Test API Department",
        description="Test department for API",
        is_active=True,
    )
    dept = Department.model_validate(dept_in)
    db.add(dept)
    db.commit()
    db.refresh(dept)

    # Create a cost element type with department
    from app.models import CostElementType, CostElementTypeCreate

    cet_in = CostElementTypeCreate(
        type_code=f"test_api_dept_{dept.department_code}",
        type_name="Test Type with Department API",
        category_type="software",
        tracks_hours=True,
        display_order=1,
        is_active=True,
    )
    cet = CostElementType.model_validate(cet_in)
    cet.department_id = dept.department_id
    db.add(cet)
    db.commit()
    db.refresh(cet)

    # Get cost element types via API
    response = client.get(
        f"{settings.API_V1_STR}/cost-element-types/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()

    # Find the created type in response
    found_type = None
    for ce_type in content["data"]:
        if ce_type["cost_element_type_id"] == str(cet.cost_element_type_id):
            found_type = ce_type
            break

    assert found_type is not None
    assert found_type["department_id"] == str(dept.department_id)
    assert found_type["department_code"] == "TEST_API"
    assert found_type["department_name"] == "Test API Department"
