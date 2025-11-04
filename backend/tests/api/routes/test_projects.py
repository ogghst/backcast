import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.cost_element_type import create_random_cost_element_type
from tests.utils.project import create_random_project
from tests.utils.user import create_random_user
from tests.utils.wbe import create_random_wbe


def test_create_project(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a project."""
    # Create a user to be project manager
    pm_user = create_random_user(db)
    assert pm_user.id is not None

    data = {
        "project_name": "Test Project",
        "customer_name": "Test Customer",
        "contract_value": 100000.00,
        "start_date": str(date.today()),
        "planned_completion_date": str(date.today() + timedelta(days=365)),
        "project_manager_id": str(pm_user.id),
        "status": "active",
    }
    response = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["project_name"] == data["project_name"]
    assert content["customer_name"] == data["customer_name"]
    assert float(content["contract_value"]) == data["contract_value"]
    assert "project_id" in content
    assert content["project_manager_id"] == str(pm_user.id)


def test_read_project(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test reading a single project."""
    project = create_random_project(db)
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["project_name"] == project.project_name
    assert content["customer_name"] == project.customer_name
    assert content["project_id"] == str(project.project_id)


def test_read_project_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test reading a non-existent project."""
    response = client.get(
        f"{settings.API_V1_STR}/projects/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    content = response.json()
    assert content["detail"] == "Project not found"


def test_read_projects_list(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test reading list of projects."""
    create_random_project(db)
    create_random_project(db)
    response = client.get(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content["data"]) >= 2
    assert "count" in content
    assert content["count"] >= 2


def test_update_project(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating a project."""
    project = create_random_project(db)
    data = {"project_name": "Updated Project Name", "status": "completed"}
    response = client.put(
        f"{settings.API_V1_STR}/projects/{project.project_id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["project_name"] == data["project_name"]
    assert content["status"] == data["status"]
    assert content["project_id"] == str(project.project_id)


def test_update_project_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test updating a non-existent project."""
    data = {"project_name": "Updated Project Name"}
    response = client.put(
        f"{settings.API_V1_STR}/projects/{uuid.uuid4()}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 404
    content = response.json()
    assert content["detail"] == "Project not found"


def test_delete_project(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test deleting a project."""
    project = create_random_project(db)
    response = client.delete(
        f"{settings.API_V1_STR}/projects/{project.project_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Project deleted successfully"


def test_delete_project_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test deleting a non-existent project."""
    response = client.delete(
        f"{settings.API_V1_STR}/projects/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    content = response.json()
    assert content["detail"] == "Project not found"


def test_delete_project_with_wbes_should_fail(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test deleting a project with WBEs should be blocked."""
    project = create_random_project(db)
    # Create a WBE for this project
    create_random_wbe(db, project.project_id)

    response = client.delete(
        f"{settings.API_V1_STR}/projects/{project.project_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 400
    content = response.json()
    assert "Cannot delete project" in content["detail"]
    assert "existing WBE(s)" in content["detail"]

    # Verify project still exists
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.project_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200


def test_create_from_template_success(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a complete project structure from a template."""
    pm_user = create_random_user(db)
    cost_element_type = create_random_cost_element_type(db)

    template = {
        "project": {
            "project_name": "Template Project",
            "customer_name": "Template Customer",
            "contract_value": 500000.00,
            "start_date": str(date.today()),
            "planned_completion_date": str(date.today() + timedelta(days=365)),
            "project_manager_id": str(pm_user.id),
            "status": "active",
        },
        "wbes": [
            {
                "wbe": {
                    "machine_type": "Robotic Welding Station",
                    "serial_number": "RWS-001",
                    "contracted_delivery_date": str(date.today() + timedelta(days=180)),
                    "revenue_allocation": 200000.00,
                    "status": "designing",
                },
                "cost_elements": [
                    {
                        "department_code": "MECH",
                        "department_name": "Mechanical Engineering",
                        "cost_element_type_id": str(
                            cost_element_type.cost_element_type_id
                        ),
                        "budget_bac": 50000.00,
                        "revenue_plan": 60000.00,
                        "status": "planned",
                    },
                    {
                        "department_code": "ELEC",
                        "department_name": "Electrical Engineering",
                        "cost_element_type_id": str(
                            cost_element_type.cost_element_type_id
                        ),
                        "budget_bac": 40000.00,
                        "revenue_plan": 50000.00,
                        "status": "planned",
                    },
                ],
            },
            {
                "wbe": {
                    "machine_type": "Assembly Robot",
                    "serial_number": "ASM-001",
                    "contracted_delivery_date": str(date.today() + timedelta(days=240)),
                    "revenue_allocation": 300000.00,
                    "status": "designing",
                },
                "cost_elements": [
                    {
                        "department_code": "SOFT",
                        "department_name": "Software Development",
                        "cost_element_type_id": str(
                            cost_element_type.cost_element_type_id
                        ),
                        "budget_bac": 35000.00,
                        "revenue_plan": 42000.00,
                        "status": "planned",
                    }
                ],
            },
        ],
    }

    response = client.post(
        f"{settings.API_V1_STR}/projects/from-template",
        headers=superuser_token_headers,
        json=template,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["project_name"] == "Template Project"
    assert content["customer_name"] == "Template Customer"
    assert "project_id" in content


def test_create_from_template_invalid_project(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test template import with invalid project data."""
    template = {
        "project": {
            "project_name": "Invalid Project",
            # Missing required fields
        },
        "wbes": [],
    }

    response = client.post(
        f"{settings.API_V1_STR}/projects/from-template",
        headers=superuser_token_headers,
        json=template,
    )
    assert response.status_code in [400, 422]  # Validation error or bad request


def test_create_from_template_rollback_on_error(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test that template import rolls back on any error."""
    pm_user = create_random_user(db)

    # Create template with invalid cost_element_type_id to trigger rollback
    template = {
        "project": {
            "project_name": "Rollback Test Project",
            "customer_name": "Test Customer",
            "contract_value": 100000.00,
            "start_date": str(date.today()),
            "planned_completion_date": str(date.today() + timedelta(days=365)),
            "project_manager_id": str(pm_user.id),
            "status": "active",
        },
        "wbes": [
            {
                "wbe": {
                    "machine_type": "Test Machine",
                    "revenue_allocation": 50000.00,
                    "status": "designing",
                },
                "cost_elements": [
                    {
                        "department_code": "TEST",
                        "department_name": "Test Department",
                        "cost_element_type_id": str(uuid.uuid4()),  # Invalid type ID
                        "budget_bac": 10000.00,
                        "revenue_plan": 12000.00,
                        "status": "planned",
                    }
                ],
            }
        ],
    }

    response = client.post(
        f"{settings.API_V1_STR}/projects/from-template",
        headers=superuser_token_headers,
        json=template,
    )
    # Should fail and rollback
    assert response.status_code == 400
    content = response.json()
    assert "Failed to create project from template" in content["detail"]

    # Verify nothing was created (rollback occurred)
    response_list = client.get(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
    )
    projects = response_list.json()
    project_names = [p["project_name"] for p in projects["data"]]
    assert "Rollback Test Project" not in project_names
